import os
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx
from streamlit.testing.v1 import AppTest

from controllers.roomflow_api import ApiResponseError, ApiRuntime, ApiSessionExpired, ApiTimeout, ApiUnavailable, RoomFlowApi


URL = "http://127.0.0.1:8000"
PROJECT = Path(__file__).resolve().parents[1]


class ApiClientErrorsTests(unittest.TestCase):
    def setUp(self):
        self.api = RoomFlowApi(URL, lambda: "test-token")
        self.addCleanup(self.api._client.close)

    def test_connection_and_timeout_errors_are_distinct(self):
        for failure, expected in (
            (httpx.ConnectError("connection refused"), ApiUnavailable),
            (httpx.ReadTimeout("timed out"), ApiTimeout),
        ):
            with self.subTest(failure=type(failure).__name__):
                with patch.object(self.api._client, "request", side_effect=failure):
                    with self.assertRaises(expected) as raised:
                        self.api.request("GET", "/auth/me")
                    self.assertIs(type(raised.exception), expected)

    def test_http_status_is_retained_and_only_the_api_401_expires_a_session(self):
        cases = (
            (httpx.Response(401, json={"error": {"message": "Sessão inválida."}}), ApiSessionExpired),
            (httpx.Response(401, text="Proxy login"), ApiResponseError),
            (httpx.Response(500, json={"error": {}}), ApiResponseError),
            (httpx.Response(200, text="<html>Streamlit</html>"), ApiResponseError),
        )
        for response, expected in cases:
            with self.subTest(status=response.status_code, expected=expected):
                with patch.object(self.api._client, "request", return_value=response):
                    with self.assertRaises(expected) as raised:
                        self.api.request("GET", "/auth/me")
                    if expected is ApiResponseError:
                        self.assertIn(str(response.status_code), str(raised.exception))

    def test_connection_failure_keeps_token_and_api_401_clears_it_on_retry(self):
        unauthorized = httpx.Response(401, json={"error": {"message": "Sessão inválida."}})
        with (
            patch.dict(os.environ, {"ROOMFLOW_API_URL": URL}),
            patch("controllers.streamlit_runtime._get_api_runtime", return_value=ApiRuntime(self.api)),
            patch.object(self.api._client, "request", side_effect=[httpx.ConnectError("offline"), unauthorized]),
        ):
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "conta"
            app.session_state["auth_token"] = "test-token"
            app.run()
            self.assertFalse(app.exception)
            self.assertIn("conectar", app.error[0].value)
            self.assertEqual(app.session_state["auth_token"], "test-token")
            # A Streamlit interaction reruns the script from the top and rechecks the API.
            app.button(key="roomflow_api_retry").click().run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.session_state["auth_token"])
