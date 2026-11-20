from domain.entities.institution import Institution
from domain.entities.profile import Profile
from domain.entities.user import User
from domain.exceptions import InstitutionAccessDenied


class InstitutionAccessPolicy:
    """Limits the confirmed admin profile to its institution relationship."""

    def resolve_listing_scope(
        self,
        user: User,
        requested_institution_id: str | None = None,
    ) -> str:
        institution_id = self._admin_institution_id(user)
        if (
            requested_institution_id is not None
            and requested_institution_id != institution_id
        ):
            raise InstitutionAccessDenied(
                "O administrador não pode acessar outra instituição."
            )
        return institution_id

    def assert_resource_access(
        self,
        user: User,
        resource_institution: Institution,
    ) -> None:
        institution_id = self._admin_institution_id(user)
        if resource_institution.id != institution_id:
            raise InstitutionAccessDenied(
                "O recurso pertence a outra instituição."
            )

    @staticmethod
    def _admin_institution_id(user: User) -> str:
        if user.profile is not Profile.ADMIN:
            raise InstitutionAccessDenied(
                "O escopo institucional deste perfil ainda não foi definido."
            )
        if not user.institution_id:
            raise InstitutionAccessDenied(
                "O administrador autenticado não possui vínculo institucional."
            )
        return user.institution_id
