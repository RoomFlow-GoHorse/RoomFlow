import secrets
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from application.services.institution_management_service import InstitutionUpdate
from controllers.streamlit_runtime import get_streamlit_runtime
from models.domain.entities.authorized_enrollment import AuthorizedEnrollment


class MemberSignupStreamlitTests(unittest.TestCase):
    def test_streamlit_login_and_logout_use_backend_session(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "main.py"))
        app.query_params["page"] = "login"
        app.session_state["login_email"] = "participante@gmail.com"
        app.session_state["login_password"] = "participante123"
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        app.button(key="login_submit").click().run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.session_state["auth_token"])
        app.button(key="rf_logout").click().run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertIsNone(app.session_state["auth_token"])

    def test_streamlit_admin_user_page_renders_with_authenticated_identity(self):
        runtime = get_streamlit_runtime()
        admin = runtime.users.find_by_email("admin@gmail.com").user
        member_email = f"streamlit-admin-list-{secrets.token_hex(4)}@example.edu"
        runtime.user_management.create_user(
            admin, "Backend Listed User", member_email, "secure-password"
        )
        login = runtime.authentication.login("admin@gmail.com", "admin123", "streamlit-admin-page")
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "main.py"))
        app.query_params["page"] = "usuarios"
        app.session_state["auth_token"] = login.access_token
        app.session_state["users_search"] = member_email
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any(tab.label == "Codigos e matriculas" for tab in app.tabs))
        user_selector = next(item for item in app.selectbox if item.key == "managed_user_select")
        self.assertTrue(any(member_email in option for option in user_selector.options))

    def test_streamlit_institution_settings_load_and_save_backend_data(self):
        runtime = get_streamlit_runtime()
        admin = runtime.users.find_by_email("admin@gmail.com").user
        login = runtime.authentication.login("admin@gmail.com", "admin123", "streamlit-settings")
        original = runtime.institution_management.get_own(admin)
        updated_name = f"Configuração salva {secrets.token_hex(3)}"

        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "main.py"))
        app.query_params["page"] = "configuracoes_instituicao"
        app.session_state["auth_token"] = login.access_token
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.text_input(key="cfg_nome").value, original.name)
        app.text_input(key="cfg_nome").set_value(updated_name)
        app.button(key="cfg_salvar").click().run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(runtime.institution_management.get_own(admin).name, updated_name)

        reopened = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "main.py"))
        reopened.query_params["page"] = "configuracoes_instituicao"
        reopened.session_state["auth_token"] = login.access_token
        reopened.run(timeout=15)
        self.assertEqual(len(reopened.exception), 0)
        self.assertEqual(reopened.text_input(key="cfg_nome").value, updated_name)

        runtime.institution_management.update_own(
            admin,
            InstitutionUpdate(
                name=original.name,
                institution_type=original.institution_type,
                city=original.city,
                state=original.state,
                phone=original.phone,
                email=original.email,
                address=original.address,
                timezone=original.timezone,
                preferences=original.preferences,
            ),
        )

    def test_streamlit_page_completes_simulated_email_confirmation(self):
        runtime = get_streamlit_runtime()
        admin = runtime.users.find_by_email("admin@gmail.com").user
        registration_number = f"UI-{secrets.token_hex(5)}"
        email = f"ui-{secrets.token_hex(5)}@example.edu"
        code, _ = runtime.invite_codes.issue_or_replace(admin)
        runtime.authorized_enrollments.add(AuthorizedEnrollment(
            id=f"ui-{secrets.token_urlsafe(8)}",
            institution_id=admin.institution_id,
            registration_number=registration_number,
            name="Streamlit Student",
            email=email,
        ))

        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "main.py"))
        app.query_params["page"] = "signup_member"
        app.run(timeout=15)
        values = {
            "nome": "Streamlit Student",
            "email": email,
            "ra": registration_number,
            "codigo_institucional": code,
            "senha": "streamlit-password-123",
            "confirm_senha": "streamlit-password-123",
        }
        for field, value in values.items():
            app.text_input(key=f"signup_member_{field}").set_value(value)
        app.button(key="signup_member_submit").click().run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["signup_member_screen"], "confirm")

        app.button(key="signup_member_confirm_institution").click().run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["signup_member_screen"], "email_pending")
        sent = runtime.simulated_email_sender.latest_for(email)
        self.assertIsNotNone(sent)

        app.button(key="signup_member_verify_email").click().run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["signup_member_screen"], "success")
        self.assertIsNotNone(runtime.users.find_by_email(email))
        app.button(key="signup_member_login").click().run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertIn(app.query_params["page"], ("login", ["login"]))


if __name__ == "__main__":
    unittest.main()
