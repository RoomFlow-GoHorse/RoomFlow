import unittest

from controllers.navigation_service import dashboard_for_role


class DashboardRoutingTests(unittest.TestCase):
    def test_persistent_roles_land_on_their_supported_area(self):
        self.assertEqual(dashboard_for_role("admin", persistent=True), "admin_dashboard")
        self.assertEqual(dashboard_for_role("gerente", persistent=True), "gerente_dashboard")
        self.assertEqual(dashboard_for_role("solicitante", persistent=True), "minhas_reservas")
        self.assertEqual(dashboard_for_role("participante", persistent=True), "participante_dashboard")

    def test_demo_role_destinations_remain_available(self):
        self.assertEqual(dashboard_for_role("solicitante", persistent=False), "solicitante_dashboard")
        self.assertEqual(dashboard_for_role("participante", persistent=False), "participante_dashboard")

    def test_unknown_persistent_role_falls_back_to_account(self):
        self.assertEqual(dashboard_for_role("unknown", persistent=True), "conta")


if __name__ == "__main__":
    unittest.main()
