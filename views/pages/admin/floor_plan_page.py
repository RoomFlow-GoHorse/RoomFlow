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
    st.session_state.pop("fp_select_building_widget", None)

    if "buildings" not in st.session_state or not st.session_state.buildings:
        st.session_state.buildings = [
            {"id": "b-1", "name": "Bloco A"},
            {"id": "b-2", "name": "Bloco B"},
            {"id": "b-3", "name": "Bloco C"},
            {"id": "b-4", "name": "Bloco D"},
        ]
    if "floors" not in st.session_state or not st.session_state.floors:
        st.session_state.floors = [
            {"id": "b-1-f-1", "buildingId": "b-1", "name": "Térreo"},
            {"id": "b-1-f-2", "buildingId": "b-1", "name": "1º andar"},
            {"id": "b-1-f-3", "buildingId": "b-1", "name": "2º andar"},
            {"id": "b-2-f-1", "buildingId": "b-2", "name": "Térreo"},
            {"id": "b-2-f-2", "buildingId": "b-2", "name": "2º andar"},
            {"id": "b-3-f-1", "buildingId": "b-3", "name": "Térreo"},
            {"id": "b-4-f-1", "buildingId": "b-4", "name": "Térreo"},
        ]
    if "plans" not in st.session_state:
        st.session_state.plans = {}

    blist = _buildings()
    if "fp_sel_building" not in st.session_state or not any(b["id"] == st.session_state.fp_sel_building for b in blist):
        st.session_state.fp_sel_building = blist[0]["id"] if blist else ""

    bid = st.session_state.fp_sel_building
    matching = _building_floors(bid)
    if "fp_sel_floor" not in st.session_state or not any(f["id"] == st.session_state.fp_sel_floor for f in matching):
        st.session_state.fp_sel_floor = matching[0]["id"] if matching else ""

    if "fp_positioning" not in st.session_state:
        st.session_state.fp_positioning = None


# =========================================================
# DERIVED HELPERS
# =========================================================

def _buildings() -> list[dict]:
    return st.session_state.get("buildings", [])


def _all_floors() -> list[dict]:
    return st.session_state.get("floors", [])


def _current_building() -> dict | None:
    bid = st.session_state.fp_sel_building
    return next((b for b in _buildings() if b["id"] == bid), None)


def _current_floor() -> dict | None:
    fid = st.session_state.fp_sel_floor
    return next((f for f in _all_floors() if f["id"] == fid), None)


def _building_floors(bid: str) -> list[dict]:
    return _sort_floors([f for f in _all_floors() if f.get("buildingId") == bid])


def _select_building(building_id: str) -> None:
    floors = _building_floors(building_id)
    st.session_state.fp_sel_building = building_id
    st.session_state.fp_sel_floor = floors[0]["id"] if floors else ""
    st.session_state.fp_positioning = None


def _plan_key() -> str:
    return f"{st.session_state.fp_sel_building}__{st.session_state.fp_sel_floor}"


def _current_plan() -> dict:
    return st.session_state.plans.get(_plan_key(), {"src": None, "positions": {}})


def _rooms_for(building_name: str, floor_name: str) -> list[dict]:
    return [
        s for s in st.session_state.get("spaces", [])
        if s.get("building") == building_name and s.get("floor") == floor_name
    ]


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
            st.session_state.buildings.append({"id": new_id, "name": name})
            st.session_state.buildings = sorted(st.session_state.buildings, key=lambda x: x["name"])
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
            if not new_name or new_name == building["name"]:
                st.rerun()
                return
            exists = any(b["id"] != building["id"] and b["name"].lower() == new_name.lower() for b in _buildings())
            if exists:
                st.session_state.fp_rename_building_err = "Já existe um bloco com esse nome."
                st.rerun()
                return
            old_name = building["name"]
            for b in st.session_state.buildings:
                if b["id"] == building["id"]:
                    b["name"] = new_name
            for s in st.session_state.spaces:
                if s.get("building") == old_name:
                    s["building"] = new_name
                    s["location"] = f"{new_name}, {s.get('floor', '')}"
            st.session_state.pop("fp_rename_building_err", None)
            set_toast("Bloco renomeado.")
            st.rerun()


@st.dialog("Remover bloco")
def _dialog_confirm_remove_building(building: dict):
    has_floors = any(f.get("buildingId") == building["id"] for f in _all_floors())
    has_rooms = any(s.get("building") == building["name"] for s in st.session_state.spaces)
    has_plans = any(k.startswith(f"{building['id']}__") for k in st.session_state.plans)

    if has_floors or has_rooms or has_plans:
        st.warning("Este bloco possui andares, salas ou plantas cadastradas. Ao remover, esses dados serão perdidos.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Remover bloco", type="primary", use_container_width=True):
            remaining = [b for b in st.session_state.buildings if b["id"] != building["id"]]
            next_building = remaining[0] if remaining else None
            st.session_state.buildings = remaining
            st.session_state.floors = [f for f in _all_floors() if f.get("buildingId") != building["id"]]
            st.session_state.spaces = [s for s in st.session_state.spaces if s.get("building") != building["name"]]
            to_del = [k for k in st.session_state.plans if k.startswith(f"{building['id']}__")]
            for k in to_del:
                del st.session_state.plans[k]
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
            st.session_state.floors.append({"id": new_id, "buildingId": building["id"], "name": name})
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
            for f in st.session_state.floors:
                if f["id"] == floor["id"]:
                    f["name"] = new_name
            for s in st.session_state.spaces:
                if s.get("building") == building["name"] and s.get("floor") == old_name:
                    s["floor"] = new_name
                    s["location"] = f"{building['name']}, {new_name}"
            st.session_state.pop("fp_rename_floor_err", None)
            set_toast("Andar renomeado.")
            st.rerun()


@st.dialog("Remover andar")
def _dialog_confirm_remove_floor(floor: dict, building: dict):
    has_rooms = any(
        s.get("building") == building["name"] and s.get("floor") == floor["name"]
        for s in st.session_state.spaces
    )
    plan_key = f"{building['id']}__{floor['id']}"
    has_plan = plan_key in st.session_state.plans

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
            st.session_state.floors = [f for f in _all_floors() if f["id"] != floor["id"]]
            st.session_state.spaces = [
                s for s in st.session_state.spaces
                if not (s.get("building") == building["name"] and s.get("floor") == floor["name"])
            ]
            if plan_key in st.session_state.plans:
                del st.session_state.plans[plan_key]
            if st.session_state.fp_sel_floor == floor["id"]:
                st.session_state.fp_sel_floor = remaining[0]["id"] if remaining else ""
            set_toast(f'Andar "{floor["name"]}" removido.')
            st.rerun()


@st.dialog("Adicionar sala")
def _dialog_add_room(building: dict, floor: dict):
    st.caption(f"{building['name']} · {floor['name']}")
    name = st.text_input("Nome da sala *", placeholder="Ex: Sala 102", key="fp_new_room_name")
    room_type = st.selectbox("Tipo *", ROOM_TYPES, key="fp_new_room_type")
    custom_room_type = ""
    if room_type == "Outro":
        custom_room_type = st.text_input("Tipo da sala", key="fp_new_custom_room_type")
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
            if room_type == "Outro" and not custom_room_type.strip():
                st.session_state.fp_add_room_err = "Informe o tipo da sala."
                st.rerun()
                return
            existing = _rooms_for(building["name"], floor["name"])
            if any(r["name"].lower() == name.lower() for r in existing):
                st.session_state.fp_add_room_err = "Já existe uma sala com esse nome neste andar."
                st.rerun()
                return
            st.session_state.spaces.append({
                "id": f"s-{_uid()}",
                "name": name,
                "building": building["name"],
                "floor": floor["name"],
                "type": custom_room_type.strip() if room_type == "Outro" else room_type,
                "capacity": int(capacity),
                "location": f"{building['name']}, {floor['name']}",
                "status": "disponivel",
                "resources": [],
                "occupancy": 0,
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

    with st.expander(":material/settings: Configurar estrutura da instituição", expanded=False):
        col_b, col_f = st.columns(2, gap="medium")

        # -------------------------------------------------
        # BLOCOS
        # -------------------------------------------------
        with col_b:
            with st.container(border=True):
                hc1, hc2 = st.columns([3, 1])
                hc1.markdown("**Blocos**")
                with hc2:
                    if st.button("", key="fp_open_add_building", icon=":material/add:", help="Adicionar bloco"):
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
                                    _select_building(b["id"])
                                    st.rerun()
                        with rc2:
                            if st.button("", key=f"fp_ren_b_{b['id']}", icon=":material/edit:", help="Renomear"):
                                _dialog_rename_building(b)
                        with rc3:
                            if st.button("", key=f"fp_del_b_{b['id']}", icon=":material/delete:", help="Remover"):
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
                    if st.button("", key="fp_open_add_floor", icon=":material/add:", help="Adicionar andar", disabled=not current_b):
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
                                if st.button("", key=f"fp_ren_f_{f['id']}", icon=":material/edit:", help="Renomear"):
                                    _dialog_rename_floor(f, current_b)
                            with fc3:
                                if st.button("", key=f"fp_del_f_{f['id']}", icon=":material/delete:", help="Remover"):
                                    _dialog_confirm_remove_floor(f, current_b)


# =========================================================
# SEÇÃO: SELEÇÃO BLOCO / ANDAR
# =========================================================

def _render_selectors():
    buildings = _buildings()
    if not buildings:
        return

    col_b, col_f, _ = st.columns([2, 2, 3])

    building_ids = [b["id"] for b in buildings]
    building_names = {b["id"]: b["name"] for b in buildings}

    with col_b:
        st.selectbox(
            "Prédio",
            building_ids,
            format_func=building_names.get,
            key="fp_sel_building",
            on_change=lambda: _select_building(st.session_state.fp_sel_building),
        )

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
                  <p style="font-weight:600; color:var(--graphite); margin-bottom:4px;">
                    Adicione a planta deste andar
                  </p>
                  <p style="font-size:12px; color:var(--graphite-muted);">
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
                st.session_state.plans[_plan_key()] = {**plan, "src": src}
                st.rerun()

            st.write("")
            if st.button("Usar planta de exemplo", key="fp_demo_plan", use_container_width=True):
                st.session_state.plans[_plan_key()] = {**plan, "src": "demo"}
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
            if st.button("", key="fp_remove_plan", icon=":material/delete:", help="Remover planta", type="tertiary"):
                st.session_state.plans[_plan_key()] = {"src": None, "positions": {}}
                st.rerun()

        # Planta SVG ou imagem
        if plan["src"] == "demo":
            st.html(f'<div style="border:1px solid var(--stroke); border-radius:8px; overflow:hidden;">{_DEMO_SVG}</div>')
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
                    if st.button("", key=f"fp_unpin_{room_id}", icon=":material/close:", help="Remover da planta"):
                        new_pos = {k: v for k, v in positions.items() if k != room_id}
                        st.session_state.plans[_plan_key()] = {**plan, "positions": new_pos}
                        for s in st.session_state.spaces:
                            if s["id"] == room_id:
                                s.pop("position", None)
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
        if st.button("", key="fp_open_add_room", icon=":material/add:", help="Adicionar sala", disabled=disabled):
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
            with st.container(gap=None):
                r_head1, r_head2 = st.columns([4, 1])
                with r_head1:
                    st.markdown(
                        f'<div style="font-size:14px; font-weight:600; color:var(--graphite);">{room["name"]}</div>',
                        unsafe_allow_html=True,
                    )
                with r_head2:
                    if st.button("", key=f"fp_del_room_{rid}", icon=":material/delete:", help="Remover sala"):
                        st.session_state.spaces = [s for s in st.session_state.spaces if s["id"] != rid]
                        if rid in positions:
                            new_pos = {k: v for k, v in positions.items() if k != rid}
                            st.session_state.plans[_plan_key()] = {**plan, "positions": new_pos}
                        if st.session_state.fp_positioning == rid:
                            st.session_state.fp_positioning = None
                        set_toast(f'Sala "{room["name"]}" removida.')
                        st.rerun()

                st.caption(f'{room["type"]} · {room["capacity"]} pessoas')

                if is_positioned:
                    st.markdown(
                        '<span style="background:var(--success-bg); color:var(--success); font-size:11px; font-weight:600; padding:2px 8px; border-radius:999px; display:inline-block; margin-bottom:0;">✓ Posicionada</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<span style="background:var(--warning-bg); color:var(--warning); font-size:11px; font-weight:600; padding:2px 8px; border-radius:999px; display:inline-block; margin-bottom:0;">Não posicionada</span>',
                        unsafe_allow_html=True,
                    )

            if has_plan:
                if is_positioning_this:
                    st.caption("Informe a posição:")
                    cx, cy = st.columns(2)
                    with cx:
                        px = st.number_input("X (%)", 1, 99, 50, key=f"fp_px_{rid}", label_visibility="collapsed")
                    with cy:
                        py = st.number_input("Y (%)", 1, 99, 50, key=f"fp_py_{rid}", label_visibility="collapsed")

                    cb1, cb2 = st.columns(2)
                    with cb1:
                        if st.button("Confirmar", key=f"fp_confirm_pos_{rid}", type="primary", use_container_width=True):
                            pos_data = {"x": float(px), "y": float(py)}
                            new_positions = {**positions, rid: pos_data}
                            st.session_state.plans[_plan_key()] = {**plan, "positions": new_positions}
                            for s in st.session_state.spaces:
                                if s["id"] == rid:
                                    s["position"] = pos_data
                            st.session_state.fp_positioning = None
                            st.rerun()
                    with cb2:
                        if st.button("Cancelar", key=f"fp_cancel_pos_{rid}", type="tertiary", use_container_width=True):
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
