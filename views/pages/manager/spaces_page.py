import pandas as pd
import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import set_toast
from controllers.streamlit_runtime import get_streamlit_actor, get_streamlit_runtime, uses_roomflow_api
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource, ResourceNotFound
from views.components.ui_components import badge, page_header

# ============================================================
# HELPERS
# ============================================================

def _resource_names():
    actor = get_streamlit_actor()
    if actor is None:
        raise PermissionError("Sua sessão expirou. Entre novamente.")
    return get_streamlit_runtime().resource_management.list_resources(actor, include_inactive=True)


def _load_spaces(query: str = "", status: str | None = None, resource_id: str | None = None):
    actor = get_streamlit_actor()
    if actor is None:
        raise PermissionError("Sua sessão expirou. Entre novamente.")
    selected_status = None if status in {None, "Todos"} else status
    real_spaces = get_streamlit_runtime().space_management.list_spaces(
        actor, search=query, status=selected_status, resource_id=resource_id
    )
    return [
        {
            "id": item.id,
            "name": item.name,
            "location": item.location,
            "type": item.type,
            "capacity": item.capacity,
            "resources": list(item.resources),
            "resource_ids": list(item.resource_ids),
            "status": item.status,
            "active": item.active,
            "building_id": item.building_id,
            "floor_id": item.floor_id,
        }
        for item in real_spaces
    ]


def _register_resource(resource):
    actor = get_streamlit_actor()
    if actor is None:
        raise PermissionError("Sua sessão expirou. Entre novamente.")
    try:
        get_streamlit_runtime().resource_management.create_resource(actor, resource)
    except DuplicateResource:
        return False
    return True


def _resource_summary(space):
    resources = space.get("resources", [])
    visible = resources[:3]
    summary = ", ".join(visible) or "Não informados"

    if len(resources) > len(visible):
        summary += f" +{len(resources) - len(visible)}"

    return summary


def _spaces_dataframe(items_list: list) -> pd.DataFrame:
    status_labels = {
        "disponivel": "Disponível",
        "ocupado": "Ocupado",
        "bloqueado": "Bloqueado",
    }
    return pd.DataFrame(
        [
            {
                "Espaço": space["name"],
                "Localização": space["location"],
                "Tipo": space["type"],
                "Capacidade": f"{space['capacity']} pessoas",
                "Recursos": _resource_summary(space),
                "Status": status_labels.get(space["status"], space["status"].capitalize()),
            }
            for space in items_list
        ]
    )

# ============================================================
# DIALOGS
# ============================================================

@st.dialog("Bloquear sala", width="medium")
def block_space_dialog(space):
    col_title, col_badge = st.columns([3, 1], vertical_alignment="center")
    with col_title:
        st.subheader(space["name"], anchor=False)
    with col_badge:
        st.html(f'<div style="display: flex; justify-content: flex-end; width: 100%;">{badge(space["status"])}</div>')

    st.caption(f"{space['location']} · {space['type']}")
    remote = uses_roomflow_api()
    if remote:
        st.warning("A sala ficará bloqueada no catálogo.", icon=":material/warning:")
    else:
        st.warning("Reservas ativas para esta sala serão sinalizadas como conflito e precisarão ser tratadas.", icon=":material/warning:")

    with st.form(f"block_space_form_{space['id']}"):
        reason = "" if remote else st.text_area(
            "Motivo do bloqueio *",
            placeholder="Ex.: Manutenção do ar-condicionado prevista para esta semana.",
            height=100,
        )
        cancel_col, submit_col = st.columns(2)
        with cancel_col:
            cancelled = st.form_submit_button("Cancelar", use_container_width=True)
        with submit_col:
            submitted = st.form_submit_button("Bloquear sala", type="primary", use_container_width=True)

    if cancelled:
        st.session_state["block_space_id"] = None
        st.rerun()

    if submitted:
        if not remote and not reason.strip():
            st.error("Informe o motivo do bloqueio.")
            return

        actor = get_streamlit_actor()
        try:
            get_streamlit_runtime().space_management.update_space(
                actor, space["id"], status="bloqueado"
            )
        except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
            st.error(str(exc))
            return
        affected = [] if remote else mock_data_service.block_space(space["id"], reason.strip())[1]
        message = (
            f"Sala bloqueada. {len(affected)} reserva(s) foram sinalizadas em Conflitos."
            if affected else "Sala bloqueada."
        )
        st.session_state["block_space_id"] = None
        set_toast(message)
        st.rerun()


@st.dialog("Editar espaço", width="medium")
def edit_space_dialog(space):
    col_title, col_badge = st.columns([3, 1], vertical_alignment="center")
    with col_title:
        st.subheader(space["name"], anchor=False)
    with col_badge:
        st.html(f'<div style="display: flex; justify-content: flex-end; width: 100%;">{badge(space["status"])}</div>')

    st.caption(f"{space['location']} · {space['type']}")

    with st.expander("Criar novo recurso", expanded=False):
        col_input, col_add = st.columns([3, 1], vertical_alignment="bottom")
        with col_input:
            new_resource_input = st.text_input("Nome do recurso", placeholder="Ex.: Lousa digital", key=f"new_res_input_{space['id']}")
        with col_add:
            if st.button("Criar", key=f"btn_create_res_{space['id']}", use_container_width=True):
                formatted_name = " ".join(new_resource_input.split())
                if not formatted_name:
                    st.error("Informe o nome do recurso.")
                else:
                    try:
                        created = _register_resource(formatted_name)
                    except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
                        st.error(str(exc))
                    else:
                        if not created:
                            st.warning("Esse recurso já está cadastrado.")
                        else:
                            set_toast("Recurso criado.")
                            st.rerun()

    st.divider()

    with st.form(f"edit_space_form_{space['id']}"):
        capacity = st.number_input("Capacidade *", min_value=1, value=int(space["capacity"]))
        catalog = _resource_names()
        resource_by_id = {item.id: item for item in catalog}
        selected_resource_ids = st.multiselect(
            "Recursos disponíveis",
            options=[item.id for item in catalog if item.active or item.id in space.get("resource_ids", [])],
            default=[item_id for item_id in space.get("resource_ids", []) if item_id in resource_by_id],
            format_func=lambda item_id: resource_by_id[item_id].name,
        )

        cancel_col, save_col = st.columns(2)
        with cancel_col:
            cancelled = st.form_submit_button("Cancelar", use_container_width=True)
        with save_col:
            submitted = st.form_submit_button("Salvar alterações", type="primary", use_container_width=True)

    if cancelled:
        st.session_state["edit_space_id"] = None
        st.rerun()

    if submitted:
        actor = get_streamlit_actor()
        try:
            runtime = get_streamlit_runtime()
            if uses_roomflow_api():
                runtime.resource_management.update_space_configuration(space["id"], capacity, selected_resource_ids)
            else:
                runtime.space_management.update_space(actor, space["id"], capacity=capacity)
                runtime.resource_management.set_space_resources(actor, space["id"], selected_resource_ids)
        except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
            st.error(str(exc))
            return
        st.session_state["edit_space_id"] = None
        set_toast("Dados operacionais do espaço atualizados.")
        st.rerun()

# ============================================================
# COMPONENTE DE TABELA E AÇÕES DO ESPAÇO
# ============================================================

def _space_table_and_actions(items):
    with st.container(border=True):
        st.caption(":material/info: Selecione um espaço abaixo no menu de ações para editar dados ou alterar a disponibilidade.")

    df_spaces = _spaces_dataframe(items)
    st.dataframe(
        df_spaces,
        column_config={
            "Espaço": st.column_config.TextColumn("Espaço", width="medium", pinned=True),
            "Localização": st.column_config.TextColumn("Localização", width="medium"),
            "Tipo": st.column_config.TextColumn("Tipo", width="small"),
            "Capacidade": st.column_config.TextColumn("Capacidade", width="small"),
            "Recursos": st.column_config.TextColumn("Recursos", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )

    space_map = {
        f"{space['name']} ({space['location']})": space
        for space in items
    }

    col_select, col_edit, col_block = st.columns([4, 1, 1], vertical_alignment="bottom")

    with col_select:
        selected_label = st.selectbox(
            "Ações do espaço",
            options=list(space_map.keys()),
            help="Selecione um espaço para tomar ações",
        )
        selected_space = space_map.get(selected_label, items[0])

    is_blocked = selected_space["status"] == "bloqueado"

    with col_edit:
        if st.button("Editar", icon=":material/edit:", use_container_width=True, key="btn_action_edit_space"):
            st.session_state["block_space_id"] = None
            st.session_state["edit_space_id"] = selected_space["id"]
            st.rerun()

    with col_block:
        if is_blocked:
            if st.button("Desbloquear", icon=":material/lock_open:", use_container_width=True, key="btn_action_unblock_space"):
                actor = get_streamlit_actor()
                get_streamlit_runtime().space_management.update_space(
                    actor, selected_space["id"], status="disponivel"
                )
                if not uses_roomflow_api():
                    mock_data_service.toggle_space(selected_space["id"])
                set_toast("Sala desbloqueada.")
                st.rerun()
        else:
            if st.button("Bloquear", icon=":material/lock:", use_container_width=True, key="btn_action_block_space"):
                st.session_state["edit_space_id"] = None
                st.session_state["block_space_id"] = selected_space["id"]
                st.rerun()


def _render_dialogs(all_spaces):
    edit_id = st.session_state.get("edit_space_id")
    block_id = st.session_state.get("block_space_id")

    if edit_id:
        target = next((item for item in all_spaces if item["id"] == edit_id), None)
        if target:
            edit_space_dialog(target)

    elif block_id:
        target = next((item for item in all_spaces if item["id"] == block_id), None)
        if target:
            block_space_dialog(target)

# ============================================================
# VIEWS
# ============================================================

def spaces(user=None):
    page_header("Espaços", "Gerencie a capacidade, recursos e disponibilidade das salas.")

    search_col, status_col, resource_col = st.columns([3, 1, 1], vertical_alignment="bottom")
    query = search_col.text_input("Buscar espaço", placeholder="Buscar por espaço ou localização...", icon=":material/search:", label_visibility="collapsed", key="space_search_query")
    status = status_col.selectbox(
        "Status",
        ["Todos", "disponivel", "ocupado", "bloqueado"],
        format_func=lambda v: {"Todos": "Todos os status", "disponivel": "Disponível", "ocupado": "Ocupado", "bloqueado": "Bloqueado"}[v],
        label_visibility="collapsed",
        key="space_status_filter",
    )
    try:
        resources = _resource_names()
    except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
        st.error(str(exc))
        return
    resource_labels = {"Todos": "Todos os recursos", **{item.id: item.name for item in resources}}
    resource_id = resource_col.selectbox(
        "Recurso",
        options=["Todos", *(item.id for item in resources)],
        format_func=resource_labels.get,
        label_visibility="collapsed",
        key="space_resource_filter",
    )

    try:
        items = _load_spaces(query, status, None if resource_id == "Todos" else resource_id)
    except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
        st.error(str(exc))
        return

    st.write("")

    if not items:
        st.info("Nenhum espaço encontrado.", icon=":material/search_off:")
        return

    _space_table_and_actions(items)
    _render_dialogs(_load_spaces())


def occupancy(user=None):
    page_header("Ocupação", "Acompanhe a situação das salas e as reservas em andamento.")

    try:
        items = _load_spaces()
    except (DomainAuthorizationError, ResourceNotFound, ValueError, PermissionError) as exc:
        st.error(str(exc))
        return
    counts = (
        ("Ocupadas", sum(i["status"] == "ocupado" for i in items)),
        ("Disponíveis", sum(i["status"] == "disponivel" for i in items)),
        ("Bloqueadas", sum(i["status"] == "bloqueado" for i in items)),
    )

    for col, (label, val) in zip(st.columns(3), counts):
        col.metric(label, val)

    st.write("")

    if not items:
        st.info("Nenhum espaço encontrado.", icon=":material/search_off:")
        return

    _space_table_and_actions(items)
    _render_dialogs(items)


def localizar(user=None):
    spaces(user)
