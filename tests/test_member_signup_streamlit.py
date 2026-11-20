import secrets
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

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
        login = runtime.authentication.login("admin@gmail.com", "admin123", "streamlit-admin-page")
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "main.py"))
        app.query_params["page"] = "usuarios"
        app.session_state["auth_token"] = login.access_token
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any(tab.label == "Codigos e matriculas" for tab in app.tabs))

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
        app.session_state["signup_member_screen"] = "confirm"
        app.session_state["signup_member_nome"] = "Streamlit Student"
        app.session_state["signup_member_email"] = email
        app.session_state["signup_member_ra"] = registration_number
        app.session_state["signup_member_codigo_institucional"] = code
        app.session_state["signup_member_attempt_key"] = secrets.token_urlsafe(12)
        app.session_state["signup_member_senha"] = "streamlit-password-123"
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)

        app.button(key="signup_member_confirm_institution").click().run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["signup_member_screen"], "email_pending")
        sent = runtime.simulated_email_sender.latest_for(email)
        self.assertIsNotNone(sent)

        app.button(key="signup_member_verify_email").click().run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["signup_member_screen"], "success")
        self.assertIsNotNone(runtime.users.find_by_email(email))


if __name__ == "__main__":
    unittest.main()
