import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from api.app import create_app
from application.services.authentication_service import AuthenticationService
from infrastructure.repositories.in_memory_session_repository import InMemorySessionRepository
from infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository
from infrastructure.security.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.entities.user_account import UserAccount


class MutableClock:
    def __init__(self) -> None:
        self.instant = datetime(2026, 11, 20, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.instant


def make_inactive_authentication_service(clock: MutableClock | None = None) -> AuthenticationService:
    hasher = Pbkdf2PasswordHasher()
    account = UserAccount(
        user=User(
            id="inactive-1",
            name="Conta Inativa",
            email="inativo@example.com",
            profile=Profile.REQUESTER,
            institution_id="inst-demo",
            status=UserStatus.INACTIVE,
        ),
        password_hash=hasher.hash_password("senha-correta"),
    )
    return AuthenticationService(
        users=InMemoryUserRepository([account]),
        sessions=InMemorySessionRepository(),
        password_hasher=hasher,
        clock=clock,
        session_lifetime=timedelta(minutes=1),
    )


class AuthenticationApiTests(unittest.TestCase):
    def test_valid_login_returns_opaque_token_and_server_user(self) -> None:
        with TestClient(create_app(environment="test")) as client:
            response = client.post(
                "/auth/login",
                json={"email": "admin@gmail.com", "password": "admin123"},
            )
            self.assertEqual(response.status_code, 200)
            body = response.json()["data"]
            token = body["access_token"]
            self.assertEqual(body["token_type"], "bearer")
            self.assertEqual(body["user"]["id"], "u1")
            self.assertEqual(body["user"]["profile"], "admin")
            self.assertEqual(body["user"]["institution_id"], "inst-demo")
            self.assertNotIn("password", str(body))

            me = client.get(
                "/auth/me?uid=u3",
                headers={"Authorization": f"Bearer {token}"},
            )

        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["data"]["id"], "u1")
        self.assertEqual(me.json()["data"]["profile"], "admin")

    def test_unknown_email_and_wrong_password_use_same_generic_error(self) -> None:
        with TestClient(create_app(environment="test")) as client:
            wrong_password = client.post(
                "/auth/login",
                json={"email": "admin@gmail.com", "password": "incorreta"},
            )
            unknown_email = client.post(
                "/auth/login",
                json={"email": "desconhecido@example.com", "password": "incorreta"},
            )

        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_email.status_code, 401)
        self.assertEqual(
            wrong_password.json()["error"]["message"],
            unknown_email.json()["error"]["message"],
        )
        self.assertEqual(wrong_password.json()["error"]["message"], "E-mail ou senha incorretos.")

    def test_inactive_account_uses_same_generic_error(self) -> None:
        app = create_app(
            environment="test",
            authentication_service=make_inactive_authentication_service(),
        )
        with TestClient(app) as client:
            response = client.post(
                "/auth/login",
                json={"email": "inativo@example.com", "password": "senha-correta"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["message"], "E-mail ou senha incorretos.")

    def test_expired_session_is_rejected(self) -> None:
        clock = MutableClock()
        hasher = Pbkdf2PasswordHasher()
        account = UserAccount(
            User("u-clock", "Relógio", "clock@example.com", Profile.REQUESTER, "inst-demo"),
            hasher.hash_password("senha"),
        )
        service = AuthenticationService(
            InMemoryUserRepository([account]),
            InMemorySessionRepository(),
            hasher,
            clock=clock,
            session_lifetime=timedelta(minutes=1),
        )
        app = create_app(environment="test", authentication_service=service)
        with TestClient(app) as client:
            login = client.post("/auth/login", json={"email": account.user.email, "password": "senha"})
            token = login.json()["data"]["access_token"]
            clock.instant += timedelta(minutes=2)
            response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "unauthorized")

    def test_logout_revokes_session(self) -> None:
        with TestClient(create_app(environment="test")) as client:
            login = client.post(
                "/auth/login",
                json={"email": "solicitante@gmail.com", "password": "solicitante123"},
            )
            token = login.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            logout = client.post("/auth/logout", headers=headers)
            after_logout = client.get("/auth/me", headers=headers)

        self.assertEqual(logout.status_code, 200)
        self.assertEqual(logout.json(), {"data": {"status": "logged_out"}})
        self.assertEqual(after_logout.status_code, 401)

    def test_local_login_attempts_are_limited(self) -> None:
        with TestClient(create_app(environment="test")) as client:
            responses = [
                client.post(
                    "/auth/login",
                    json={"email": "admin@gmail.com", "password": "incorreta"},
                )
                for _ in range(6)
            ]

        self.assertTrue(all(response.status_code == 401 for response in responses[:5]))
        self.assertEqual(responses[5].status_code, 429)
        self.assertEqual(responses[5].headers["retry-after"], "60")

    def test_production_does_not_enable_demo_credentials(self) -> None:
        with TestClient(create_app(environment="production")) as client:
            response = client.post(
                "/auth/login",
                json={"email": "admin@gmail.com", "password": "admin123"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["message"], "E-mail ou senha incorretos.")


class PasswordHasherTests(unittest.TestCase):
    def test_verifies_hexadecimal_hashes_used_by_the_database_seed(self) -> None:
        from controllers.password_service import hash_password

        encoded = hash_password("senha do seed")
        hasher = Pbkdf2PasswordHasher()
        self.assertTrue(hasher.verify_password("senha do seed", encoded))
        self.assertFalse(hasher.verify_password("outra senha", encoded))

    def test_rejects_malformed_password_hashes(self) -> None:
        hasher = Pbkdf2PasswordHasher()
        valid = hasher.hash_password("senha")
        scheme, _, salt, digest = valid.split("$")
        for encoded in (f"${valid}", f"{scheme}$0${salt}${digest}", f"{valid}!", f"{scheme}$310000$bad$bad"):
            with self.subTest(encoded=encoded):
                self.assertFalse(hasher.verify_password("senha", encoded))

    def test_each_password_hash_has_a_random_salt(self) -> None:
        hasher = Pbkdf2PasswordHasher()
        first = hasher.hash_password("senha")
        second = hasher.hash_password("senha")

        self.assertNotEqual(first, second)
        self.assertTrue(hasher.verify_password("senha", first))
        self.assertFalse(hasher.verify_password("outra", first))


if __name__ == "__main__":
    unittest.main()
