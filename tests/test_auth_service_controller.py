import unittest
from unittest.mock import Mock, patch

from application.services.authentication_service import InvalidCredentials
from controllers import auth_service


class AuthServiceControllerTests(unittest.TestCase):
    def test_invalid_credentials_are_returned_as_a_login_error(self):
        runtime = Mock()
        runtime.authentication.login.side_effect = InvalidCredentials()
        with patch.object(auth_service, "get_streamlit_runtime", return_value=runtime):
            user, error = auth_service.login("person@example.test", "wrong-password")
        self.assertIsNone(user)
        self.assertIn("E-mail ou senha", error)

    def test_stale_streamlit_exception_class_is_also_handled(self):
        stale_invalid_credentials = type(
            "InvalidCredentials", (Exception,),
            {"__module__": InvalidCredentials.__module__},
        )
        runtime = Mock()
        runtime.authentication.login.side_effect = stale_invalid_credentials()
        with patch.object(auth_service, "get_streamlit_runtime", return_value=runtime):
            user, error = auth_service.login("person@example.test", "wrong-password")
        self.assertIsNone(user)
        self.assertIn("E-mail ou senha", error)

    def test_unrelated_runtime_errors_are_not_hidden_as_bad_passwords(self):
        runtime = Mock()
        runtime.authentication.login.side_effect = RuntimeError("database setup defect")
        with patch.object(auth_service, "get_streamlit_runtime", return_value=runtime):
            with self.assertRaisesRegex(RuntimeError, "database setup defect"):
                auth_service.login("person@example.test", "wrong-password")


if __name__ == "__main__":
    unittest.main()
