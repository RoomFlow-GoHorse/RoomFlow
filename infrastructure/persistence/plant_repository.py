from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from infrastructure.persistence.structure_records import andares, arquivos_planta, plantas_andar, posicoes_planta
from infrastructure.persistence.structure_repository import PostgresStructureRepository
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.domain.entities.floor_plan import FloorPlan, RoomPosition
from models.domain.exceptions import ResourceNotFound


class PostgresPlantFileStorage:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    def save(self, storage_key: str, content: bytes) -> None:
        with self._transaction.session() as session:
            session.execute(arquivos_planta.insert().values(chave=storage_key, conteudo=content))

    def read(self, storage_key: str) -> bytes | None:
        with self._transaction.session() as session:
            return session.scalar(select(arquivos_planta.c.conteudo).where(arquivos_planta.c.chave == storage_key))

    def delete(self, storage_key: str) -> None:
        with self._transaction.session() as session:
            session.execute(update(arquivos_planta).where(
                arquivos_planta.c.chave == storage_key, arquivos_planta.c.retirado_em.is_(None),
            ).values(retirado_em=datetime.now(timezone.utc)))


class PostgresFloorPlanRepository:
    def __init__(self, transaction: PostgresTransaction, structure: PostgresStructureRepository):
        self._transaction = transaction
        self._structure = structure

    def find_building(self, building_id):
        return self._structure.find_building(building_id)

    def find_floor(self, floor_id):
        return self._structure.find_floor(floor_id)

    def find_space(self, space_id):
        return self._structure.find_space(space_id)

    def find_floor_plan_by_floor(self, floor_id):
        return self._find_plan(plantas_andar.c.andar_id == floor_id)

    def find_floor_plan(self, plan_id):
        return self._find_plan(plantas_andar.c.id == plan_id)

    def _find_plan(self, condition):
        with self._transaction.session() as session:
            row = session.execute(select(plantas_andar, andares.c.predio_id)
                .join(andares, andares.c.id == plantas_andar.c.andar_id)
                .where(condition, plantas_andar.c.removida_em.is_(None))).first()
            if row is None:
                return None
            positions = session.execute(select(posicoes_planta).where(
                posicoes_planta.c.planta_id == row.id, posicoes_planta.c.ativo,
            ).order_by(posicoes_planta.c.espaco_id))
            return FloorPlan(
                row.id, str(row.instituicao_id), row.predio_id, row.andar_id,
                row.nome, row.tipo_midia, row.checksum, row.arquivo_chave,
                tuple(RoomPosition(str(item.espaco_id), item.x, item.y) for item in positions),
            )

    def save_floor_plan(self, plan: FloorPlan) -> None:
        institution_id = to_database_identity_id(plan.institution_id)
        with self._transaction.session() as session:
            floor = self.find_floor(plan.floor_id)
            if floor is None or floor.building_id != plan.building_id:
                raise ResourceNotFound("Andar não encontrado.")
            values = dict(instituicao_id=institution_id, andar_id=plan.floor_id,
                          arquivo_chave=plan.storage_key, nome=plan.original_filename,
                          tipo_midia=plan.media_type, checksum=plan.checksum)
            session.execute(insert(plantas_andar).values(id=plan.id, **values).on_conflict_do_update(
                index_elements=[plantas_andar.c.id], set_=values,
            ))
            desired = []
            for position in plan.positions:
                room = self.find_space(position.space_id)
                if room is None or room.institution_id != plan.institution_id or room.floor_id != plan.floor_id or not room.active:
                    raise ResourceNotFound("Sala não encontrada neste andar.")
                room_id = to_database_identity_id(position.space_id, bits=64)
                desired.append(room_id)
                changes = dict(x=position.x, y=position.y, ativo=True)
                session.execute(insert(posicoes_planta).values(
                    planta_id=plan.id, espaco_id=room_id, instituicao_id=institution_id, **changes,
                ).on_conflict_do_update(
                    index_elements=[posicoes_planta.c.planta_id, posicoes_planta.c.espaco_id], set_=changes,
                ))
            session.execute(update(posicoes_planta).where(
                posicoes_planta.c.planta_id == plan.id, posicoes_planta.c.ativo,
                posicoes_planta.c.espaco_id.not_in(desired),
            ).values(ativo=False))

    def remove_floor_plan(self, floor_id):
        plan = self.find_floor_plan_by_floor(floor_id)
        if plan is None:
            return None
        with self._transaction.session() as session:
            session.execute(update(plantas_andar).where(plantas_andar.c.id == plan.id)
                            .values(removida_em=datetime.now(timezone.utc)))
        return plan
