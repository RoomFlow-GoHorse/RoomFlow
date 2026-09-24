import pandas as pd
import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import set_toast
from views.components.ui_components import badge, page_header

ALL_RESOURCES = [
    "Projetor",
    "Ar-condicionado",
    "Computadores",
    "Quadro branco",
    "Sistema de áudio",
    "Videoconferência",
    'TV 55"',
    "Microfones",
]

# ============================================================
# HELPERS
# ============================================================

def _resource_names():
    names = set(ALL_RESOURCES)
    
    for item in mock_data_service.resources():
        names.add(item["name"] if isinstance(item, dict) else item)

    for space in mock_data_service.spaces():
        for res in space.get("resources", []):
            names.add(res)

    return sorted(list(names))


def _resource_key(value):
    return " ".join(str(value).split()).casefold()


def _register_resource(resource):
    resource_key = _resource_key(resource)

    if any(_resource_key(name) == resource_key for name in _resource_names()):
        return False

    if "resources" not in st.session_state:
        st.session_state.resources = []

    st.session_state.resources.append(
        {"name": resource, "total": 0, "available": 0}
    )
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
    st.warning("Reservas ativas para esta sala serão sinalizadas como conflito e precisarão ser tratadas.", icon=":material/warning:")

    with st.form(f"block_space_form_{space['id']}"):
        reason = st.text_area(
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
        if not reason.strip():
            st.error("Informe o motivo do bloqueio.")
            return

        _, affected = mock_data_service.block_space(space["id"], reason.strip())
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
                elif not _register_resource(formatted_name):
                    st.warning("Esse recurso já está cadastrado.")
                else:
                    set_toast("Recurso criado.")
                    st.rerun()

    st.divider()

    with st.form(f"edit_space_form_{space['id']}"):
        capacity = st.number_input("Capacidade *", min_value=1, value=int(space["capacity"]))
        resources = st.multiselect("Recursos disponíveis", _resource_names(), default=space.get("resources", []))

        cancel_col, save_col = st.columns(2)
        with cancel_col:
            cancelled = st.form_submit_button("Cancelar", use_container_width=True)
        with save_col:
            submitted = st.form_submit_button("Salvar alterações", type="primary", use_container_width=True)

    if cancelled:
        st.session_state["edit_space_id"] = None
        st.rerun()

    if submitted:
        mock_data_service.update_space(space["id"], capacity, resources)
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

    search_col, status_col = st.columns([3, 1], vertical_alignment="bottom")
    query = search_col.text_input("Buscar espaço", placeholder="Buscar por espaço ou localização...", icon=":material/search:", label_visibility="collapsed", key="space_search_query")
    status = status_col.selectbox(
        "Status",
        ["Todos", "disponivel", "ocupado", "bloqueado"],
        format_func=lambda v: {"Todos": "Todos os status", "disponivel": "Disponível", "ocupado": "Ocupado", "bloqueado": "Bloqueado"}[v],
        label_visibility="collapsed",
        key="space_status_filter",
    )

    items = mock_data_service.spaces(status, query)

    st.write("")

    if not items:
        st.info("Nenhum espaço encontrado.", icon=":material/search_off:")
        return

    _space_table_and_actions(items)
    _render_dialogs(mock_data_service.spaces())


def occupancy(user=None):
    page_header("Ocupação", "Acompanhe a situação das salas e as reservas em andamento.")

    items = mock_data_service.spaces()
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