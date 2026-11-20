import unittest
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from api.app import create_app
from infrastructure.repositories.in_memory_authorized_enrollment_repository import (
    InMemoryAuthorizedEnrollmentRepository,
)
from models.domain.entities.authorized_enrollment import AuthorizedEnrollment
from models.domain.exceptions import ResourceNotFound
from concurrent.futures import as_completed


def token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def workbook_bytes(rows: list[tuple[object, ...]], headers: tuple[str, ...] = ("Matrícula", "Nome", "E-mail")) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


class InstitutionEnrollmentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client_context = TestClient(create_app(environment="test"))
        self.client = self.client_context.__enter__()
        self.admin_token = token_for(self.client, "admin@gmail.com", "admin123")
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)

    def _rotate_code(self) -> str:
        response = self.client.post(
            "/institutions/me/invitation-code/rotate", headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["code"]

    def test_admin_code_is_revealed_on_issue_and_old_code_is_revoked(self) -> None:
        first = self._rotate_code()
        second = self._rotate_code()
        self.assertNotEqual(first, second)
        self.assertEqual(
            self.client.get(
                "/institutions/me/invitation-code", headers=self.headers
            ).json()["data"]["active"],
            True,
        )
        self.client.post("/admin/enrollments", headers=self.headers, json={"registration_number": "A123"})
        preview_old = self.client.post(
            "/auth/signup/member/preview",
            json={"name": "Ana", "email": "ana@example.edu", "registration_number": "A123", "institutional_code": first},
        )
        preview_new = self.client.post(
            "/auth/signup/member/preview",
            json={"name": "Ana", "email": "ana@example.edu", "registration_number": "A123", "institutional_code": second},
        )
        self.assertEqual(preview_old.status_code, 400)
        self.assertEqual(preview_new.status_code, 200)
        self.assertEqual(preview_new.json()["data"]["institution_name"], "Instituição de Demonstração")
        # Rotation does not alter an already-created account or its login session.
        self.assertEqual(self.client.get("/auth/me", headers=self.headers).status_code, 200)

    def test_invitation_code_is_scoped_and_not_available_by_other_tenant_id(self) -> None:
        response = self.client.get(
            "/institutions/me/invitation-code?institution_id=other-institution",
            headers=self.headers,
        )
        by_tenant_path = self.client.get(
            "/institutions/other-institution/invitation-code", headers=self.headers
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(by_tenant_path.status_code, 404)

    def test_enrollment_listing_rejects_another_institution_scope(self) -> None:
        response = self.client.get(
            "/admin/enrollments?institution_id=another-institution",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_manual_enrollment_is_unique_per_institution(self) -> None:
        payload = {"registration_number": "RA 9001", "name": "Aluno Teste", "email": "aluno@example.edu"}
        first = self.client.post("/admin/enrollments", headers=self.headers, json=payload)
        duplicate = self.client.post("/admin/enrollments", headers=self.headers, json={**payload, "registration_number": "RA9001"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)

        other_inst = self.client.post(
            "/institutions/signup",
            json={
                "responsible_name": "Admin B", "responsible_email": "adminb@example.edu", "password": "senha-segura",
                "name": "Instituição B", "cnpj": "98765432000110", "institution_type": "Instituto",
            },
        )
        token_b = token_for(self.client, "adminb@example.edu", "senha-segura")
        same_number_other_inst = self.client.post(
            "/admin/enrollments",
            headers={"Authorization": f"Bearer {token_b}"},
            json=payload,
        )
        self.assertEqual(other_inst.status_code, 201)
        self.assertEqual(same_number_other_inst.status_code, 201)

    def test_import_preview_separates_valid_duplicate_and_invalid_rows(self) -> None:
        self.client.post("/admin/enrollments", headers=self.headers, json={"registration_number": "KNOWN"})
        content = workbook_bytes([
            ("NEW-1", "New Student", "new@example.edu"),
            ("KNOWN", "Existing", None),
            ("NEW-1", "Duplicate In Sheet", None),
            (None, "Missing RA", "bad@example.edu"),
            ("NEW-2", "Bad Email", "not-an-email"),
        ])
        response = self.client.post(
            "/admin/enrollments/import/preview",
            headers=self.headers,
            files={"file": ("roster.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["counts"], {"valid": 1, "duplicates": 2, "invalid": 2})

        confirmed = self.client.post(
            "/admin/enrollments/import/confirm",
            headers=self.headers,
            json={"preview_id": data["preview_id"]},
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["data"]["imported"], 1)
        self.assertEqual(
            self.client.get("/admin/enrollments?q=NEW-1", headers=self.headers).json()["data"][0]["registration_number"],
            "NEW-1",
        )

    def test_import_confirmation_rejects_whole_batch_if_data_changed(self) -> None:
        content = workbook_bytes([("RACE", "Race Student", None), ("SAFE", "Safe Student", None)])
        preview = self.client.post(
            "/admin/enrollments/import/preview",
            headers=self.headers,
            files={"file": ("roster.xlsx", content)},
        ).json()["data"]
        self.client.post("/admin/enrollments", headers=self.headers, json={"registration_number": "RACE"})
        response = self.client.post(
            "/admin/enrollments/import/confirm",
            headers=self.headers,
            json={"preview_id": preview["preview_id"]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get("/admin/enrollments?q=SAFE", headers=self.headers).json()["data"], [])

    def test_enrollment_search_filter_deactivation_and_tenant_scope(self) -> None:
        created = self.client.post(
            "/admin/enrollments", headers=self.headers,
            json={"registration_number": "RA-22", "name": "Nome Aluno"},
        ).json()["data"]
        filtered = self.client.get("/admin/enrollments?q=nome&status=ativo", headers=self.headers)
        deactivated = self.client.delete(f"/admin/enrollments/{created['id']}", headers=self.headers)
        filtered_after = self.client.get("/admin/enrollments?status=inativo", headers=self.headers)
        self.assertEqual(len(filtered.json()["data"]), 1)
        self.assertEqual(deactivated.json()["data"]["status"], "inativo")
        self.assertEqual(len(filtered_after.json()["data"]), 1)

    def test_member_preview_hides_enrollment_existence_and_confirms_institution(self) -> None:
        code = self._rotate_code()
        self.client.post(
            "/admin/enrollments", headers=self.headers,
            json={"registration_number": "AUTHORIZED", "name": "Maria Silva", "email": "maria@example.edu"},
        )
        valid = self.client.post(
            "/auth/signup/member/preview",
            json={"name": "maria silva", "email": "MARIA@example.edu", "registration_number": "AUTHORIZED", "institutional_code": code},
        )
        invalid = self.client.post(
            "/auth/signup/member/preview",
            json={"name": "Outra Pessoa", "email": "other@example.edu", "registration_number": "MISSING", "institutional_code": code},
        )
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()["data"]["institution_name"], "Instituição de Demonstração")
        self.assertEqual(invalid.status_code, 400)
        member_cannot_assign_profile = self.client.post(
            "/auth/signup/member/preview",
            json={
                "name": "Maria Silva",
                "email": "maria@example.edu",
                "registration_number": "AUTHORIZED",
                "institutional_code": code,
                "profile": "admin",
                "institution_id": "other-institution",
            },
        )
        self.assertEqual(member_cannot_assign_profile.status_code, 422)
        # Public request cannot pick an institution or profile.
        self.assertEqual(
            self.client.post("/auth/signup/member/start", json={
                "name": "Maria Silva", "email": "maria@example.edu", "registration_number": "AUTHORIZED",
                "institutional_code": code, "password": "password-123", "profile": "admin",
            }).status_code,
            422,
        )
        still_available = self.client.get(
            "/admin/enrollments?q=AUTHORIZED",
            headers=self.headers,
        )
        self.assertEqual(still_available.status_code, 200)
        self.assertEqual(still_available.json()["data"][0]["status"], "ativo")

    def _start_signup(self, registration_number="RA-NEW", email="student@example.edu"):
        code = self._rotate_code()
        self.client.post("/admin/enrollments", headers=self.headers, json={
            "registration_number": registration_number,
            "name": "Test Student", "email": email,
        })
        payload = {
            "name": "Test Student", "email": email,
            "registration_number": registration_number,
            "institutional_code": code, "password": "secure-password-123",
        }
        response = self.client.post("/auth/signup/member/start", json=payload)
        return response, self.client_context.app.state.simulated_email_sender.latest_for(email)

    def test_email_verified_signup_creates_participant_and_consumes_ra_once(self):
        started, email = self._start_signup()
        self.assertEqual(started.status_code, 202)
        self.assertNotIn("token", started.text.lower())
        self.assertEqual(started.json()["data"]["institution_name"], "Institui\u00e7\u00e3o de Demonstra\u00e7\u00e3o")
        self.assertIsNotNone(email)

        complete = self.client.post("/auth/signup/member/verify-email", json={"token": email.verification_token})
        self.assertEqual(complete.status_code, 200)
        data = complete.json()["data"]
        self.assertEqual(data["profile"], "participante")
        self.assertEqual(data["institution_id"], "inst-demo")
        self.assertEqual(data["status"], "ativo")
        self.assertEqual(self.client.post("/auth/login", json={
            "email": "student@example.edu", "password": "secure-password-123",
        }).status_code, 200)
        self.assertEqual(self.client.get("/admin/enrollments?q=RA-NEW", headers=self.headers).json()["data"][0]["status"], "utilizado")
        self.assertEqual(self.client.post("/auth/signup/member/verify-email", json={"token": email.verification_token}).status_code, 400)
        self.assertEqual(self.client.post("/auth/signup/member/start", json={
            "name": "Test Student", "email": "another@example.edu", "registration_number": "RA-NEW",
            "institutional_code": self._rotate_code(), "password": "secure-password-123",
        }).status_code, 400)

    def test_invalid_and_rotated_invitation_tokens_cannot_create_member(self):
        started, email = self._start_signup("RA-ROTATE", "rotate@example.edu")
        self.assertEqual(started.status_code, 202)
        self._rotate_code()
        response = self.client.post("/auth/signup/member/verify-email", json={"token": email.verification_token})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/auth/login", json={
            "email": "rotate@example.edu", "password": "secure-password-123",
        }).status_code, 401)

    def test_wrong_email_token_never_creates_account(self):
        response, _ = self._start_signup("RA-WRONG", "wrong@example.edu")
        self.assertEqual(response.status_code, 202)
        invalid = self.client.post("/auth/signup/member/verify-email", json={"token": "x" * 40})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.client.post("/auth/login", json={
            "email": "wrong@example.edu", "password": "secure-password-123",
        }).status_code, 401)

    def test_member_identity_validation_attempts_are_limited(self):
        payload = {
            "name": "Unknown", "email": "unknown@example.edu",
            "registration_number": "NOT-AUTHORIZED", "institutional_code": "invalid-code",
        }
        responses = [self.client.post("/auth/signup/member/preview", json=payload) for _ in range(9)]
        self.assertTrue(all(response.status_code == 400 for response in responses[:8]))
        self.assertEqual(responses[8].status_code, 429)

    def test_simultaneous_verification_of_one_token_creates_one_account(self):
        _, email = self._start_signup("RA-RACE", "race@example.edu")
        token = email.verification_token
        app = self.client_context.app

        def verify():
            return app.state.member_signup_service.verify_email(token, "parallel-test")

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(verify) for _ in range(2)]
            outcomes = []
            for future in as_completed(futures):
                try:
                    outcomes.append(future.result())
                except Exception as exc:
                    outcomes.append(exc)
        self.assertEqual(sum(not isinstance(result, Exception) for result in outcomes), 1)
        self.assertEqual(sum(isinstance(result, Exception) for result in outcomes), 1)
        self.assertEqual(self.client.post("/auth/login", json={
            "email": "race@example.edu", "password": "secure-password-123",
        }).status_code, 200)

    def test_expired_verification_token_is_rejected(self):
        _, email = self._start_signup("RA-EXPIRED", "expired@example.edu")
        digest = hashlib.sha256(email.verification_token.encode("utf-8")).hexdigest()
        repository = self.client_context.app.state.pending_member_signups
        pending = repository.find_by_digest(digest)
        repository.save(replace(pending, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        response = self.client.post("/auth/signup/member/verify-email", json={"token": email.verification_token})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/auth/login", json={
            "email": "expired@example.edu", "password": "secure-password-123",
        }).status_code, 401)

    def test_concurrent_members_with_same_email_create_only_one_account(self):
        code = self._rotate_code()
        for ra in ("RA-DUP-A", "RA-DUP-B"):
            self.client.post("/admin/enrollments", headers=self.headers, json={
                "registration_number": ra, "name": "Same Student", "email": "same@example.edu",
            })
        tokens = []
        for ra in ("RA-DUP-A", "RA-DUP-B"):
            started = self.client.post("/auth/signup/member/start", json={
                "name": "Same Student", "email": "same@example.edu",
                "registration_number": ra, "institutional_code": code,
                "password": "secure-password-123",
            })
            self.assertEqual(started.status_code, 202)
            tokens.append(self.client_context.app.state.simulated_email_sender.latest_for("same@example.edu").verification_token)

        service = self.client_context.app.state.member_signup_service
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(service.verify_email, token, f"parallel-{i}") for i, token in enumerate(tokens)]
            outcomes = []
            for future in as_completed(futures):
                try:
                    outcomes.append(future.result())
                except Exception as exc:
                    outcomes.append(exc)
        self.assertEqual(sum(not isinstance(result, Exception) for result in outcomes), 1)
        self.assertEqual(sum(isinstance(result, Exception) for result in outcomes), 1)
        self.assertEqual(self.client.post("/auth/login", json={
            "email": "same@example.edu", "password": "secure-password-123",
        }).status_code, 200)
        statuses = self.client.get("/admin/enrollments?q=RA-DUP", headers=self.headers).json()["data"]
        self.assertEqual(sum(item["status"] == "utilizado" for item in statuses), 1)

    def test_admin_cannot_manage_enrollment_from_another_institution(self) -> None:
        second_signup = self.client.post(
            "/institutions/signup",
            json={
                "responsible_name": "Admin B", "responsible_email": "adminb@example.edu", "password": "senha-segura",
                "name": "Instituição B", "cnpj": "98765432000110", "institution_type": "Instituto",
            },
        ).json()["data"]
        token_b = token_for(self.client, "adminb@example.edu", "senha-segura")
        b_enrollment = self.client.post(
            "/admin/enrollments", headers={"Authorization": f"Bearer {token_b}"},
            json={"registration_number": "PRIVATE-B"},
        ).json()["data"]
        response = self.client.delete(
            f"/admin/enrollments/{b_enrollment['id']}", headers=self.headers
        )
        self.assertEqual(response.status_code, 404)

    def test_atomic_repository_allows_only_one_concurrent_consumption(self) -> None:
        repository = InMemoryAuthorizedEnrollmentRepository()
        repository.add(AuthorizedEnrollment("e-1", "institution-1", "RA-1"))

        def consume(user_id: str) -> bool:
            try:
                repository.consume("institution-1", "RA-1", user_id)
                return True
            except ResourceNotFound:
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(consume, ("u-1", "u-2")))
        self.assertEqual(sum(results), 1)
        self.assertEqual(repository.find("institution-1", "RA-1").status.value, "utilizado")


if __name__ == "__main__":
    unittest.main()
