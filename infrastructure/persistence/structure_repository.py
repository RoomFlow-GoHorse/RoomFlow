from collections import defaultdict
from dataclasses import replace

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from infrastructure.persistence.structure_records import (
    andares, ativacao_recurso, bloqueios_espaco, estrutura_espaco, plantas_andar, posicoes_planta, predios,
)
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.database_models import Espaco, EspacoRecurso, Recurso, Reserva
from models.domain.entities.building import Building
from models.domain.entities.floor import Floor
from models.domain.entities.resource import Resource
from models.domain.entities.reservation import ReservationPeriod
from models.domain.entities.space import Space
from models.domain.exceptions import DuplicateResource, ResourceNotFound


class PostgresStructureRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    @staticmethod
    def _building(row) -> Building:
        return Building(row.id, str(row.instituicao_id), row.nome, row.ativo)

    @staticmethod
    def _floor(row) -> Floor:
        return Floor(row.id, row.predio_id, row.nome, row.ativo)

    def list_buildings(self, institution_id, include_inactive=False):
        query = select(predios).where(predios.c.instituicao_id == to_database_identity_id(institution_id))
        if not include_inactive:
            query = query.where(predios.c.ativo)
        with self._transaction.session() as session:
            return tuple(self._building(row) for row in session.execute(query.order_by(predios.c.nome)))

    def find_building(self, building_id):
        with self._transaction.session() as session:
            row = session.execute(select(predios).where(predios.c.id == building_id)).first()
            return self._building(row) if row else None

    def add_building(self, building):
        self._write_building(building, new=True)

    def save_building(self, building):
        self._write_building(building, new=False)

    def _write_building(self, building, *, new):
        institution_id = to_database_identity_id(building.institution_id)
        with self._transaction.atomic(), self._transaction.session() as session:
            self._unique_name(session, predios, predios.c.instituicao_id == institution_id,
                              building.id, building.name, "Já existe um prédio com esse nome.")
            values = dict(instituicao_id=institution_id, nome=building.name, ativo=building.active)
            statement = predios.insert().values(id=building.id) if new else update(predios).where(predios.c.id == building.id)
            session.execute(statement.values(**values))

    def list_institution_floors(self, institution_id: str, include_inactive: bool = False) -> tuple[Floor, ...]:
        query = select(andares).join(predios, andares.c.predio_id == predios.c.id).where(
            predios.c.instituicao_id == to_database_identity_id(institution_id),
        )
        if not include_inactive:
            query = query.where(predios.c.ativo, andares.c.ativo)
        with self._transaction.session() as session:
            return tuple(self._floor(row) for row in session.execute(query.order_by(andares.c.nome, andares.c.id)))

    def list_floors(self, building_id, include_inactive=False):
        query = select(andares).where(andares.c.predio_id == building_id)
        if not include_inactive:
            query = query.where(andares.c.ativo)
        with self._transaction.session() as session:
            return tuple(self._floor(row) for row in session.execute(query.order_by(andares.c.nome)))

    def find_floor(self, floor_id):
        with self._transaction.session() as session:
            row = session.execute(select(andares).where(andares.c.id == floor_id)).first()
            return self._floor(row) if row else None

    def add_floor(self, floor):
        self._write_floor(floor, new=True)

    def save_floor(self, floor):
        self._write_floor(floor, new=False)

    def _write_floor(self, floor, *, new):
        with self._transaction.atomic(), self._transaction.session() as session:
            building = self.find_building(floor.building_id)
            if building is None:
                raise ResourceNotFound("Prédio não encontrado.")
            self._unique_name(session, andares, andares.c.predio_id == floor.building_id,
                              floor.id, floor.name, "Já existe um andar com esse nome.")
            values = dict(instituicao_id=to_database_identity_id(building.institution_id),
                          predio_id=floor.building_id, nome=floor.name, ativo=floor.active)
            statement = andares.insert().values(id=floor.id) if new else update(andares).where(andares.c.id == floor.id)
            session.execute(statement.values(**values))

    def count_active_floors(self, building_id):
        return len(self.list_floors(building_id))

    def count_active_spaces(self, floor_id):
        with self._transaction.session() as session:
            return session.scalar(select(func.count()).select_from(estrutura_espaco).where(
                estrutura_espaco.c.andar_id == floor_id, estrutura_espaco.c.ativo,
            ))

    @staticmethod
    def _space_select():
        occupancy = select(Reserva.quantidade_participantes).where(
            Reserva.espaco_id == Espaco.id, Reserva.instituicao_id == Espaco.instituicao_id,
            Reserva.status == "aprovada",
            Reserva.inicio <= func.now(), Reserva.fim > func.now(),
        ).correlate(Espaco).scalar_subquery()
        return (
            select(Espaco, estrutura_espaco.c.ativo, andares.c.id.label("floor_id"),
                   andares.c.nome.label("floor_name"), predios.c.id.label("building_id"),
                   predios.c.nome.label("building_name"), func.coalesce(occupancy, 0).label("occupancy"),
                   bloqueios_espaco.c.motivo)
            .outerjoin(estrutura_espaco, estrutura_espaco.c.espaco_id == Espaco.id)
            .outerjoin(andares, andares.c.id == estrutura_espaco.c.andar_id)
            .outerjoin(predios, predios.c.id == andares.c.predio_id)
            .outerjoin(bloqueios_espaco, (
                (bloqueios_espaco.c.espaco_id == Espaco.id)
                & (bloqueios_espaco.c.instituicao_id == Espaco.instituicao_id)
                & bloqueios_espaco.c.desbloqueado_em.is_(None)
            ))
        )

    def list_all(self):
        with self._transaction.session() as session:
            return self._spaces(session, self._space_select().order_by(Espaco.nome))

    def list_spaces(
        self, institution_id, search="", status=None, building_id=None, floor_id=None,
        resource_id=None, include_inactive=False,
        *, room_type=None, min_capacity=None, max_capacity=None,
    ):
        statement = self._space_select().where(Espaco.instituicao_id == to_database_identity_id(institution_id))
        if building_id:
            statement = statement.where(predios.c.id == building_id)
        if floor_id:
            statement = statement.where(andares.c.id == floor_id)
        if room_type:
            statement = statement.where(Espaco.tipo == room_type)
        if min_capacity is not None:
            statement = statement.where(Espaco.capacidade >= min_capacity)
        if max_capacity is not None:
            statement = statement.where(Espaco.capacidade <= max_capacity)
        with self._transaction.session() as session:
            rows = self._spaces(session, statement.order_by(Espaco.nome))
        query = search.strip().casefold()
        return tuple(
            room for room in rows
            if (include_inactive or room.active)
            and (status is None or status == room.status)
            and (not resource_id or resource_id in room.resource_ids)
            and query in " ".join((room.name, room.type, room.location, room.building, room.floor)).casefold()
        )

    def find_space(self, space_id):
        try:
            database_id = to_database_identity_id(space_id, bits=64)
        except ValueError:
            return None
        with self._transaction.session() as session:
            rows = self._spaces(session, self._space_select().where(Espaco.id == database_id))
            return rows[0] if rows else None

    def block_periods(self, institution_id: str, period: ReservationPeriod) -> dict[str, list[ReservationPeriod]]:
        columns = bloqueios_espaco.c
        statement = select(columns.espaco_id, columns.bloqueado_em, columns.desbloqueado_em).where(
            columns.instituicao_id == to_database_identity_id(institution_id),
            columns.bloqueado_em < period.end,
            columns.desbloqueado_em.is_(None) | (columns.desbloqueado_em > period.start),
            columns.desbloqueado_em.is_(None) | (columns.bloqueado_em < columns.desbloqueado_em),
        )
        blocks = defaultdict(list)
        with self._transaction.session() as session:
            for room, blocked, unblocked in session.execute(statement):
                blocks[str(room)].append(ReservationPeriod(blocked, unblocked or period.end))
        return dict(blocks)

    @staticmethod
    def _spaces(session, statement):
        rows = session.execute(statement).all()
        if not rows:
            return ()
        associations = defaultdict(list)
        for item in session.execute(
            select(EspacoRecurso.espaco_id, Recurso.id, Recurso.nome, EspacoRecurso.quantidade)
            .join(Recurso, (Recurso.id == EspacoRecurso.recurso_id) & (Recurso.instituicao_id == EspacoRecurso.instituicao_id))
            .where(EspacoRecurso.espaco_id.in_([row[0].id for row in rows]))
            .order_by(Recurso.nome)
        ):
            associations[item.espaco_id].append((str(item.id), item.nome, item.quantidade))
        spaces = []
        for row in rows:
            room = row[0]
            assigned = associations[room.id]
            active = row.ativo is not False
            status = room.status
            if not active:
                status = "inativo"
            elif status == "disponivel" and row.occupancy:
                status = "ocupado"
            spaces.append(Space(
                id=str(room.id), institution_id=str(room.instituicao_id),
                name=room.nome, type=room.tipo, capacity=room.capacidade, location=room.localizacao,
                building=row.building_name or "", floor=row.floor_name or "",
                building_id=row.building_id or "", floor_id=row.floor_id or "",
                active=active, status=status, occupancy=row.occupancy,
                resources=tuple(name for _, name, _ in assigned),
                resource_ids=tuple(key for key, _, _ in assigned),
                resource_quantities=tuple((key, quantity) for key, _, quantity in assigned),
                block_reason=row.motivo, occupancy_verified=True,
                created_at=room.criado_em,
            ))
        return tuple(spaces)

    def add_space(self, space):
        return self._write_space(space, new=True)

    def save_space(self, space):
        self._write_space(space, new=False)

    def block_space(self, space, actor_id):
        with self._transaction.atomic(), self._transaction.session() as session:
            self.save_space(space)
            session.execute(bloqueios_espaco.insert().values(
                instituicao_id=to_database_identity_id(space.institution_id),
                espaco_id=to_database_identity_id(space.id, bits=64),
                responsavel_id=to_database_identity_id(actor_id),
                motivo=space.block_reason,
            ))

    def _write_space(self, space, *, new):
        institution_id = to_database_identity_id(space.institution_id)
        if len(space.type) > 60:
            raise ValueError("O tipo de sala aceita até 60 caracteres no banco.")
        try:
            with self._transaction.atomic(), self._transaction.session() as session:
                room_id = None if new else to_database_identity_id(space.id, bits=64)
                row = Espaco(instituicao_id=institution_id) if new else session.get(Espaco, room_id)
                if row is None or row.instituicao_id != institution_id:
                    raise ResourceNotFound("Sala não encontrada.")
                self._unique_name(session, Espaco, Espaco.instituicao_id == institution_id, room_id,
                                  space.name, "Já existe uma sala com esse nome na instituição.")
                existing = None if new else self.find_space(space.id)
                was_blocked = not new and row.status == "bloqueado"
                row.nome, row.tipo, row.capacidade, row.localizacao = space.name, space.type, space.capacity, space.location
                if space.status != "inativo" or new:
                    row.status = "bloqueado" if space.status == "bloqueado" else "disponivel"
                session.add(row)
                session.flush()
                if was_blocked and row.status != "bloqueado":
                    session.execute(update(bloqueios_espaco).where(
                        bloqueios_espaco.c.espaco_id == row.id,
                        bloqueios_espaco.c.instituicao_id == institution_id,
                        bloqueios_espaco.c.desbloqueado_em.is_(None),
                    ).values(desbloqueado_em=func.now()))
                values = dict(instituicao_id=institution_id, andar_id=space.floor_id or None, ativo=space.active)
                session.execute(insert(estrutura_espaco).values(espaco_id=row.id, **values)
                                .on_conflict_do_update(index_elements=[estrutura_espaco.c.espaco_id], set_=values))
                if existing and (existing.floor_id != space.floor_id or not space.active):
                    plans = select(plantas_andar.c.id).where(plantas_andar.c.andar_id == existing.floor_id)
                    session.execute(update(posicoes_planta).where(
                        posicoes_planta.c.espaco_id == row.id, posicoes_planta.c.planta_id.in_(plans),
                    ).values(ativo=False))
                self._update_associations(session, row, space.resource_ids, dict(space.resource_quantities))
                return self.find_space(str(row.id))
        except IntegrityError as exc:
            if exc.orig.sqlstate == "23514":
                raise ValueError("A capacidade informada é incompatível com as reservas vigentes.") from exc
            raise

    @staticmethod
    def _update_associations(session, room, resource_ids, quantities):
        desired = {to_database_identity_id(item, bits=64) for item in resource_ids}
        current = {item.recurso_id: item for item in session.scalars(select(EspacoRecurso).where(
            EspacoRecurso.espaco_id == room.id,
        ))}
        for key in current.keys() - desired:
            session.delete(current[key])
        for key in desired - current.keys():
            session.add(EspacoRecurso(instituicao_id=room.instituicao_id, espaco_id=room.id, recurso_id=key,
                                     quantidade=quantities.get(str(key), 1)))
        for key in current.keys() & desired:
            if str(key) in quantities:
                current[key].quantidade = quantities[str(key)]

    @staticmethod
    def _resource_select():
        return select(Recurso, ativacao_recurso.c.ativo).outerjoin(ativacao_recurso, ativacao_recurso.c.recurso_id == Recurso.id)

    @staticmethod
    def _resource(row):
        record, active = row
        return Resource(str(record.id), str(record.instituicao_id), record.nome, active is not False,
                        record.quantidade_total, record.quantidade_indisponivel)

    def list_resources(self, institution_id, search="", include_inactive=False):
        lookup = self._resource_select().where(Recurso.instituicao_id == to_database_identity_id(institution_id))
        with self._transaction.session() as session:
            resources = tuple(self._resource(row) for row in session.execute(lookup.order_by(Recurso.nome)))
        return tuple(item for item in resources if (include_inactive or item.active) and search.strip().casefold() in item.name.casefold())

    def find_resource(self, resource_id):
        try:
            database_id = to_database_identity_id(resource_id, bits=64)
        except ValueError:
            return None
        with self._transaction.session() as session:
            row = session.execute(self._resource_select().where(Recurso.id == database_id)).first()
            return self._resource(row) if row else None

    def add_resource(self, resource):
        return self._write_resource(resource, new=True)

    def save_resource(self, resource):
        self._write_resource(resource, new=False)

    def _write_resource(self, resource, *, new):
        institution_id = to_database_identity_id(resource.institution_id)
        with self._transaction.atomic(), self._transaction.session() as session:
            resource_id = None if new else to_database_identity_id(resource.id, bits=64)
            row = Recurso(instituicao_id=institution_id) if new else session.get(Recurso, resource_id)
            if row is None or row.instituicao_id != institution_id:
                raise ResourceNotFound("Recurso não encontrado.")
            self._unique_name(session, Recurso, Recurso.instituicao_id == institution_id, resource_id,
                              resource.name, "Já existe um recurso com esse nome na instituição.")
            row.nome = resource.name
            row.quantidade_total = resource.quantity_total
            row.quantidade_indisponivel = resource.quantity_unavailable
            session.add(row)
            session.flush()
            session.execute(insert(ativacao_recurso).values(
                recurso_id=row.id, instituicao_id=institution_id, ativo=resource.active,
            ).on_conflict_do_update(index_elements=[ativacao_recurso.c.recurso_id], set_={"ativo": resource.active}))
            return replace(resource, id=str(row.id))

    @staticmethod
    def _unique_name(session, relation, scope, current_id, name, message):
        columns = getattr(relation, "c", relation)
        statement = select(columns.id, columns.nome).where(scope)
        if any(key != current_id and value.strip().casefold() == name.strip().casefold()
               for key, value in session.execute(statement)):
            raise DuplicateResource(message)
