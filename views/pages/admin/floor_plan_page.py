import base64
import html
import time as _time
import streamlit as st

from controllers.app_state_service import set_toast
from controllers.streamlit_runtime import get_streamlit_actor, get_streamlit_runtime
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource, ResourceNotFound
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


def _space_service():
    actor = get_streamlit_actor()
    if actor is None:
        raise PermissionError("Sua sessão expirou. Entre novamente.")
    return actor, get_streamlit_runtime().space_management


# =========================================================
# BOOT — session_state inicial
# =========================================================

def _boot():
    st.session_state.pop("fp_select_building_widget", None)
    actor = get_streamlit_actor()
    if actor is None:
        st.error("Sua sessão expirou. Entre novamente para gerenciar a planta.")
        return
    runtime = get_streamlit_runtime()
    buildings = runtime.space_management.list_buildings(actor, include_inactive=True)
    st.session_state.buildings = [
        {"id": item.id, "name": item.name, "active": item.active}
        for item in buildings
    ]
    st.session_state.floors = [
        {"id": item.id, "buildingId": item.building_id, "name": item.name, "active": item.active}
        for item in runtime.space_management.list_institution_floors(actor, include_inactive=True)
    ]
    st.session_state.spaces = [
        {
            "id": item.id, "name": item.name, "building": item.building,
            "floor": item.floor, "type": item.type, "capacity": item.capacity,
            "location": item.location, "status": item.status,
            "resources": list(item.resources), "occupancy": item.occupancy,
            "building_id": item.building_id, "floor_id": item.floor_id,
            "active": item.active,
        }
        for item in runtime.space_management.list_spaces(actor, include_inactive=True)
    ]
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


def _upload_key(kind: str) -> str:
    state_key = f"fp_{kind}_widget_key_{_plan_key()}"
    if state_key not in st.session_state:
        st.session_state[state_key] = f"fp_{kind}_{_plan_key()}_{_uid()}"
    return st.session_state[state_key]


def _reset_upload_keys() -> None:
    for kind in ("upload", "replace"):
        st.session_state[f"fp_{kind}_widget_key_{_plan_key()}"] = f"fp_{kind}_{_plan_key()}_{_uid()}"


def _current_plan() -> dict:
    floor = _current_floor()
    actor = get_streamlit_actor()
    if floor is None or actor is None:
        return {"src": None, "positions": {}}
    runtime = get_streamlit_runtime()
    try:
        saved_plan, content = runtime.floor_plan_management.read_file(actor, floor["id"])
    except ResourceNotFound:
        return {"src": None, "positions": {}}
    return {
        "src": content,
        "media_type": saved_plan.media_type,
        "positions": {item.space_id: {"x": item.x, "y": item.y} for item in saved_plan.positions},
    }


def _rooms_for(floor_id: str) -> list[dict]:
    return [
        s for s in st.session_state.get("spaces", [])
        if s["floor_id"] == floor_id
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
        if st.button("Cancelar", width="stretch"):
            st.session_state.pop("fp_add_building_err", None)
            st.rerun()
    with c2:
        if st.button("Adicionar bloco", type="primary", width="stretch"):
            name = name.strip()
            if not name:
                st.session_state.fp_add_building_err = "Nome do bloco é obrigatório."
                st.rerun()
                return
            try:
                actor, service = _space_service()
                building = service.create_building(actor, name)
            except (DomainAuthorizationError, DuplicateResource, ValueError, PermissionError) as exc:
                st.session_state.fp_add_building_err = str(exc)
                st.rerun()
                return
            st.session_state.fp_sel_building = building.id
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
        if st.button("Cancelar", width="stretch"):
            st.session_state.pop("fp_rename_building_err", None)
            st.rerun()
    with c2:
        if st.button("Salvar", type="primary", width="stretch"):
            new_name = new_name.strip()
            if not new_name or new_name == building["name"]:
                st.rerun()
                return
            try:
                actor, service = _space_service()
                service.update_building(actor, building["id"], new_name)
            except (DomainAuthorizationError, DuplicateResource, ResourceNotFound, ValueError, PermissionError) as exc:
                st.session_state.fp_rename_building_err = str(exc)
                st.rerun()
                return
            st.session_state.pop("fp_rename_building_err", None)
            set_toast("Bloco renomeado.")
            st.rerun()


@st.dialog("Remover bloco")
def _dialog_confirm_remove_building(building: dict):
    has_floors = any(f.get("buildingId") == building["id"] for f in _all_floors())
    has_rooms = any(s.get("building") == building["name"] for s in st.session_state.spaces)
    actor = get_streamlit_actor()
    runtime = get_streamlit_runtime()
    has_plans = actor is not None and any(
        runtime.floor_plan_management.get_for_floor(actor, floor["id"]) is not None
        for floor in _building_floors(building["id"])
    )

    if has_floors or has_rooms or has_plans:
        st.warning("Prédios com andares ou salas ativos não podem ser inativados. Os registros serão preservados.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", width="stretch"):
            st.rerun()
    with c2:
        if st.button("Inativar prédio", type="primary", width="stretch"):
            try:
                actor, service = _space_service()
                service.deactivate_building(actor, building["id"])
            except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                st.error(str(exc))
                return
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
        if st.button("Cancelar", width="stretch"):
            st.session_state.pop("fp_add_floor_err", None)
            st.rerun()
    with c2:
        if st.button("Adicionar andar", type="primary", width="stretch"):
            name = name.strip()
            if not name:
                st.session_state.fp_add_floor_err = "Nome do andar é obrigatório."
                st.rerun()
                return
            try:
                actor, service = _space_service()
                floor = service.create_floor(actor, building["id"], name)
            except (DomainAuthorizationError, DuplicateResource, ResourceNotFound, ValueError, PermissionError) as exc:
                st.session_state.fp_add_floor_err = str(exc)
                st.rerun()
                return
            st.session_state.fp_sel_floor = floor.id
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
        if st.button("Cancelar", width="stretch"):
            st.session_state.pop("fp_rename_floor_err", None)
            st.rerun()
    with c2:
        if st.button("Salvar", type="primary", width="stretch"):
            new_name = new_name.strip()
            if not new_name or new_name == floor["name"]:
                st.rerun()
                return
            try:
                actor, service = _space_service()
                service.update_floor(actor, floor["id"], new_name)
            except (DomainAuthorizationError, DuplicateResource, ResourceNotFound, ValueError, PermissionError) as exc:
                st.session_state.fp_rename_floor_err = str(exc)
                st.rerun()
                return
            st.session_state.pop("fp_rename_floor_err", None)
            set_toast("Andar renomeado.")
            st.rerun()


@st.dialog("Remover andar")
def _dialog_confirm_remove_floor(floor: dict, building: dict):
    has_rooms = any(
        s.get("building") == building["name"] and s.get("floor") == floor["name"]
        for s in st.session_state.spaces
    )
    actor = get_streamlit_actor()
    has_plan = actor is not None and get_streamlit_runtime().floor_plan_management.get_for_floor(actor, floor["id"]) is not None

    if has_rooms or has_plan:
        st.warning("Inative as salas antes de inativar este andar. Os registros e a planta serão preservados.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", width="stretch"):
            st.rerun()
    with c2:
        if st.button("Inativar andar", type="primary", width="stretch"):
            try:
                actor, service = _space_service()
                service.deactivate_floor(actor, floor["id"])
            except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                st.error(str(exc))
                return
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
        if st.button("Cancelar", width="stretch"):
            st.session_state.pop("fp_add_room_err", None)
            st.rerun()
    with c2:
        if st.button("Adicionar sala", type="primary", width="stretch"):
            name = name.strip()
            if not name:
                st.session_state.fp_add_room_err = "Nome da sala é obrigatório."
                st.rerun()
                return
            if room_type == "Outro" and not custom_room_type.strip():
                st.session_state.fp_add_room_err = "Informe o tipo da sala."
                st.rerun()
                return
            try:
                actor, service = _space_service()
                service.create_space(
                    actor, floor["id"], name,
                    custom_room_type.strip() if room_type == "Outro" else room_type,
                    int(capacity),
                )
            except (DomainAuthorizationError, DuplicateResource, ResourceNotFound, ValueError, PermissionError) as exc:
                st.session_state.fp_add_room_err = str(exc)
                st.rerun()
                return
            st.session_state.pop("fp_add_room_err", None)
            set_toast(f'Sala "{name}" adicionada ao {floor["name"]}.')
            st.rerun()


@st.dialog("Editar sala")
def _dialog_edit_room(room: dict):
    actor, service = _space_service()
    floors = service.list_floors(actor, room["building_id"], include_inactive=True)
    floor_ids = [item.id for item in floors]
    floor_names = {item.id: item.name for item in floors}
    if not floor_ids:
        st.error("Não há andares disponíveis para esta sala.")
        return
    st.text_input("Nome da sala", value=room["name"], key="fp_edit_room_name")
    available_types = list(dict.fromkeys([*ROOM_TYPES[:-1], room["type"], "Outro"]))
    current_type = room["type"] if room["type"] in available_types else "Outro"
    selected_type = st.selectbox(
        "Tipo da sala", available_types, index=available_types.index(current_type), key="fp_edit_room_type"
    )
    custom_type = ""
    if selected_type == "Outro":
        custom_type = st.text_input(
            "Tipo personalizado", value=room["type"] if current_type == "Outro" else "",
            key="fp_edit_room_custom_type",
        )
    floor_index = floor_ids.index(room["floor_id"]) if room["floor_id"] in floor_ids else 0
    st.selectbox("Andar", floor_ids, index=floor_index, format_func=floor_names.get, key="fp_edit_room_floor")
    st.number_input("Capacidade", min_value=1, max_value=10000, value=int(room["capacity"]), key="fp_edit_room_capacity")
    status_values = ["disponivel", "ocupado", "bloqueado"]
    status_labels = {"disponivel": "Disponível", "ocupado": "Ocupado", "bloqueado": "Bloqueado"}
    if room["status"] not in status_values:
        status_values.append(room["status"])
        status_labels[room["status"]] = room["status"].capitalize()
    st.selectbox(
        "Status", status_values, index=status_values.index(room["status"]),
        format_func=status_labels.get, key="fp_edit_room_status",
    )
    cancel, save = st.columns(2)
    if cancel.button("Cancelar", width="stretch"):
        st.rerun()
    if save.button("Salvar alterações", type="primary", width="stretch"):
        room_type = custom_type.strip() if selected_type == "Outro" else selected_type
        try:
            service.update_space(
                actor, room["id"],
                name=st.session_state.fp_edit_room_name,
                room_type=room_type,
                capacity=int(st.session_state.fp_edit_room_capacity),
                status=st.session_state.fp_edit_room_status,
                floor_id=st.session_state.fp_edit_room_floor,
            )
        except (DomainAuthorizationError, DuplicateResource, ResourceNotFound, ValueError) as exc:
            st.error(str(exc))
            return
        set_toast("Sala atualizada.")
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
                                f'{b["name"]}{" · Inativo" if not b["active"] else ""}',
                                key=f"fp_sel_b_{b['id']}",
                                type="primary" if is_sel else "tertiary",
                                width="stretch",
                            ):
                                if not is_sel:
                                    _select_building(b["id"])
                                    st.rerun()
                        with rc2:
                            if st.button("", key=f"fp_ren_b_{b['id']}", icon=":material/edit:", help="Renomear"):
                                _dialog_rename_building(b)
                        with rc3:
                            if b["active"]:
                                if st.button("", key=f"fp_del_b_{b['id']}", icon=":material/archive:", help="Inativar prédio"):
                                    _dialog_confirm_remove_building(b)
                            else:
                                if st.button("", key=f"fp_activate_b_{b['id']}", icon=":material/restore:", help="Reativar prédio"):
                                    try:
                                        actor, service = _space_service()
                                        service.activate_building(actor, b["id"])
                                    except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                                        st.error(str(exc))
                                    else:
                                        st.rerun()

        # -------------------------------------------------
        # ANDARES
        # -------------------------------------------------
        with col_f:
            with st.container(border=True):
                hf1, hf2 = st.columns([3, 1])
                floor_title = f"**Andares** — {current_b['name']}" if current_b else "**Andares**"
                hf1.markdown(floor_title)
                with hf2:
                    if st.button("", key="fp_open_add_floor", icon=":material/add:", help="Adicionar andar", disabled=not current_b or not current_b["active"]):
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
                                    f'{f["name"]}{" · Inativo" if not f["active"] else ""}',
                                    key=f"fp_sel_f_{f['id']}",
                                    type="primary" if is_sel else "tertiary",
                                    width="stretch",
                                ):
                                    if not is_sel:
                                        st.session_state.fp_sel_floor = f["id"]
                                        st.session_state.fp_positioning = None
                                        st.rerun()
                            with fc2:
                                if st.button("", key=f"fp_ren_f_{f['id']}", icon=":material/edit:", help="Renomear"):
                                    _dialog_rename_floor(f, current_b)
                            with fc3:
                                if f["active"]:
                                    if st.button("", key=f"fp_del_f_{f['id']}", icon=":material/archive:", help="Inativar andar"):
                                        _dialog_confirm_remove_floor(f, current_b)
                                else:
                                    if st.button("", key=f"fp_activate_f_{f['id']}", icon=":material/restore:", help="Reativar andar"):
                                        try:
                                            actor, service = _space_service()
                                            service.activate_floor(actor, f["id"])
                                        except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                                            st.error(str(exc))
                                        else:
                                            st.rerun()


# =========================================================
# SEÇÃO: SELEÇÃO BLOCO / ANDAR
# =========================================================

def _render_selectors():
    buildings = _buildings()
    if not buildings:
        return

    col_b, col_f, _ = st.columns([2, 2, 3])

    building_ids = [b["id"] for b in buildings]
    building_names = {
        b["id"]: f'{b["name"]}{" · Inativo" if not b["active"] else ""}'
        for b in buildings
    }

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
            floor_names = [f'{f["name"]}{" · Inativo" if not f["active"] else ""}' for f in b_floors]
            sel_f_idx = next((i for i, f in enumerate(b_floors) if f["id"] == st.session_state.fp_sel_floor), 0)
            chosen_f_name = st.selectbox(
                "Andar",
                floor_names,
                index=sel_f_idx,
                key="fp_select_floor_widget",
            )
            chosen_f = next((f for f in b_floors if f'{f["name"]}{" · Inativo" if not f["active"] else ""}' == chosen_f_name), None)
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
                key=_upload_key("upload"),
                label_visibility="collapsed",
                max_upload_size=10,
            )
            if uploaded:
                actor = get_streamlit_actor()
                try:
                    get_streamlit_runtime().floor_plan_management.upload(
                        actor, current_f["id"], uploaded.name, uploaded.getvalue()
                    )
                except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                    st.error(str(exc))
                else:
                    _reset_upload_keys()
                    set_toast("Planta enviada e salva.")
                    st.rerun()

            st.write("")
            if st.button("Usar planta de exemplo", key="fp_demo_plan", width="stretch"):
                actor = get_streamlit_actor()
                try:
                    get_streamlit_runtime().floor_plan_management.upload(
                        actor, current_f["id"], "planta-exemplo.svg", _DEMO_SVG.encode("utf-8")
                    )
                except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                    st.error(str(exc))
                else:
                    _reset_upload_keys()
                    set_toast("Planta de exemplo salva.")
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
                actor = get_streamlit_actor()
                try:
                    get_streamlit_runtime().floor_plan_management.remove(actor, current_f["id"])
                except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                    st.error(str(exc))
                else:
                    _reset_upload_keys()
                    set_toast("Planta removida.")
                    st.rerun()

        # Planta SVG ou imagem
        data_uri = f"data:{plan['media_type']};base64,{base64.b64encode(plan['src']).decode('ascii')}"
        markers = []
        for room_id, pos in positions.items():
            room = next((item for item in rooms if item["id"] == room_id), None)
            if room:
                label = html.escape(room["name"])
                markers.append(
                    f'<span title="{label}" style="position:absolute;left:{float(pos["x"]):.2f}%;top:{float(pos["y"]):.2f}%;transform:translate(-50%,-50%);display:flex;align-items:center;gap:4px;background:#6D28D9;color:#fff;border:2px solid #fff;border-radius:999px;padding:4px 9px;font:600 11px sans-serif;white-space:nowrap;box-shadow:0 1px 5px #0005">📍 {label}</span>'
                )
        st.html(
            '<div style="position:relative;width:100%;border:1px solid var(--stroke);border-radius:8px;overflow:hidden">'
            f'<img alt="Planta do andar" src="{data_uri}" style="display:block;width:100%;height:auto">'
            + "".join(markers)
            + "</div>"
        )

        with st.expander("Substituir planta"):
            replacement = st.file_uploader(
                "Enviar nova planta (PNG, JPG ou SVG)",
                type=["png", "jpg", "jpeg", "svg"],
                key=_upload_key("replace"),
                max_upload_size=10,
            )
            if replacement:
                actor = get_streamlit_actor()
                try:
                    get_streamlit_runtime().floor_plan_management.upload(
                        actor, current_f["id"], replacement.name, replacement.getvalue()
                    )
                except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                    st.error(str(exc))
                else:
                    _reset_upload_keys()
                    set_toast("Planta substituída. As posições das salas foram mantidas.")
                    st.rerun()

        # Marcadores de salas posicionadas
        if positions:
            st.divider()
            st.caption("📌 Salas posicionadas")
            for room_id, pos in positions.items():
                room = next((r for r in rooms if r["id"] == room_id), None)
                rname = room["name"] if room else room_id
                mc1, mc2, mc3 = st.columns([3, 1, 1])
                mc1.markdown(
                    f'<span style="background:#EDE9FE; color:#6D28D9; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:600;">📍 {html.escape(rname)}</span>',
                    unsafe_allow_html=True,
                )
                mc2.caption(f"x:{pos['x']:.0f}% y:{pos['y']:.0f}%")
                with mc3:
                    if st.button("", key=f"fp_unpin_{room_id}", icon=":material/close:", help="Remover da planta"):
                        actor = get_streamlit_actor()
                        try:
                            get_streamlit_runtime().floor_plan_management.remove_room_position(actor, current_f["id"], room_id)
                        except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                            st.error(str(exc))
                        else:
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
                r_head1, r_edit, r_status = st.columns([4, 1, 1])
                with r_head1:
                    st.markdown(
                        f'<div style="font-size:14px; font-weight:600; color:var(--graphite);">{html.escape(room["name"])}</div>',
                        unsafe_allow_html=True,
                    )
                with r_edit:
                    if st.button("", key=f"fp_edit_room_{rid}", icon=":material/edit:", help="Editar sala"):
                        _dialog_edit_room(room)
                with r_status:
                    if room["active"]:
                        if st.button("", key=f"fp_del_room_{rid}", icon=":material/archive:", help="Inativar sala"):
                            try:
                                actor, service = _space_service()
                                service.deactivate_space(actor, rid)
                            except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                                st.error(str(exc))
                            else:
                                set_toast(f'Sala "{room["name"]}" inativada.')
                                st.rerun()
                    else:
                        if st.button("", key=f"fp_activate_room_{rid}", icon=":material/restore:", help="Reativar sala"):
                            try:
                                actor, service = _space_service()
                                service.activate_space(actor, rid)
                            except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                                st.error(str(exc))
                            else:
                                set_toast(f'Sala "{room["name"]}" reativada.')
                                st.rerun()

                status_suffix = " · Inativa" if not room["active"] else ""
                st.caption(f'{room["type"]} · {room["capacity"]} pessoas{status_suffix}')

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
                        if st.button("Confirmar", key=f"fp_confirm_pos_{rid}", type="primary", width="stretch"):
                            actor = get_streamlit_actor()
                            try:
                                get_streamlit_runtime().floor_plan_management.set_room_position(
                                    actor, current_f["id"], rid, float(px), float(py)
                                )
                            except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                                st.error(str(exc))
                            else:
                                st.session_state.fp_positioning = None
                                st.rerun()
                    with cb2:
                        if st.button("Cancelar", key=f"fp_cancel_pos_{rid}", type="tertiary", width="stretch"):
                            st.session_state.fp_positioning = None
                            st.rerun()
                else:
                    btn_label = "Editar posição" if is_positioned else "Posicionar"
                    if st.button(btn_label, key=f"fp_pos_{rid}", width="stretch"):
                        st.session_state.fp_positioning = rid
                        st.rerun()


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def _render_resources(rooms: list[dict]) -> None:
    actor = get_streamlit_actor()
    if actor is None:
        return
    runtime = get_streamlit_runtime()
    service = runtime.resource_management
    with st.expander("Recursos institucionais"):
        try:
            resources = {
                item.id: item for item in service.list_resources(actor, include_inactive=True)
            }
            with st.form("fp_create_resource", clear_on_submit=True):
                name = st.text_input("Nome do novo recurso", max_chars=100)
                total = st.number_input("Estoque total", min_value=0, max_value=2**31 - 1, step=1)
                unavailable = st.number_input("Quantidade indisponível", min_value=0, max_value=2**31 - 1, step=1)
                if st.form_submit_button("Cadastrar recurso"):
                    service.create_resource(actor, name, total, unavailable)
                    st.rerun()

            if not resources:
                st.info("Nenhum recurso cadastrado.")
                return

            def resource_label(resource_id: str) -> str:
                resource = resources[resource_id]
                return resource.name if resource.active else f"{resource.name} (inativo)"

            selected = st.selectbox("Recurso", list(resources), format_func=resource_label)
            resource = resources[selected]
            with st.form(f"fp_edit_resource_{resource.id}"):
                new_name = st.text_input("Nome do recurso", value=resource.name, max_chars=100)
                total = st.number_input("Estoque total", min_value=0, max_value=2**31 - 1,
                                        value=resource.quantity_total, step=1)
                unavailable = st.number_input("Quantidade indisponível", min_value=0, max_value=2**31 - 1,
                                              value=resource.quantity_unavailable, step=1)
                if st.form_submit_button("Salvar recurso"):
                    service.update_resource(actor, resource.id, new_name, total, unavailable)
                    st.rerun()
            if st.button("Inativar recurso" if resource.active else "Reativar recurso", key="fp_toggle_resource"):
                service.set_resource_active(actor, resource.id, not resource.active)
                st.rerun()

            if rooms:
                room_names = {room["id"]: room["name"] for room in rooms if room["active"]}
                if room_names:
                    room_id = st.selectbox("Sala para associar recursos", list(room_names), format_func=room_names.__getitem__)
                    room = runtime.space_management.get_space(actor, room_id)
                    available = [
                        item.id for item in resources.values() if item.active or item.id in room.resource_ids
                    ]
                    with st.form(f"fp_assign_resources_{room.id}"):
                        assigned = st.multiselect(
                            "Recursos da sala", available, default=list(room.resource_ids),
                            format_func=resource_label,
                        )
                        if st.form_submit_button("Salvar recursos da sala"):
                            service.set_space_resources(actor, room.id, assigned)
                            st.rerun()
        except (DomainAuthorizationError, DuplicateResource, ResourceNotFound, ValueError) as exc:
            st.error(str(exc))


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

    rooms = _rooms_for(current_f["id"]) if current_f else []
    _render_resources(rooms)

    if not current_b:
        st.info("Adicione pelo menos um bloco para começar.")
        return

    if not current_f:
        st.info(f"Adicione um andar ao **{current_b['name']}** para continuar.")
        return

    plan = _current_plan()

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
        if st.button("Cancelar", key="fp_cancel", width="stretch"):
            set_toast("Alterações descartadas.")
            st.rerun()
    with ac2:
        if st.button("Salvar planta", key="fp_save", type="primary", width="stretch"):
            set_toast("Planta e posições já estão salvas.")
            st.rerun()
