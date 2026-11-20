import unittest

from fastapi.testclient import TestClient

from api.app import create_app


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

        owner_token = login(
            self.client, "responsavel@exemplo.edu.br", "senha-segura"
        )
        own_institution = self.client.get(
            "/institutions/me",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        self.assertEqual(own_institution.status_code, 200)
        self.assertEqual(own_institution.json()["data"]["id"], data["institution"]["id"])

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
