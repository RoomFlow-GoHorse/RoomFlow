import unittest

from infrastructure.persistence.user_mapping import to_database_identity_id, to_user_account
from models.database_models import Instituicao, Usuario, UsuarioInstituicao
from models.domain.entities.profile import Profile
from models.domain.entities.user import UserStatus


class UserMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user = Usuario(
            id=10,
            name="Usuário",
            email=" User@Example.org ",
            password_hash="stored-hash",
            status="ativo",
            role="admin",
        )
        self.institution = Instituicao(id=20, status="ativo")
        self.membership = UsuarioInstituicao(
            user_id=10, institution_id=20, role="gerente", status="ativo"
        )

    def test_maps_the_explicit_membership_and_keeps_the_stored_hash(self) -> None:
        second_institution = Instituicao(id=30, status="ativo")
        second_membership = UsuarioInstituicao(
            user_id=10, institution_id=30, role="participante", status="ativo"
        )

        first = to_user_account(self.user, self.membership, self.institution)
        second = to_user_account(self.user, second_membership, second_institution)

        self.assertEqual(first.user.id, second.user.id)
        self.assertEqual(first.user.email, "user@example.org")
        self.assertEqual(first.password_hash, self.user.password_hash)
        self.assertEqual(first.user.profile, Profile.MANAGER)
        self.assertEqual(second.user.profile, Profile.PARTICIPANT)
        self.assertEqual(first.user.institution_id, "20")
        self.assertEqual(second.user.institution_id, "30")
        self.assertEqual(to_database_identity_id(first.user.id), self.user.id)

    def test_inactive_account_membership_or_institution_blocks_active_projection(self) -> None:
        for row in (self.user, self.membership, self.institution):
            with self.subTest(row=type(row).__name__):
                row.status = "inativo"
                account = to_user_account(self.user, self.membership, self.institution)
                self.assertEqual(account.user.status, UserStatus.INACTIVE)
                row.status = "ativo"

    def test_requires_matching_institution_and_user(self) -> None:
        with self.assertRaises(ValueError):
            to_user_account(self.user, self.membership, Instituicao(id=30, status="ativo"))
        self.membership.user_id = 11
        with self.assertRaises(ValueError):
            to_user_account(self.user, self.membership, self.institution)

    def test_rejects_in_memory_and_noncanonical_ids_at_database_boundary(self) -> None:
        for domain_id in ("u-demo", "010", " 10", "2147483648"):
            with self.subTest(domain_id=domain_id), self.assertRaises(ValueError):
                to_database_identity_id(domain_id)
