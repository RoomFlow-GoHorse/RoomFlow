import pandas as pd
import streamlit as st

from controllers.app_state_service import set_toast
from controllers.streamlit_runtime import get_streamlit_actor, get_streamlit_runtime, uses_roomflow_api
from models.domain.entities.space import Space
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource, ResourceNotFound
from views.components.ui_components import badge, page_header


STATUS_LABELS = {"disponivel": "Disponível", "ocupado": "Ocupado", "bloqueado": "Bloqueado"}
SPACE_ERRORS = (DomainAuthorizationError, DuplicateResource, ResourceNotFound, ValueError)


def _resource_summary(space: Space) -> str:
    summary = ", ".join(space.resources[:3]) or "Não informados"
    if len(space.resources) > 3:
        summary += f" +{len(space.resources) - 3}"
    return summary


def _spaces_dataframe(spaces: list[Space]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Espaço": space.name,
            "Localização": space.location,
            "Tipo": space.type,
            "Capacidade": f"{space.capacity} pessoas",
            "Recursos": _resource_summary(space),
            "Status": STATUS_LABELS.get(space.status, space.status.capitalize()),
        }
        for space in spaces
    ])


def _room_header(space: Space) -> None:
    title, status = st.columns([3, 1], vertical_alignment="center")
    title.subheader(space.name, anchor=False)
    status.html(badge(space.status))
    st.caption(f"{space.location} · {space.type}")


def _dismiss_space_dialog(key):
    st.session_state.pop(key, None)


@st.dialog("Bloquear sala", width="medium", on_dismiss=lambda: _dismiss_space_dialog("block_space_id"))
def block_space_dialog(space: Space):
    _room_header(space)
    st.warning("A sala ficará bloqueada no catálogo.", icon=":material/warning:")
    with st.form(f"block_space_form_{space.id}"):
        reason = st.text_area("Motivo do bloqueio *", max_chars=500, height=100)
        cancel, submit = st.columns(2)
        cancelled = cancel.form_submit_button("Cancelar", width="stretch")
        submitted = submit.form_submit_button("Bloquear sala", type="primary", width="stretch")

    if cancelled:
        st.session_state.pop("block_space_id", None)
        st.rerun()
    if submitted:
        actor = get_streamlit_actor()
        if actor is None:
            st.error("Sua sessão expirou. Entre novamente.")
            return
        try:
            get_streamlit_runtime().space_management.block_space(actor, space.id, reason)
        except SPACE_ERRORS as exc:
            st.error(str(exc))
            return
        st.session_state.pop("block_space_id", None)
        set_toast("Sala bloqueada.")
        st.rerun()


@st.dialog("Editar espaço", width="medium", on_dismiss=lambda: _dismiss_space_dialog("edit_space_id"))
def edit_space_dialog(space: Space):
    _room_header(space)
    actor = get_streamlit_actor()
    if actor is None:
        st.error("Sua sessão expirou. Entre novamente.")
        return
    runtime = get_streamlit_runtime()
    with st.expander("Criar novo recurso", expanded=False):
        col_input, col_add = st.columns([3, 1], vertical_alignment="bottom")
        resource_name = col_input.text_input("Nome do recurso", key=f"new_res_input_{space.id}")
        if col_add.button("Criar", key=f"btn_create_res_{space.id}", width="stretch"):
            try:
                runtime.resource_management.create_resource(actor, resource_name)
            except DuplicateResource:
                st.warning("Esse recurso já está cadastrado.")
            except SPACE_ERRORS as exc:
                st.error(str(exc))
            else:
                set_toast("Recurso criado.")
                st.rerun()

    try:
        catalog = runtime.resource_management.list_resources(actor, include_inactive=True)
    except SPACE_ERRORS as exc:
        st.error(str(exc))
        return
    resource_by_id = {resource.id: resource for resource in catalog}
    st.divider()
    with st.form(f"edit_space_form_{space.id}"):
        name = st.text_input("Nome *", value=space.name, max_chars=120, key="space_edit_name")
        room_type = st.text_input("Tipo *", value=space.type, max_chars=60, key="space_edit_type")
        capacity = st.number_input("Capacidade *", min_value=1, max_value=10000,
                                   value=space.capacity, key="space_edit_capacity")
        selected = st.multiselect(
            "Recursos disponíveis",
            [resource.id for resource in catalog if resource.active or resource.id in space.resource_ids],
            default=[resource_id for resource_id in space.resource_ids if resource_id in resource_by_id],
            format_func=lambda resource_id: resource_by_id[resource_id].name,
            key="space_edit_resources",
        )
        cancel, submit = st.columns(2)
        cancelled = cancel.form_submit_button("Cancelar", width="stretch")
        submitted = submit.form_submit_button("Salvar alterações", type="primary", width="stretch")

    if cancelled:
        st.session_state.pop("edit_space_id", None)
        st.rerun()
    if submitted:
        try:
            if uses_roomflow_api():
                runtime.resource_management.update_space_configuration(
                    space.id, capacity, selected, name=name, room_type=room_type,
                )
            else:
                with runtime.admin_audit.atomic():
                    runtime.space_management.update_space(actor, space.id, name=name,
                                                          room_type=room_type, capacity=capacity)
                    runtime.resource_management.set_space_resources(actor, space.id, selected)
        except SPACE_ERRORS as exc:
            st.error(str(exc))
            return
        st.session_state.pop("edit_space_id", None)
        set_toast("Dados operacionais do espaço atualizados.")
        st.rerun()


def _space_table_and_actions(items: list[Space], actor):
    with st.container(border=True):
        st.caption(":material/info: Selecione um espaço abaixo para editar dados ou alterar a disponibilidade.")

    st.dataframe(
        _spaces_dataframe(items),
        column_config={
            "Espaço": st.column_config.TextColumn("Espaço", width="medium", pinned=True),
            "Localização": st.column_config.TextColumn("Localização", width="medium"),
            "Tipo": st.column_config.TextColumn("Tipo", width="small"),
            "Capacidade": st.column_config.TextColumn("Capacidade", width="small"),
            "Recursos": st.column_config.TextColumn("Recursos", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        hide_index=True,
        width="stretch",
    )
    rooms = {space.id: space for space in items}
    choose, edit, block = st.columns([4, 1, 1], vertical_alignment="bottom")
    space_id = choose.selectbox(
        "Ações do espaço", list(rooms), format_func=lambda item: f"{rooms[item].name} ({rooms[item].location})",
        key="space_action_selection",
    )
    selected = rooms[space_id]
    if edit.button("Editar", icon=":material/edit:", width="stretch", key="btn_action_edit_space"):
        st.session_state.pop("block_space_id", None)
        st.session_state.edit_space_id = space_id
        st.rerun()

    if selected.status == "bloqueado":
        if block.button("Desbloquear", icon=":material/lock_open:", width="stretch", key="btn_action_unblock_space"):
            try:
                get_streamlit_runtime().space_management.unblock_space(actor, space_id)
            except SPACE_ERRORS as exc:
                st.error(str(exc))
            else:
                set_toast("Sala desbloqueada.")
                st.rerun()
        if selected.block_reason:
            st.text(f"Motivo do bloqueio: {selected.block_reason}")
    elif block.button("Bloquear", icon=":material/lock:", width="stretch", key="btn_action_block_space"):
        st.session_state.pop("edit_space_id", None)
        st.session_state.block_space_id = space_id
        st.rerun()


def _render_dialogs(rooms: list[Space]):
    edit_id = st.session_state.get("edit_space_id")
    block_id = st.session_state.get("block_space_id")
    target = next((room for room in rooms if room.id == (edit_id or block_id)), None)
    if target:
        if edit_id:
            edit_space_dialog(target)
        else:
            block_space_dialog(target)


def _filter_options(rooms: list[Space], resources) -> dict:
    search, status_col, resource_col = st.columns([3, 1, 1], vertical_alignment="bottom")
    query = search.text_input("Buscar espaço", placeholder="Buscar por espaço ou localização...",
                              icon=":material/search:", label_visibility="collapsed", key="space_search_query",
                              max_chars=120)
    status = status_col.selectbox("Status", [None, *STATUS_LABELS], key="space_status_filter",
                                  format_func=lambda item: STATUS_LABELS.get(item, "Todos os status"))
    resource_labels = {item.id: item.name for item in resources}
    resource_id = resource_col.selectbox(
        "Recurso", [None, *resource_labels], key="space_resource_filter",
        format_func=lambda item: resource_labels.get(item, "Todos os recursos"),
    )
    buildings = {room.building_id: room.building for room in rooms if room.building_id}
    building_col, floor_col, type_col, min_col, max_col = st.columns(5)
    building_id = building_col.selectbox(
        "Prédio", [None, *buildings], key="space_building_filter",
        format_func=lambda item: buildings.get(item, "Todos os prédios"),
    )
    floors = {
        room.floor_id: room.floor if building_id else f"{room.building} · {room.floor}"
        for room in rooms if room.floor_id and (not building_id or room.building_id == building_id)
    }
    floor_id = floor_col.selectbox(
        "Andar", [None, *floors], key=f"space_floor_filter_{building_id}",
        format_func=lambda item: floors.get(item, "Todos os andares"),
    )
    room_type = type_col.selectbox(
        "Tipo", [None, *sorted({room.type for room in rooms})], key="space_type_filter",
        format_func=lambda item: item or "Todos os tipos",
    )
    minimum = min_col.number_input("Capacidade mínima", min_value=1, max_value=10000, value=None, key="space_min_capacity")
    maximum = max_col.number_input("Capacidade máxima", min_value=1, max_value=10000, value=None, key="space_max_capacity")
    return dict(search=query, status=status, resource_id=resource_id, building_id=building_id,
                floor_id=floor_id, room_type=room_type, min_capacity=minimum, max_capacity=maximum)


def spaces(user=None):
    page_header("Espaços", "Gerencie os dados, recursos e disponibilidade das salas.")
    actor = get_streamlit_actor(user)
    if actor is None:
        st.error("Sua sessão expirou. Entre novamente.")
        return
    runtime = get_streamlit_runtime()
    try:
        rooms = runtime.space_management.list_spaces(actor)
        resources = runtime.resource_management.list_resources(actor, include_inactive=True)
        filters = _filter_options(rooms, resources)
        visible = runtime.space_management.list_spaces(actor, **filters) if any(filters.values()) else rooms
    except SPACE_ERRORS as exc:
        st.error(str(exc))
        return

    if rooms and all(room.occupancy_verified for room in rooms):
        st.caption("Disponibilidade atual calculada pelas reservas aprovadas em andamento e pelos bloqueios.")
    elif rooms:
        st.caption("A disponibilidade será confirmada ao consultar as reservas do espaço.")

    if visible:
        _space_table_and_actions(visible, actor)
    else:
        st.info("Nenhum espaço encontrado.", icon=":material/search_off:")
    _render_dialogs(rooms)
