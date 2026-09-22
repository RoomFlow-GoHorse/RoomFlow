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


def _resource_names():
    names = [
        item["name"] if isinstance(item, dict) else item
        for item in mock_data_service.resources()
    ]

    for resource in ALL_RESOURCES:
        if resource not in names:
            names.append(resource)

    for space in st.session_state.get("spaces", []):
        for resource in space.get("resources", []):
            if resource not in names:
                names.append(resource)

    return names


def _resource_key(value):
    return " ".join(str(value).split()).casefold()


def _register_resource(resource):
    resource_key = _resource_key(resource)

    if any(_resource_key(name) == resource_key for name in _resource_names()):
        return False

    st.session_state.resources.append(
        {
            "name": resource,
            "total": 0,
            "available": 0,
        }
    )
    return True


@st.dialog("Bloquear sala")
def block_space_dialog(space):
    st.caption(f"{space['name']} · {space['location']}")

    st.warning(
        "Reservas ativas para esta sala serão sinalizadas como conflito "
        "e precisarão ser tratadas.",
        icon=":material/warning:",
    )

    with st.form(f"block_space_{space['id']}"):
        reason = st.text_area(
            "Motivo do bloqueio *",
            placeholder="Ex.: Manutenção do ar-condicionado prevista para esta semana.",
            height=100,
        )

        submitted = st.form_submit_button(
            "Bloquear sala",
            type="primary",
            width="stretch",
        )

    if submitted:
        if not reason.strip():
            st.error("Informe o motivo do bloqueio.")
            return

        _, affected = mock_data_service.block_space(
            space["id"],
            reason.strip(),
        )

        message = (
            f"Sala bloqueada. {len(affected)} reserva(s) foram sinalizadas em Conflitos."
            if affected
            else "Sala bloqueada."
        )

        set_toast(message)
        st.rerun()


@st.dialog("Editar espaço")
def edit_space_dialog(space):
    st.caption(f"{space['location']} · {space['type']}")

    with st.form(f"create_resource_{space['id']}"):
        new_resource_column, create_column = st.columns([4, 1])

        with new_resource_column:
            new_resource = st.text_input(
                "Criar novo recurso",
                placeholder="Ex.: Lousa digital",
            )

        with create_column:
            st.write("")
            create_resource = st.form_submit_button(
                "Criar",
                type="secondary",
                width="stretch",
            )

    if create_resource:
        new_resource = " ".join(new_resource.split())

        if not new_resource:
            st.error("Informe o nome do recurso.")
        elif not _register_resource(new_resource):
            st.warning("Esse recurso já está cadastrado.")
        else:
            set_toast("Recurso criado.")
            st.rerun()

    with st.form(f"edit_space_{space['id']}"):
        capacity = st.number_input(
            "Capacidade *",
            min_value=1,
            value=space["capacity"],
        )

        resources = st.multiselect(
            "Recursos disponíveis",
            _resource_names(),
            default=space.get("resources", []),
        )

        cancel_column, save_column = st.columns(2)

        with cancel_column:
            cancelled = st.form_submit_button(
                "Cancelar",
                width="stretch",
            )

        with save_column:
            submitted = st.form_submit_button(
                "Salvar alterações",
                type="primary",
                width="stretch",
            )

    if cancelled:
        st.rerun()

    if submitted:
        mock_data_service.update_space(
            space["id"],
            capacity,
            resources,
        )

        set_toast("Dados operacionais do espaço atualizados.")
        st.rerun()


def _resource_summary(space):
    resources = space.get("resources", [])
    visible = resources[:3]

    summary = ", ".join(visible) or "Não informados"

    if len(resources) > len(visible):
        summary += f" +{len(resources) - len(visible)}"

    return summary


def _load_spaces_layout_style():
    st.html(
        """
        <style>
            .st-key-rf_space_cards {
                display: none;
            }

            .st-key-rf_space_actions {
                gap: 0.5rem;
            }

            @media (max-width: 768px) {
                .st-key-rf_space_table {
                    display: none;
                }

                .st-key-rf_space_cards {
                    display: block;
                }
            }
        </style>
        """
    )


def _space_actions(space, layout_key):
    with st.container(
        key=f"rf_space_actions_{layout_key}_{space['id']}",
        horizontal=True,
        gap="small",
    ):
        if st.button(
            "Editar",
            key=f"edit_space_{layout_key}_{space['id']}",
            icon=":material/edit:",
            width="content",
        ):
            edit_space_dialog(space)

        if space["status"] != "bloqueado":
            if st.button(
                "Bloquear",
                key=f"block_space_{layout_key}_{space['id']}",
                icon=":material/lock:",
                width="content",
            ):
                block_space_dialog(space)

        elif st.button(
            "Desbloquear",
            key=f"unblock_space_{layout_key}_{space['id']}",
            icon=":material/lock_open:",
            width="content",
        ):
            mock_data_service.toggle_space(space["id"])
            set_toast("Sala desbloqueada.")
            st.rerun()


def _space_table(items):
    with st.container(key="rf_space_table", border=True):
        header = st.columns(
            [2.1, 1.6, 1.25, 1.05, 2.1, 1.2, 1.8]
        )

        for column, label in zip(
            header,
            [
                "Espaço",
                "Localização",
                "Tipo",
                "Capacidade",
                "Recursos",
                "Status",
                "Ações",
            ],
        ):
            with column:
                st.caption(label)

        for space in items:
            columns = st.columns(
                [2.1, 1.6, 1.25, 1.05, 2.1, 1.2, 1.8],
                vertical_alignment="center",
            )

            with columns[0]:
                st.markdown(f"**{space['name']}**")

            with columns[1]:
                st.caption(space["location"])

            with columns[2]:
                st.caption(space["type"])

            with columns[3]:
                st.caption(f"{space['capacity']} pessoas")

            with columns[4]:
                st.caption(_resource_summary(space))

            with columns[5]:
                st.html(badge(space["status"]))

            with columns[6]:
                _space_actions(space, "table")

            if space.get("block_reason"):
                st.caption(
                    f"Motivo do bloqueio: {space['block_reason']}"
                )


def _space_card(space):
    with st.container(border=True):
        title_column, status_column = st.columns(
            [4, 1],
            vertical_alignment="center",
        )

        with title_column:
            st.markdown(f"**{space['name']}**")
            st.caption(
                f"{space['location']} · {space['type']}"
            )

        with status_column:
            st.html(badge(space["status"]))

        detail_column, resource_column = st.columns(2)

        with detail_column:
            st.caption(
                f"Capacidade: {space['capacity']} pessoas"
            )

        with resource_column:
            st.caption(
                f"Recursos: {_resource_summary(space)}"
            )

        if space.get("block_reason"):
            st.warning(
                f"Motivo do bloqueio: {space['block_reason']}",
                icon=":material/block:",
            )

        _space_actions(space, "card")


def _space_cards(items):
    with st.container(key="rf_space_cards"):
        for space in items:
            _space_card(space)


def spaces(user):
    page_header(
        "Espaços",
        "Gerencie a capacidade, recursos e disponibilidade das salas.",
    )

    search_column, status_column = st.columns([3, 1])

    with search_column:
        query = st.text_input(
            "Buscar espaço",
            placeholder="Buscar espaço...",
            icon=":material/search:",
        )

    with status_column:
        status = st.selectbox(
            "Status",
            ["Todos", "disponivel", "ocupado", "bloqueado"],
            format_func=lambda value: {
                "Todos": "Todos os status",
                "disponivel": "Disponível",
                "ocupado": "Ocupado",
                "bloqueado": "Bloqueado",
            }[value],
        )

    items = mock_data_service.spaces(status, query)

    if not items:
        with st.container(border=True):
            st.info(
                "Nenhum espaço encontrado.",
                icon=":material/search_off:",
            )
        return

    _load_spaces_layout_style()
    _space_table(items)
    _space_cards(items)


def occupancy(user):
    page_header(
        "Ocupação",
        "Acompanhe a situação das salas e as reservas em andamento.",
    )

    items = mock_data_service.spaces()

    counts = (
        (
            "Ocupadas",
            sum(item["status"] == "ocupado" for item in items),
        ),
        (
            "Disponíveis",
            sum(item["status"] == "disponivel" for item in items),
        ),
        (
            "Bloqueadas",
            sum(item["status"] == "bloqueado" for item in items),
        ),
    )

    for column, (label, value) in zip(st.columns(3), counts):
        with column:
            st.metric(label, value)

    _load_spaces_layout_style()
    _space_table(items)
    _space_cards(items)


def localizar(user):
    spaces(user)