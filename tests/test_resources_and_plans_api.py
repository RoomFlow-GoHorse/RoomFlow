import io
import secrets
import unittest

from fastapi.testclient import TestClient
from PIL import Image

from api.app import create_app


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (12, 8), "white").save(output, format="PNG")
    return output.getvalue()


class ResourceAndPlanApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = TestClient(create_app(environment="test"))
        self.client = self.context.__enter__()
        self.admin = _login(self.client, "admin@gmail.com", "admin123")
        self.manager = _login(self.client, "gerente@gmail.com", "gerente123")

    def tearDown(self) -> None:
        self.context.__exit__(None, None, None)

    def _floor_with_room(self):
        building = self.client.post("/structure/buildings", headers=self.admin, json={"name": f"Bloco {secrets.token_hex(3)}"}).json()["data"]
        floor = self.client.post(f"/structure/buildings/{building['id']}/floors", headers=self.admin, json={"name": "Térreo"}).json()["data"]
        room = self.client.post("/structure/spaces", headers=self.admin, json={
            "floor_id": floor["id"], "name": f"Sala {secrets.token_hex(3)}", "type": "Laboratório", "capacity": 20,
        }).json()["data"]
        return building, floor, room

    def test_resource_catalog_associations_filtering_and_institution_scope(self):
        room = self.client.get("/structure/spaces", headers=self.admin).json()["data"][0]
        name = f"Recurso {secrets.token_hex(3)}"
        created = self.client.post("/structure/resources", headers=self.admin, json={"name": name})
        self.assertEqual(created.status_code, 201)
        resource = created.json()["data"]
        duplicate = self.client.post("/structure/resources", headers=self.admin, json={"name": name.upper()})
        self.assertEqual(duplicate.status_code, 409)

        renamed = self.client.patch(f"/structure/resources/{resource['id']}", headers=self.admin, json={"name": name + " atualizado"})
        self.assertEqual(renamed.status_code, 200)
        assigned = self.client.put(f"/structure/spaces/{room['id']}/resources", headers=self.manager, json={"resource_ids": [resource["id"]]})
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()["data"]["resource_ids"], [resource["id"]])
        filtered = self.client.get(f"/structure/spaces?resource_id={resource['id']}", headers=self.manager)
        self.assertEqual([item["id"] for item in filtered.json()["data"]], [room["id"]])
        self.assertIn(name + " atualizado", filtered.json()["data"][0]["resources"])
        self.assertEqual(self.client.put(f"/structure/spaces/{room['id']}/resources", headers=self.admin, json={"resource_ids": [resource["id"], resource["id"]]}).status_code, 422)
        inactive = self.client.patch(f"/structure/resources/{resource['id']}/status", headers=self.admin, json={"active": False})
        self.assertEqual(inactive.status_code, 200)
        self.assertFalse(any(item["id"] == resource["id"] for item in self.client.get("/structure/resources", headers=self.admin).json()["data"]))
        self.assertTrue(any(item["id"] == resource["id"] for item in self.client.get("/structure/resources?include_inactive=true", headers=self.admin).json()["data"]))
        other_room = self.client.get("/structure/spaces", headers=self.admin).json()["data"][-1]
        self.assertEqual(self.client.put(f"/structure/spaces/{other_room['id']}/resources", headers=self.admin, json={"resource_ids": [resource["id"]]}).status_code, 404)

        other = self.client.post("/institutions/signup", json={
            "responsible_name": "Outro Admin", "responsible_email": f"other-{secrets.token_hex(3)}@example.edu",
            "password": "senha-segura", "name": f"Instituição {secrets.token_hex(3)}",
            "cnpj": "98.765.432/0001-10", "institution_type": "Universidade",
        })
        self.assertEqual(other.status_code, 201)
        other_admin = _login(self.client, other.json()["data"]["administrator"]["email"], "senha-segura")
        self.assertEqual(self.client.get(f"/structure/resources/{resource['id']}", headers=other_admin).status_code, 404)
        self.assertEqual(self.client.put(f"/structure/spaces/{room['id']}/resources", headers=other_admin, json={"resource_ids": []}).status_code, 404)

    def test_floor_plan_upload_position_replacement_and_structure_change(self):
        _, floor, room = self._floor_with_room()
        uploaded = self.client.post(
            f"/structure/floors/{floor['id']}/plan", headers=self.admin,
            files={"file": ("floor.png", _png(), "image/png")},
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        plan = uploaded.json()["data"]
        self.assertEqual(plan["positions"], [])
        self.assertEqual(self.client.get(f"/structure/floors/{floor['id']}/plan/file", headers=self.admin).content, _png())

        positioned = self.client.put(
            f"/structure/floors/{floor['id']}/positions/{room['id']}", headers=self.admin,
            json={"x": 32.5, "y": 71},
        )
        self.assertEqual(positioned.status_code, 200)
        self.assertEqual(positioned.json()["data"]["positions"][0], {"space_id": room["id"], "x": 32.5, "y": 71.0})

        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10" fill="white"/></svg>'
        replaced = self.client.post(
            f"/structure/floors/{floor['id']}/plan", headers=self.admin,
            files={"file": ("replacement.svg", svg, "image/svg+xml")},
        )
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(replaced.json()["data"]["id"], plan["id"])
        self.assertEqual(len(replaced.json()["data"]["positions"]), 1)

        second_floor = self.client.post(
            f"/structure/buildings/{floor['building_id']}/floors", headers=self.admin,
            json={"name": "1º andar"},
        ).json()["data"]
        moved = self.client.patch(f"/structure/spaces/{room['id']}", headers=self.admin, json={"floor_id": second_floor["id"]})
        self.assertEqual(moved.status_code, 200)
        reloaded = self.client.get(f"/structure/floors/{floor['id']}/plan", headers=self.admin)
        self.assertEqual(reloaded.json()["data"]["positions"], [])
        wrong_room = self.client.post("/structure/spaces", headers=self.admin, json={
            "floor_id": second_floor["id"], "name": f"Sala {secrets.token_hex(3)}", "type": "Sala", "capacity": 10,
        }).json()["data"]
        self.assertEqual(self.client.put(
            f"/structure/floors/{floor['id']}/positions/{wrong_room['id']}", headers=self.admin,
            json={"x": 20, "y": 20},
        ).status_code, 404)
        self.assertEqual(self.client.delete(f"/structure/floors/{floor['id']}/plan", headers=self.admin).status_code, 204)
        self.assertEqual(self.client.get(f"/structure/floors/{floor['id']}/plan", headers=self.admin).status_code, 404)

    def test_rejects_invalid_plans_and_foreign_institution(self):
        _, floor, _ = self._floor_with_room()
        wrong_extension = self.client.post(
            f"/structure/floors/{floor['id']}/plan", headers=self.admin,
            files={"file": ("bad.png", b"not an image", "image/png")},
        )
        active_svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        unsafe_svg = self.client.post(
            f"/structure/floors/{floor['id']}/plan", headers=self.admin,
            files={"file": ("bad.svg", active_svg, "image/svg+xml")},
        )
        oversized = self.client.post(
            f"/structure/floors/{floor['id']}/plan", headers=self.admin,
            files={"file": ("large.svg", b" " * (10 * 1024 * 1024 + 1), "image/svg+xml")},
        )
        self.assertEqual(wrong_extension.status_code, 422)
        self.assertEqual(unsafe_svg.status_code, 422)
        self.assertEqual(oversized.status_code, 422)

        other = self.client.post("/institutions/signup", json={
            "responsible_name": "Outro Admin", "responsible_email": f"scope-{secrets.token_hex(3)}@example.edu",
            "password": "senha-segura", "name": f"Instituição {secrets.token_hex(3)}",
            "cnpj": "98.765.432/0001-10", "institution_type": "Universidade",
        })
        self.assertEqual(other.status_code, 201)
        foreign = _login(self.client, other.json()["data"]["administrator"]["email"], "senha-segura")
        self.assertEqual(self.client.get(f"/structure/floors/{floor['id']}/plan", headers=foreign).status_code, 404)


if __name__ == "__main__":
    unittest.main()
