import io
import secrets
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from openpyxl import Workbook
from streamlit.testing.v1 import AppTest

from api.app import create_app
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


class AdminAuditHttpTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(environment="test")
        self.client = self.enterContext(TestClient(self.app))
        self.admin = self.login("admin@gmail.com", "admin123")

    def login(self, email, password):
        result = self.client.post("/auth/login", json={"email": email, "password": password})
        self.assertEqual(result.status_code, 200, result.text)
        return {"Authorization": "Bearer " + result.json()["data"]["access_token"]}

    def request(self, method, path, status=200, **kwargs):
        result = self.client.request(method, path, headers=kwargs.pop("headers", self.admin), **kwargs)
        self.assertEqual(result.status_code, status, result.text)
        return result.json()["data"] if status < 400 and result.content else None

    def test_admin_workflow_records_successes_by_action_and_resource(self):
        expected = set()

        def record(action, item):
            expected.add((action.value, item["id"]))
            return item["id"]

        user = self.request("POST", "/admin/users", 201, json={
            "name": "Audit user", "email": "audit-user@example.edu", "password": PASSWORD,
        })
        uid = record(Action.USER_CREATED, user)
        user_path = f"/admin/users/{uid}"
        record(Action.USER_ACCOUNT_UPDATED, self.request("PATCH", user_path, json={
            "name": "Edited user", "email": "edited-user@example.edu",
        }))
        record(Action.USER_PROFILE_CHANGED, self.request("PATCH", user_path + "/profile", json={"profile": "gerente"}))
        user_session = self.login("edited-user@example.edu", PASSWORD)
        record(Action.USER_DEACTIVATED, self.request("PATCH", user_path + "/status", json={"status": "inativo"}))
        record(Action.USER_ACTIVATED, self.request("PATCH", user_path + "/status", json={"status": "ativo"}))
        self.assertEqual(self.client.get("/auth/me", headers=user_session).status_code, 401)

        code_path = "/institutions/me/invitation-code"
        first = self.request("POST", code_path + "/rotate")["code"]
        self.request("DELETE", code_path)
        second = self.request("POST", code_path + "/rotate")["code"]
        self.request("DELETE", code_path)
        self.request("DELETE", code_path)

        enrollment_path = "/admin/enrollments"
        enrollment = self.request("POST", enrollment_path, 201, json={"registration_number": "RA-SECRET"})
        enrollment_id = record(Action.ENROLLMENT_CREATED, enrollment)
        record(Action.ENROLLMENT_DEACTIVATED, self.request("DELETE", f"{enrollment_path}/{enrollment_id}"))
        preview = self.request("POST", enrollment_path + "/import/preview", files={
            "file": ("enrollments.xlsx", excel("RA-IMPORT")),
        })
        self.request("POST", enrollment_path + "/import/confirm", json={"preview_id": preview["preview_id"]})
        record(Action.ENROLLMENT_IMPORTED, self.request("GET", enrollment_path, params={"q": "RA-IMPORT"})[0])
        record(Action.INSTITUTION_SETTINGS_UPDATED, self.request("PATCH", "/institutions/me", json={"name": "Updated institution"}))

        building = record(Action.BUILDING_CREATED, self.request("POST", "/structure/buildings", 201, json={"name": "Building Audit"}))
        building_path = f"/structure/buildings/{building}"
        record(Action.BUILDING_UPDATED, self.request("PATCH", building_path, json={"name": "Building Edited"}))
        floor = record(Action.FLOOR_CREATED, self.request("POST", building_path + "/floors", 201, json={"name": "First"}))
        floor_path = f"/structure/floors/{floor}"
        record(Action.FLOOR_UPDATED, self.request("PATCH", floor_path, json={"name": "Second"}))
        room = record(Action.SPACE_CREATED, self.request("POST", "/structure/spaces", 201, json={
            "floor_id": floor, "name": "Audit room", "type": "Sala de aula", "capacity": 16,
        }))
        room_path = f"/structure/spaces/{room}"
        record(Action.SPACE_UPDATED, self.request("PATCH", room_path, json={"capacity": 18}))
        resource = record(Action.RESOURCE_CREATED, self.request("POST", "/structure/resources", 201, json={"name": "Audit resource"}))
        resource_path = f"/structure/resources/{resource}"
        record(Action.RESOURCE_UPDATED, self.request("PATCH", resource_path, json={"name": "Edited resource"}))
        record(Action.SPACE_RESOURCES_UPDATED, self.request("PUT", room_path + "/resources", json={"resource_ids": [resource]}))
        record(Action.RESOURCE_DEACTIVATED, self.request("PATCH", resource_path + "/status", json={"active": False}))

        plan_path = floor_path + "/plan"
        upload = record(Action.FLOOR_PLAN_UPLOADED, self.request("POST", plan_path, files={"file": ("audit.svg", SVG)}))
        position_path = floor_path + f"/positions/{room}"
        self.request("PUT", position_path, json={"x": 25, "y": 40})
        expected.add((Action.FLOOR_PLAN_POSITION_SET.value, room))
        record(Action.FLOOR_PLAN_REPLACED, self.request("POST", plan_path, files={"file": ("replacement.svg", SVG)}))
        self.request("DELETE", position_path)
        expected.add((Action.FLOOR_PLAN_POSITION_REMOVED.value, room))
        self.request("DELETE", plan_path, 204)
        expected.add((Action.FLOOR_PLAN_REMOVED.value, upload))
        record(Action.SPACE_DEACTIVATED, self.request("PATCH", room_path, json={"status": "inativo"}))
        record(Action.FLOOR_DEACTIVATED, self.request("PATCH", floor_path + "/status", json={"active": False}))
        record(Action.BUILDING_DEACTIVATED, self.request("PATCH", building_path + "/status", json={"active": False}))

        events = self.request("GET", "/admin/audit")
        self.assertEqual(
            {(event["action"], event["resource_id"]) for event in events if "invitation_code" not in event["action"]},
            expected,
        )
        self.assertEqual({event["actor_user_id"] for event in events}, {"u1"})
        self.assertEqual({event["institution_id"] for event in events}, {"inst-demo"})
        self.assertEqual([event["action"] for event in events if "invitation_code" in event["action"]], [
            Action.INVITATION_CODE_REVOKED.value, Action.INVITATION_CODE_GENERATED.value,
            Action.INVITATION_CODE_REVOKED.value, Action.INVITATION_CODE_REPLACED.value,
        ])
        for secret in (first, second, PASSWORD, "RA-SECRET", "RA-IMPORT", "audit.svg"):
            self.assertNotIn(secret, str(events))

    def test_filters_permissions_isolation_and_rejected_mutations(self):
        path = "/admin/audit"
        self.assertEqual(self.client.get(path).status_code, 401)
        manager = self.login("gerente@gmail.com", "gerente123")
        self.request("GET", path, 403, headers=manager)
        self.request("POST", "/admin/users", 422, json={"name": "Invalid"})
        self.request("PATCH", "/admin/users/u1/status", 409, json={"status": "inativo"})
        self.request("POST", "/structure/floors/b-1-f-1/plan", 422, files={"file": ("invalid.png", b"invalid")})
        self.assertEqual(self.request("GET", path), [])

        self.request("POST", "/structure/resources", 201, headers=manager, json={"name": "Manager resource"})
        building = self.request("POST", "/structure/buildings", 201, json={"name": "Scoped building"})
        self.request("POST", "/institutions/signup", 201, json={
            "responsible_name": "Other admin", "responsible_email": "other-audit@example.edu",
            "password": PASSWORD, "name": "Other institution", "cnpj": "99887766000155",
            "institution_type": "Universidade",
        })
        other = self.login("other-audit@example.edu", PASSWORD)
        scoped = self.request("GET", path, headers=other, params={"institution_id": "inst-demo"})
        self.assertTrue(scoped)
        self.assertTrue(all(event["institution_id"] != "inst-demo" for event in scoped))
        self.request("PATCH", f"/structure/buildings/{building['id']}", 404, headers=other, json={"name": "Rejected"})
        self.assertEqual(self.request("GET", path, headers=other), scoped)

        events = self.request("GET", path)
        self.assertEqual(len(events), 2)
        selected = self.request("GET", path, params={"action": "building.created", "actor_user_id": "u1"})
        self.assertEqual([event["resource_id"] for event in selected], [building["id"]])
        self.assertEqual(len(self.request("GET", path, params={"actor_user_id": "u2"})), 1)
        timestamp = datetime.fromisoformat(selected[0]["occurred_at"])
        offset = timezone(timedelta(hours=-4))
        self.assertEqual(self.request("GET", path, params={
            "start_at": timestamp.astimezone(offset).isoformat(), "end_at": timestamp.isoformat(),
        }), selected)
        self.assertEqual(self.request("GET", path, params={"start_at": (timestamp + timedelta(days=1)).isoformat()}), [])
        self.request("GET", path, 422, params={"start_at": "2026-01-01T00:00:00"})
        self.request("GET", path, 422, params={"start_at": "2026-02-01T00:00:00Z", "end_at": "2026-01-01T00:00:00Z"})


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
