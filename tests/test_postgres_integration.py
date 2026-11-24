import json
import os
import secrets
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch
from zoneinfo import ZoneInfo

from dotenv import dotenv_values
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker
from streamlit.testing.v1 import AppTest

from application.services.institution_management_service import InstitutionRegistration
from controllers.local_runtime import LocalRuntime
from infrastructure.email.in_memory_email_sender import InMemoryEmailSender
from infrastructure.persistence.runtime import build_postgres_runtime
from models.database_models import Espaco, Reserva
from models.domain.entities.profile import Profile
from models.domain.exceptions import DuplicateResource


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
        self.services = build_postgres_runtime(self.factory, self.mailbox)

    def register(self):
        tag = secrets.token_hex(5)
        registration = InstitutionRegistration(
            responsible_name="Administrador Teste", responsible_email=f"{tag}@example.test",
            password=PASSWORD, name=f"Instituição {tag}", institution_type="Faculdade",
            city="", state="", phone="", email="",
        )
        _, admin, _ = self.runtime(None).institution_management.register(registration)
        return admin

    def runtime(self, login):
        return LocalRuntime(self.services, lambda: login.access_token if login else None)

    def role_login(self, admin, profile):
        email = f"{secrets.token_hex(5)}@example.test"
        self.services.user_management.create_user(admin, profile.value, email, PASSWORD, profile)
        return self.services.authentication.login(email, PASSWORD)

    def _structure_room(self, admin, name):
        building = self.services.space_management.create_building(admin, "Bloco A")
        floor = self.services.space_management.create_floor(admin, building.id, "Térreo")
        return self.services.space_management.create_space(admin, floor.id, name, "Sala", 20)

    @staticmethod
    def _reservation_payload(room):
        start = (datetime.now(ZoneInfo("America/Sao_Paulo")) + timedelta(days=3)).replace(
            hour=10, minute=0, second=0, microsecond=0,
        )
        end = start + timedelta(hours=1)
        return {
            "space_id": room.id, "title": "Oficina", "activity_type": "Aula",
            "start": start.isoformat(), "end": end.isoformat(), "participants": 20,
            "justification": "Atividade com a turma",
        }

    def test_participant_navigation_renders_only_its_institution_and_reservations(self):
        admin = self.register()
        requester = self.role_login(admin, Profile.REQUESTER)
        participant = self.role_login(admin, Profile.PARTICIPANT)
        other_participant = self.role_login(admin, Profile.PARTICIPANT)
        room = self._structure_room(admin, "Sala da instituição")
        other_room = self._structure_room(self.register(), "Sala de outra instituição")
        reservation = self.runtime(requester).reservation_service.create({
            **self._reservation_payload(room), "participant_ids": [participant.user.id],
        })
        api = self.runtime(participant).reservation_service
        self.assertEqual(
            [(item["id"], item["participation_status"]) for item in api.list_participating()],
            [(reservation["id"], "pendente")],
        )
        self.assertEqual(self.runtime(other_participant).reservation_service.list_participating(), [])
        _, _, rooms = self.runtime(participant).space_management.location_catalog(None)
        self.assertEqual([item.id for item in rooms], [room.id])
        self.assertNotIn(other_room.id, {item.id for item in rooms})

        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "participante_dashboard"
            app.session_state["auth_token"] = participant.access_token
            app.run()
            self.assertFalse(app.exception or app.error)
            for page in ("agenda", "localizar"):
                app.button(key=f"rf_nav_{page}").click().run()
                self.assertEqual(app.query_params["page"], [page])
                self.assertFalse(app.exception or app.error)

    def test_reservation_streamlit_submission_reaches_manager_directly(self):
        admin = self.register()
        requester = self.role_login(admin, Profile.REQUESTER)
        manager = self.role_login(admin, Profile.MANAGER)
        room = self._structure_room(admin, "Sala Streamlit Reserva")
        with self.streamlit_runtime():
            def open_page(login, page):
                app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
                app.query_params["page"] = page
                app.session_state["auth_token"] = login.access_token
                app.run()
                self.assertFalse(app.exception)
                return app

            title = "Oficina criada pelo Streamlit"
            app = open_page(requester, "nova_reserva")
            app.selectbox(key="new_reservation_room").select(room.id)
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

    def test_conflict_streamlit_moves_reservation_to_compatible_room(self):
        admin = self.register()
        foreign_admin = self.register()
        login = self.role_login(admin, Profile.MANAGER)
        manager = self.runtime(login)
        source = self._structure_room(admin, "Sala Original")
        foreign = self._structure_room(foreign_admin, "Sala de Outra Instituição")
        resources = self.services.resource_management
        resource = resources.create_resource(login.user, "Projetor", quantity_total=8)

        def room(name, capacity=20, quantity=0):
            space = self.services.space_management.create_space(admin, source.floor_id, name, "Sala", capacity)
            if quantity:
                resources.set_space_resources(login.user, space.id, [resource.id], {resource.id: quantity})
            return space.id

        resources.set_space_resources(login.user, source.id, [resource.id], {resource.id: 2})
        compatible = room("Sala Compatível", quantity=2)
        busy = room("Sala com Solicitação", quantity=2)
        room("Sala Pequena", capacity=10)
        incompatible = room("Sala sem Equipamento")
        limited = room("Sala com Pouco Equipamento", quantity=1)
        owners = [self.runtime(self.role_login(admin, Profile.REQUESTER)) for _ in range(2)]
        payload = self._reservation_payload(source)
        for index, owner in enumerate(owners):
            owner.reservation_service.create({**payload, "title": f"Oficina {index}"})
        owners[0].reservation_service.create({**payload, "space_id": busy})
        item, = manager.conflict_service.list()["items"]
        a, b = item["reservations"]
        suggestions = manager.conflict_service.alternatives(item["id"])
        for reservation in (a, b):
            self.assertEqual([space["id"] for space in suggestions[reservation["id"]]], [compatible])
        for invalid in (incompatible, limited, busy, foreign.id):
            with self.assertRaises(DuplicateResource):
                manager.conflict_service.resolve(item["id"], {
                    "action": "alterou", "reason": "Realocação", "reservation_id": a["id"], "space_id": invalid,
                })
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "gerente_conflitos"
            app.session_state["auth_token"] = login.access_token
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
        resolved = manager.conflict_service.detail(item["id"])
        self.assertIn("Realocada com projetores", resolved["decision"])
        moved, kept = resolved["reservations"]
        self.assertEqual((moved["space_id"], moved["status"]), (compatible, "em_analise"))
        self.assertEqual((kept["space_id"], kept["status"]), (source.id, "pendente"))
        history = manager.reservation_service.detail(a["id"])["history"]
        self.assertEqual(history[-1]["reason"], "Realocada com projetores")

    def test_streamlit_reads_notifications_and_shows_requester_history(self):
        admin = self.register()
        manager_login = self.role_login(admin, Profile.MANAGER)
        requester_login = self.role_login(admin, Profile.REQUESTER)
        manager = self.runtime(manager_login)
        requester = self.runtime(requester_login)
        room = self._structure_room(admin, "Sala de histórico Streamlit")
        payload = self._reservation_payload(room)
        reservation_id = requester.reservation_service.create(payload)["id"]
        item, = manager.notifications.inbox()["items"]
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "notificacoes"
            app.session_state["auth_token"] = manager_login.access_token
            app.run()
            self.assertFalse(app.exception)
            self.assertIn("Nova solicitação de reserva", [item.value for item in app.subheader])
            self.assertNotIn("notifications", app.session_state)
            app.button(key=f"btn_read_{item['id']}").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(manager.notifications.unread_count(), 0)

            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "minhas_reservas"
            app.session_state["auth_token"] = requester_login.access_token
            app.run()
            app.button(key=f"history_{reservation_id}").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Solicitação criada" in item.value for item in app.caption))
            self.assertIn(payload["justification"], [item.value for item in app.text])

    def test_streamlit_manager_dashboard_and_occupancy_use_persisted_status(self):
        admin = self.register()
        login = self.role_login(admin, Profile.MANAGER)
        manager = self.runtime(login)
        requester = self.runtime(self.role_login(admin, Profile.REQUESTER))
        room = self._structure_room(admin, "Sala Painel Real")
        payload = self._reservation_payload(room)
        reservation = requester.reservation_service.create({**payload, "title": "Aula do Painel Real"})
        day = datetime.fromisoformat(payload["start"]).date()
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "gerente_dashboard"
            app.session_state["auth_token"] = login.access_token
            app.run()
            self.assertFalse(app.exception)
            app.date_input(key="dashboard_start").set_value(day).run()
            self.assertEqual({item.label: item.value for item in app.metric}["Pendentes"], "1")
            self.assertIn("Aula do Painel Real", app.dataframe[0].value["Título"].tolist())
            manager.reservation_service.review(reservation["id"], "aprovada")
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

    def test_original_constraint_rejects_simultaneous_overlapping_approvals(self):
        admin = self.register()
        institution_id = int(admin.institution_id)
        owner_id = int(admin.id)
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

    @contextmanager
    def streamlit_runtime(self):
        from controllers import streamlit_runtime
        with patch.dict(os.environ, {"ROOMFLOW_PERSISTENCE": "postgres"}), patch.object(
            streamlit_runtime, "_get_postgres_runtime", return_value=self.services,
        ):
            yield

    def test_manager_streamlit_filters_edits_and_blocks_directly(self):
        admin = self.register()
        login = self.role_login(admin, Profile.MANAGER)
        room = self._structure_room(admin, "Sala Streamlit")
        resource_id = self.services.resource_management.create_resource(login.user, "Webcam").id
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "espacos"
            app.session_state["auth_token"] = login.access_token
            app.run()
            self.assertFalse(app.exception)
            self.assertIn("Sala Streamlit", app.dataframe[0].value["Espaço"].tolist())
            self.assertNotIn("spaces", app.session_state)
            self.assertNotIn("resources", app.session_state)
            app.selectbox(key="space_building_filter").select(room.building_id).run()
            app.selectbox(key=f"space_floor_filter_{room.building_id}").select(room.floor_id).run()
            app.number_input(key="space_min_capacity").set_value(21).run()
            self.assertFalse(app.dataframe)
            app.number_input(key="space_min_capacity").set_value(20).run()
            app.button(key="btn_action_edit_space").click().run()
            app.text_input(key="space_edit_name").set_value("Sala Atualizada")
            app.number_input(key="space_edit_capacity").set_value(25)
            app.multiselect(key="space_edit_resources").set_value([resource_id])
            next(button for button in app.button if button.label == "Salvar alterações").click().run()
            self.assertFalse(app.exception)
            current = self.services.space_management.get_space(login.user, room.id)
            self.assertEqual((current.name, current.capacity, current.resource_ids),
                             ("Sala Atualizada", 25, (resource_id,)))
            app.button(key="btn_action_block_space").click().run()
            next(iter(app.text_area)).set_value("Troca de equipamentos")
            next(button for button in app.button if button.label == "Bloquear sala").click().run()
            self.assertFalse(app.exception)
            self.assertIn("Troca de equipamentos", app.text[0].value)
            app.button(key="btn_action_unblock_space").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(self.services.space_management.get_space(login.user, room.id).status, "disponivel")
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
        admin = self.register()
        requester_login = self.role_login(admin, Profile.REQUESTER)
        manager_login = self.role_login(admin, Profile.MANAGER)
        requester = self.runtime(requester_login)
        manager = self.runtime(manager_login)
        room = self._structure_room(admin, "Sala de dois processos")
        resource = self.services.resource_management.create_resource(admin, "Projetor da auditoria")
        title = "Reserva criada em outro processo"
        reason = "Aprovada após consulta à instituição"
        fixture = {"password": PASSWORD, "room": room.id, "title": title, "reason": reason,
                   "resource": resource.id, "phone": "(65) 90000-0000"}

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
                for key in ("spaces", "resources", "reservations", "conflicts", "notifications"):
                    assert key not in app.session_state
            """) + dedent(steps)
            result = subprocess.run(
                [sys.executable, "-B", "-c", script],
                input=json.dumps({**fixture, "role": role, "email": login.user.email}),
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
            self.assertEqual(manager.reservation_service.list_institution()[0]["status"], "aprovada")

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
            available = self.services.space_management.get_space(manager_login.user, room.id)
            self.assertEqual((available.capacity, available.resource_ids), (25, (fixture["resource"],)))
            account = manager.authentication.authenticate(manager_login.access_token)
            updated = self.services.user_management.update_own_profile(account, account.name, account.email)
            self.assertEqual(updated.phone, fixture["phone"])
            report, = requester.reservation_service.list_own()
            self.assertEqual((report["title"], report["status"]), (title, "aprovada"))
            notification, = requester.notifications.inbox()["items"]
            self.assertIsNotNone(notification["read_at"])

    def test_streamlit_uses_direct_postgres_runtime(self):
        admin = self.register()
        with self.streamlit_runtime():
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "login"
            app.run()
            app.text_input(key="login_email").input(admin.email)
            app.text_input(key="login_password").input(PASSWORD)
            app.button(key="login_submit").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["user"]["email"], admin.email)
            self.assertNotIn("reservations", app.session_state)
            app.query_params["page"] = "configuracoes_instituicao"
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.query_params["page"], ["configuracoes_instituicao"])
            app.text_input(key="cfg_endereco").input("Endereço salvo pelo Streamlit")
            app.button(key="cfg_salvar").click().run()
            self.assertFalse(app.exception)
            token = app.session_state["auth_token"]
            actor = self.services.authentication.authenticate(token)
            institution = self.services.institution_management.get_own(actor)
            self.assertEqual(institution.address, "Endereço salvo pelo Streamlit")
            app.query_params["page"] = "permissoes"
            app.run()
            matrix = app.dataframe[0].value.set_index("Funcionalidade")
            block = matrix.loc["Bloquear e desbloquear salas"]
            self.assertEqual((block["Administrador"], block["Gerente"], block["Solicitante"]),
                             ("Instituição do vínculo", "Instituição do vínculo", "—"))

    def test_direct_signup_identity_isolation_restart_and_pool_lifecycle(self):
        from controllers.runtime_errors import SessionExpired
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
        env = {**os.environ, **self.database_config, "DATABASE_URL": ""}
        result = subprocess.run([sys.executable, "-m", "db.seeds", "--demo"], cwd=PROJECT,
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        runtime = LocalRuntime(build_postgres_runtime(self.factory, self.mailbox), lambda: None)
        login = runtime.authentication.login("admin@gmail.com", "123456789")
        restarted = LocalRuntime(build_postgres_runtime(self.factory, self.mailbox), lambda: login.access_token)
        self.assertEqual(restarted.institution_management.get_own(login.user).id, login.user.institution_id)
