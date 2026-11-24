import unittest
from unittest.mock import Mock, patch

from fastapi import Query
from fastapi.testclient import TestClient

from api.app import create_app
from controllers.http.dependencies import get_space_service
from api.main import app as entrypoint_app
from infrastructure.repositories.in_memory_space_repository import (
    InMemorySpaceRepository,
)
from models.domain.entities.space import Space


class ApiTests(unittest.TestCase):
    def test_asgi_entrypoint_exposes_health_route(self) -> None:
        with TestClient(entrypoint_app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": {"status": "ok"}})

    def test_health_route_returns_success_envelope(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": {"status": "ok"}})

    def test_spaces_route_uses_injected_repository(self) -> None:
        expected = Space(
            "s-test", "Sala de teste", "Sala", 10, "Bloco X", "Térreo",
            "Bloco X, Térreo", "disponivel", ("Projetor",), 20,
        )
        repository = InMemorySpaceRepository([expected])

        with TestClient(
            create_app(space_repository=repository, environment="test")
        ) as client:
            response = client.get("/spaces")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "data": [
                    {
                        "id": "s-test",
                        "name": "Sala de teste",
                        "type": "Sala",
                        "capacity": 10,
                        "building": "Bloco X",
                        "floor": "Térreo",
                        "location": "Bloco X, Térreo",
                        "status": "disponivel",
                        "resources": ["Projetor"],
                        "occupancy": 20,
                    }
                ]
            },
        )

    def test_http_errors_use_standard_envelope(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "not_found",
                    "message": "Not Found",
                    "details": None,
                }
            },
        )

    def test_validation_errors_use_standard_envelope(self) -> None:
        app = create_app(environment="test")

        @app.get("/validation-probe")
        def validation_probe(quantity: int = Query(ge=1)) -> dict[str, int]:
            return {"data": quantity}

        with TestClient(app) as client:
            response = client.get("/validation-probe?quantity=0")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "validation_error")
        self.assertEqual(response.json()["error"]["details"][0]["location"], ["query", "quantity"])

    def test_unhandled_errors_hide_internal_details(self) -> None:
        app = create_app(environment="test")

        def fail_service():
            raise RuntimeError("do-not-return-this-detail")

        app.dependency_overrides[get_space_service] = fail_service
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/spaces")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "internal_error",
                    "message": "Ocorreu um erro interno.",
                    "details": None,
                }
            },
        )
        self.assertNotIn("do-not-return-this-detail", response.text)

    def test_spaces_route_is_enabled_only_in_development_and_test(self) -> None:
        for environment in ("development", "test"):
            with self.subTest(environment=environment):
                with TestClient(create_app(environment=environment)) as client:
                    response = client.get("/spaces")
                self.assertEqual(response.status_code, 200)

    def test_spaces_route_is_hidden_outside_development_and_test(self) -> None:
        for environment in ("production", "staging"):
            with self.subTest(environment=environment):
                with patch("infrastructure.persistence.runtime.build_postgres_runtime"), TestClient(create_app(environment=environment, postgres_session_factory=Mock())) as client:
                    response = client.get("/spaces")
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_spaces_route_is_disabled_by_default(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("infrastructure.persistence.runtime.build_postgres_runtime"), TestClient(create_app(postgres_session_factory=Mock())) as client:
                response = client.get("/spaces")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
