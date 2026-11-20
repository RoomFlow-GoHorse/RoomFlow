import secrets
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from controllers.streamlit_runtime import get_streamlit_runtime


class StructureStreamlitTests(unittest.TestCase):
    def test_floor_plan_reads_rooms_from_structure_service(self):
        runtime = get_streamlit_runtime()
        admin = runtime.users.find_by_email("admin@gmail.com").user
        token = runtime.authentication.login("admin@gmail.com", "admin123", "floor-plan-test")
        floor = runtime.space_management.list_floors(admin, "b-1", include_inactive=True)[0]
        room_name = f"Sala Backend {secrets.token_hex(3)}"
        room = runtime.space_management.create_space(admin, floor.id, room_name, "Sala de aula", 17)

        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "main.py"))
        app.query_params["page"] = "planta_instituicao"
        app.session_state["auth_token"] = token.access_token
        app.run(timeout=15)

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any(button.key == f"fp_edit_room_{room.id}" for button in app.button))
        runtime.space_management.deactivate_space(admin, room.id)

    def test_manager_spaces_page_reads_rooms_from_structure_service(self):
        runtime = get_streamlit_runtime()
        manager = runtime.users.find_by_email("gerente@gmail.com").user
        token = runtime.authentication.login("gerente@gmail.com", "gerente123", "manager-space-test")
        floor_id = "b-1-f-1"
        room_name = f"Sala Gerente {secrets.token_hex(3)}"
        room = runtime.space_management.create_space(manager, floor_id, room_name, "Sala de aula", 19)

        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "main.py"))
        app.query_params["page"] = "espacos"
        app.session_state["auth_token"] = token.access_token
        app.run(timeout=15)

        self.assertEqual(len(app.exception), 0)
        table_text = "\n".join(str(table.value) for table in app.dataframe)
        self.assertIn(room_name, table_text)
        runtime.space_management.deactivate_space(manager, room.id)


if __name__ == "__main__":
    unittest.main()
