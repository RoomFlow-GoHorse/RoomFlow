import time as _time
import streamlit as st

from controllers.app_state_service import set_toast
from views.components.ui_components import page_header

# =========================================================
# CONSTANTES
# =========================================================

FLOOR_ORDER = [
    "Subsolo",
    "Térreo",
    "Mezanino",
    "1º andar",
    "2º andar",
    "3º andar",
    "4º andar",
    "5º andar",
]

ROOM_TYPES = [
    "Sala de aula",
    "Laboratório",
    "Auditório",
    "Sala de reuniões",
    "Outro",
]

# Salas do mock de SPACES adaptadas ao modelo building/floor
_MOCK_SPACES = [
    {"id": "s1", "name": "Sala 101",               "building": "Bloco A", "floor": "1º andar",  "type": "Sala de aula",    "capacity": 20},
    {"id": "s2", "name": "Sala 204",               "building": "Bloco B", "floor": "2º andar",  "type": "Sala de aula",    "capacity": 30},
    {"id": "s3", "name": "Auditório Principal",    "building": "Bloco A", "floor": "Térreo",    "type": "Auditório",       "capacity": 150},
    {"id": "s4", "name": "Lab. de Informática",   "building": "Bloco C", "floor": "Térreo",    "type": "Laboratório",     "capacity": 40},
    {"id": "s5", "name": "Auditório A",            "building": "Bloco D", "floor": "Térreo",    "type": "Auditório",       "capacity": 80},
    {"id": "s6", "name": "Sala de Reuniões B",     "building": "Bloco A", "floor": "1º andar",  "type": "Sala de reuniões","capacity": 8},
]


# =========================================================
# HELPERS
# =========================================================

def _sort_floor_names(names: list[str]) -> list[str]:
    def _key(n):
        idx = FLOOR_ORDER.index(n) if n in FLOOR_ORDER else len(FLOOR_ORDER)
        return (idx, n)
    return sorted(names, key=_key)


def _sort_floors(floors: list[dict]) -> list[dict]:
    def _key(f):
        idx = FLOOR_ORDER.index(f["name"]) if f["name"] in FLOOR_ORDER else len(FLOOR_ORDER)
        return (idx, f["name"])
    return sorted(floors, key=_key)


def _uid() -> str:
    return str(int(_time.time() * 1000))


# =========================================================
# BOOT — session_state inicial
# =========================================================

def _boot():
    if "fp_buildings" not in st.session_state:
        buildings = []
        seen = set()
        for s in _MOCK_SPACES:
            b = s["building"]
            if b not in seen:
                seen.add(b)
                buildings.append({"id": f"b-{len(buildings)+1}", "name": b})
        st.session_state.fp_buildings = sorted(buildings, key=lambda x: x["name"])

    if "fp_floors" not in st.session_state:
        floors = []
        bname_to_id = {b["name"]: b["id"] for b in st.session_state.fp_buildings}
        seen = set()
        for s in _MOCK_SPACES:
            key = (s["building"], s["floor"])
            if key not in seen:
                seen.add(key)
                bid = bname_to_id.get(s["building"], "")
                fid = f"{bid}-f-{len(floors)+1}"
                floors.append({"id": fid, "buildingId": bid, "name": s["floor"]})
        st.session_state.fp_floors = floors

    if "fp_extra_rooms" not in st.session_state:
        st.session_state.fp_extra_rooms = []

    if "fp_plans" not in st.session_state:
        # {plan_key: {"src": str|None, "positions": {room_id: {"x": float, "y": float}}}}
        st.session_state.fp_plans = {}

    if "fp_sel_building" not in st.session_state:
        blist = st.session_state.fp_buildings
        st.session_state.fp_sel_building = blist[0]["id"] if blist else ""

    if "fp_sel_floor" not in st.session_state:
        bid = st.session_state.fp_sel_building
        matching = _sort_floors([f for f in st.session_state.fp_floors if f["buildingId"] == bid])
        st.session_state.fp_sel_floor = matching[0]["id"] if matching else ""

    if "fp_positioning" not in st.session_state:
        st.session_state.fp_positioning = None  # room_id being positioned


# =========================================================
# DERIVED HELPERS
# =========================================================

def _buildings() -> list[dict]:
    return st.session_state.fp_buildings


def _all_floors() -> list[dict]:
    return st.session_state.fp_floors


def _current_building() -> dict | None:
    bid = st.session_state.fp_sel_building
    return next((b for b in _buildings() if b["id"] == bid), None)


def _current_floor() -> dict | None:
    fid = st.session_state.fp_sel_floor
    return next((f for f in _all_floors() if f["id"] == fid), None)


def _building_floors(bid: str) -> list[dict]:
    return _sort_floors([f for f in _all_floors() if f["buildingId"] == bid])


def _plan_key() -> str:
    return f"{st.session_state.fp_sel_building}__{st.session_state.fp_sel_floor}"


def _current_plan() -> dict:
    return st.session_state.fp_plans.get(_plan_key(), {"src": None, "positions": {}})


def _rooms_for(building_name: str, floor_name: str) -> list[dict]:
    mock = [s for s in _MOCK_SPACES if s["building"] == building_name and s["floor"] == floor_name]
    extra = [r for r in st.session_state.fp_extra_rooms if r["building"] == building_name and r["floor"] == floor_name]
    return mock + extra


# =========================================================
# DIALOGS
# =========================================================

@st.dialog("Adicionar bloco")
def _dialog_add_building():
    name = st.text_input("Nome do bloco *", placeholder="Ex: Bloco D", key="fp_new_building_name")
    err = st.session_state.get("fp_add_building_err", "")
    if err:
        st.error(err)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop("fp_add_building_err", None)
            st.rerun()
    with c2:
        if st.button("Adicionar bloco", type="primary", use_container_width=True):
            name = name.strip()
            if not name:
                st.session_state.fp_add_building_err = "Nome do bloco é obrigatório."
                st.rerun()
                return
            exists = any(b["name"].lower() == name.lower() for b in _buildings())
            if exists:
                st.session_state.fp_add_building_err = "Já existe um bloco com esse nome."
                st.rerun()
                return
            new_id = f"b-{_uid()}"
            st.session_state.fp_buildings.append({"id": new_id, "name": name})
            st.session_state.fp_buildings = sorted(st.session_state.fp_buildings, key=lambda x: x["name"])
            st.session_state.fp_sel_building = new_id
            st.session_state.fp_sel_floor = ""
            st.session_state.pop("fp_add_building_err", None)
            set_toast(f'Bloco "{name}" adicionado.')
            st.rerun()


@st.dialog("Renomear bloco")
def _dialog_rename_building(building: dict):
    new_name = st.text_input("Novo nome", value=building["name"], key="fp_rename_building_val")
    err = st.session_state.get("fp_rename_building_err", "")
    if err:
        st.error(err)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop("fp_rename_building_err", None)
            st.rerun()
    with c2:
        if st.button("Salvar", type="primary", use_container_width=True):
            new_name = new_name.strip()
            if not new_name:
                st.rerun()
                return
            if new_name == building["name"]:
                st.rerun()
                return
            exists = any(b["id"] != building["id"] and b["name"].lower() == new_name.lower() for b in _buildings())
            if exists:
                st.session_state.fp_rename_building_err = "Já existe um bloco com esse nome."
                st.rerun()
                return
            old_name = building["name"]
            for b in st.session_state.fp_buildings:
                if b["id"] == building["id"]:
                    b["name"] = new_name
            for r in st.session_state.fp_extra_rooms:
                if r["building"] == old_name:
                    r["building"] = new_name
            st.session_state.pop("fp_rename_building_err", None)
            set_toast("Bloco renomeado.")
            st.rerun()


@st.dialog("Remover bloco")
def _dialog_confirm_remove_building(building: dict):
    has_floors = any(f["buildingId"] == building["id"] for f in _all_floors())
    has_rooms = any(r["building"] == building["name"] for r in st.session_state.fp_extra_rooms)
    has_plans = any(k.startswith(f"{building['id']}__") for k in st.session_state.fp_plans)

    if has_floors or has_rooms or has_plans:
        st.warning("Este bloco possui andares, salas ou plantas cadastradas. Ao remover, esses dados serão perdidos.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Remover bloco", type="primary", use_container_width=True):
            remaining = [b for b in st.session_state.fp_buildings if b["id"] != building["id"]]
            next_building = remaining[0] if remaining else None
            st.session_state.fp_buildings = remaining
            st.session_state.fp_floors = [f for f in _all_floors() if f["buildingId"] != building["id"]]
            st.session_state.fp_extra_rooms = [r for r in st.session_state.fp_extra_rooms if r["building"] != building["name"]]
            to_del = [k for k in st.session_state.fp_plans if k.startswith(f"{building['id']}__")]
            for k in to_del:
                del st.session_state.fp_plans[k]
            if st.session_state.fp_sel_building == building["id"]:
                st.session_state.fp_sel_building = next_building["id"] if next_building else ""
                next_floors = _building_floors(next_building["id"]) if next_building else []
                st.session_state.fp_sel_floor = next_floors[0]["id"] if next_floors else ""
            set_toast(f'Bloco "{building["name"]}" removido.')
            st.rerun()


@st.dialog("Adicionar andar")
def _dialog_add_floor(building: dict):
    st.caption(f"Bloco: **{building['name']}**")
    name = st.text_input(
        "Nome do andar *",
        placeholder="Ex: 2º andar, Mezanino, Subsolo",
        key="fp_new_floor_name",
    )
    err = st.session_state.get("fp_add_floor_err", "")
    if err:
        st.error(err)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop("fp_add_floor_err", None)
            st.rerun()
    with c2:
        if st.button("Adicionar andar", type="primary", use_container_width=True):
            name = name.strip()
            if not name:
                st.session_state.fp_add_floor_err = "Nome do andar é obrigatório."
                st.rerun()
                return
            b_floors = _building_floors(building["id"])
            if any(f["name"].lower() == name.lower() for f in b_floors):
                st.session_state.fp_add_floor_err = "Já existe um andar com esse nome neste bloco."
                st.rerun()
                return
            new_id = f"f-{_uid()}"
            st.session_state.fp_floors.append({"id": new_id, "buildingId": building["id"], "name": name})
            st.session_state.fp_sel_floor = new_id
            st.session_state.pop("fp_add_floor_err", None)
            set_toast(f'Andar "{name}" adicionado ao {building["name"]}.')
            st.rerun()


@st.dialog("Renomear andar")
def _dialog_rename_floor(floor: dict, building: dict):
    new_name = st.text_input("Novo nome", value=floor["name"], key="fp_rename_floor_val")
    err = st.session_state.get("fp_rename_floor_err", "")
    if err:
        st.error(err)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop("fp_rename_floor_err", None)
            st.rerun()
    with c2:
        if st.button("Salvar", type="primary", use_container_width=True):
            new_name = new_name.strip()
            if not new_name or new_name == floor["name"]:
                st.rerun()
                return
            b_floors = _building_floors(building["id"])
            if any(f["id"] != floor["id"] and f["name"].lower() == new_name.lower() for f in b_floors):
                st.session_state.fp_rename_floor_err = "Já existe um andar com esse nome neste bloco."
                st.rerun()
                return
            old_name = floor["name"]
            for f in st.session_state.fp_floors:
                if f["id"] == floor["id"]:
                    f["name"] = new_name
            for r in st.session_state.fp_extra_rooms:
                if r["building"] == building["name"] and r["floor"] == old_name:
                    r["floor"] = new_name
            st.session_state.pop("fp_rename_floor_err", None)
            set_toast("Andar renomeado.")
            st.rerun()


@st.dialog("Remover andar")
def _dialog_confirm_remove_floor(floor: dict, building: dict):
    has_rooms = any(
        r["building"] == building["name"] and r["floor"] == floor["name"]
        for r in st.session_state.fp_extra_rooms
    )
    plan_key = f"{building['id']}__{floor['id']}"
    has_plan = plan_key in st.session_state.fp_plans

    if has_rooms or has_plan:
        st.warning("Este andar possui salas ou uma planta cadastrada. Ao remover, esses dados serão perdidos.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Remover andar", type="primary", use_container_width=True):
            b_floors = _building_floors(building["id"])
            remaining = [f for f in b_floors if f["id"] != floor["id"]]
            st.session_state.fp_floors = [f for f in _all_floors() if f["id"] != floor["id"]]
            st.session_state.fp_extra_rooms = [
                r for r in st.session_state.fp_extra_rooms
                if not (r["building"] == building["name"] and r["floor"] == floor["name"])
            ]
            if plan_key in st.session_state.fp_plans:
                del st.session_state.fp_plans[plan_key]
            if st.session_state.fp_sel_floor == floor["id"]:
                st.session_state.fp_sel_floor = remaining[0]["id"] if remaining else ""
            set_toast(f'Andar "{floor["name"]}" removido.')
            st.rerun()


@st.dialog("Adicionar sala")
def _dialog_add_room(building: dict, floor: dict):
    st.caption(f"{building['name']} · {floor['name']}")
    name = st.text_input("Nome da sala *", placeholder="Ex: Sala 102", key="fp_new_room_name")
    room_type = st.selectbox("Tipo *", ROOM_TYPES, key="fp_new_room_type")
    capacity = st.number_input("Capacidade *", min_value=1, value=30, key="fp_new_room_cap")
    err = st.session_state.get("fp_add_room_err", "")
    if err:
        st.error(err)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop("fp_add_room_err", None)
            st.rerun()
    with c2:
        if st.button("Adicionar sala", type="primary", use_container_width=True):
            name = name.strip()
            if not name:
                st.session_state.fp_add_room_err = "Nome da sala é obrigatório."
                st.rerun()
                return
            existing = _rooms_for(building["name"], floor["name"])
            if any(r["name"].lower() == name.lower() for r in existing):
                st.session_state.fp_add_room_err = "Já existe uma sala com esse nome neste andar."
                st.rerun()
                return
            st.session_state.fp_extra_rooms.append({
                "id": f"local-{_uid()}",
                "name": name,
                "building": building["name"],
                "floor": floor["name"],
                "type": room_type,
                "capacity": int(capacity),
            })
            st.session_state.pop("fp_add_room_err", None)
            set_toast(f'Sala "{name}" adicionada ao {floor["name"]}.')
            st.rerun()


# =========================================================
# DEMO FLOOR PLAN SVG
# =========================================================

_DEMO_SVG = """
<svg viewBox="0 0 800 560" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;height:100%;display:block;">
  <rect x="10" y="10" width="780" height="540"
        fill="#f8f7f4" stroke="#1c1c2e" stroke-width="4" rx="3"/>
  <rect x="10" y="245" width="780" height="70"
        fill="#e4e1db" stroke="#c8c4bc" stroke-width="1"/>
  <text x="400" y="286" text-anchor="middle" font-size="13"
        fill="#71717a" font-family="DM Sans,sans-serif"
        font-weight="600" letter-spacing="3">CORREDOR</text>
  <!-- salas andar superior -->
  <rect x="30"  y="30" width="150" height="195" fill="white" stroke="#a1a1aa" stroke-width="1.5" rx="2"/>
  <rect x="200" y="30" width="150" height="195" fill="white" stroke="#a1a1aa" stroke-width="1.5" rx="2"/>
  <rect x="370" y="30" width="150" height="195" fill="white" stroke="#a1a1aa" stroke-width="1.5" rx="2"/>
  <rect x="540" y="30" width="155" height="195" fill="white" stroke="#a1a1aa" stroke-width="1.5" rx="2"/>
  <rect x="715" y="30" width="55"  height="195" fill="#f0eee9" stroke="#a1a1aa" stroke-width="1.5" rx="2"/>
  <!-- escada -->
  <text x="742" y="48" text-anchor="middle" font-size="9" fill="#71717a" font-family="DM Sans,sans-serif">ESC.</text>
  <!-- salas andar inferior -->
  <rect x="30"  y="335" width="230" height="185" fill="white" stroke="#a1a1aa" stroke-width="1.5" rx="2"/>
  <rect x="280" y="335" width="230" height="185" fill="white" stroke="#a1a1aa" stroke-width="1.5" rx="2"/>
  <rect x="530" y="335" width="240" height="185" fill="white" stroke="#a1a1aa" stroke-width="1.5" rx="2"/>
  <!-- portas superiores -->
  <path d="M30 210 Q30 225 45 225"   fill="none" stroke="#a1a1aa" stroke-width="1.5"/>
  <path d="M200 210 Q200 225 215 225" fill="none" stroke="#a1a1aa" stroke-width="1.5"/>
  <path d="M370 210 Q370 225 385 225" fill="none" stroke="#a1a1aa" stroke-width="1.5"/>
  <path d="M540 210 Q540 225 555 225" fill="none" stroke="#a1a1aa" stroke-width="1.5"/>
  <!-- portas inferiores -->
  <path d="M30 365 Q30 350 45 350"   fill="none" stroke="#a1a1aa" stroke-width="1.5"/>
  <path d="M280 365 Q280 350 295 350" fill="none" stroke="#a1a1aa" stroke-width="1.5"/>
  <path d="M530 365 Q530 350 545 350" fill="none" stroke="#a1a1aa" stroke-width="1.5"/>
</svg>
"""


# =========================================================
# SEÇÃO: CONFIGURAR ESTRUTURA
# =========================================================

def _render_structure_config():
    buildings = _buildings()
    bid = st.session_state.fp_sel_building
    current_b = _current_building()

    with st.expander("⚙️ Configurar estrutura da instituição", expanded=False):
        col_b, col_f = st.columns(2, gap="medium")

        # -------------------------------------------------
        # BLOCOS
        # -------------------------------------------------
        with col_b:
            with st.container(border=True):
                hc1, hc2 = st.columns([3, 1])
                hc1.markdown("**Blocos**")
                with hc2:
                    if st.button("＋ Bloco", key="fp_open_add_building", use_container_width=True):
                        _dialog_add_building()

                if not buildings:
                    st.caption("Nenhum bloco cadastrado.")
                else:
                    for b in buildings:
                        is_sel = b["id"] == bid
                        rc1, rc2, rc3 = st.columns([3, 1, 1])
                        with rc1:
                            if st.button(
                                b["name"],
                                key=f"fp_sel_b_{b['id']}",
                                type="primary" if is_sel else "tertiary",
                                use_container_width=True,
                            ):
                                if not is_sel:
                                    floors = _building_floors(b["id"])
                                    st.session_state.fp_sel_building = b["id"]
                                    st.session_state.fp_sel_floor = floors[0]["id"] if floors else ""
                                    st.session_state.fp_positioning = None
                                    st.rerun()
                        with rc2:
                            if st.button("✏️", key=f"fp_ren_b_{b['id']}", help="Renomear"):
                                _dialog_rename_building(b)
                        with rc3:
                            if st.button("🗑", key=f"fp_del_b_{b['id']}", help="Remover"):
                                _dialog_confirm_remove_building(b)

        # -------------------------------------------------
        # ANDARES
        # -------------------------------------------------
        with col_f:
            with st.container(border=True):
                hf1, hf2 = st.columns([3, 1])
                floor_title = f"**Andares** — {current_b['name']}" if current_b else "**Andares**"
                hf1.markdown(floor_title)
                with hf2:
                    if st.button("＋ Andar", key="fp_open_add_floor", use_container_width=True, disabled=not current_b):
                        if current_b:
                            _dialog_add_floor(current_b)

                if not current_b:
                    st.caption("Selecione um bloco.")
                else:
                    b_floors = _building_floors(current_b["id"])
                    if not b_floors:
                        st.caption("Nenhum andar cadastrado.")
                    else:
                        fid = st.session_state.fp_sel_floor
                        for f in b_floors:
                            is_sel = f["id"] == fid
                            fc1, fc2, fc3 = st.columns([3, 1, 1])
                            with fc1:
                                if st.button(
                                    f["name"],
                                    key=f"fp_sel_f_{f['id']}",
                                    type="primary" if is_sel else "tertiary",
                                    use_container_width=True,
                                ):
                                    if not is_sel:
                                        st.session_state.fp_sel_floor = f["id"]
                                        st.session_state.fp_positioning = None
                                        st.rerun()
                            with fc2:
                                if st.button("✏️", key=f"fp_ren_f_{f['id']}", help="Renomear"):
                                    _dialog_rename_floor(f, current_b)
                            with fc3:
                                if st.button("🗑", key=f"fp_del_f_{f['id']}", help="Remover"):
                                    _dialog_confirm_remove_floor(f, current_b)


# =========================================================
# SEÇÃO: SELEÇÃO BLOCO / ANDAR
# =========================================================

def _render_selectors():
    buildings = _buildings()
    if not buildings:
        return

    col_b, col_f, _ = st.columns([2, 2, 3])

    building_names = [b["name"] for b in buildings]
    current_b = _current_building()
    sel_b_idx = next((i for i, b in enumerate(buildings) if b["id"] == st.session_state.fp_sel_building), 0)

    with col_b:
        chosen_b_name = st.selectbox(
            "Prédio",
            building_names,
            index=sel_b_idx,
            key="fp_select_building_widget",
        )
        chosen_b = next((b for b in buildings if b["name"] == chosen_b_name), None)
        if chosen_b and chosen_b["id"] != st.session_state.fp_sel_building:
            floors = _building_floors(chosen_b["id"])
            st.session_state.fp_sel_building = chosen_b["id"]
            st.session_state.fp_sel_floor = floors[0]["id"] if floors else ""
            st.session_state.fp_positioning = None
            st.rerun()

    bid = st.session_state.fp_sel_building
    b_floors = _building_floors(bid)

    with col_f:
        if b_floors:
            floor_names = [f["name"] for f in b_floors]
            sel_f_idx = next((i for i, f in enumerate(b_floors) if f["id"] == st.session_state.fp_sel_floor), 0)
            chosen_f_name = st.selectbox(
                "Andar",
                floor_names,
                index=sel_f_idx,
                key="fp_select_floor_widget",
            )
            chosen_f = next((f for f in b_floors if f["name"] == chosen_f_name), None)
            if chosen_f and chosen_f["id"] != st.session_state.fp_sel_floor:
                st.session_state.fp_sel_floor = chosen_f["id"]
                st.session_state.fp_positioning = None
                st.rerun()
        else:
            st.selectbox("Andar", ["—"], disabled=True, key="fp_select_floor_empty")


# =========================================================
# SEÇÃO: PLANTA DO ANDAR
# =========================================================

def _render_floor_plan(current_b: dict | None, current_f: dict | None, plan: dict, rooms: list[dict]):
    st.markdown("**Planta do andar**")

    positioning = st.session_state.fp_positioning
    positions = plan.get("positions", {})

    if positioning:
        pos_room = next((r for r in rooms if r["id"] == positioning), None)
        room_label = pos_room["name"] if pos_room else positioning
        st.info(f"📍 Clique no botão de posição abaixo para registrar: **{room_label}**")

    # ── Upload ou planta de exemplo ──────────────────────
    if plan["src"] is None:
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align:center; padding:32px 16px;">
                  <div style="font-size:32px; margin-bottom:8px;">🗺️</div>
                  <p style="font-weight:600; color:#1C1C2E; margin-bottom:4px;">
                    Adicione a planta deste andar
                  </p>
                  <p style="font-size:12px; color:#71717A;">
                    Aceito: PNG, JPG, SVG
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            uploaded = st.file_uploader(
                "Selecionar arquivo",
                type=["png", "jpg", "jpeg", "svg"],
                key=f"fp_upload_{_plan_key()}",
                label_visibility="collapsed",
            )
            if uploaded:
                import base64
                data = base64.b64encode(uploaded.read()).decode()
                mime = uploaded.type or "image/png"
                src = f"data:{mime};base64,{data}"
                st.session_state.fp_plans[_plan_key()] = {**plan, "src": src}
                st.rerun()

            st.write("")
            if st.button("Usar planta de exemplo", key="fp_demo_plan", use_container_width=True):
                st.session_state.fp_plans[_plan_key()] = {**plan, "src": "demo"}
                st.rerun()
        return

    # ── Exibir planta ────────────────────────────────────
    with st.container(border=True):
        # Cabeçalho da planta
        pc1, pc2 = st.columns([3, 1])
        with pc1:
            b_label = current_b["name"] if current_b else ""
            f_label = current_f["name"] if current_f else ""
            st.caption(f"{b_label} · {f_label}")
        with pc2:
            if st.button("🗑 Remover planta", key="fp_remove_plan", type="tertiary"):
                st.session_state.fp_plans[_plan_key()] = {"src": None, "positions": {}}
                st.rerun()

        # Planta SVG ou imagem
        if plan["src"] == "demo":
            st.html(f'<div style="border:1px solid #E4E1DB; border-radius:8px; overflow:hidden;">{_DEMO_SVG}</div>')
        else:
            st.image(plan["src"], use_container_width=True)

        # Marcadores de salas posicionadas
        if positions:
            st.divider()
            st.caption("📌 Salas posicionadas")
            for room_id, pos in positions.items():
                room = next((r for r in rooms if r["id"] == room_id), None)
                rname = room["name"] if room else room_id
                mc1, mc2, mc3 = st.columns([3, 1, 1])
                mc1.markdown(
                    f'<span style="background:#EDE9FE; color:#6D28D9; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:600;">📍 {rname}</span>',
                    unsafe_allow_html=True,
                )
                mc2.caption(f"x:{pos['x']:.0f}% y:{pos['y']:.0f}%")
                with mc3:
                    if st.button("✕", key=f"fp_unpin_{room_id}", help="Remover da planta"):
                        new_pos = {k: v for k, v in positions.items() if k != room_id}
                        st.session_state.fp_plans[_plan_key()] = {**plan, "positions": new_pos}
                        if st.session_state.fp_positioning == room_id:
                            st.session_state.fp_positioning = None
                        st.rerun()


# =========================================================
# SEÇÃO: SALAS DO ANDAR
# =========================================================

def _render_rooms_panel(current_b: dict | None, current_f: dict | None, plan: dict, rooms: list[dict]):
    has_plan = plan["src"] is not None
    positions = plan.get("positions", {})

    hc1, hc2 = st.columns([3, 1])
    hc1.markdown("**Salas do andar**")
    with hc2:
        disabled = not (current_b and current_f)
        if st.button("＋ Sala", key="fp_open_add_room", use_container_width=True, disabled=disabled):
            if current_b and current_f:
                _dialog_add_room(current_b, current_f)

    if not rooms:
        with st.container(border=True):
            st.caption("Nenhuma sala cadastrada neste andar.")
        return

    positioning = st.session_state.fp_positioning

    for room in rooms:
        rid = room["id"]
        is_positioned = rid in positions
        is_positioning_this = positioning == rid

        with st.container(border=True):
            c1, c2 = st.columns([3, 1], vertical_alignment="center")

            with c1:
                st.markdown(
                    f'<div style="font-size:14px; font-weight:600; color:#1C1C2E;">{room["name"]}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(f'{room["type"]} · {room["capacity"]} pessoas')

                if is_positioned:
                    st.markdown(
                        '<span style="background:#DCFCE7; color:#15803D; font-size:11px; font-weight:600; padding:2px 8px; border-radius:999px;">✓ Posicionada</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<span style="background:#FEF3C7; color:#B45309; font-size:11px; font-weight:600; padding:2px 8px; border-radius:999px;">! Não posicionada</span>',
                        unsafe_allow_html=True,
                    )

            with c2:
                if has_plan:
                    if is_positioning_this:
                        # Modo de posicionamento ativo: mostrar percentuais de coordenadas
                        st.caption("Informe a posição:")
                        px = st.number_input("X (%)", 1, 99, 50, key=f"fp_px_{rid}", label_visibility="collapsed")
                        py = st.number_input("Y (%)", 1, 99, 50, key=f"fp_py_{rid}", label_visibility="collapsed")
                        if st.button("✓ Confirmar", key=f"fp_confirm_pos_{rid}", type="primary", use_container_width=True):
                            new_positions = {**positions, rid: {"x": float(px), "y": float(py)}}
                            st.session_state.fp_plans[_plan_key()] = {**plan, "positions": new_positions}
                            st.session_state.fp_positioning = None
                            st.rerun()
                        if st.button("✕ Cancelar", key=f"fp_cancel_pos_{rid}", type="tertiary", use_container_width=True):
                            st.session_state.fp_positioning = None
                            st.rerun()
                    else:
                        btn_label = "Editar posição" if is_positioned else "Posicionar"
                        if st.button(btn_label, key=f"fp_pos_{rid}", use_container_width=True):
                            st.session_state.fp_positioning = rid
                            st.rerun()


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def floor_plan(user):
    _boot()

    # CSS local — não interfere em outras páginas
    st.markdown(
        """
        <style>
        [class*="st-key-fp_sel_b_"] button[kind="primary"],
        [class*="st-key-fp_sel_f_"] button[kind="primary"] {
            background: #6D28D9 !important;
            color: #FFFFFF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Cabeçalho ──────────────────────────────────────
    page_header(
        "Planta da instituição",
        "Cadastre a planta dos espaços e defina a localização das salas.",
    )

    # ── Configuração da estrutura ──────────────────────
    _render_structure_config()

    st.write("")

    # ── Seletores de bloco/andar ───────────────────────
    _render_selectors()

    current_b = _current_building()
    current_f = _current_floor()

    if not current_b:
        st.info("Adicione pelo menos um bloco para começar.")
        return

    if not current_f:
        st.info(f"Adicione um andar ao **{current_b['name']}** para continuar.")
        return

    plan = _current_plan()
    rooms = _rooms_for(current_b["name"], current_f["name"])

    st.divider()

    # ── Área principal: planta + lista de salas ────────
    col_plan, col_rooms = st.columns([3, 1], gap="medium")

    with col_plan:
        _render_floor_plan(current_b, current_f, plan, rooms)

    with col_rooms:
        _render_rooms_panel(current_b, current_f, plan, rooms)

    st.divider()

    # ── Ações finais ───────────────────────────────────
    ac1, _, ac2 = st.columns([1, 4, 1])
    with ac1:
        if st.button("Cancelar", key="fp_cancel", use_container_width=True):
            set_toast("Alterações descartadas.")
            st.rerun()
    with ac2:
        if st.button("Salvar planta", key="fp_save", type="primary", use_container_width=True):
            set_toast("Planta salva com sucesso.")
            st.rerun()
