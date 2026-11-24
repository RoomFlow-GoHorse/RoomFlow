import hashlib
import io
import json
import os
import secrets
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent
from threading import Barrier
from unittest.mock import patch
from zoneinfo import ZoneInfo

from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker
from PIL import Image
from openpyxl import Workbook
from streamlit.testing.v1 import AppTest

from api.app import create_app
from infrastructure.email.in_memory_email_sender import InMemoryEmailSender
from infrastructure.persistence.notification_repository import PostgresNotificationRepository
from infrastructure.persistence.records import institution_invites, pending_signups, sessions
from infrastructure.persistence.reservation_repository import PostgresReservationRepository
from infrastructure.persistence.structure_records import bloqueios_espaco
from models.database_models import DestinatarioNotificacao, Espaco, Notificacao, Reserva, UsuarioInstituicao


TEST_DATABASE = os.getenv("ROOMFLOW_TEST_DATABASE", "")
PASSWORD = "teste-postgres-123"
PROJECT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(TEST_DATABASE, "Informe ROOMFLOW_TEST_DATABASE para testar PostgreSQL local isolado.")
class PostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = {**dotenv_values(PROJECT / ".env"), **os.environ}
        if not TEST_DATABASE.startswith("roomflow_test_") or config["DB_HOST"] not in {"localhost", "127.0.0.1", "::1"}:
            raise RuntimeError("Os testes exigem um banco PostgreSQL local com prefixo roomflow_test_.")
        cls.database_config = {**config, "DB_NAME": TEST_DATABASE}
        cls.engine = create_engine(URL.create(
            "postgresql+psycopg", username=config["DB_USERNAME"], password=config["DB_PASSWORD"],
            host=config["DB_HOST"], port=int(config["DB_PORT"]), database=TEST_DATABASE,
        ))
        cls.factory = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.mailbox = InMemoryEmailSender()
        self.client = self.enterContext(TestClient(create_app(
            postgres_session_factory=self.factory, postgres_email_sender=self.mailbox,
        )))

    def register(self):
        tag = secrets.token_hex(5)
        payload = {
            "responsible_name": "Administrador Teste", "responsible_email": f"{tag}@example.test",
            "password": PASSWORD, "name": f"Instituição {tag}",
            "cnpj": str(secrets.randbelow(10**14)).zfill(14), "institution_type": "Faculdade",
        }
        response = self.client.post("/institutions/signup", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return payload, response.json()["data"]

    def login(self, email, institution_id=None):
        return self.client.post("/auth/login", json={
            "email": email, "password": PASSWORD, "institution_id": institution_id,
        })

    @staticmethod
    def headers(login):
        assert login.status_code == 200, login.text
        return {"Authorization": "Bearer " + login.json()["data"]["access_token"]}

    def _structure_room(self, headers, name):
        building = self.client.post("/structure/buildings", headers=headers, json={"name": "Bloco A"})
        self.assertEqual(building.status_code, 201, building.text)
        building_id = building.json()["data"]["id"]
        floor = self.client.post(f"/structure/buildings/{building_id}/floors", headers=headers,
                                 json={"name": "Térreo"})
        self.assertEqual(floor.status_code, 201, floor.text)
        room = self.client.post("/structure/spaces", headers=headers, json={
            "floor_id": floor.json()["data"]["id"], "name": name, "type": "Sala", "capacity": 20,
        })
        self.assertEqual(room.status_code, 201, room.text)
        return room.json()["data"]

    def _manager_login(self, admin):
        email = f"{secrets.token_hex(5)}@example.test"
        created = self.client.post("/admin/users", headers=admin, json={
            "name": "Gerente Teste", "email": email, "password": PASSWORD, "profile": "gerente",
        })
        self.assertEqual(created.status_code, 201, created.text)
        return self.login(email)

    def _requester_login(self, admin):
        email = f"{secrets.token_hex(5)}@example.test"
        created = self.client.post("/admin/users", headers=admin, json={
            "name": "Solicitante Teste", "email": email, "password": PASSWORD, "profile": "solicitante",
        })
        self.assertEqual(created.status_code, 201, created.text)
        return self.login(email)

    def _participant_login(self, admin):
        email = f"{secrets.token_hex(5)}@example.test"
        created = self.client.post("/admin/users", headers=admin, json={
            "name": "Participante Teste", "email": email, "password": PASSWORD, "profile": "participante",
        })
        self.assertEqual(created.status_code, 201, created.text)
        return self.login(email)

    @staticmethod
    def _reservation_payload(room):
        start = (datetime.now(ZoneInfo("America/Sao_Paulo")) + timedelta(days=3)).replace(
            hour=10, minute=0, second=0, microsecond=0,
        )
        end = start + timedelta(hours=1)
        return {
            "space_id": room["id"], "title": "Oficina", "activity_type": "Aula",
            "start": start.isoformat(), "end": end.isoformat(), "participants": 20,
            "justification": "Atividade com a turma",
        }

    def test_reservation_participants_are_isolated_and_can_respond(self):
        own, _ = self.register()
        other, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        foreign_admin = self.headers(self.login(other["responsible_email"]))
        requester = self.headers(self._requester_login(admin))
        participant_login = self._participant_login(admin)
        participant = self.headers(participant_login)
        foreign_participant = self.headers(self._participant_login(foreign_admin))
        room = self._structure_room(admin, "Sala com participantes")

        eligible = self.client.get("/reservations/participants", headers=requester)
        self.assertEqual(eligible.status_code, 200, eligible.text)
        participant_id = participant_login.json()["data"]["user"]["id"]
        self.assertIn(participant_id, [item["id"] for item in eligible.json()["data"]])

        payload = {**self._reservation_payload(room), "participant_ids": [participant_id]}
        created = self.client.post("/reservations", headers=requester, json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        reservation_id = created.json()["data"]["id"]

        self.assertEqual(self.client.post("/reservations", headers=requester, json={
            **payload, "title": "Duplicada", "participant_ids": [participant_id, participant_id],
        }).status_code, 422)
        self.assertEqual(self.client.get("/reservations/participating", headers=foreign_participant)
                         .json()["data"], [])
        linked = self.client.get("/reservations/participating", headers=participant)
        self.assertEqual([item["id"] for item in linked.json()["data"]], [reservation_id])

        detail = self.client.get(f"/reservations/participating/{reservation_id}", headers=participant)
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["data"]["participation_status"], "pendente")
        self.assertEqual(self.client.patch(f"/reservations/participating/{reservation_id}", headers=foreign_participant,
                                           json={"status": "confirmada"}).status_code, 404)
        confirmed = self.client.patch(f"/reservations/participating/{reservation_id}", headers=participant,
                                      json={"status": "confirmada"})
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json()["data"]["participation_status"], "confirmada")

    def test_reservations_are_scoped_validated_and_persisted(self):
        own, _ = self.register()
        other, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        foreign_admin = self.headers(self.login(other["responsible_email"]))
        manager_login = self._manager_login(admin)
        manager = self.headers(manager_login)
        foreign_manager = self.headers(self._manager_login(foreign_admin))
        requester = self.headers(self._requester_login(admin))
        colleague = self.headers(self._requester_login(admin))
        foreign_requester = self.headers(self._requester_login(foreign_admin))
        room = self._structure_room(admin, "Sala Reserva")
        foreign_room = self._structure_room(foreign_admin, "Sala Externa")
        data = self._reservation_payload(room)
        end = datetime.fromisoformat(data["end"])
        base = "/reservations"
        for attrs, code in (
            ({"participants": 21}, 422), ({"end": data["start"]}, 422),
            ({"start": data["start"][:19]}, 422), ({"justification": " "}, 422),
            ({"start": end.replace(hour=6).isoformat()}, 422), ({"institution_id": "1"}, 422),
            ({"requester_id": "1"}, 422), ({"status": "aprovada"}, 422), ({"space_id": foreign_room["id"]}, 404),
        ):
            response = self.client.post(base, headers=requester, json={**data, **attrs})
            self.assertEqual(response.status_code, code, response.text)
        self.assertEqual(self.client.post(base, headers=foreign_requester, json=data).status_code, 404)
        self.assertEqual(self.client.post(base, headers=manager, json=data).status_code, 403)
        self.assertEqual(self.client.get(base + "/institution", headers=requester).status_code, 403)
        self.assertEqual(self.client.get(base + "/institution", headers=admin).status_code, 403)
        block = f"/structure/spaces/{room['id']}"
        self.assertEqual(self.client.post(block + "/block", headers=manager, json={"reason": "Manutenção"}).status_code, 200)
        self.assertEqual(self.client.post(base, headers=requester, json=data).status_code, 409)
        self.assertEqual(self.client.delete(block + "/block", headers=manager).status_code, 200)

        first = self.client.post(base, headers=requester, json=data)
        self.assertEqual(first.status_code, 201, first.text)
        reservation_id = first.json()["data"]["id"]
        self.assertEqual(first.json()["data"]["status"], "pendente")
        self.assertEqual(self.client.post(base, headers=requester, json=data).status_code, 409)
        second = self.client.post(base, headers=colleague, json={**data, "title": "Reunião"})
        self.assertEqual(second.status_code, 201, second.text)
        second_id = second.json()["data"]["id"]
        self.assertTrue(second.json()["data"]["has_overlap"])
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            mine = restarted.get(base + "/mine", headers=requester).json()["data"]
            self.assertEqual([item["id"] for item in mine], [reservation_id])
            self.assertTrue(mine[0]["has_overlap"])
            all_items = restarted.get(base + "/institution", headers=manager).json()["data"]
            self.assertEqual({item["id"] for item in all_items}, {reservation_id, second_id})
            self.assertEqual(restarted.get(base + "/institution", headers=foreign_manager).json()["data"], [])
        path = f"{base}/{reservation_id}"
        self.assertEqual(self.client.get(path, headers=foreign_manager).status_code, 404)
        self.assertEqual(self.client.get(path, headers=requester).status_code, 403)
        self.assertEqual(self.client.get(path, headers=admin).status_code, 403)
        self.assertEqual(self.client.post(path + "/cancel", headers=manager).status_code, 403)
        self.assertEqual(self.client.post(path + "/cancel", headers=colleague).status_code, 404)
        self.assertEqual(self.client.put(path, headers=colleague, json=data).status_code, 404)
        self.assertEqual(self.client.put(path, headers=foreign_manager, json=data).status_code, 404)
        self.assertEqual(self.client.patch(path + "/decision", headers=foreign_manager,
                                           json={"status": "aprovada"}).status_code, 404)
        decision = path + "/decision"
        analyzed = self.client.patch(decision, headers=manager, json={"status": "em_analise"})
        self.assertEqual(analyzed.status_code, 200, analyzed.text)
        self.assertEqual(self.client.patch(decision, headers=manager, json={"status": "em_analise"}).status_code, 409)
        self.assertEqual(self.client.patch(decision, headers=manager, json={"status": "cancelada"}).status_code, 422)
        edited = self.client.put(path, headers=manager, json={**data, "title": "Oficina atualizada"})
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["data"]["status"], "em_analise")
        self.assertEqual(self.client.post(block + "/block", headers=manager, json={"reason": "Obra"}).status_code, 200)
        self.assertEqual(self.client.patch(decision, headers=manager, json={"status": "aprovada"}).status_code, 409)
        self.assertEqual(self.client.delete(block + "/block", headers=manager).status_code, 200)
        spaces = self.client.app.state.reservation_service._spaces
        current_room = spaces.find_space(room["id"])
        with patch.object(spaces, "find_space", return_value=replace(current_room, capacity=19)):
            over_capacity = self.client.patch(decision, headers=manager, json={"status": "aprovada"})
        self.assertEqual(over_capacity.status_code, 422, over_capacity.text)
        approved = self.client.patch(decision, headers=manager, json={"status": "aprovada", "reason": "Confirmada"})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["data"]["status"], "aprovada")
        self.assertEqual(self.client.patch(decision, headers=manager,
                                           json={"status": "rejeitada", "reason": "Outra decisão"}).status_code, 409)
        second_decision = f"{base}/{second_id}/decision"
        self.assertEqual(self.client.patch(second_decision, headers=manager,
                                           json={"status": "aprovada"}).status_code, 409)
        self.assertEqual(self.client.post(base, headers=colleague, json=data).status_code, 409)
        catalog = self.client.get(base + "/spaces", headers=requester, params={"start": data["start"], "end": data["end"]})
        self.assertEqual(catalog.json()["data"]["spaces"], [])
        adjacent = self.client.post(base, headers=requester, json={
            **data, "start": end.isoformat(), "end": (end + timedelta(hours=1)).isoformat(),
        })
        self.assertEqual(adjacent.status_code, 201, adjacent.text)
        self.assertEqual(self.client.patch(second_decision, headers=manager,
                                           json={"status": "rejeitada"}).status_code, 422)
        rejected = self.client.patch(second_decision, headers=manager,
                                     json={"status": "rejeitada", "reason": "Horário ocupado"})
        self.assertEqual(rejected.json()["data"]["status"], "rejeitada")
        self.assertEqual(rejected.json()["data"]["decision_reason"], "Horário ocupado")
        reopened = self.client.put(path, headers=manager, json={**data, "title": "Oficina reaberta"})
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()["data"]["status"], "em_analise")
        self.assertIsNone(reopened.json()["data"]["decision_reason"])
        catalog = self.client.get(base + "/spaces", headers=requester, params={"start": data["start"], "end": data["end"]})
        self.assertEqual([space["id"] for space in catalog.json()["data"]["spaces"]], [room["id"]])
        reapplied = self.client.patch(decision, headers=manager, json={"status": "aprovada", "reason": "Reavaliada"})
        self.assertEqual(reapplied.status_code, 200, reapplied.text)
        cancelled = self.client.post(path + "/cancel", headers=requester)
        self.assertEqual(cancelled.json()["data"]["status"], "cancelada")
        self.assertEqual(self.client.post(path + "/cancel", headers=requester).status_code, 409)
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            response = restarted.get(path, headers=manager)
            self.assertEqual(response.status_code, 200, response.text)
            detail = response.json()["data"]
            self.assertEqual(detail["reviewed_by"], manager_login.json()["data"]["user"]["id"])
            self.assertEqual(detail["decision_reason"], "Reavaliada")
            self.assertEqual(detail["available_decisions"], [])
            events = detail["history"]
            self.assertEqual([(item["action"], item["previous_status"], item["status"]) for item in events], [
                ("criacao", None, "pendente"),
                ("avaliacao", "pendente", "em_analise"), ("edicao", "em_analise", "em_analise"),
                ("avaliacao", "em_analise", "aprovada"), ("edicao", "aprovada", "em_analise"),
                ("avaliacao", "em_analise", "aprovada"), ("cancelamento", "aprovada", "cancelada"),
            ])
            self.assertEqual(events[3]["actor_name"], "Gerente Teste")
            self.assertEqual(events[3]["reason"], "Confirmada")
            self.assertEqual(events[5]["occurred_at"], detail["reviewed_at"])
            self.assertEqual(events[6]["actor_name"], "Solicitante Teste")
            rejection = restarted.get(f"{base}/{second_id}", headers=manager).json()["data"]["history"]
            self.assertEqual(rejection[-1]["reason"], "Horário ocupado")
            self.assertEqual([item["status"] for item in rejection], ["pendente", "rejeitada"])
            catalog = restarted.get(base + "/spaces", headers=requester,
                                    params={"start": data["start"], "end": data["end"]})
            self.assertEqual([space["id"] for space in catalog.json()["data"]["spaces"]], [room["id"]])

    def test_concurrent_reservation_approvals_record_only_the_winner(self):
        own, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        managers = [self.headers(self._manager_login(admin)) for _ in range(2)]
        room = self._structure_room(admin, "Sala de decisões concorrentes")
        data = self._reservation_payload(room)
        reservations = []
        for _ in range(2):
            owner = self.headers(self._requester_login(admin))
            created = self.client.post("/reservations", headers=owner, json=data)
            self.assertEqual(created.status_code, 201, created.text)
            reservations.append(created.json()["data"]["id"])
        ready = Barrier(2)

        def approve(pair):
            reservation_id, headers = pair
            with TestClient(create_app(postgres_session_factory=self.factory)) as api:
                ready.wait(timeout=10)
                return api.patch(f"/reservations/{reservation_id}/decision", headers=headers,
                                 json={"status": "aprovada"})

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(approve, zip(reservations, managers, strict=True)))
        self.assertCountEqual([response.status_code for response in responses], [200, 409])

        for reservation_id, response in zip(reservations, responses, strict=True):
            path = f"/reservations/{reservation_id}"
            detail = self.client.get(path, headers=managers[0]).json()["data"]
            if response.status_code == 200:
                self.assertEqual(detail["status"], "aprovada")
                self.assertEqual([event["status"] for event in detail["history"]], ["pendente", "aprovada"])
            else:
                self.assertEqual(detail["status"], "pendente")
                self.assertEqual([event["action"] for event in detail["history"]], ["criacao"])
                service = self.client.app.state.reservation_service
                with patch.object(service, "_overlap", return_value=False):
                    database_conflict = self.client.patch(path + "/decision", headers=managers[0],
                                                          json={"status": "aprovada"})
                self.assertEqual(database_conflict.status_code, 409, database_conflict.text)
                self.assertNotIn("ex_reservas_aprovadas_periodo", database_conflict.text)
                detail = self.client.get(path, headers=managers[0]).json()["data"]
                self.assertEqual(detail["status"], "pendente")
                self.assertEqual([event["action"] for event in detail["history"]], ["criacao"])

    def test_reservation_decision_rolls_back_when_history_insert_fails(self):
        own, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        manager = self.headers(self._manager_login(admin))
        requester = self.headers(self._requester_login(admin))
        room = self._structure_room(admin, "Sala com histórico atômico")
        payload = self._reservation_payload(room)
        created = self.client.post("/reservations", headers=requester, json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        path = f"/reservations/{created.json()['data']['id']}"
        append = PostgresReservationRepository.append_history

        def fail_actor_constraint(repository, reservation, event):
            return append(repository, reservation, replace(event, actor_id="-1"))

        with patch.object(PostgresReservationRepository, "append_history", fail_actor_constraint):
            response = self.client.patch(path + "/decision", headers=manager, json={"status": "aprovada"})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertNotIn("fk_historico_reserva_ator", response.text)
        data = self.client.get(path, headers=manager).json()["data"]
        self.assertEqual((data["status"], data["reviewed_by"]), ("pendente", None))
        self.assertEqual([event["action"] for event in data["history"]], ["criacao"])
        catalog = self.client.get("/reservations/spaces", headers=requester,
                                  params={"start": payload["start"], "end": payload["end"]})
        self.assertEqual([space["id"] for space in catalog.json()["data"]["spaces"]], [room["id"]])

    def test_reservation_streamlit_submission_reaches_manager_directly(self):
        own, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        requester = self._requester_login(admin)
        manager = self._manager_login(admin)
        room = self._structure_room(admin, "Sala Streamlit Reserva")
        with self.streamlit_runtime():
            def open_page(login, page):
                app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
                app.query_params["page"] = page
                app.session_state["auth_token"] = login.json()["data"]["access_token"]
                app.run()
                self.assertFalse(app.exception)
                return app

            title = "Oficina criada pelo Streamlit"
            app = open_page(requester, "nova_reserva")
            app.selectbox(key="new_reservation_room").select(room["id"])
            app.text_input(key="new_reservation_title").set_value(title)
            app.text_input(key="new_reservation_activity").set_value("Oficina")
            app.text_area(key="new_reservation_reason").set_value("Atividade em grupo")
            next(button for button in app.button if button.label == "Solicitar reserva").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.success, [item.value for item in app.error])
            mine = open_page(requester, "minhas_reservas")
            self.assertIn(title, [item.value for item in mine.subheader])
            self.assertNotIn("reservations", mine.session_state)
            institution = open_page(manager, "gerente_reservas")
            self.assertIn(title, institution.dataframe[0].value["Solicitação"].tolist())
            self.assertNotIn("reservations", institution.session_state)
            next(button for button in institution.button if button.label == "Analisar solicitação").click().run()
            institution.selectbox(key="reservation_decision").select("aprovada")
            institution.text_area[0].set_value("Aprovada pelo Streamlit")
            next(button for button in institution.button if button.label == "Confirmar decisão").click().run()
            self.assertFalse(institution.exception)
            self.assertIn("Aprovada", institution.dataframe[0].value["Status"].tolist())
            self.assertIn("Aprovada pelo Streamlit", [item.value for item in institution.text])

    def test_conflicts_detect_existing_overlaps_and_close_after_cancellation(self):
        own, info = self.register()
        other, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        foreign_admin = self.headers(self.login(other["responsible_email"]))
        manager = self.headers(self._manager_login(admin))
        foreign_manager = self.headers(self._manager_login(foreign_admin))
        owners = [self._requester_login(admin) for _ in range(3)]
        room = self._structure_room(admin, "Sala de Sobreposições")
        data = self._reservation_payload(room)
        start, end = (datetime.fromisoformat(data[key]) for key in ("start", "end"))
        intervals = [(start, end), (start + timedelta(minutes=30), end), (end, end + timedelta(hours=1))]
        with self.factory.begin() as session:
            for login, (begin, finish) in zip(owners, intervals, strict=True):
                session.add(Reserva(
                    instituicao_id=int(info["institution"]["id"]), espaco_id=int(room["id"]),
                    solicitante_id=int(login.json()["data"]["user"]["id"]), titulo=data["title"], tipo="Aula",
                    inicio=begin, fim=finish, quantidade_participantes=20,
                ))
        self.assertEqual(self.client.get("/conflicts", headers=manager).json()["data"]["items"], [])
        self.assertEqual(self.client.post("/conflicts/detect", headers=foreign_manager).json()["data"]["updated"], 0)
        scan = self.client.post("/conflicts/detect", headers=manager)
        self.assertEqual(scan.status_code, 200, scan.text)
        self.assertEqual(scan.json()["data"]["updated"], 1)
        self.assertEqual(self.client.post("/conflicts/detect", headers=manager).json()["data"]["updated"], 0)
        result = self.client.get("/conflicts", headers=manager, params={"query": room["name"], "status": "nao_resolvido"})
        item, = result.json()["data"]["items"]
        path = f"/conflicts/{item['id']}"
        requester = self.headers(owners[0])
        self.assertEqual(self.client.get("/conflicts", headers=requester).status_code, 403)
        self.assertEqual(self.client.get("/conflicts", headers=admin).status_code, 403)
        self.assertEqual(self.client.get(path, headers=foreign_manager).status_code, 404)
        self.assertEqual(self.client.get(path + "/alternatives", headers=foreign_manager).status_code, 404)
        self.assertEqual(self.client.post(path + "/resolve", headers=foreign_manager, json={
            "action": "manteve_a", "reason": "Aula",
        }).status_code, 404)
        own_reservation, = self.client.get("/reservations/mine", headers=requester).json()["data"]
        self.assertEqual(self.client.post(f"/reservations/{own_reservation['id']}/cancel",
                                          headers=requester).status_code, 200)
        resolved = self.client.get(path, headers=manager).json()["data"]
        self.assertEqual(resolved["status"], "resolvido")
        self.assertEqual(resolved["resolved_by"], owners[0].json()["data"]["user"]["id"])
        self.assertEqual(resolved["available_actions"], [])
        self.assertEqual(self.client.get("/conflicts", headers=manager, params={"status": "nao_resolvido"})
                         .json()["data"]["items"], [])

    def test_conflict_keep_rolls_back_and_serializes_competing_decisions(self):
        own, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        managers = [self.headers(self._manager_login(admin)) for _ in range(2)]
        room = self._structure_room(admin, "Sala de Conflitos")
        data = self._reservation_payload(room)
        for _ in range(2):
            owner = self.headers(self._requester_login(admin))
            created = self.client.post("/reservations", headers=owner, json=data)
            self.assertEqual(created.status_code, 201, created.text)
        item, = self.client.get("/conflicts", headers=managers[0]).json()["data"]["items"]
        path = f"/conflicts/{item['id']}"
        decision = {"action": "manteve_a", "reason": "Aula prioritária"}
        self.assertEqual(self.client.post(path + "/resolve", headers=managers[0],
                                          json={**decision, "reason": " "}).status_code, 422)
        block = f"/structure/spaces/{room['id']}/block"
        self.assertEqual(self.client.post(block, headers=managers[0], json={"reason": "Obra"}).status_code, 200)
        self.assertEqual(self.client.post(path + "/resolve", headers=managers[0], json=decision).status_code, 409)
        rolled_back = self.client.get(path, headers=managers[0]).json()["data"]
        self.assertEqual(rolled_back["status"], "nao_resolvido")
        self.assertIsNone(rolled_back["resolved_by"])
        for reservation in rolled_back["reservations"]:
            self.assertEqual(reservation["status"], "pendente")
            stored = self.client.get(f"/reservations/{reservation['id']}", headers=managers[0]).json()["data"]
            self.assertEqual([event["action"] for event in stored["history"]], ["criacao"])
        self.assertEqual(self.client.delete(block, headers=managers[0]).status_code, 200)

        ready = Barrier(2)

        def resolve(pair):
            action, headers = pair
            with TestClient(create_app(postgres_session_factory=self.factory)) as api:
                ready.wait(timeout=10)
                return api.post(path + "/resolve", headers=headers, json={**decision, "action": action})

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(resolve, zip(("manteve_a", "manteve_b"), managers, strict=True)))
        self.assertCountEqual([response.status_code for response in responses], [200, 409])
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            result = restarted.get(path, headers=managers[0]).json()["data"]
        self.assertEqual(result["status"], "resolvido")
        self.assertEqual(result["resolver_name"], "Gerente Teste")
        self.assertIn(decision["reason"], result["decision"])
        self.assertCountEqual([reservation["status"] for reservation in result["reservations"]],
                              ["aprovada", "rejeitada"])

    def test_conflict_streamlit_moves_reservation_to_compatible_room(self):
        own, _ = self.register()
        other, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        foreign_admin = self.headers(self.login(other["responsible_email"]))
        login = self._manager_login(admin)
        manager = self.headers(login)
        source = self._structure_room(admin, "Sala Original")
        foreign = self._structure_room(foreign_admin, "Sala de Outra Instituição")
        resource = self.client.post("/structure/resources", headers=manager, json={"name": "Projetor", "quantity_total": 8})
        self.assertEqual(resource.status_code, 201, resource.text)
        resource_id = resource.json()["data"]["id"]

        def room(name, capacity=20, quantity=0):
            response = self.client.post("/structure/spaces", headers=admin, json={
                "floor_id": source["floor_id"], "name": name, "type": "Sala", "capacity": capacity,
            })
            self.assertEqual(response.status_code, 201, response.text)
            room_id = response.json()["data"]["id"]
            if quantity:
                response = self.client.put(f"/structure/spaces/{room_id}/resources", headers=manager,
                                           json={"resource_ids": [resource_id], "quantities": {resource_id: quantity}})
                self.assertEqual(response.status_code, 200, response.text)
            return room_id

        assigned = self.client.put(f"/structure/spaces/{source['id']}/resources", headers=manager,
                                   json={"resource_ids": [resource_id], "quantities": {resource_id: 2}})
        self.assertEqual(assigned.status_code, 200, assigned.text)
        compatible = room("Sala Compatível", quantity=2)
        busy = room("Sala com Solicitação", quantity=2)
        room("Sala Pequena", capacity=10)
        incompatible = room("Sala sem Equipamento")
        limited = room("Sala com Pouco Equipamento", quantity=1)
        owners = [self.headers(self._requester_login(admin)) for _ in range(2)]
        payload = self._reservation_payload(source)
        for index, owner in enumerate(owners):
            created = self.client.post("/reservations", headers=owner, json={**payload, "title": f"Oficina {index}"})
            self.assertEqual(created.status_code, 201, created.text)
        busy_slot = self.client.post("/reservations", headers=owners[0], json={**payload, "space_id": busy})
        self.assertEqual(busy_slot.status_code, 201, busy_slot.text)
        item, = self.client.get("/conflicts", headers=manager).json()["data"]["items"]
        path = f"/conflicts/{item['id']}"
        a, b = item["reservations"]
        suggestions = self.client.get(path + "/alternatives", headers=manager).json()["data"]
        for reservation in (a, b):
            self.assertEqual([space["id"] for space in suggestions[reservation["id"]]], [compatible])
        for invalid in (incompatible, limited, busy, foreign["id"]):
            failed = self.client.post(path + "/resolve", headers=manager, json={
                "action": "alterou", "reason": "Realocação", "reservation_id": a["id"], "space_id": invalid,
            })
            self.assertEqual(failed.status_code, 409, failed.text)
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "gerente_conflitos"
            app.session_state["auth_token"] = login.json()["data"]["access_token"]
            app.run()
            self.assertFalse(app.exception)
            self.assertNotIn("conflicts", app.session_state)
            self.assertEqual(app.dataframe[0].value["Status"].tolist(), ["Em aberto"])
            app.button(key="btn_resolve_conflict").click().run()
            app.selectbox(key=f"conflict_outcome_{item['id']}").select("alterou").run()
            app.text_area(key=f"conflict_justification_{item['id']}").set_value("Realocada com projetores")
            next(button for button in app.button if button.label == "Aplicar decisão").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.dataframe[0].value["Status"].tolist(), ["Resolvido"])
        resolved = self.client.get(path, headers=manager).json()["data"]
        self.assertIn("Realocada com projetores", resolved["decision"])
        moved, kept = resolved["reservations"]
        self.assertEqual((moved["space_id"], moved["status"]), (compatible, "em_analise"))
        self.assertEqual((kept["space_id"], kept["status"]), (source["id"], "pendente"))
        history = self.client.get(f"/reservations/{a['id']}", headers=manager).json()["data"]["history"]
        self.assertEqual(history[-1]["reason"], "Realocada com projetores")

    def test_notification_recipients_reads_and_history_are_scoped_to_the_membership(self):
        own, _ = self.register()
        other, other_info = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        outside_admin = self.headers(self.login(other["responsible_email"]))
        manager_login = self._manager_login(admin)
        manager = self.headers(manager_login)
        coworker = self.headers(self._manager_login(admin))
        inactive_login = self._manager_login(admin)
        disabled = self.client.patch(f"/admin/users/{inactive_login.json()['data']['user']['id']}/status", headers=admin,
                                     json={"status": "inativo"})
        self.assertEqual(disabled.status_code, 200, disabled.text)
        requester_login = self._requester_login(admin)
        requester = self.headers(requester_login)
        another_requester = self.headers(self._requester_login(admin))
        user = manager_login.json()["data"]["user"]
        outside_id = other_info["institution"]["id"]
        with self.factory.begin() as session:
            session.add(UsuarioInstituicao(user_id=int(user["id"]), institution_id=int(outside_id),
                                          role="gerente", status="ativo"))
        outside = self.headers(self.login(user["email"], outside_id))
        room = self._structure_room(admin, "Sala de notificações")
        data = self._reservation_payload(room)
        self.assertEqual(self.client.get("/notifications").status_code, 401)

        def inbox(headers, **params):
            response = self.client.get("/notifications", headers=headers, params=params)
            self.assertEqual(response.status_code, 200, response.text)
            return response.json()["data"]

        created = self.client.post("/reservations", headers=requester, json=data)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(self.client.post("/reservations", headers=requester, json=data).status_code, 409)
        reservation_id = created.json()["data"]["id"]
        path = f"/reservations/{reservation_id}"
        item, = inbox(manager)["items"]
        self.assertEqual((item["title"], item["reservation_id"]), ("Nova solicitação de reserva", reservation_id))
        self.assertEqual(inbox(coworker)["items"][0]["id"], item["id"])
        with self.factory.begin() as session:
            recipients = session.scalars(select(DestinatarioNotificacao.usuario_id).where(
                DestinatarioNotificacao.notificacao_id == int(item["id"]),
            )).all()
        self.assertEqual(len(recipients), 2)
        self.assertNotIn(int(inactive_login.json()["data"]["user"]["id"]), recipients)
        for credential in (outside, outside_admin, admin, requester, another_requester):
            self.assertEqual(inbox(credential)["items"], [])
        read_path = f"/notifications/{item['id']}/read"
        self.assertEqual(self.client.patch(read_path, headers=outside).status_code, 404)
        self.assertEqual(self.client.patch(read_path, headers=requester).status_code, 404)
        first_read = self.client.patch(read_path, headers=manager)
        self.assertEqual(first_read.status_code, 200, first_read.text)
        self.assertEqual(self.client.patch(read_path, headers=manager).json(), first_read.json())
        self.assertEqual(inbox(manager, unread_only=True)["items"], [])
        self.assertEqual(inbox(coworker)["unread_count"], 1)
        self.assertEqual(self.client.patch("/notifications/read", headers=manager).json()["data"]["updated"], 0)
        self.assertEqual(self.client.patch("/notifications/read", headers=coworker).json()["data"]["updated"], 1)

        changes = {**data, "title": "Oficina atualizada", "reason": "Ajuste operacional"}
        for _ in range(2):
            edited = self.client.put(path, headers=manager, json=changes)
            self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(inbox(manager)["total"], 1)
        self.assertEqual(inbox(coworker, category="alteracao")["total"], 1)
        self.assertEqual(inbox(requester, category="alteracao")["total"], 1)
        decision = self.client.patch(path + "/decision", headers=manager, json={"status": "aprovada"})
        self.assertEqual(decision.status_code, 200, decision.text)
        self.assertEqual(self.client.patch(path + "/decision", headers=coworker,
                                           json={"status": "aprovada"}).status_code, 409)
        cancelled = self.client.post(path + "/cancel", headers=requester, json={"reason": "Turma indisponível"})
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(self.client.post(path + "/cancel", headers=requester).status_code, 409)
        events = inbox(requester)
        self.assertCountEqual([item["title"] for item in events["items"]],
                              ["Reserva alterada", "Reserva aprovada", "Reserva cancelada"])
        self.assertEqual(inbox(requester, limit=1, offset=1)["items"][0]["id"], events["items"][1]["id"])
        other_reservation = self.client.post("/reservations", headers=requester, json=data)
        rejection = self.client.patch(f"/reservations/{other_reservation.json()['data']['id']}/decision",
                                      headers=manager, json={"status": "rejeitada", "reason": "Fora da política"})
        self.assertEqual(rejection.status_code, 200, rejection.text)
        rejected = inbox(requester)["items"][0]
        self.assertEqual(rejected["title"], "Reserva rejeitada")
        self.assertIn("Fora da política", rejected["message"])
        self.assertEqual(self.client.get(f"/reservations/mine/{reservation_id}", headers=another_requester).status_code,
                         404)
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            self.assertEqual(restarted.get("/notifications/unread-count", headers=requester).json()["data"],
                             {"unread_count": 4})
            history = restarted.get(f"/reservations/mine/{reservation_id}", headers=requester).json()["data"]["history"]
        self.assertEqual([event["action"] for event in history], ["criacao", "edicao", "avaliacao", "cancelamento"])
        self.assertEqual([event["reason"] for event in history],
                         [data["justification"], "Ajuste operacional", None, "Turma indisponível"])
        self.assertEqual(history[0]["actor_id"], requester_login.json()["data"]["user"]["id"])
        self.assertEqual(history[1]["actor_id"], user["id"])

    def test_notification_rollback_and_institutional_preferences(self):
        own, info = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        manager = self.headers(self._manager_login(admin))
        requester = self.headers(self._requester_login(admin))
        room = self._structure_room(admin, "Sala para rollback de avisos")
        data = self._reservation_payload(room)
        add = PostgresNotificationRepository.add

        def fail_recipient_constraint(repository, institution_id, item, recipients):
            return add(repository, institution_id, item, recipients | {"-1"})

        with patch.object(PostgresNotificationRepository, "add", fail_recipient_constraint):
            failed_creation = self.client.post("/reservations", headers=requester, json=data)
        self.assertEqual(failed_creation.status_code, 409, failed_creation.text)
        self.assertEqual(self.client.get("/reservations/mine", headers=requester).json()["data"], [])
        created = self.client.post("/reservations", headers=requester, json=data)
        self.assertEqual(created.status_code, 201, created.text)
        reservation_id = created.json()["data"]["id"]
        path = f"/reservations/{reservation_id}"
        with patch.object(PostgresNotificationRepository, "add", fail_recipient_constraint):
            failed_approval = self.client.patch(path + "/decision", headers=manager, json={"status": "aprovada"})
        self.assertEqual(failed_approval.status_code, 409, failed_approval.text)
        self.assertNotIn("fk_notificacao_destinatarios_usuario", failed_approval.text)
        record = self.client.get(path, headers=manager).json()["data"]
        self.assertEqual(record["status"], "pendente")
        self.assertEqual([event["action"] for event in record["history"]], ["criacao"])
        institution = info["institution"]
        with self.factory.begin() as session:
            notifications = session.scalars(select(Notificacao.titulo).where(
                Notificacao.instituicao_id == int(institution["id"]),
            )).all()
        self.assertEqual(notifications, ["Nova solicitação de reserva"])

        preferences = institution["preferences"]
        preferences["notifications"].update(reservation_approved=False, reservation_rejected=False,
                                            reservation_cancelled=False, space_changed=False)
        saved = self.client.patch("/institutions/me", headers=admin,
                                  json={"name": institution["name"], "preferences": preferences})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.client.put(path, headers=manager, json={**data, "title": "Atualizada"}).status_code, 200)
        self.assertEqual(self.client.patch(path + "/decision", headers=manager, json={"status": "aprovada"}).status_code, 200)
        self.assertEqual(self.client.post(path + "/cancel", headers=requester).status_code, 200)
        new = self.client.post("/reservations", headers=requester, json=data)
        self.assertEqual(new.status_code, 201, new.text)
        self.assertEqual(self.client.patch(f"/reservations/{new.json()['data']['id']}/decision", headers=manager,
                                         json={"status": "rejeitada", "reason": "Motivo"}).status_code, 200)
        self.assertEqual(self.client.get("/notifications", headers=requester).json()["data"]["total"], 0)
        self.assertEqual([item["title"] for item in self.client.get("/notifications", headers=manager)
                          .json()["data"]["items"]], ["Nova solicitação de reserva"] * 2)
        preferences["reservations"]["automatic_approval"] = "no_conflict"
        preferences["notifications"]["reservation_approved"] = True
        saved = self.client.patch("/institutions/me", headers=admin,
                                  json={"name": institution["name"], "preferences": preferences})
        self.assertEqual(saved.status_code, 200, saved.text)
        automatic = self.client.post("/reservations", headers=requester, json=data)
        self.assertEqual(automatic.status_code, 201, automatic.text)
        reservation = automatic.json()["data"]
        self.assertEqual(reservation["status"], "aprovada")
        self.assertEqual(self.client.post("/reservations", headers=requester, json=data).status_code, 409)
        item, = self.client.get("/notifications", headers=requester).json()["data"]["items"]
        self.assertEqual((item["title"], item["reservation_id"]), ("Reserva aprovada", reservation["id"]))
        history = self.client.get(f"/reservations/mine/{reservation['id']}", headers=requester).json()["data"]["history"]
        self.assertEqual([event["action"] for event in history], ["criacao", "aprovacao_automatica"])
        self.assertIsNone(history[1]["actor_id"])

    def test_streamlit_reads_notifications_and_shows_requester_history(self):
        own, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        manager_login = self._manager_login(admin)
        requester_login = self._requester_login(admin)
        manager = self.headers(manager_login)
        requester = self.headers(requester_login)
        room = self._structure_room(admin, "Sala de histórico Streamlit")
        payload = self._reservation_payload(room)
        result = self.client.post("/reservations", headers=requester, json=payload)
        self.assertEqual(result.status_code, 201, result.text)
        reservation_id = result.json()["data"]["id"]
        item, = self.client.get("/notifications", headers=manager).json()["data"]["items"]
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "notificacoes"
            app.session_state["auth_token"] = manager_login.json()["data"]["access_token"]
            app.run()
            self.assertFalse(app.exception)
            self.assertIn("Nova solicitação de reserva", [item.value for item in app.subheader])
            self.assertNotIn("notifications", app.session_state)
            app.button(key=f"btn_read_{item['id']}").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(self.client.get("/notifications/unread-count", headers=manager).json()["data"],
                             {"unread_count": 0})

            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "minhas_reservas"
            app.session_state["auth_token"] = requester_login.json()["data"]["access_token"]
            app.run()
            app.button(key=f"history_{reservation_id}").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Solicitação criada" in item.value for item in app.caption))
            self.assertIn(payload["justification"], [item.value for item in app.text])

    def test_manager_operations_filters_rates_and_refreshes_after_decisions(self):
        own, info = self.register()
        other, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        foreign_admin = self.headers(self.login(other["responsible_email"]))
        manager_login = self._manager_login(admin)
        manager = self.headers(manager_login)
        foreign_manager = self.headers(self._manager_login(foreign_admin))
        requester_login = self._requester_login(admin)
        requester = self.headers(requester_login)
        institution = info["institution"]
        institution["preferences"]["reservations"].update(allowed_start="08:00", allowed_end="18:00")
        updated = self.client.patch("/institutions/me", headers=admin, json={
            "name": institution["name"], "timezone": "America/Manaus", "preferences": institution["preferences"],
        })
        self.assertEqual(updated.status_code, 200, updated.text)
        room = self._structure_room(admin, "Sala dos Indicadores")
        foreign = self._structure_room(foreign_admin, "Sala de Outra Instituição")
        building = self.client.post("/structure/buildings", headers=admin, json={"name": "Bloco B"}).json()["data"]
        floor = self.client.post(f"/structure/buildings/{building['id']}/floors", headers=admin,
                                 json={"name": "Térreo"}).json()["data"]
        spare = self.client.post("/structure/spaces", headers=admin, json={
            "floor_id": floor["id"], "name": "Sala Livre", "type": "Sala", "capacity": 25,
        }).json()["data"]
        timezone = ZoneInfo("America/Manaus")
        start = (datetime.now(timezone) + timedelta(days=3)).replace(hour=8, minute=0, second=0, microsecond=0)
        day = start.date()
        ids = []
        for index, (begin, finish) in enumerate(((0, 2), (2, 3), (3, 4), (4, 5))):
            created = self.client.post("/reservations", headers=requester, json={
                **self._reservation_payload(room), "title": f"Atividade {index}",
                "start": (start + timedelta(hours=begin)).isoformat(), "end": (start + timedelta(hours=finish)).isoformat(),
            })
            self.assertEqual(created.status_code, 201, created.text)
            ids.append(created.json()["data"]["id"])
        for reservation_id, status in ((ids[0], "aprovada"), (ids[2], "rejeitada")):
            decision = self.client.patch(f"/reservations/{reservation_id}/decision", headers=manager, json={
                "status": status, "reason": "Decisão de teste",
            })
            self.assertEqual(decision.status_code, 200, decision.text)
        self.assertEqual(self.client.post(f"/reservations/{ids[3]}/cancel", headers=requester).status_code, 200)

        path = "/manager/operations"
        query = {"start_date": day.isoformat()}
        self.assertEqual(self.client.get(path, headers=requester).status_code, 403)
        self.assertEqual(self.client.get(path + "/context", headers=admin).status_code, 403)
        self.assertEqual(self.client.get(path, headers=foreign_manager, params={**query, "space_id": room["id"]})
                         .status_code, 404)
        self.assertEqual(self.client.get(path, headers=manager, params={**query, "building_id": foreign["building_id"]})
                         .status_code, 404)
        context = self.client.get(path + "/context", headers=manager).json()["data"]
        self.assertEqual(context["timezone"], "America/Manaus")
        self.assertEqual(context["today"], datetime.now(timezone).date().isoformat())
        self.assertCountEqual([item["id"] for item in context["spaces"]], [room["id"], spare["id"]])

        def report(**filters):
            response = self.client.get(path, headers=manager, params={**query, **filters})
            self.assertEqual(response.status_code, 200, response.text)
            return response.json()["data"]

        listing = report()
        self.assertEqual(listing["metrics"], {
            "total": 4, "pending": 1, "approved": 1, "rejected": 1, "cancelled": 1, "conflicts": 0, "occupied_spaces": 1,
        })
        self.assertAlmostEqual(listing["occupancy_rate"], 0.1)
        self.assertEqual(listing["space_counts"]["available"], 1)
        selected = report(building_id=room["building_id"], status="pendente")
        self.assertEqual([row["id"] for row in selected["reservations"]], [ids[1]])
        self.assertEqual([row["id"] for row in selected["spaces"]], [room["id"]])
        self.assertAlmostEqual(selected["occupancy_rate"], 0.2)
        self.assertEqual(selected["space_counts"]["available"], 0)
        clipped = report(space_id=room["id"], start_time="09:00", end_time="11:00")
        self.assertEqual(clipped["spaces"][0]["occupied_seconds"], 3600)
        self.assertAlmostEqual(clipped["occupancy_rate"], 0.5)
        adjacent = report(space_id=room["id"], start_time="10:00", end_time="11:00")
        self.assertEqual(adjacent["metrics"]["approved"], 0)
        self.assertEqual(adjacent["space_counts"]["available"], 1)
        empty = report(start_date=(day + timedelta(days=1)).isoformat())
        self.assertEqual(empty["metrics"]["total"], 0)
        self.assertEqual(empty["occupancy_rate"], 0)
        self.assertEqual(empty["space_counts"]["available"], 2)
        before_rooms = datetime.now(timezone).date() - timedelta(days=1)
        self.assertEqual(report(start_date=before_rooms.isoformat())["space_counts"]["unavailable"], 2)
        self.assertAlmostEqual(report(end_date=(day + timedelta(days=1)).isoformat())["occupancy_rate"], 0.05)
        for invalid in ({"end_date": (day - timedelta(days=1)).isoformat()}, {"start_time": "09:00"},
                        {"start_time": "07:30", "end_time": "09:30"}):
            self.assertEqual(self.client.get(path, headers=manager, params={**query, **invalid}).status_code, 422)

        # Historical block overlaps one hour of the approved reservation.
        with self.factory.begin() as session:
            session.execute(bloqueios_espaco.insert().values(
                instituicao_id=int(institution["id"]), espaco_id=int(room["id"]),
                responsavel_id=int(manager_login.json()["data"]["user"]["id"]), motivo="Bloqueio de teste",
                bloqueado_em=start + timedelta(minutes=30), desbloqueado_em=start + timedelta(minutes=90),
            ))
            late = start.replace(hour=23, minute=30)
            session.add(Reserva(
                instituicao_id=int(institution["id"]), espaco_id=int(spare["id"]),
                solicitante_id=int(requester_login.json()["data"]["user"]["id"]), titulo="Data local", tipo="Aula",
                inicio=late, fim=late + timedelta(minutes=15), quantidade_participantes=1,
            ))
        historical = report(space_id=room["id"])
        self.assertEqual(historical["spaces"][0]["status"], "bloqueado")
        self.assertEqual(historical["spaces"][0]["blocked_seconds"], 3600)
        self.assertAlmostEqual(historical["occupancy_rate"], 1 / 9)
        self.assertEqual([item["title"] for item in report(space_id=spare["id"])["reservations"]], ["Data local"])
        self.assertEqual(report(space_id=spare["id"], start_date=(day + timedelta(days=1)).isoformat())
                         ["metrics"]["total"], 0)
        self.assertEqual(self.client.post(f"/reservations/{ids[0]}/cancel", headers=requester).status_code, 200)
        final = report(space_id=room["id"])
        self.assertEqual(final["metrics"]["approved"], 0)
        self.assertEqual(final["metrics"]["cancelled"], 2)
        self.assertEqual(final["occupancy_rate"], 0)

    def test_streamlit_manager_dashboard_and_occupancy_use_persisted_status(self):
        own, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        login = self._manager_login(admin)
        manager = self.headers(login)
        requester = self.headers(self._requester_login(admin))
        room = self._structure_room(admin, "Sala Painel Real")
        payload = self._reservation_payload(room)
        created = self.client.post("/reservations", headers=requester, json={**payload, "title": "Aula do Painel Real"})
        self.assertEqual(created.status_code, 201, created.text)
        reservation = created.json()["data"]
        day = datetime.fromisoformat(payload["start"]).date()
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "gerente_dashboard"
            app.session_state["auth_token"] = login.json()["data"]["access_token"]
            app.run()
            self.assertFalse(app.exception)
            app.date_input(key="dashboard_start").set_value(day).run()
            self.assertEqual({item.label: item.value for item in app.metric}["Pendentes"], "1")
            self.assertIn("Aula do Painel Real", app.dataframe[0].value["Título"].tolist())
            approved = self.client.patch(f"/reservations/{reservation['id']}/decision",
                                         headers=manager, json={"status": "aprovada"})
            self.assertEqual(approved.status_code, 200, approved.text)
            app.run()
            metrics = {item.label: item.value for item in app.metric}
            self.assertEqual((metrics["Pendentes"], metrics["Aprovadas"]), ("0", "1"))
            app.button(key="manager_dashboard_ver_ocupacao").click().run()
            app.date_input(key="occupancy_date").set_value(day).run()
            self.assertFalse(app.exception)
            self.assertEqual({item.label: item.value for item in app.metric}["Taxa de ocupação no período"], "6.7%")
            self.assertNotIn("reservations", app.session_state)
            self.assertEqual(app.selectbox(key="occupancy_reservation_selector").value, reservation["id"])
            next(button for button in app.button if button.label == "Ver detalhes").click().run()
            self.assertIn("Aula do Painel Real", [item.value for item in app.subheader])
            app.selectbox(key="occupancy_status").select("pendente").run()
            self.assertEqual(app.selectbox(key="occupancy_status").value, "pendente")
            self.assertFalse(any(item.key == "occupancy_reservation_selector" for item in app.selectbox))
            self.assertEqual({item.label: item.value for item in app.metric}["Salas disponíveis no período"], "0")

    def test_manager_persists_room_changes_blocks_and_reports_real_availability(self):
        own, registration = self.register()
        foreign, _ = self.register()
        admin = self.headers(self.login(own["responsible_email"]))
        outside = self.headers(self.login(foreign["responsible_email"]))
        login = self._manager_login(admin)
        manager = self.headers(login)
        room = self._structure_room(admin, "Sala Gerente")
        foreign_room = self._structure_room(outside, "Sala Externa")
        path = f"/structure/spaces/{room['id']}"
        resource = self.client.post("/structure/resources", headers=manager, json={"name": "Projetor"})
        foreign_resource = self.client.post("/structure/resources", headers=outside, json={"name": "Projetor"})
        self.assertEqual((resource.status_code, foreign_resource.status_code), (201, 201))
        resource_id = resource.json()["data"]["id"]
        foreign_resource_id = foreign_resource.json()["data"]["id"]
        self.assertEqual(self.client.get(f"/structure/spaces/{foreign_room['id']}", headers=manager).status_code, 404)
        self.assertEqual(self.client.post(f"/structure/spaces/{foreign_room['id']}/block", headers=manager,
                                         json={"reason": "Manutenção"}).status_code, 404)
        rejected = self.client.put(path + "/configuration", headers=manager, json={
            "name": "Não deve gravar", "type": "Estúdio", "capacity": 30, "resource_ids": [foreign_resource_id],
        })
        self.assertEqual(rejected.status_code, 404, rejected.text)
        original = self.client.get(path, headers=manager).json()["data"]
        self.assertEqual((original["name"], original["type"], original["capacity"]), ("Sala Gerente", "Sala", 20))
        change = {"name": "Estúdio 01", "type": "Estúdio", "capacity": 24, "resource_ids": [resource_id]}
        changed = self.client.put(path + "/configuration", headers=manager, json=change)
        self.assertEqual(changed.status_code, 200, changed.text)

        now = datetime.now(timezone.utc)
        with self.factory.begin() as session:
            session.add(Reserva(
                instituicao_id=int(room["institution_id"]), espaco_id=int(room["id"]),
                solicitante_id=int(registration["administrator"]["id"]), titulo="Reserva vigente",
                tipo="Aula", inicio=now - timedelta(minutes=5), fim=now + timedelta(hours=1),
                quantidade_participantes=12, status="aprovada",
            ))
        result = self.client.get("/structure/spaces", headers=manager, params={
            "q": "01", "building_id": room["building_id"], "floor_id": room["floor_id"], "room_type": "Estúdio",
            "min_capacity": 24, "max_capacity": 24, "resource_id": resource_id, "status": "ocupado",
        }).json()["data"]
        self.assertEqual([(row["id"], row["occupancy"], row["occupancy_verified"]) for row in result],
                         [(room["id"], 12, True)])
        blocked = self.client.post(path + "/block", headers=manager, json={"reason": "  Manutenção elétrica  "})
        self.assertEqual(blocked.status_code, 200, blocked.text)
        self.assertEqual(blocked.json()["data"]["status"], "bloqueado")
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            saved = restarted.get(path, headers=manager).json()["data"]
            self.assertEqual((saved["name"], saved["capacity"], saved["resource_ids"]),
                             ("Estúdio 01", 24, [resource_id]))
            self.assertEqual(saved["block_reason"], "Manutenção elétrica")
            self.assertEqual(restarted.patch(path, headers=manager, json={"status": "disponivel"}).status_code, 422)
            unblocked = restarted.delete(path + "/block", headers=manager).json()["data"]
            self.assertEqual((unblocked["status"], unblocked["block_reason"]), ("ocupado", None))
            changed = restarted.put(path + "/configuration", headers=manager, json={**change, "resource_ids": []})
            self.assertEqual(changed.json()["data"]["resource_ids"], [])
        with self.factory() as session:
            entry = session.execute(select(bloqueios_espaco).where(
                bloqueios_espaco.c.espaco_id == int(room["id"]),
            )).one()
            self.assertEqual(entry.motivo, "Manutenção elétrica")
            self.assertEqual(entry.responsavel_id, int(login.json()["data"]["user"]["id"]))
            self.assertIsNotNone(entry.desbloqueado_em)

    def test_manager_reactivation_preserves_an_open_block_and_admin_behavior(self):
        payload, _ = self.register()
        admin = self.headers(self.login(payload["responsible_email"]))
        manager = self.headers(self._manager_login(admin))
        requester = self.headers(self._requester_login(admin))
        room = self._structure_room(admin, "Sala de reativação")
        path = f"/structure/spaces/{room['id']}"
        reason = "Manutenção em andamento"
        self.assertEqual(self.client.post(path + "/block", headers=manager, json={"reason": reason}).status_code, 200)
        self.assertEqual(self.client.patch(path + "/status", headers=manager, json={"active": False}).status_code, 200)
        restored = self.client.patch(path + "/status", headers=manager, json={"active": True})
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()["data"]["status"], "bloqueado")
        self.assertEqual(restored.json()["data"]["block_reason"], reason)
        request = self._reservation_payload(room)
        self.assertEqual(self.client.post("/reservations", headers=requester, json=request).status_code, 409)
        self.assertEqual(self.client.delete(path + "/block", headers=manager).status_code, 200)
        self.assertEqual(self.client.post("/reservations", headers=requester, json=request).status_code, 201)

        self.assertEqual(self.client.post(path + "/block", headers=admin, json={"reason": reason}).status_code, 200)
        self.assertEqual(self.client.patch(path + "/status", headers=admin, json={"active": False}).status_code, 200)
        restored = self.client.patch(path + "/status", headers=admin, json={"active": True})
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()["data"]["status"], "disponivel")

    def test_registration_session_settings_and_audit_survive_runtime_restart(self):
        payload, registration = self.register()
        login = self.login(payload["responsible_email"].upper())
        headers = self.headers(login)
        digest = hashlib.sha256(login.json()["data"]["access_token"].encode()).hexdigest()
        with self.factory.begin() as session:
            self.assertIsNotNone(session.scalar(select(sessions.c.token_digest).where(sessions.c.token_digest == digest)))
            code_digest = session.scalar(select(institution_invites.c.digest).where(
                institution_invites.c.instituicao_id == int(registration["institution"]["id"])))
            self.assertEqual(code_digest, hashlib.sha256(registration["invitation_code"].encode()).hexdigest())

        update = self.client.patch("/institutions/me", headers=headers, json={
            "name": "Instituição atualizada", "address": "Rua de Teste",
        })
        self.assertEqual(update.status_code, 200, update.text)
        invalid = self.client.patch("/institutions/me", headers=headers, json={"name": "x" * 151})
        self.assertEqual(invalid.status_code, 422)
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            institution = restarted.get("/institutions/me", headers=headers).json()["data"]
            self.assertEqual(institution["name"], "Instituição atualizada")
            self.assertEqual(institution["address"], "Rua de Teste")
            events = restarted.get("/admin/audit", headers=headers).json()["data"]
            self.assertEqual(len(events), 4)
            self.assertEqual(restarted.post("/auth/logout", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/auth/me", headers=headers).status_code, 401)

    def test_membership_selection_and_tenant_isolation(self):
        payload, first = self.register()
        other_payload, second = self.register()
        first_id = first["institution"]["id"]
        second_id = second["institution"]["id"]
        owner = first["administrator"]["id"]
        with self.factory.begin() as session:
            session.add(UsuarioInstituicao(
                user_id=int(owner), institution_id=int(second_id), role="gerente", status="ativo",
            ))
        selection = self.login(payload["responsible_email"])
        self.assertEqual(selection.status_code, 409)
        self.assertEqual({row["institution_id"] for row in selection.json()["error"]["details"]},
                         {first_id, second_id})
        invalid = self.client.post("/auth/login", json={
            "email": payload["responsible_email"], "password": "incorrect",
        })
        self.assertEqual(invalid.status_code, 401)
        manager = self.headers(self.login(payload["responsible_email"], second_id))
        self.assertEqual(self.client.get("/auth/me", headers=manager).json()["data"]["profile"], "gerente")
        self.assertEqual(self.client.get("/admin/audit", headers=manager).status_code, 403)
        headers = self.headers(self.login(other_payload["responsible_email"]))
        identity = self.client.patch(f"/admin/users/{owner}", headers=headers, json={
            "name": "Nome alterado por outra instituição", "email": payload["responsible_email"],
        })
        self.assertEqual(identity.status_code, 403)
        result = self.client.patch(f"/admin/users/{owner}/status", headers=headers, json={"status": "inativo"})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.client.get("/auth/me", headers=manager).status_code, 401)
        self.assertEqual(self.login(payload["responsible_email"], first_id).status_code, 200)

    def test_concurrent_demotion_preserves_last_admin_and_audits_only_success(self):
        payload, registration = self.register()
        first = registration["administrator"]["id"]
        headers = self.headers(self.login(payload["responsible_email"]))
        tag = secrets.token_hex(5)
        result = self.client.post("/admin/users", headers=headers, json={
            "name": "Outro admin", "email": f"{tag}@example.test", "password": PASSWORD, "profile": "admin",
        })
        self.assertEqual(result.status_code, 201, result.text)
        second = result.json()["data"]["id"]
        second_headers = self.headers(self.login(f"{tag}@example.test"))

        def demote(selected):
            user_id, credential = selected
            return self.client.patch(f"/admin/users/{user_id}/profile", headers=credential,
                                     json={"profile": "gerente"})

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = tuple(pool.map(demote, [(first, headers), (second, second_headers)]))
        self.assertEqual(sorted(row.status_code for row in results), [200, 409])
        surviving = second_headers if results[0].status_code == 200 else headers
        events = self.client.get("/admin/audit", headers=surviving,
                                 params={"action": "user.profile_changed"}).json()["data"]
        self.assertEqual(len(events), 1)

    def test_invitation_rotation_and_revocation_persist(self):
        payload, registration = self.register()
        headers = self.headers(self.login(payload["responsible_email"]))
        path = "/institutions/me/invitation-code"
        rotated = self.client.post(path + "/rotate", headers=headers)
        self.assertEqual(rotated.status_code, 200, rotated.text)
        self.assertNotEqual(rotated.json()["data"]["code"], registration["invitation_code"])
        self.assertEqual(self.client.delete(path, headers=headers).status_code, 200)
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            data = restarted.get(path, headers=headers).json()["data"]
            self.assertFalse(data["active"])
            self.assertNotIn("code", data)

    def test_expired_session_is_rejected_after_restart(self):
        payload, _ = self.register()
        login = self.login(payload["responsible_email"])
        headers = self.headers(login)
        token = login.json()["data"]["access_token"].encode()
        with self.factory.begin() as session:
            session.execute(update(sessions).where(sessions.c.token_digest == hashlib.sha256(token).hexdigest())
                            .values(expira_em=datetime.now(timezone.utc) - timedelta(seconds=1)))
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            self.assertEqual(restarted.get("/auth/me", headers=headers).status_code, 401)

    def test_original_constraint_rejects_simultaneous_overlapping_approvals(self):
        _, registration = self.register()
        institution_id = int(registration["institution"]["id"])
        owner_id = int(registration["administrator"]["id"])
        with self.factory.begin() as session:
            room = Espaco(instituicao_id=institution_id, nome="Sala de teste", tipo="Sala",
                          capacidade=20, localizacao="Térreo")
            session.add(room)
            session.flush()
            room_id = room.id
        start = datetime.now(timezone.utc) + timedelta(days=1)

        def approve(_):
            for attempt in range(2):
                try:
                    with self.factory.begin() as session:
                        session.add(Reserva(
                            instituicao_id=institution_id, espaco_id=room_id, solicitante_id=owner_id,
                            titulo="Reserva de teste", tipo="Aula", inicio=start, fim=start + timedelta(hours=1),
                            quantidade_participantes=10, status="aprovada",
                        ))
                    return None
                except IntegrityError as exc:
                    return exc.orig.diag.constraint_name
                except OperationalError as exc:
                    if attempt or exc.orig.sqlstate != "40P01":
                        raise

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = tuple(pool.map(approve, range(2)))
        self.assertCountEqual(results, (None, "ex_reservas_aprovadas_periodo"))

    def test_member_verification_survives_restart_and_consumes_enrollment_once(self):
        payload, registration = self.register()
        admin = self.headers(self.login(payload["responsible_email"]))
        member_email = f"{secrets.token_hex(5)}@example.test"
        enrollment = self.client.post("/admin/enrollments", headers=admin, json={
            "registration_number": "RA 2026", "name": "Novo membro", "email": member_email,
        })
        self.assertEqual(enrollment.status_code, 201, enrollment.text)
        duplicate = self.client.post("/admin/enrollments", headers=admin, json={"registration_number": "ra2026"})
        self.assertEqual(duplicate.status_code, 409)
        started = self.client.post("/auth/signup/member/start", json={
            "name": "Novo membro", "email": member_email, "registration_number": "ra2026",
            "institutional_code": registration["invitation_code"], "password": PASSWORD,
        })
        self.assertEqual(started.status_code, 202, started.text)
        token = self.mailbox.latest_for(member_email).verification_token
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            def verify(_):
                return restarted.post("/auth/signup/member/verify-email", json={"token": token})

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = tuple(pool.map(verify, range(2)))
        self.assertEqual(sorted(row.status_code for row in results), [200, 400], [row.text for row in results])
        saved = self.client.get("/admin/enrollments", headers=admin).json()["data"][0]
        self.assertEqual(saved["status"], "utilizado")
        self.assertEqual(self.login(member_email).status_code, 200)
        with self.factory.begin() as session:
            membership = session.scalar(select(UsuarioInstituicao).where(
                UsuarioInstituicao.user_id == int(saved["used_by_user_id"]),
            ))
            self.assertEqual(membership.registration_number, "RA 2026")
            pending = session.execute(select(pending_signups).where(
                pending_signups.c.token_digest == hashlib.sha256(token.encode()).hexdigest(),
            )).one()
            self.assertIsNotNone(pending.encerrado_em)
            self.assertIsNone(pending.senha_hash)

    def test_structure_stock_and_private_plan_survive_restart(self):
        payload, _ = self.register()
        other, _ = self.register()
        headers = self.headers(self.login(payload["responsible_email"]))
        outside = self.headers(self.login(other["responsible_email"]))

        def post(path, data):
            response = self.client.post("/structure" + path, headers=headers, json=data)
            self.assertEqual(response.status_code, 201, response.text)
            return response.json()["data"]["id"]

        building = post("/buildings", {"name": "Bloco A"})
        floor = post(f"/buildings/{building}/floors", {"name": "Térreo"})
        room = post("/spaces", {"floor_id": floor, "name": "Sala", "type": "Sala", "capacity": 12})
        resource = post("/resources", {"name": "Computador", "quantity_total": 7, "quantity_unavailable": 1})
        response = self.client.put(f"/structure/spaces/{room}/resources", headers=headers,
                                   json={"resource_ids": [resource], "quantities": {resource: 4}})
        self.assertEqual(response.status_code, 200, response.text)
        rejected = self.client.put(f"/structure/spaces/{room}/configuration", headers=headers,
                                   json={"capacity": 30, "resource_ids": ["99999999"]})
        self.assertEqual(rejected.status_code, 404, rejected.text)
        self.assertEqual(self.client.get(f"/structure/spaces/{room}", headers=headers).json()["data"]["capacity"], 12)

        image = io.BytesIO()
        Image.new("RGB", (16, 16), "white").save(image, format="PNG")
        path = f"/structure/floors/{floor}"
        upload = self.client.post(path + "/plan", headers=headers, files={"file": ("planta.png", image.getvalue())})
        self.assertEqual(upload.status_code, 200, upload.text)
        position = self.client.put(path + f"/positions/{room}", headers=headers, json={"x": 10, "y": 20})
        self.assertEqual(position.status_code, 200, position.text)
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            room_data = restarted.get(f"/structure/spaces/{room}", headers=headers).json()["data"]
            self.assertEqual(room_data["resource_quantities"], {resource: 4})
            resource_data = restarted.get(f"/structure/resources/{resource}", headers=headers).json()["data"]
            self.assertEqual((resource_data["quantity_total"], resource_data["quantity_unavailable"]), (7, 1))
            plant = restarted.get(path + "/plan/file", headers=headers)
            self.assertEqual(plant.content, image.getvalue())
            self.assertEqual(plant.headers["Cache-Control"], "private, no-store")
            self.assertEqual(restarted.get(path + "/plan/file", headers=outside).status_code, 404)
            self.assertEqual(restarted.get(path + "/plan", headers=headers).json()["data"]["positions"],
                             [{"space_id": room, "x": 10.0, "y": 20.0}])

    def test_password_recovery_is_single_use_and_revokes_sessions(self):
        payload, _ = self.register()
        email = payload["responsible_email"]
        old_headers = self.headers(self.login(email))
        response = self.client.post("/auth/password/recovery", json={"email": email})
        unknown = self.client.post("/auth/password/recovery", json={"email": "nobody@example.test"})
        self.assertEqual((response.status_code, unknown.status_code), (202, 202))
        self.assertEqual(response.json(), unknown.json())
        token = self.mailbox.latest_recovery_for(email).verification_token
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            change = {"token": token, "new_password": "senha-renovada-2026"}
            reset = restarted.post("/auth/password/reset", json=change)
            self.assertEqual(reset.status_code, 200, reset.text)
            self.assertEqual(restarted.post("/auth/password/reset", json=change).status_code, 400)
            self.assertEqual(restarted.get("/auth/me", headers=old_headers).status_code, 401)
            authenticated = restarted.post("/auth/login", json={"email": email, "password": change["new_password"]})
            self.assertEqual(authenticated.status_code, 200, authenticated.text)

    def test_preview_can_be_confirmed_by_another_instance_once(self):
        payload, _ = self.register()
        other, _ = self.register()
        headers = self.headers(self.login(payload["responsible_email"]))
        outside = self.headers(self.login(other["responsible_email"]))
        workbook = Workbook()
        workbook.active.append(["RA", "Nome", "E-mail"])
        workbook.active.append(["RA-9091", "Membro importado", "importacao@example.test"])
        buffer = io.BytesIO()
        workbook.save(buffer)
        preview = self.client.post("/admin/enrollments/import/preview", headers=headers,
                                   files={"file": ("matriculas.xlsx", buffer.getvalue())})
        self.assertEqual(preview.status_code, 200, preview.text)
        identifier = {"preview_id": preview.json()["data"]["preview_id"]}
        path = "/admin/enrollments/import/confirm"
        with TestClient(create_app(postgres_session_factory=self.factory)) as restarted:
            self.assertEqual(restarted.post(path, headers=outside, json=identifier).status_code, 404)
            self.assertEqual(restarted.post(path, headers=headers, json=identifier).json()["data"]["imported"], 1)
            self.assertEqual(restarted.post(path, headers=headers, json=identifier).status_code, 404)

    @contextmanager
    def streamlit_runtime(self):
        from controllers import streamlit_runtime
        from infrastructure.persistence.runtime import build_postgres_runtime
        services = build_postgres_runtime(self.factory, self.mailbox)
        with patch.dict(os.environ, {"ROOMFLOW_PERSISTENCE": "postgres"}), patch.object(
            streamlit_runtime, "_get_postgres_runtime", return_value=services,
        ):
            yield

    def test_manager_streamlit_filters_edits_and_blocks_directly(self):
        payload, _ = self.register()
        admin = self.headers(self.login(payload["responsible_email"]))
        login = self._manager_login(admin)
        manager = self.headers(login)
        room = self._structure_room(admin, "Sala Streamlit")
        resource = self.client.post("/structure/resources", headers=manager, json={"name": "Webcam"})
        self.assertEqual(resource.status_code, 201, resource.text)
        resource_id = resource.json()["data"]["id"]
        path = f"/structure/spaces/{room['id']}"
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "espacos"
            app.session_state["auth_token"] = login.json()["data"]["access_token"]
            app.run()
            self.assertFalse(app.exception)
            self.assertIn("Sala Streamlit", app.dataframe[0].value["Espaço"].tolist())
            self.assertNotIn("spaces", app.session_state)
            self.assertNotIn("resources", app.session_state)
            app.selectbox(key="space_building_filter").select(room["building_id"]).run()
            app.selectbox(key=f"space_floor_filter_{room['building_id']}").select(room["floor_id"]).run()
            app.number_input(key="space_min_capacity").set_value(21).run()
            self.assertFalse(app.dataframe)
            app.number_input(key="space_min_capacity").set_value(20).run()
            app.button(key="btn_action_edit_space").click().run()
            app.text_input(key="space_edit_name").set_value("Sala Atualizada")
            app.number_input(key="space_edit_capacity").set_value(25)
            app.multiselect(key="space_edit_resources").set_value([resource_id])
            next(button for button in app.button if button.label == "Salvar alterações").click().run()
            self.assertFalse(app.exception)
            current = self.client.get(path, headers=manager).json()["data"]
            self.assertEqual((current["name"], current["capacity"], current["resource_ids"]),
                             ("Sala Atualizada", 25, [resource_id]))
            app.button(key="btn_action_block_space").click().run()
            next(iter(app.text_area)).set_value("Troca de equipamentos")
            next(button for button in app.button if button.label == "Bloquear sala").click().run()
            self.assertFalse(app.exception)
            self.assertIn("Troca de equipamentos", app.text[0].value)
            app.button(key="btn_action_unblock_space").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(self.client.get(path, headers=manager).json()["data"]["status"], "disponivel")
            app.button(key="btn_action_edit_space").click().run()
            self.assertEqual(app.text_input(key="space_edit_name").value, "Sala Atualizada")
            app.button(key="rf_nav_gerente_dashboard").click().run()
            app.button(key="rf_nav_espacos").click().run()
            self.assertFalse(any(item.key == "space_edit_name" for item in app.text_input))
            self.assertNotIn("edit_space_id", app.session_state)

            app.button(key="btn_action_block_space").click().run()
            app.query_params["page"] = "gerente_dashboard"
            app.run()
            app.query_params["page"] = "espacos"
            app.run()
            self.assertFalse(any(item.label == "Motivo do bloqueio *" for item in app.text_area))
            self.assertNotIn("block_space_id", app.session_state)

    def test_manager_workflow_persists_across_streamlit_processes(self):
        institution, _ = self.register()
        admin = self.headers(self.login(institution["responsible_email"]))
        requester_login = self._requester_login(admin)
        manager_login = self._manager_login(admin)
        requester = self.headers(requester_login)
        manager = self.headers(manager_login)
        room = self._structure_room(admin, "Sala de dois processos")
        resource = self.client.post("/structure/resources", headers=admin, json={"name": "Projetor da auditoria"})
        self.assertEqual(resource.status_code, 201, resource.text)
        title = "Reserva criada em outro processo"
        reason = "Aprovada após consulta à instituição"
        fixture = {"password": PASSWORD, "room": room["id"], "title": title, "reason": reason,
                   "resource": resource.json()["data"]["id"], "phone": "(65) 90000-0000"}

        def run_streamlit(role, login, steps):
            script = dedent("""
                import json
                import sys

                from streamlit.testing.v1 import AppTest

                fixture = json.load(sys.stdin)
                app = AppTest.from_file("main.py", default_timeout=30)
                app.query_params["page"] = "login"
                app.run()
                app.text_input(key="login_email").input(fixture["email"])
                app.text_input(key="login_password").input(fixture["password"])
                app.button(key="login_submit").click().run()
                assert not app.exception
                assert app.session_state["user"]["role"] == fixture["role"]
                assert not {"spaces", "resources", "reservations", "conflicts", "notifications"} & app.session_state.keys()
            """) + dedent(steps)
            result = subprocess.run(
                [sys.executable, "-B", "-c", script],
                input=json.dumps({**fixture, "role": role, "email": login.json()["data"]["user"]["email"]}),
                encoding="utf-8", capture_output=True, timeout=90,
                cwd=PROJECT, env={**os.environ, **self.database_config, "DATABASE_URL": "", "ROOMFLOW_PERSISTENCE": "postgres", "PYTHONIOENCODING": "utf-8"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        with self.streamlit_runtime():
            run_streamlit("solicitante", requester_login, """
                app.button(key="rf_nav_nova_reserva").click().run()
                app.selectbox(key="new_reservation_room").select(fixture["room"])
                app.text_input(key="new_reservation_title").set_value(fixture["title"])
                app.text_input(key="new_reservation_activity").set_value("Aula")
                app.text_area(key="new_reservation_reason").set_value("Solicitação de teste")
                next(button for button in app.button if button.label == "Solicitar reserva").click().run()
                assert not app.exception and app.success
            """)
            run_streamlit("gerente", manager_login, """
                assert app.query_params["page"] == ["gerente_dashboard"]
                app.query_params["page"] = "usuarios"
                app.run()
                assert app.query_params["page"] == ["gerente_dashboard"]
                app.button(key="rf_nav_gerente_reservas").click().run()
                assert fixture["title"] in app.dataframe[0].value["Solicitação"].tolist()
                next(button for button in app.button if button.label == "Analisar solicitação").click().run()
                app.selectbox(key="reservation_decision").select("aprovada")
                app.text_area[0].set_value(fixture["reason"])
                next(button for button in app.button if button.label == "Confirmar decisão").click().run()
                assert "Aprovada" in app.dataframe[0].value["Status"].tolist()
                app.button(key="rf_nav_espacos").click().run()
                app.button(key="btn_action_edit_space").click().run()
                app.number_input(key="space_edit_capacity").set_value(25)
                app.multiselect(key="space_edit_resources").set_value([fixture["resource"]])
                next(button for button in app.button if button.label == "Salvar alterações").click().run()
                assert not app.exception and "25 pessoas" in app.dataframe[0].value["Capacidade"].tolist()
                app.button(key="rf_account").click().run()
                assert next(field for field in app.text_input if field.label == "Telefone").value == ""
                next(button for button in app.button if button.label == "Editar perfil").click().run()
                next(field for field in app.text_input if field.label == "Telefone").set_value(fixture["phone"])
                next(button for button in app.button if button.label == "Salvar alterações").click().run()
                assert not app.exception
                assert next(field for field in app.text_input if field.label == "Telefone").value == fixture["phone"]
            """)
            with TestClient(create_app(postgres_session_factory=self.factory), headers=manager) as client:
                self.assertEqual(client.get("/admin/users").status_code, 403)
                self.assertEqual(client.get("/structure/buildings").status_code, 403)
                self.assertEqual(client.get("/reservations/institution").json()["data"][0]["status"], "aprovada")

        with self.streamlit_runtime():
            run_streamlit("solicitante", requester_login, """
                assert fixture["title"] in [item.value for item in app.subheader]
                next(button for button in app.button if button.label == "Ver histórico").click().run()
                assert fixture["reason"] in [item.value for item in app.text]
                app.button(key="rf_nav_notificacoes").click().run()
                assert "Reserva aprovada" in [item.value for item in app.subheader]
                next(button for button in app.button if button.label == "Marcar como lida").click().run()
                assert not app.exception
            """)
            with TestClient(create_app(postgres_session_factory=self.factory)) as client:
                available = client.get(f"/structure/spaces/{room['id']}", headers=manager).json()["data"]
                self.assertEqual((available["capacity"], available["resource_ids"]), (25, [fixture["resource"]]))
                account = client.get("/auth/me", headers=manager).json()["data"]
                self.assertEqual(account["phone"], fixture["phone"])
                update = client.patch("/auth/me", headers=manager,
                                      json={"name": account["name"], "email": account["email"]})
                self.assertEqual(update.status_code, 200, update.text)
                self.assertEqual(update.json()["data"]["phone"], fixture["phone"])
                report, = client.get("/reservations/mine", headers=requester).json()["data"]
                self.assertEqual((report["title"], report["status"]), (title, "aprovada"))
                notification, = client.get("/notifications", headers=requester).json()["data"]["items"]
                self.assertIsNotNone(notification["read_at"])

    def test_streamlit_uses_direct_postgres_runtime(self):
        payload, _ = self.register()
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "login"
            app.run()
            app.text_input(key="login_email").input(payload["responsible_email"])
            app.text_input(key="login_password").input(PASSWORD)
            app.button(key="login_submit").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["user"]["email"], payload["responsible_email"])
            self.assertNotIn("reservations", app.session_state)
            app.query_params["page"] = "configuracoes_instituicao"
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.query_params["page"], ["configuracoes_instituicao"])
            app.text_input(key="cfg_endereco").input("Endereço salvo pelo Streamlit")
            app.button(key="cfg_salvar").click().run()
            self.assertFalse(app.exception)
            token = app.session_state["auth_token"]
            result = self.client.get("/institutions/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(result.json()["data"]["address"], "Endereço salvo pelo Streamlit")
            app.query_params["page"] = "permissoes"
            app.run()
            matrix = app.dataframe[0].value.set_index("Funcionalidade")
            block = matrix.loc["Bloquear e desbloquear salas"]
            self.assertEqual((block["Administrador"], block["Gerente"], block["Solicitante"]),
                             ("Instituição do vínculo", "Instituição do vínculo", "—"))

    def test_direct_signup_identity_isolation_restart_and_pool_lifecycle(self):
        from controllers.local_runtime import LocalRuntime
        from controllers.runtime_errors import SessionExpired
        from application.services.institution_management_service import InstitutionRegistration
        from infrastructure.persistence.runtime import build_postgres_runtime
        from models.domain.entities.profile import Profile
        from models.domain.exceptions import DomainAuthorizationError, ResourceNotFound

        services = build_postgres_runtime(self.factory, self.mailbox)
        tokens = [None, None]
        first = LocalRuntime(services, lambda: tokens[0])
        second = LocalRuntime(services, lambda: tokens[1])
        owners = []
        for index, runtime in enumerate((first, second)):
            tag = secrets.token_hex(6)
            registration = InstitutionRegistration(
                name=f"Direct {tag}", institution_type="Faculdade", city="", state="", phone="", email="",
                responsible_name="Admin", responsible_email=f"{tag}@example.test", password=PASSWORD,
            )
            institution, owner, code = runtime.institution_management.register(registration)
            self.assertTrue(code)
            login = runtime.authentication.login(owner.email, PASSWORD)
            tokens[index] = login.access_token
            owners.append(owner)
            self.assertEqual(runtime.institution_management.get_own(owner).id, institution.id)

        # A supplied actor can never replace the identity held by this browser session.
        self.assertEqual(first.institution_management.get_own(owners[1]).id, owners[0].institution_id)
        building = first.space_management.create_building(owners[0], "Private building")
        with self.assertRaises((DomainAuthorizationError, ResourceNotFound)):
            second.space_management.list_floors(owners[0], building.id)
        tag = secrets.token_hex(6)
        user = first.user_management.create_user(owners[0], "Member", f"{tag}@example.test", PASSWORD, Profile.REQUESTER)
        restarted = LocalRuntime(build_postgres_runtime(self.factory, self.mailbox), lambda: tokens[0])
        self.assertEqual(restarted.authentication.login(user.email, PASSWORD).user.id, user.id)
        self.assertTrue(restarted.admin_audit.list_events(owners[0]))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda runtime: runtime.institution_management.get_own(None).id, (first, second)))
        self.assertEqual(results, [owner.institution_id for owner in owners])
        first.authentication.logout(tokens[0])
        with self.assertRaises(SessionExpired):
            restarted.institution_management.get_own(owners[0])
        self.assertEqual(second.institution_management.get_own(owners[1]).id, owners[1].institution_id)
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_seed_passwords_work_in_direct_runtime_after_restart(self):
        from controllers.local_runtime import LocalRuntime
        from infrastructure.persistence.runtime import build_postgres_runtime
        env = {**os.environ, **self.database_config, "DATABASE_URL": ""}
        result = subprocess.run([sys.executable, "-m", "db.seeds", "--demo"], cwd=PROJECT,
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        runtime = LocalRuntime(build_postgres_runtime(self.factory, self.mailbox), lambda: None)
        login = runtime.authentication.login("admin@gmail.com", "123456789")
        restarted = LocalRuntime(build_postgres_runtime(self.factory, self.mailbox), lambda: login.access_token)
        self.assertEqual(restarted.institution_management.get_own(login.user).id, login.user.institution_id)
