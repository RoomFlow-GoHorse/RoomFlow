import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api.app import create_app
from application.services.admin_dashboard_service import AdminDashboardService
from application.services.institution_management_service import InstitutionRegistration
from controllers.streamlit_runtime import get_streamlit_runtime
from infrastructure.authentication_factory import build_application_runtime
from infrastructure.repositories.in_memory_space_repository import InMemorySpaceRepository
from infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository
from infrastructure.time.system_clock import SystemClock
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.entities.user_account import UserAccount


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


class AdminDashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.runtime = build_application_runtime("test")
        self.admin = self.runtime.users.find_by_email("admin@gmail.com").user

    def test_counts_users_profiles_buildings_floors_spaces_and_resources(self):
        metrics = self.runtime.admin_dashboard.get_metrics(self.admin)
        self.assertEqual(metrics.users.total, 4)
        self.assertEqual(metrics.users.active, 4)
        self.assertEqual(metrics.users.inactive, 0)
        self.assertEqual({item.profile: item.count for item in metrics.users_by_profile}, {
            Profile.ADMIN: 1, Profile.MANAGER: 1, Profile.REQUESTER: 1, Profile.PARTICIPANT: 1,
        })
        self.assertEqual(metrics.buildings.total, 4)
        self.assertEqual(metrics.floors.total, 7)
        self.assertEqual(metrics.spaces.total, 6)
        self.assertEqual(metrics.resources.total, 8)

    def test_new_users_and_inactive_users_and_spaces_change_indicators(self):
        user = self.runtime.user_management.create_user(
            self.admin, "Dashboard Test", "dashboard-test@example.edu", "password-123", Profile.PARTICIPANT
        )
        recent = self.runtime.admin_dashboard.get_metrics(self.admin, 7)
        self.assertEqual(recent.users.total, 5)
        self.assertEqual(recent.users_by_profile[-1].count, 2)
        self.assertEqual(recent.recent_user_count, 1)
        self.assertEqual(recent.recent_users[0].id, user.id)

        self.runtime.user_management.set_status(self.admin, user.id, UserStatus.INACTIVE)
        admin = self.runtime.users.find_by_email("admin@gmail.com").user
        space = self.runtime.spaces.find_space("s1")
        self.runtime.space_management.deactivate_space(admin, space.id)
        updated = self.runtime.admin_dashboard.get_metrics(admin)
        self.assertEqual((updated.users.active, updated.users.inactive), (4, 1))
        self.assertEqual((updated.spaces.active, updated.spaces.inactive), (5, 1))

    def test_period_filter_and_institution_scope(self):
        now = datetime.now(timezone.utc)
        older = User(
            "old-user", "Usuário antigo", "old-user@example.edu", Profile.REQUESTER,
            "inst-demo", UserStatus.ACTIVE, now - timedelta(days=45),
        )
        self.runtime.users.add(UserAccount(older, "unused-hash"))
        self.assertEqual(self.runtime.admin_dashboard.get_metrics(self.admin, 7).recent_user_count, 0)
        self.assertEqual(self.runtime.admin_dashboard.get_metrics(self.admin, 30).recent_user_count, 0)
        self.assertEqual(self.runtime.admin_dashboard.get_metrics(self.admin, 90).recent_user_count, 1)
        with self.assertRaises(ValueError):
            self.runtime.admin_dashboard.get_metrics(self.admin, 14)

        institution, other_admin = self.runtime.institution_management.register(
            InstitutionRegistration(
                name="Outra Instituição", cnpj="12345678000199", institution_type="Universidade",
                city="", state="", phone="", email="", responsible_name="Outro Admin",
                responsible_email="other-admin-dashboard@example.edu", password="password-123",
            )
        )
        other_metrics = self.runtime.admin_dashboard.get_metrics(other_admin)
        self.assertEqual(other_metrics.institution_id, institution.id)
        self.assertEqual(other_metrics.users.total, 1)
        self.assertEqual(other_metrics.buildings.total, 0)
        self.assertEqual(other_metrics.spaces.total, 0)

    def test_institution_without_structure_returns_zero_space_counts(self):
        other = self.runtime.institution_management.register(
            InstitutionRegistration(
                name="Instituição Vazia", cnpj="22345678000198", institution_type="Universidade",
                city="", state="", phone="", email="", responsible_name="Admin Vazio",
                responsible_email="empty-admin-dashboard@example.edu", password="password-123",
            )
        )[1]
        metrics = self.runtime.admin_dashboard.get_metrics(other)
        self.assertEqual(metrics.users.total, 1)
        self.assertEqual(metrics.buildings.total, 0)
        self.assertEqual(metrics.floors.total, 0)
        self.assertEqual(metrics.spaces.total, 0)
        self.assertEqual(metrics.resources.total, 0)
        self.assertEqual(len(metrics.recent_users), 1)

    def test_empty_repository_returns_zero_indicators(self):
        actor = User("admin-empty", "Admin", "admin-empty@example.edu", Profile.ADMIN, "inst-empty")
        spaces = InMemorySpaceRepository(spaces=())
        service = AdminDashboardService(InMemoryUserRepository(), spaces, spaces, SystemClock())
        metrics = service.get_metrics(actor)
        self.assertEqual(metrics.users.total, 0)
        self.assertTrue(all(item.count == 0 for item in metrics.users_by_profile))
        self.assertEqual(metrics.buildings.total, 0)
        self.assertEqual(metrics.floors.total, 0)
        self.assertEqual(metrics.spaces.total, 0)
        self.assertEqual(metrics.resources.total, 0)
        self.assertEqual(metrics.recent_users, ())


class AdminDashboardHttpAndStreamlitTests(unittest.TestCase):
    def test_http_dashboard_is_authenticated_and_institution_scoped(self):
        with TestClient(create_app(environment="test")) as client:
            admin = _login(client, "admin@gmail.com", "admin123")
            manager = _login(client, "gerente@gmail.com", "gerente123")
            dashboard = client.get("/admin/dashboard?period_days=30", headers=admin)
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(dashboard.json()["users"]["total"], 4)
            self.assertEqual(client.get("/admin/dashboard", headers=manager).status_code, 403)
            self.assertEqual(client.get("/admin/dashboard?period_days=14", headers=admin).status_code, 422)
            self.assertEqual(client.get("/admin/dashboard").status_code, 401)
            registration = client.post("/institutions/signup", json={
                "responsible_name": "Admin externo", "responsible_email": "external-dashboard@example.edu",
                "password": "password-123", "name": "Instituição externa",
                "cnpj": "99887766000155", "institution_type": "Universidade",
            })
            self.assertEqual(registration.status_code, 201)
            other_admin = _login(client, "external-dashboard@example.edu", "password-123")
            own_scope = client.get("/admin/dashboard?institution_id=inst-demo", headers=other_admin)
            self.assertEqual(own_scope.status_code, 200)
            self.assertEqual(own_scope.json()["institution_id"], registration.json()["data"]["institution"]["id"])

    def test_streamlit_admin_dashboard_uses_application_metrics(self):
        runtime = get_streamlit_runtime()
        admin = runtime.users.find_by_email("admin@gmail.com").user
        token = runtime.authentication.login("admin@gmail.com", "admin123", "admin-dashboard-streamlit-test")
        runtime.user_management.create_user(
            admin, "Painel Streamlit", "panel-streamlit@example.edu", "password-123", Profile.MANAGER
        )
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "main.py"))
        app.query_params["page"] = "admin_dashboard"
        app.session_state["auth_token"] = token.access_token
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Usuários ativos" in metric.label for metric in app.metric))
        self.assertTrue(any("Reservas e ocupação" in str(item.value) for item in app.subheader))


if __name__ == "__main__":
    unittest.main()
