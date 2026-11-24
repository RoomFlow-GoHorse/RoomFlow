import io
import secrets
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook
from streamlit.testing.v1 import AppTest

from controllers.streamlit_runtime import get_streamlit_runtime
from infrastructure.authentication_factory import build_application_runtime
from models.domain.entities.admin_audit_event import AdminAuditAction as Action
from models.domain.entities.user import UserStatus


SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"/>'
MAIN = Path(__file__).resolve().parents[1] / "main.py"
PASSWORD = "audit-test-password"


def excel(*registrations):
    workbook = Workbook()
    workbook.active.append(["RA"])
    for registration in registrations:
        workbook.active.append([registration])
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class AdminAuditServiceTests(unittest.TestCase):
    def setUp(self):
        self.runtime = build_application_runtime("test")
        self.admin = self.runtime.users.find_by_id("u1").user

    def test_rolls_back_data_and_history_when_append_fails(self):
        audit = self.runtime.admin_audit_repository
        original_append = audit.append

        def fail_after_append(event):
            original_append(event)
            raise OSError("audit unavailable")

        with patch.object(audit, "append", side_effect=fail_after_append):
            with self.assertRaises(OSError):
                self.runtime.space_management.create_building(self.admin, "Rollback building")
        self.assertFalse(any(
            item.name == "Rollback building" for item in self.runtime.space_management.list_buildings(self.admin)
        ))
        self.assertEqual(self.runtime.admin_audit.list_events(self.admin), [])

    def test_import_failure_rolls_back_whole_batch_and_allows_retry(self):
        service = self.runtime.enrollment_management
        preview = service.preview_import(self.admin, excel("RA-100", "RA-200"))
        audit = self.runtime.admin_audit_repository
        original_append = audit.append

        def fail_second(event):
            if audit.list_for_institution(self.admin.institution_id):
                raise OSError("audit unavailable")
            original_append(event)

        with patch.object(audit, "append", side_effect=fail_second):
            with self.assertRaises(OSError):
                service.confirm_import(self.admin, preview.preview_id)
        self.assertEqual(service.list_enrollments(self.admin), [])
        self.assertEqual(self.runtime.admin_audit.list_events(self.admin), [])
        self.assertEqual(service.confirm_import(self.admin, preview.preview_id), 2)
        events = self.runtime.admin_audit.list_events(self.admin, action=Action.ENROLLMENT_IMPORTED)
        self.assertEqual({event.resource_id for event in events}, {
            item.id for item in service.list_enrollments(self.admin)
        })

    def test_failed_status_change_preserves_original_session(self):
        user = self.runtime.user_management.create_user(self.admin, "Test user", "failure@example.edu", PASSWORD)
        session = self.runtime.authentication.login(user.email, PASSWORD)
        with patch.object(self.runtime.admin_audit_repository, "append", side_effect=OSError):
            with self.assertRaises(OSError):
                self.runtime.user_management.set_status(self.admin, user.id, UserStatus.INACTIVE)
        self.assertEqual(self.runtime.authentication.authenticate(session.access_token), user)

    def test_failed_plan_replacement_and_removal_preserve_file_and_history(self):
        floor = "b-1-f-1"
        service = self.runtime.floor_plan_management
        plan = service.upload(self.admin, floor, "before.svg", SVG)
        with patch.object(self.runtime.admin_audit_repository, "append", side_effect=OSError):
            with self.assertRaises(OSError):
                service.upload(self.admin, floor, "after.svg", SVG)
            with self.assertRaises(OSError):
                service.remove(self.admin, floor)
        with patch.object(self.runtime.plant_file_storage, "delete", side_effect=OSError):
            with self.assertRaises(OSError):
                service.remove(self.admin, floor)
        self.assertEqual(service.read_file(self.admin, floor), (plan, SVG))
        events = self.runtime.admin_audit.list_events(self.admin)
        self.assertEqual([event.action for event in events], [Action.FLOOR_PLAN_UPLOADED])


class AdminAuditStreamlitTests(unittest.TestCase):
    def setUp(self):
        get_streamlit_runtime.clear()
        self.addCleanup(get_streamlit_runtime.clear)

    def test_institution_signup_creates_admin_who_can_log_in(self):
        runtime = get_streamlit_runtime()
        app = AppTest.from_file(str(MAIN), default_timeout=20)
        app.query_params["page"] = "signup_institution"
        app.run()
        for key, value in {
            "nome": "New administrator", "email": "new-institution@example.edu",
            "senha": PASSWORD, "confirm_senha": PASSWORD,
        }.items():
            app.text_input(key=f"signup_inst_{key}").set_value(value)
        app.button(key="signup_inst_continue").click().run()
        app.text_input(key="signup_inst_instituicao").set_value("Streamlit institution")
        app.text_input(key="signup_inst_cnpj").set_value("99887766000155")
        app.selectbox(key="signup_inst_tipo_select").select("Universidade")
        app.button(key="signup_inst_submit").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["signup_inst_screen"], "success")
        token = runtime.authentication.login("new-institution@example.edu", PASSWORD)
        actor = runtime.authentication.authenticate(token.access_token)
        institution = runtime.institution_management.get_own(actor)
        self.assertEqual(institution.name, "Streamlit institution")
        self.assertEqual({event.action for event in runtime.admin_audit.list_events(actor)}, {
            Action.INSTITUTION_CREATED, Action.USER_CREATED,
        })

    def test_admin_can_create_and_assign_resources_in_streamlit(self):
        runtime = get_streamlit_runtime()
        actor = runtime.users.find_by_id("u1").user
        token = runtime.authentication.login("admin@gmail.com", "admin123")
        app = AppTest.from_file(str(MAIN), default_timeout=20)
        app.query_params["page"] = "planta_instituicao"
        app.session_state["auth_token"] = token.access_token
        app.run()
        self.assertEqual(len(app.exception), 0)
        next(item for item in app.text_input if item.label == "Nome do novo recurso").set_value("Recurso AppTest")
        next(item for item in app.button if item.label == "Cadastrar recurso").click().run()
        self.assertEqual(len(app.exception), 0)
        resource = runtime.resource_management.list_resources(actor, "Recurso AppTest")[0]
        room = next(item for item in app.selectbox if item.label == "Sala para associar recursos").value
        picker = next(item for item in app.multiselect if item.label == "Recursos da sala")
        picker.select(resource.id)
        next(item for item in app.button if item.label == "Salvar recursos da sala").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn(resource.id, runtime.space_management.get_space(actor, room).resource_ids)
        self.assertEqual(runtime.admin_audit.list_events(actor, action=Action.SPACE_RESOURCES_UPDATED)[0].resource_id, room)

    def test_history_filters_and_navigation_use_authenticated_services(self):
        runtime = get_streamlit_runtime()
        actor = runtime.users.find_by_id("u1").user
        suffix = secrets.token_hex(3)
        user = runtime.user_management.create_user(actor, f"New user {suffix}", f"{suffix}@example.edu", PASSWORD)
        runtime.user_management.set_status(actor, user.id, UserStatus.INACTIVE)
        token = runtime.authentication.login("admin@gmail.com", "admin123")
        app = AppTest.from_file(str(MAIN), default_timeout=20)
        app.query_params["page"] = "historico_admin"
        app.session_state["auth_token"] = token.access_token
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.dataframe[0].value), 2)
        app.selectbox(key="audit_action").select(Action.USER_DEACTIVATED).run()
        self.assertEqual(app.dataframe[0].value["Identificador do recurso"].tolist(), [user.id])
        app.selectbox(key="audit_actor").select("u2").run()
        self.assertEqual(len(app.dataframe), 0)

        manager = runtime.authentication.login("gerente@gmail.com", "gerente123")
        app.session_state["auth_token"] = manager.access_token
        app.query_params["page"] = "historico_admin"
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn(app.query_params["page"], ("gerente_dashboard", ["gerente_dashboard"]))
