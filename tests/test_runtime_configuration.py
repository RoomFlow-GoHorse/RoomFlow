import os
import unittest
from unittest.mock import Mock, patch

from config.runtime import persistence_mode
from controllers.local_runtime import LocalRuntime
from controllers.runtime_errors import RuntimeUnavailable
from controllers import streamlit_runtime


class RuntimeConfigurationTests(unittest.TestCase):
    def test_production_defaults_to_postgres(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(persistence_mode(), "postgres")

    def test_production_cannot_select_memory_or_unknown_backend(self):
        for mode in ("memory", "postgre", ""):
            with self.subTest(mode=mode), patch.dict(os.environ, {"ROOMFLOW_PERSISTENCE": mode}, clear=True):
                with self.assertRaises(ValueError):
                    persistence_mode()

    def test_memory_requires_explicit_local_environment(self):
        for environment in ("test", "development"):
            with patch.dict(os.environ, {"APP_ENV": environment}, clear=True):
                self.assertEqual(persistence_mode(), "postgres")
                os.environ["ROOMFLOW_PERSISTENCE"] = "memory"
                self.assertEqual(persistence_mode(), "memory")

    def test_streamlit_without_external_api_uses_postgres_in_production(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(streamlit_runtime, "_get_postgres_runtime") as postgres, patch.object(streamlit_runtime, "_get_local_runtime") as memory:
            self.assertIs(streamlit_runtime.get_streamlit_runtime()._services, postgres.return_value)
            self.assertTrue(streamlit_runtime.uses_persistent_runtime())
            memory.assert_not_called()

    def test_failed_postgres_does_not_fall_back_to_memory(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(streamlit_runtime, "_get_postgres_runtime", side_effect=RuntimeUnavailable("offline")), patch.object(streamlit_runtime, "_get_local_runtime") as memory:
            with self.assertRaises(RuntimeUnavailable):
                streamlit_runtime.get_streamlit_runtime()
            memory.assert_not_called()

    def test_obsolete_api_url_does_not_enable_http(self):
        with patch.dict(os.environ, {"ROOMFLOW_API_URL": "https://unused.invalid"}, clear=True), patch.object(streamlit_runtime, "_get_postgres_runtime") as postgres:
            self.assertIs(streamlit_runtime.get_streamlit_runtime()._services, postgres.return_value)

    def test_local_controllers_resolve_identity_for_every_action(self):
        services = Mock()
        token = "first-session"
        runtime = LocalRuntime(services, lambda: token)
        runtime.user_management.list_users(Mock())
        first = services.authentication.authenticate.return_value
        services.user_management.list_users.assert_called_once_with(first)
        token = "second-session"
        runtime.notifications.unread_count()
        services.authentication.authenticate.assert_called_with("second-session")

    def test_database_error_is_sanitized(self):
        from sqlalchemy.exc import OperationalError
        services = Mock()
        services.authentication.login.side_effect = OperationalError("private SQL", {}, Exception("private host"))
        runtime = LocalRuntime(services, lambda: None)
        with self.assertRaises(RuntimeUnavailable) as error:
            runtime.authentication.login("user", "password")
        self.assertNotIn("private", str(error.exception))

    def test_email_failure_has_a_safe_message(self):
        from application.ports.email_sender import EmailDeliveryUnavailable
        services = Mock()
        services.password_recovery.request.side_effect = EmailDeliveryUnavailable("private SMTP details")
        runtime = LocalRuntime(services, lambda: None)
        with self.assertRaises(RuntimeUnavailable) as error:
            runtime.password_recovery.request("user@example.test")
        self.assertNotIn("private", str(error.exception))
        self.assertIn("SMTP", str(error.exception))
