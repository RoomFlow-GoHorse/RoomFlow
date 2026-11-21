import hashlib
import io
import os
import secrets
import socket
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx2
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
from infrastructure.persistence.records import institution_invites, pending_signups, sessions
from infrastructure.persistence.structure_records import bloqueios_espaco
from models.database_models import Espaco, Reserva, UsuarioInstituicao


TEST_DATABASE = os.getenv("ROOMFLOW_TEST_DATABASE", "")
PASSWORD = "teste-postgres-123"
PROJECT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(TEST_DATABASE, "Informe ROOMFLOW_TEST_DATABASE para testar PostgreSQL local isolado.")
class PostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = dotenv_values(PROJECT / ".env")
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
    def api_process(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        env = {**os.environ, **self.database_config, "DATABASE_URL": "", "ROOMFLOW_PERSISTENCE": "postgres"}
        process = subprocess.Popen([
            sys.executable, "-B", "-m", "uvicorn", "api.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "error",
        ], cwd=PROJECT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    break
                try:
                    if httpx2.get(url + "/ready", timeout=1, trust_env=False).is_success:
                        yield url
                        return
                except httpx2.HTTPError:
                    pass
                time.sleep(0.1)
            self.fail("O processo FastAPI de teste não ficou disponível.")
        finally:
            process.terminate()
            process.wait(timeout=10)

    def test_manager_streamlit_filters_edits_and_blocks_via_http(self):
        payload, _ = self.register()
        admin = self.headers(self.login(payload["responsible_email"]))
        login = self._manager_login(admin)
        manager = self.headers(login)
        room = self._structure_room(admin, "Sala Streamlit")
        resource = self.client.post("/structure/resources", headers=manager, json={"name": "Webcam"})
        self.assertEqual(resource.status_code, 201, resource.text)
        resource_id = resource.json()["data"]["id"]
        path = f"/structure/spaces/{room['id']}"
        with self.api_process() as url, patch.dict(os.environ, {"ROOMFLOW_API_URL": url}):
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "espacos"
            app.session_state["auth_token"] = login.json()["data"]["access_token"]
            app.run()
            self.assertFalse(app.exception)
            self.assertIn("Sala Streamlit", app.dataframe[0].value["Espaço"].tolist())
            self.assertNotIn("spaces", app.session_state.filtered_state)
            self.assertNotIn("resources", app.session_state.filtered_state)
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

    def test_streamlit_uses_separate_api_process(self):
        payload, _ = self.register()
        with self.api_process() as url, patch.dict(os.environ, {"ROOMFLOW_API_URL": url}):
            status = httpx2.get(url + "/ready", trust_env=False)
            self.assertEqual(status.json()["data"], {"status": "ready", "persistence": "postgres"})
            app = AppTest.from_file(str(PROJECT / "main.py"), default_timeout=20)
            app.query_params["page"] = "login"
            app.run()
            app.text_input(key="login_email").input(payload["responsible_email"])
            app.text_input(key="login_password").input(PASSWORD)
            app.button(key="login_submit").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["user"]["email"], payload["responsible_email"])
            self.assertNotIn("reservations", app.session_state.filtered_state)
            app.query_params["page"] = "configuracoes_instituicao"
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.query_params["page"], ["configuracoes_instituicao"])
            app.text_input(key="cfg_endereco").input("Endereço salvo pelo Streamlit")
            app.button(key="cfg_salvar").click().run()
            self.assertFalse(app.exception)
            token = app.session_state["auth_token"]
            result = httpx2.get(url + "/institutions/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(result.json()["data"]["address"], "Endereço salvo pelo Streamlit")
