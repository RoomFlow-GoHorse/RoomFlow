import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import set_toast
from views.components.ui_components import badge, page_header


def _resource_names():
    return [item["name"] if isinstance(item, dict) else item for item in mock_data_service.resources()]


@st.dialog("Bloquear sala")
def block_space_dialog(space):
    st.caption(f"{space['name']} · {space['location']}")
    reason = st.text_area("Motivo do bloqueio", placeholder="Ex.: Manutenção preventiva.")
    if st.button("Bloquear sala", type="primary"):
        if not reason.strip():
            st.error("Informe o motivo do bloqueio.")
            return
        _, affected = mock_data_service.block_space(space["id"], reason.strip())
        set_toast(f"Sala bloqueada. {len(affected)} reserva(s) foram sinalizadas em Conflitos." if affected else "Sala bloqueada.")
        st.rerun()


@st.dialog("Editar espaço")
def edit_space_dialog(space):
    with st.form(f"edit_space_{space['id']}"):
        capacity = st.number_input("Capacidade", min_value=1, value=space["capacity"])
        resources = st.multiselect("Recursos", _resource_names(), default=space.get("resources", []))
        submitted = st.form_submit_button("Salvar alterações", type="primary")
    if submitted:
        mock_data_service.update_space(space["id"], capacity, resources)
        set_toast("Dados operacionais do espaço atualizados.")
        st.rerun()


def _space_card(space):
    with st.container(border=True):
        title, status = st.columns([4, 1], vertical_alignment="center")
        with title:
            st.markdown(f"**{space['name']}**")
            st.caption(f"{space['type']} · {space['location']} · {space['capacity']} pessoas")
        with status:
            st.html(badge(space["status"]))
        st.caption("Recursos: " + (", ".join(space.get("resources", [])) or "Não informados"))
        if space.get("block_reason"):
            st.warning(f"Motivo do bloqueio: {space['block_reason']}", icon=":material/block:")
        with st.container(horizontal=True):
            if st.button("Editar capacidade e recursos", key=f"edit_space_{space['id']}", icon=":material/edit:"):
                edit_space_dialog(space)
            if space["status"] != "bloqueado" and st.button("Bloquear sala", key=f"block_space_{space['id']}", icon=":material/block:"):
                block_space_dialog(space)


def spaces(user):
    page_header("Espaços", "Acompanhe e ajuste a operação das salas cadastradas.")
    col1, col2 = st.columns(2)
    query = col1.text_input("Buscar espaço")
    status = col2.selectbox("Status", ["Todos", "disponivel", "ocupado", "bloqueado"])
    items = mock_data_service.spaces(status, query)
    for space in items:
        _space_card(space)


def occupancy(user):
    page_header("Ocupação", "Acompanhe a situação das salas e as reservas em andamento.")
    items = mock_data_service.spaces()
    counts = (("Ocupadas", sum(item["status"] == "ocupado" for item in items)), ("Disponíveis", sum(item["status"] == "disponivel" for item in items)), ("Bloqueadas", sum(item["status"] == "bloqueado" for item in items)))
    for column, (label, value) in zip(st.columns(3), counts):
        with column:
            st.metric(label, value)
    for space in items:
        _space_card(space)


def localizar(user):
    spaces(user)
