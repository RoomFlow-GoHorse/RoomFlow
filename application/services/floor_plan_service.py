import hashlib
import io
import secrets
import warnings
from dataclasses import replace
from xml.etree import ElementTree

from PIL import Image, UnidentifiedImageError

from application.ports.floor_plan_repository import FloorPlanRepository
from application.ports.plant_file_storage import PlantFileStorage
from models.domain.entities.floor_plan import FloorPlan, RoomPosition
from models.domain.entities.permission import Permission
from models.domain.entities.user import User
from models.domain.exceptions import ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


class FloorPlanService:
    """Secure upload, retrieval, and room-position management for floor plans."""

    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_IMAGE_PIXELS = 25_000_000

    def __init__(
        self,
        repository: FloorPlanRepository,
        files: PlantFileStorage,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._files = files
        self._permissions = permission_policy or PermissionPolicy()

    def upload(
        self, actor: User, floor_id: str, filename: str, content: bytes
    ) -> FloorPlan:
        institution_id = self._scope(actor)
        floor = self._repository.find_floor(floor_id)
        if floor is None:
            raise ResourceNotFound("Andar não encontrado.")
        building = self._repository.find_building(floor.building_id)
        if building is None or building.institution_id != institution_id:
            raise ResourceNotFound("Andar não encontrado.")
        if not floor.active or not building.active:
            raise ValueError("Não é possível anexar planta a prédio ou andar inativo.")
        safe_name = self._safe_filename(filename)
        media_type = self._validate_file(safe_name, content)

        existing = self._repository.find_floor_plan_by_floor(floor.id)
        plan_id = existing.id if existing else f"plan-{secrets.token_urlsafe(10)}"
        storage_key = f"plant-{secrets.token_urlsafe(18)}"
        positions = existing.positions if existing else ()
        plan = FloorPlan(
            id=plan_id,
            institution_id=institution_id,
            building_id=building.id,
            floor_id=floor.id,
            original_filename=safe_name,
            media_type=media_type,
            checksum=hashlib.sha256(content).hexdigest(),
            storage_key=storage_key,
            positions=positions,
        )
        self._files.save(storage_key, content)
        try:
            self._repository.save_floor_plan(plan)
        except Exception:
            self._files.delete(storage_key)
            raise
        if existing and existing.storage_key != storage_key:
            self._files.delete(existing.storage_key)
        return plan

    def get_for_floor(self, actor: User, floor_id: str) -> FloorPlan | None:
        self._floor_in_scope(actor, floor_id)
        return self._repository.find_floor_plan_by_floor(floor_id)

    def read_file(self, actor: User, floor_id: str) -> tuple[FloorPlan, bytes]:
        plan = self.get_for_floor(actor, floor_id)
        if plan is None:
            raise ResourceNotFound("Planta não encontrada.")
        content = self._files.read(plan.storage_key)
        if content is None:
            raise ResourceNotFound("Arquivo da planta não está disponível.")
        return plan, content

    def remove(self, actor: User, floor_id: str) -> None:
        self._floor_in_scope(actor, floor_id)
        plan = self._repository.remove_floor_plan(floor_id)
        if plan:
            self._files.delete(plan.storage_key)

    def set_room_position(
        self, actor: User, floor_id: str, space_id: str, x: float, y: float
    ) -> FloorPlan:
        self._floor_in_scope(actor, floor_id)
        plan = self._repository.find_floor_plan_by_floor(floor_id)
        if plan is None:
            raise ResourceNotFound("Cadastre uma planta para este andar antes de posicionar salas.")
        position = RoomPosition(space_id, float(x), float(y))
        space = self._repository.find_space(space_id)
        if (
            space is None or space.institution_id != plan.institution_id
            or space.floor_id != floor_id or not space.active
        ):
            raise ResourceNotFound("Sala não encontrada neste andar.")
        positions = {item.space_id: item for item in plan.positions}
        positions[space_id] = position
        updated = replace(plan, positions=tuple(sorted(positions.values(), key=lambda item: item.space_id)))
        self._repository.save_floor_plan(updated)
        return updated

    def remove_room_position(self, actor: User, floor_id: str, space_id: str) -> FloorPlan:
        self._floor_in_scope(actor, floor_id)
        plan = self._repository.find_floor_plan_by_floor(floor_id)
        if plan is None:
            raise ResourceNotFound("Planta não encontrada.")
        space = self._repository.find_space(space_id)
        if space is None or space.institution_id != plan.institution_id or space.floor_id != floor_id:
            raise ResourceNotFound("Sala não encontrada neste andar.")
        updated = replace(
            plan,
            positions=tuple(item for item in plan.positions if item.space_id != space_id),
        )
        self._repository.save_floor_plan(updated)
        return updated

    def _floor_in_scope(self, actor: User, floor_id: str):
        institution_id = self._scope(actor)
        floor = self._repository.find_floor(floor_id)
        building = self._repository.find_building(floor.building_id) if floor else None
        if floor is None or building is None or building.institution_id != institution_id:
            raise ResourceNotFound("Andar não encontrado.")
        return floor

    def _scope(self, actor: User) -> str:
        return self._permissions.authorize_listing(actor, Permission.MANAGE_FLOOR_PLAN)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not name or len(name) > 180 or any(ord(char) < 32 for char in name):
            raise ValueError("Nome de arquivo inválido.")
        return name

    def _validate_file(self, filename: str, content: bytes) -> str:
        if not content or len(content) > self.MAX_FILE_SIZE:
            raise ValueError("A planta deve ter entre 1 byte e 10 MB.")
        extension = filename.rsplit(".", 1)[-1].casefold() if "." in filename else ""
        if extension == "png" and content.startswith(b"\x89PNG\r\n\x1a\n"):
            self._verify_raster(content)
            return "image/png"
        if extension in {"jpg", "jpeg"} and content.startswith(b"\xff\xd8\xff"):
            self._verify_raster(content)
            return "image/jpeg"
        if extension == "svg":
            self._verify_svg(content)
            return "image/svg+xml"
        raise ValueError("Formato inválido. Envie uma planta PNG, JPG ou SVG válida.")

    def _verify_raster(self, content: bytes) -> None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                image = Image.open(io.BytesIO(content))
                if image.width * image.height > self.MAX_IMAGE_PIXELS:
                    raise ValueError("A imagem excede o limite de dimensões permitido.")
                image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise ValueError("O arquivo de imagem está corrompido ou é inválido.") from None

    @staticmethod
    def _verify_svg(content: bytes) -> None:
        lowered = content.lower().replace(b"\x00", b"")
        if b"<!doctype" in lowered or b"<!entity" in lowered:
            raise ValueError("O SVG contém declarações XML não permitidas.")
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            raise ValueError("O arquivo SVG está malformado.") from None
        if root.tag.rsplit("}", 1)[-1].casefold() != "svg":
            raise ValueError("O arquivo não contém uma imagem SVG.")
        forbidden = {"script", "foreignobject", "iframe", "object", "embed", "audio", "video"}
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1].casefold() in forbidden:
                raise ValueError("O SVG contém elementos ativos não permitidos.")
            for key, value in element.attrib.items():
                attr = key.rsplit("}", 1)[-1].casefold()
                value_lower = value.strip().casefold()
                if attr.startswith("on") or "javascript:" in value_lower:
                    raise ValueError("O SVG contém conteúdo ativo não permitido.")
                if attr in {"href", "src"} and value_lower and not value_lower.startswith("#"):
                    raise ValueError("O SVG não pode carregar conteúdo externo.")
                if "url(" in value_lower or "@import" in value_lower:
                    raise ValueError("O SVG não pode carregar estilos externos.")

