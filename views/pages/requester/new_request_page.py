from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go, set_toast


_STEPS = (
    "Tipo",
    "Data e horário",
    "Espaço",
    "Justificativa",
)

_ACTIVITY_TYPES = (
    "Aula",
    "Banca",
    "Workshop",
    "Reunião",
    "Monitoria",
    "Outro",
)

_LOCAL_TIMEZONE = ZoneInfo("America/Porto_Velho")


def _local_today() -> date:
    """Retorna a data atual considerando o horário de Rondônia."""
    return datetime.now(_LOCAL_TIMEZONE).date()


def _reservation_datetimes(
    day: date,
    start: time,
    end: time,
) -> tuple[datetime, datetime]:
    """Combina data e horários usando o fuso local de Rondônia."""
    return (
        datetime.combine(
            day,
            start,
            tzinfo=_LOCAL_TIMEZONE,
        ),
        datetime.combine(
            day,
            end,
            tzinfo=_LOCAL_TIMEZONE,
        ),
    )


def _duration(
    day: date,
    start: time,
    end: time,
) -> str:
    """Calcula a duração da reserva."""
    starts_at, ends_at = _reservation_datetimes(
        day,
        start,
        end,
    )

    minutes = int(
        (ends_at - starts_at).total_seconds() // 60
    )

    if minutes <= 0:
        return "Horário inválido"

    hours, remaining = divmod(minutes, 60)

    if hours and remaining:
        return f"{hours}h {remaining}min"

    if hours:
        return f"{hours}h"

    return f"{remaining}min"


def _state():
    """Inicializa os valores da solicitação no session_state."""
    defaults = {
        "new_request_step": 0,
        "new_request_type": None,
        "new_request_custom_type": "",
        "new_request_date": _local_today(),
        "new_request_start": None,
        "new_request_end": None,
        "new_request_space_mode": "Escolher espaço",
        "new_request_space_id": None,
        "new_request_capacity": 1,
        "new_request_resources": [],
        "new_request_space_type": "Qualquer tipo",
        "new_request_building": "Qualquer bloco",
        "new_request_justification": "",
        "new_request_error": "",
        "new_request_submitted": False,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _selected_space():
    """Retorna o espaço atualmente selecionado."""
    selected_id = st.session_state.new_request_space_id

    return next(
        (
            space
            for space in st.session_state.spaces
            if space["id"] == selected_id
        ),
        None,
    )


def _available_spaces():
    """Retorna somente os espaços disponíveis."""
    return [
        space
        for space in st.session_state.spaces
        if space["status"] == "disponivel"
    ]


def _resource_names():
    """Retorna os nomes dos recursos disponíveis."""
    return [
        resource["name"]
        if isinstance(resource, dict)
        else resource
        for resource in st.session_state.resources
    ]


def _matching_spaces():
    """Retorna espaços que atendem aos requisitos informados."""
    required = st.session_state.new_request_resources
    capacity = st.session_state.new_request_capacity
    space_type = st.session_state.new_request_space_type
    building = st.session_state.new_request_building

    return [
        space
        for space in _available_spaces()
        if space["capacity"] >= capacity
        and (
            space_type == "Qualquer tipo"
            or space["type"] == space_type
        )
        and (
            building == "Qualquer bloco"
            or space["building"] == building
        )
        and all(
            resource in space.get("resources", [])
            for resource in required
        )
    ]


def _step_indicator(step: int):
    """Exibe o indicador das etapas."""
    labels = [
        f"{'✓' if index < step else index + 1}. {name}"
        for index, name in enumerate(_STEPS)
    ]

    st.segmented_control(
        "Etapas da solicitação",
        labels,
        default=labels[step],
        disabled=True,
        width="stretch",
        label_visibility="collapsed",
    )

    st.caption(
        f"Etapa {step + 1} de {len(_STEPS)}"
    )

    st.progress(
        (step + 1) / len(_STEPS)
    )


def _format_time(value: time | None) -> str:
    """Formata horário ou retorna placeholder quando vazio."""
    if value is None:
        return "Não informado"

    return value.strftime("%H:%M")


def _clear_error():
    """Oculta o erro da etapa assim que o usuário altera um campo."""
    st.session_state.new_request_error = ""


def _summary(step: int):
    """Exibe o resumo lateral da solicitação."""
    space = _selected_space()

    with st.container(border=True):
        st.markdown(
            "#### :material/calendar_month: Resumo"
        )

        st.caption("Sua solicitação")

        st.markdown(
            f"**Atividade**  \n"
            f"{st.session_state.new_request_type or 'Não selecionada'}"
        )

        st.markdown(
            f"**Data**  \n"
            f"{st.session_state.new_request_date.strftime('%d/%m/%Y')}"
        )

        start = st.session_state.new_request_start
        end = st.session_state.new_request_end

        if start and end:
            schedule = (
                f"{start.strftime('%H:%M')}"
                f"–"
                f"{end.strftime('%H:%M')}"
            )
        elif start:
            schedule = (
                f"{start.strftime('%H:%M')}"
                "– Não informado"
            )
        else:
            schedule = "Não informado"

        st.markdown(
            f"**Horário**  \n{schedule}"
        )

        st.markdown(
            f"**Espaço**  \n"
            f"{space['name'] if space else 'Não selecionado'}"
        )

        st.caption(
            f"Progresso: "
            f"{round((step + 1) / len(_STEPS) * 100)}%"
        )


def _validate(step: int) -> str | None:
    """Valida os dados da etapa atual."""

    if step == 0:
        if not st.session_state.new_request_type:
            return (
                "Selecione o tipo de atividade "
                "para continuar."
            )

        if (
            st.session_state.new_request_type == "Outro"
            and not st.session_state.new_request_custom_type.strip()
        ):
            return "Informe o tipo de atividade para continuar."

    elif step == 1:
        if st.session_state.new_request_date is None:
            return "Informe a data para continuar."

        start = st.session_state.new_request_start
        end = st.session_state.new_request_end

        if start is None:
            return (
                "Informe o horário de início "
                "para continuar."
            )

        if end is None:
            return (
                "Informe o horário de término "
                "para continuar."
            )

        starts_at, ends_at = _reservation_datetimes(
            st.session_state.new_request_date,
            start,
            end,
        )

        if ends_at <= starts_at:
            return (
                "O horário de término deve ser posterior "
                "ao horário de início."
            )

    elif step == 2:
        if not _selected_space():
            return (
                "Selecione um espaço para continuar."
            )

    elif step == 3:
        if not st.session_state.new_request_justification.strip():
            return (
                "Informe uma justificativa "
                "para continuar."
            )

    return None


def _go_next():
    """Valida a etapa atual e avança."""
    step = st.session_state.new_request_step

    error = _validate(step)

    if error:
        st.session_state.new_request_error = error
        return

    st.session_state.new_request_error = ""

    st.session_state.new_request_step = min(
        step + 1,
        len(_STEPS) - 1,
    )


def _submit(user):
    """Cria a solicitação de reserva."""
    for step in range(len(_STEPS)):
        error = _validate(step)

        if error:
            st.session_state.new_request_error = error
            return

    space = _selected_space()
    activity = (
        st.session_state.new_request_custom_type.strip()
        if st.session_state.new_request_type == "Outro"
        else st.session_state.new_request_type
    )

    mock_data_service.create_reservation(
        {
            "requester": user["name"],
            "requester_id": user["id"],
            "title": f"{activity} — {space['name']}",
            "type": activity,
            "space": space["name"],
            "date": (
                st.session_state.new_request_date.isoformat()
            ),
            "start": (
                st.session_state.new_request_start.strftime(
                    "%H:%M"
                )
            ),
            "end": (
                st.session_state.new_request_end.strftime(
                    "%H:%M"
                )
            ),
            "participants": (
                st.session_state.new_request_capacity
            ),
            "resources": (
                st.session_state.new_request_resources
            ),
            "justification": (
                st.session_state
                .new_request_justification
                .strip()
            ),
        }
    )

    set_toast(
        "Solicitação enviada para análise."
    )

    st.session_state.new_request_submitted = True


def _reset():
    """Limpa os dados da solicitação atual."""
    for key in list(st.session_state):
        if key.startswith("new_request_"):
            del st.session_state[key]


def _render_step(step: int):
    """Renderiza o conteúdo da etapa atual."""

    # ---------------------------------------------------------
    # ETAPA 1 — TIPO
    # ---------------------------------------------------------
    if step == 0:
        st.subheader(
            "Qual é o tipo de atividade?"
        )

        st.caption(
            "Selecione a finalidade principal da reserva."
        )

        st.segmented_control(
            "Tipo de atividade",
            _ACTIVITY_TYPES,
            key="new_request_type",
            width="stretch",
            on_change=_clear_error,
        )

        if st.session_state.new_request_type == "Outro":
            st.text_input(
                "Qual é o tipo de atividade?",
                key="new_request_custom_type",
                placeholder="Ex.: Evento institucional",
                max_chars=80,
                on_change=_clear_error,
            )

    # ---------------------------------------------------------
    # ETAPA 2 — DATA E HORÁRIO
    # ---------------------------------------------------------
    elif step == 1:
        st.subheader(
            "Quando será a atividade?"
        )

        st.caption(
            "Informe a data e o período necessário."
        )

        st.date_input(
            "Data",
            key="new_request_date",
            min_value=_local_today(),
            format="DD/MM/YYYY",
            on_change=_clear_error,
        )

        start_column, end_column = st.columns(2)

        start_column.time_input(
            "Horário de início",
            key="new_request_start",
            on_change=_clear_error,
        )

        end_column.time_input(
            "Horário de término",
            key="new_request_end",
            on_change=_clear_error,
        )

        start = st.session_state.new_request_start
        end = st.session_state.new_request_end

        if start and end:
            duration = _duration(
                st.session_state.new_request_date,
                start,
                end,
            )

            st.info(
                f"Duração da reserva: **{duration}**",
                icon=":material/schedule:",
            )

    # ---------------------------------------------------------
    # ETAPA 3 — ESPAÇO
    # ---------------------------------------------------------
    elif step == 2:
        st.subheader(
            "Onde será a atividade?"
        )

        st.caption(
            "Escolha uma sala específica ou encontre "
            "uma que atenda aos seus requisitos."
        )

        mode = st.segmented_control(
            "Como deseja escolher?",
            (
                "Escolher espaço",
                "Encontrar por requisitos",
            ),
            key="new_request_space_mode",
            width="stretch",
        )

        if mode == "Escolher espaço":
            choices = _available_spaces()

            selected = st.selectbox(
                "Espaço disponível",
                choices,
                format_func=lambda item: (
                    f"{item['name']} · "
                    f"{item['location']} · "
                    f"{item['capacity']} pessoas"
                ),
                index=None,
                placeholder="Selecione uma sala",
            )

            if selected:
                st.session_state.new_request_space_id = (
                    selected["id"]
                )
                _clear_error()

        else:
            capacity_column, type_column = st.columns(2)

            capacity_column.number_input(
                "Capacidade mínima",
                min_value=1,
                key="new_request_capacity",
            )

            type_column.selectbox(
                "Tipo de espaço",
                (
                    "Qualquer tipo",
                    "Sala de aula",
                    "Sala de reuniões",
                    "Auditório",
                    "Laboratório",
                ),
                key="new_request_space_type",
            )

            st.multiselect(
                "Recursos necessários",
                _resource_names(),
                key="new_request_resources",
                placeholder="Selecione os recursos",
            )

            st.selectbox(
                "Localização preferida",
                (
                    "Qualquer bloco",
                    *(
                        item["name"]
                        for item in st.session_state.buildings
                    ),
                ),
                key="new_request_building",
            )

            matches = _matching_spaces()

            if not matches:
                st.warning(
                    "Nenhum espaço disponível atende "
                    "aos requisitos informados.",
                    icon=":material/search_off:",
                )

            else:
                selected = st.selectbox(
                    "Espaço encontrado",
                    matches,
                    format_func=lambda item: (
                        f"{item['name']} · "
                        f"{item['location']} · "
                        f"{item['capacity']} pessoas"
                    ),
                    index=None,
                    placeholder="Escolha um espaço",
                )

                if selected:
                    st.session_state.new_request_space_id = (
                        selected["id"]
                    )
                    _clear_error()

        selected_space = _selected_space()

        if selected_space:
            st.success(
                f"Espaço selecionado: "
                f"**{selected_space['name']}** — "
                f"{selected_space['location']} · "
                f"{selected_space['capacity']} pessoas",
                icon=":material/check_circle:",
            )

    # ---------------------------------------------------------
    # ETAPA 4 — JUSTIFICATIVA
    # ---------------------------------------------------------
    elif step == 3:
        st.subheader(
            "Por que você precisa do espaço?"
        )

        st.caption(
            "Explique brevemente a finalidade da reserva."
        )

        st.text_area(
            "Justificativa",
            key="new_request_justification",
            max_chars=600,
            height=180,
            on_change=_clear_error,
            placeholder=(
                "Ex.: Aula de Cálculo II para turma "
                "do 3º semestre. Necessidade de projetor "
                "para apresentação de slides."
            ),
        )

        st.caption(
            f"{len(st.session_state.new_request_justification)} "
            "de 600 caracteres"
        )

        st.info(
            "Após o envio, sua solicitação será analisada "
            "pelo gerente. Se for aprovada, você receberá "
            "uma notificação.",
            icon=":material/notifications:",
        )


def new_reservation(user):
    """Página de criação de uma nova reserva."""
    _state()

    # ---------------------------------------------------------
    # SOLICITAÇÃO ENVIADA
    # ---------------------------------------------------------
    if st.session_state.get("new_request_submitted"):
        space = _selected_space()

        st.success(
            "Solicitação enviada!",
            icon=":material/check_circle:",
        )

        st.write(
            "Sua solicitação foi registrada com sucesso "
            "e será analisada pelo gerente."
        )

        with st.container(border=True):
            st.markdown(
                f"**Tipo de atividade:** "
                f"{st.session_state.new_request_type}"
            )

            st.markdown(
                f"**Espaço:** "
                f"{space['name'] if space else 'Não informado'}"
            )

            st.markdown(
                f"**Data e horário:** "
                f"{st.session_state.new_request_date.strftime('%d/%m/%Y')}"
                f" · "
                f"{st.session_state.new_request_start.strftime('%H:%M')}"
                f"–"
                f"{st.session_state.new_request_end.strftime('%H:%M')}"
            )

        with st.container(horizontal=True):
            if st.button(
                "Voltar ao início",
                icon=":material/home:",
            ):
                _reset()
                go("solicitante_dashboard")
                st.rerun()

            if st.button(
                "Acompanhar solicitação",
                icon=":material/list_alt:",
                type="primary",
            ):
                _reset()
                go("minhas_reservas")
                st.rerun()

        return

    # ---------------------------------------------------------
    # CABEÇALHO
    # ---------------------------------------------------------
    if st.button(
        "Voltar ao início",
        icon=":material/arrow_back:",
        type="tertiary",
    ):
        _reset()
        go("solicitante_dashboard")
        st.rerun()

    st.title(
        "Nova solicitação de reserva"
    )

    st.caption(
        "Preencha as informações abaixo "
        "para solicitar uma sala."
    )

    step = st.session_state.new_request_step

    _step_indicator(step)

    form_column, summary_column = st.columns(
        [2, 1],
        gap="large",
    )

    # ---------------------------------------------------------
    # FORMULÁRIO
    # ---------------------------------------------------------
    with form_column:
        with st.container(border=True):
            _render_step(step)

            if st.session_state.get("new_request_error"):
                st.error(
                    st.session_state.new_request_error
                )

            with st.container(
                horizontal=True,
                horizontal_alignment="right",
            ):
                if step > 0:
                    if st.button(
                        "Voltar",
                        icon=":material/arrow_back:",
                    ):
                        st.session_state.new_request_step -= 1
                        st.session_state.new_request_error = ""
                        st.rerun()

                if step < len(_STEPS) - 1:
                    if st.button(
                        "Continuar",
                        icon=":material/arrow_forward:",
                        type="primary",
                    ):
                        _go_next()
                        st.rerun()

                else:
                    if st.button(
                        "Solicitar reserva",
                        icon=":material/check_circle:",
                        type="primary",
                    ):
                        _submit(user)
                        st.rerun()

    # ---------------------------------------------------------
    # RESUMO LATERAL
    # ---------------------------------------------------------
    with summary_column:
        _summary(step)
