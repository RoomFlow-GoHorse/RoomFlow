from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from db.seeds import _is_demo_seed_account, criar_contas, demo_passwords


class DemoSeedSafetyTests(unittest.TestCase):
    def test_demo_passwords_can_be_supplied_per_profile_without_committing_them(self):
        configured = {
            "ROOMFLOW_DEMO_PASSWORD_ADMIN": "admin-pass",
            "ROOMFLOW_DEMO_PASSWORD_GERENTE": "manager-pass",
            "ROOMFLOW_DEMO_PASSWORD_SOLICITANTE": "requester-pass",
            "ROOMFLOW_DEMO_PASSWORD_PARTICIPANTE": "participant-pass",
        }
        self.assertEqual(demo_passwords(configured), {
            "admin": "admin-pass", "gerente": "manager-pass",
            "solicitante": "requester-pass", "participante": "participant-pass",
        })

    def test_partial_password_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Configure todas"):
            demo_passwords({"ROOMFLOW_DEMO_PASSWORD_ADMIN": "one-password"})

    def test_legacy_default_is_preserved_when_no_passwords_are_supplied(self):
        self.assertEqual(set(demo_passwords({}).values()), {"123456789"})

    def test_only_a_marked_demo_account_without_other_memberships_is_mutable(self):
        account = SimpleNamespace(name="Administrador Demo", role="admin")
        membership = SimpleNamespace(role="admin")
        self.assertTrue(_is_demo_seed_account(account, membership, False, "admin", "Administrador"))
        self.assertFalse(_is_demo_seed_account(account, membership, True, "admin", "Administrador"))
        self.assertFalse(_is_demo_seed_account(
            SimpleNamespace(name="Augusto Medeiros", role="admin"), membership, False, "admin", "Administrador",
        ))

    def test_seed_refuses_to_modify_an_existing_non_demo_account(self):
        account = SimpleNamespace(
            id=17, name="Conta de integrante", email="admin@gmail.com", role="admin",
            password_hash="unchanged-hash", status="ativo", tipo_usuario_id=1,
        )
        session = MagicMock()
        session.execute.return_value.all.return_value = [("admin", 1)]
        session.scalar.side_effect = [account, None, None]

        with self.assertRaisesRegex(RuntimeError, "não foi reconhecida"):
            criar_contas(session, 5, {"admin": "new-password"})

        session.add.assert_not_called()
        self.assertEqual(account.name, "Conta de integrante")
        self.assertEqual(account.password_hash, "unchanged-hash")


if __name__ == "__main__":
    unittest.main()
