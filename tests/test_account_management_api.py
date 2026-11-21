import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient

from api.app import create_app
from models.domain.exceptions import LastActiveAdministrator
from models.domain.entities.user import UserStatus


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def institution_signup_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "responsible_name": "Responsável Exemplo",
        "responsible_email": "responsavel@exemplo.edu.br",
        "password": "senha-segura",
        "name": "Instituto Exemplo",
        "cnpj": "12.345.678/0001-95",
        "institution_type": "Instituto",
        "city": "Porto Velho",
        "state": "RO",
        "phone": "69999999999",
        "email": "contato@exemplo.edu.br",
    }
    payload.update(overrides)
    return payload


class AccountManagementApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client_context = TestClient(create_app(environment="test"))
        self.client = self.client_context.__enter__()
        self.admin_token = login(self.client, "admin@gmail.com", "admin123")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)

    def test_institution_signup_creates_active_institution_admin(self) -> None:
        response = self.client.post(
            "/institutions/signup", json=institution_signup_payload()
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["administrator"]["profile"], "admin")
        self.assertEqual(data["administrator"]["status"], "ativo")
        self.assertEqual(data["institution"]["cnpj"], "12345678000195")
        self.assertTrue(data["invitation_code"])

        owner_token = login(
            self.client, "responsavel@exemplo.edu.br", "senha-segura"
        )
        own_institution = self.client.get(
            "/institutions/me",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        self.assertEqual(own_institution.status_code, 200)
        self.assertEqual(own_institution.json()["data"]["id"], data["institution"]["id"])

    def test_institution_settings_load_update_and_persist_in_memory(self) -> None:
        initial = self.client.get("/institutions/me", headers=self.admin_headers)
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(initial.json()["data"]["id"], "inst-demo")
        self.assertEqual(initial.json()["data"]["preferences"]["reservations"]["min_advance"], 1)

        payload = {
            "name": "RoomFlow Campus Atualizado",
            "address": "Rua Central, 100",
            "city": "Cuiabá",
            "state": "mt",
            "email": "contato@campus.edu.br",
            "phone": "+55 65 3000-0000",
            "timezone": "America/Manaus",
            "preferences": {
                "reservations": {
                    "min_advance": 2,
                    "min_advance_unit": "horas",
                    "max_advance": 30,
                    "max_advance_unit": "dias",
                    "allowed_start": "08:00",
                    "allowed_end": "20:00",
                    "automatic_approval": "no_conflict",
                    "justification_required": False,
                },
                "conflicts": {
                    "resolution_criterion": "fifo",
                    "notification_timing": "one_hour",
                    "suggest_alternatives": False,
                },
                "notifications": {
                    "reservation_approved": True,
                    "reservation_rejected": False,
                    "conflict_detected": True,
                    "space_changed": False,
                    "reservation_cancelled": True,
                    "reservation_reminder": False,
                },
            },
        }
        updated = self.client.patch(
            "/institutions/me", headers=self.admin_headers, json=payload
        )
        reloaded = self.client.get("/institutions/me", headers=self.admin_headers)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(reloaded.status_code, 200)
        saved = reloaded.json()["data"]
        self.assertEqual(saved["name"], payload["name"])
        self.assertEqual(saved["state"], "MT")
        self.assertEqual(saved["timezone"], "America/Manaus")
        self.assertEqual(saved["preferences"], payload["preferences"])

    def test_institution_settings_reject_invalid_values(self) -> None:
        invalid_email = self.client.patch(
            "/institutions/me", headers=self.admin_headers,
            json={"name": "Instituição", "email": "email-invalido"},
        )
        invalid_hours = self.client.patch(
            "/institutions/me", headers=self.admin_headers,
            json={"name": "Instituição", "preferences": {
                "reservations": {
                    "min_advance": 1, "min_advance_unit": "dias",
                    "max_advance": 10, "max_advance_unit": "dias",
                    "allowed_start": "21:00", "allowed_end": "07:00",
                    "automatic_approval": "disabled", "justification_required": True,
                },
                "conflicts": {
                    "resolution_criterion": "manual", "notification_timing": "immediate",
                    "suggest_alternatives": True,
                },
                "notifications": {
                    "reservation_approved": True, "reservation_rejected": True,
                    "conflict_detected": True, "space_changed": True,
                    "reservation_cancelled": True, "reservation_reminder": True,
                },
            }},
        )
        self.assertEqual(invalid_email.status_code, 422)
        self.assertEqual(invalid_hours.status_code, 422)

    def test_only_admin_can_access_institution_settings(self) -> None:
        manager_token = login(self.client, "gerente@gmail.com", "gerente123")
        response = self.client.get(
            "/institutions/me", headers={"Authorization": f"Bearer {manager_token}"}
        )
        self.assertEqual(response.status_code, 403)

    def test_institution_settings_are_scoped_to_authenticated_admin(self) -> None:
        registered = self.client.post(
            "/institutions/signup",
            json=institution_signup_payload(
                responsible_email="second-owner@example.edu",
                name="Second Institution",
                cnpj="98.765.432/0001-10",
            ),
        )
        self.assertEqual(registered.status_code, 201)
        second_token = login(self.client, "second-owner@example.edu", "senha-segura")
        second_headers = {"Authorization": f"Bearer {second_token}"}
        second_id = registered.json()["data"]["institution"]["id"]
        original_name = self.client.get(
            "/institutions/me", headers=self.admin_headers
        ).json()["data"]["name"]

        changed = self.client.patch(
            "/institutions/me?institution_id=inst-demo",
            headers=second_headers,
            json={"name": "Second Institution Updated"},
        )
        second_own = self.client.get("/institutions/me", headers=second_headers)
        original_own = self.client.get("/institutions/me", headers=self.admin_headers)
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(second_own.json()["data"]["id"], second_id)
        self.assertEqual(original_own.json()["data"]["name"], original_name)

    def test_in_memory_registration_routes_are_local_only(self) -> None:
        with TestClient(create_app(environment="production")) as production_client:
            response = production_client.post(
                "/institutions/signup", json=institution_signup_payload()
            )

        self.assertEqual(response.status_code, 404)

    def test_duplicate_institution_cnpj_is_rejected(self) -> None:
        first = self.client.post(
            "/institutions/signup", json=institution_signup_payload()
        )
        duplicate = self.client.post(
            "/institutions/signup",
            json=institution_signup_payload(
                responsible_email="outra@exemplo.edu.br",
                name="Outro Nome de Instituição",
            ),
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)

    def test_admin_can_search_and_manage_users_in_own_institution(self) -> None:
        created = self.client.post(
            "/admin/users",
            headers=self.admin_headers,
            json={
                "name": "Pessoa Nova",
                "email": "pessoa.nova@example.edu.br",
                "password": "senha-segura",
                "profile": "solicitante",
            },
        )
        self.assertEqual(created.status_code, 201)
        user_id = created.json()["data"]["id"]

        search = self.client.get(
            "/admin/users?q=pessoa.nova",
            headers=self.admin_headers,
        )
        by_id = self.client.get(
            f"/admin/users/{user_id}", headers=self.admin_headers
        )
        update_role = self.client.patch(
            f"/admin/users/{user_id}/profile",
            headers=self.admin_headers,
            json={"profile": "gerente"},
        )

        self.assertEqual(search.status_code, 200)
        self.assertEqual([item["id"] for item in search.json()["data"]], [user_id])
        self.assertEqual(by_id.status_code, 200)
        self.assertEqual(update_role.json()["data"]["profile"], "gerente")

        deactivated = self.client.patch(
            f"/admin/users/{user_id}/status", headers=self.admin_headers,
            json={"status": "inativo"},
        )
        listed_inactive = self.client.get(
            "/admin/users?q=pessoa.nova", headers=self.admin_headers,
        )
        activated = self.client.patch(
            f"/admin/users/{user_id}/status", headers=self.admin_headers,
            json={"status": "ativo"},
        )
        self.assertEqual(deactivated.status_code, 200)
        self.assertEqual(listed_inactive.json()["data"][0]["status"], "inativo")
        self.assertEqual(activated.json()["data"]["status"], "ativo")

    def test_user_creation_requires_eight_character_password(self) -> None:
        short = self.client.post(
            "/admin/users", headers=self.admin_headers,
            json={"name": "Short Pass", "email": "short@example.edu", "password": "1234567"},
        )
        valid = self.client.post(
            "/admin/users", headers=self.admin_headers,
            json={"name": "Valid Pass", "email": "valid@example.edu", "password": "12345678"},
        )
        self.assertEqual(short.status_code, 422)
        self.assertEqual(valid.status_code, 201)

    def test_last_active_admin_cannot_be_demoted_or_deactivated(self) -> None:
        demote = self.client.patch(
            "/admin/users/u1/profile", headers=self.admin_headers,
            json={"profile": "gerente"},
        )
        deactivate = self.client.patch(
            "/admin/users/u1/status", headers=self.admin_headers,
            json={"status": "inativo"},
        )
        current = self.client.get("/admin/users/u1", headers=self.admin_headers)
        self.assertEqual(demote.status_code, 409)
        self.assertEqual(deactivate.status_code, 409)
        self.assertEqual(current.json()["data"]["profile"], "admin")
        self.assertEqual(current.json()["data"]["status"], "ativo")

    def test_admin_change_is_allowed_when_another_active_admin_remains(self) -> None:
        second = self.client.post(
            "/admin/users", headers=self.admin_headers,
            json={
                "name": "Second Admin", "email": "second.admin@example.edu",
                "password": "secure-password", "profile": "admin",
            },
        )
        second_id = second.json()["data"]["id"]
        demote_second = self.client.patch(
            f"/admin/users/{second_id}/profile", headers=self.admin_headers,
            json={"profile": "gerente"},
        )
        block_last = self.client.patch(
            "/admin/users/u1/status", headers=self.admin_headers,
            json={"status": "inativo"},
        )
        self.assertEqual(second.status_code, 201)
        self.assertEqual(demote_second.status_code, 200)
        self.assertEqual(block_last.status_code, 409)

    def test_concurrent_admin_deactivation_leaves_one_active_admin(self) -> None:
        self.client.post(
            "/admin/users", headers=self.admin_headers,
            json={
                "name": "Concurrent Admin", "email": "concurrent.admin@example.edu",
                "password": "secure-password", "profile": "admin",
            },
        )
        runtime = self.client_context.app.state.user_management_service
        admin = self.client_context.app.state.user_repository.find_by_email("admin@gmail.com").user
        second_admin = self.client_context.app.state.user_repository.find_by_email("concurrent.admin@example.edu").user

        def disable(actor):
            try:
                runtime.set_status(actor, actor.id, UserStatus.INACTIVE)
                return "disabled"
            except LastActiveAdministrator:
                return "blocked"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(as_completed([executor.submit(disable, admin), executor.submit(disable, second_admin)]))
            outcomes = [future.result() for future in results]
        active_admins = [
            account for account in self.client_context.app.state.user_repository.list_by_institution("inst-demo")
            if account.user.profile.value == "admin" and account.user.is_active
        ]
        self.assertCountEqual(outcomes, ["disabled", "blocked"])
        self.assertEqual(len(active_admins), 1)

    def test_duplicate_user_email_is_rejected(self) -> None:
        payload = {
            "name": "Pessoa Nova",
            "email": "pessoa.nova@example.edu.br",
            "password": "senha-segura",
        }
        first = self.client.post(
            "/admin/users", headers=self.admin_headers, json=payload
        )
        duplicate = self.client.post(
            "/admin/users", headers=self.admin_headers, json=payload
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(first.json()["data"]["profile"], "solicitante")

    def test_regular_account_cannot_assign_admin_profile(self) -> None:
        requester_token = login(
            self.client, "solicitante@gmail.com", "solicitante123"
        )
        response = self.client.post(
            "/admin/users",
            headers={"Authorization": f"Bearer {requester_token}"},
            json={
                "name": "Conta Tentativa",
                "email": "tentativa@example.edu.br",
                "password": "senha-segura",
                "profile": "admin",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")
        # Public member registration is intentionally absent pending profile and approval decisions.
        member_signup = self.client.post(
            "/auth/signup/member",
            json={"email": "tentativa@example.edu.br", "profile": "admin"},
        )
        self.assertEqual(member_signup.status_code, 404)

    def test_admin_cannot_list_or_access_other_institution_users(self) -> None:
        registration = self.client.post(
            "/institutions/signup",
            json=institution_signup_payload(
                responsible_email="admin.outro@exemplo.edu.br",
                name="Outra Instituição",
                cnpj="98.765.432/0001-10",
            ),
        )
        self.assertEqual(registration.status_code, 201)
        other_admin_id = registration.json()["data"]["administrator"]["id"]
        other_institution_id = registration.json()["data"]["institution"]["id"]

        forced_listing = self.client.get(
            f"/admin/users?institution_id={other_institution_id}",
            headers=self.admin_headers,
        )
        other_user = self.client.get(
            f"/admin/users/{other_admin_id}", headers=self.admin_headers
        )
        change_other_user = self.client.patch(
            f"/admin/users/{other_admin_id}/status",
            headers=self.admin_headers,
            json={"status": "inativo"},
        )

        self.assertEqual(forced_listing.status_code, 403)
        self.assertEqual(other_user.status_code, 403)
        self.assertEqual(change_other_user.status_code, 403)

    def test_deactivated_user_session_is_rejected_on_next_request(self) -> None:
        requester_token = login(
            self.client, "solicitante@gmail.com", "solicitante123"
        )
        response = self.client.patch(
            "/admin/users/u3/status",
            headers=self.admin_headers,
            json={"status": "inativo"},
        )
        next_request = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {requester_token}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "inativo")
        self.assertEqual(next_request.status_code, 401)


if __name__ == "__main__":
    unittest.main()
