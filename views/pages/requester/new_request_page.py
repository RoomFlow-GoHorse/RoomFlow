from datetime import date, datetime, time
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go, set_toast

# -----------------------------------------------------------------------------
# CONSTANTES E CONFIGURAÇÃO
# -----------------------------------------------------------------------------

_STEPS: Tuple[str, ...] = (
    "Tipo",
    "Data e horário",
    "Espaço",
    "Justificativa",
)

_ACTIVITY_TYPES: Tuple[str, ...] = (
    "Aula",
    "Banca",
    "Workshop",
    "Reunião",
    "Monitoria",
    "Outro",
)

_SPACE_TYPES: Tuple[str, ...] = (
    "Qualquer tipo",
    "Sala de aula",
    "Sala de reuniões",
    "Auditório",
    "Laboratório",
)

_LOCAL_TIMEZONE = ZoneInfo("America/Porto_Velho")


# -----------------------------------------------------------------------------
# FUNÇÕES UTILITÁRIAS DE DATA E HORA
# -----------------------------------------------------------------------------

def _local_today() -> date:
    """Retorna a data atual considerando o fuso horário local."""
    return datetime.now(_LOCAL_TIMEZONE).date()


def _reservation_datetimes(
    day: date,
    start: time,
    end: time,
) -> Tuple[datetime, datetime]:
    """Combina data e horários atribuindo o fuso horário correto."""
    return (
        datetime.combine(day, start, tzinfo=_LOCAL_TIMEZONE),
        datetime.combine(day, end, tzinfo=_LOCAL_TIMEZONE),
    )


def _format_duration(day: date, start: time, end: time) -> Optional[str]:
    """Calcula e formata a duração do intervalo de reserva."""
    starts_at, ends_at = _reservation_datetimes(day, start, end)
    minutes = int((ends_at - starts_at).total_seconds() // 60)

    if minutes <= 0:
        return None

    hours, remaining_minutes = divmod(minutes, 60)
    
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if remaining_minutes:
        parts.append(f"{remaining_minutes}min")

    return " ".join(parts)


# -----------------------------------------------------------------------------
# GERENCIAMENTO DE ESTADO
# -----------------------------------------------------------------------------

def _init_state() -> None:
    """Inicializa as variáveis de estado da solicitação no session_state de forma segura."""
    defaults: Dict[str, Any] = {
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
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_state() -> None:
    """Remove do session_state todas as variáveis do formulário de solicitação."""
    for key in list(st.session_state.keys()):
        if key.startswith("new_request_"):
            del st.session_state[key]


def _clear_error() -> None:
    """Limpa mensagens de erro vigentes."""
    st.session_state.new_request_error = ""


# -----------------------------------------------------------------------------
# CONSULTAS DE DADOS E FILTROS
# -----------------------------------------------------------------------------

def _get_spaces() -> List[Dict[str, Any]]:
    """Recupera a lista de espaços cadastrados."""
    return st.session_state.get("spaces", [])


def _get_available_spaces() -> List[Dict[str, Any]]:
    """Filtra apenas espaços com status 'disponivel'."""
    return [space for space in _get_spaces() if space.get("status") == "disponivel"]


def _get_selected_space() -> Optional[Dict[str, Any]]:
    """Retorna o objeto do espaço selecionado no estado atual."""
    selected_id = st.session_state.get("new_request_space_id")
    if not selected_id:
        return None
    return next((s for s in _get_spaces() if s.get("id") == selected_id), None)


def _get_resource_names() -> List[str]:
    """Retorna os nomes formatados de todos os recursos do sistema."""
    raw_resources = st.session_state.get("resources", [])
    return [
        res["name"] if isinstance(res, dict) else res
        for res in raw_resources
    ]


def _get_matching_spaces() -> List[Dict[str, Any]]:
    """Retorna espaços disponíveis que correspondem aos critérios do filtro."""
    required_resources = set(st.session_state.new_request_resources)
    capacity = st.session_state.new_request_capacity
    space_type = st.session_state.new_request_space_type
    building = st.session_state.new_request_building

    matches = []
    for space in _get_available_spaces():
        if space.get("capacity", 0) < capacity:
            continue
        if space_type != "Qualquer tipo" and space.get("type") != space_type:
            continue
        if building != "Qualquer bloco" and space.get("building") != building:
            continue
        
        space_resources = set(space.get("resources", []))
        if not required_resources.issubset(space_resources):
            continue

        matches.append(space)

    return matches


# -----------------------------------------------------------------------------
# VALIDAÇÕES
# -----------------------------------------------------------------------------

def _validate_step(step: int) -> Optional[str]:
    """Valida as entradas da etapa informada e retorna mensagem de erro, se houver."""
    if step == 0:
        req_type = st.session_state.new_request_type
        if not req_type:
            return "Selecione o tipo de atividade para continuar."
        if req_type == "Outro" and not st.session_state.new_request_custom_type.strip():
            return "Informe a especificação do tipo de atividade."

    elif step == 1:
        if not st.session_state.new_request_date:
            return "Informe uma data válida para a reserva."

        start = st.session_state.new_request_start
        end = st.session_state.new_request_end

        if not start:
            return "Informe o horário de início."
        if not end:
            return "Informe o horário de término."

        starts_at, ends_at = _reservation_datetimes(
            st.session_state.new_request_date, start, end
        )
        if ends_at <= starts_at:
            return "O horário de término deve ser posterior ao horário de início."

    elif step == 2:
        if not _get_selected_space():
            return "Selecione um espaço para continuar."

    elif step == 3:
        if not st.session_state.new_request_justification.strip():
            return "A justificativa da solicitação é obrigatória."

    return None


# -----------------------------------------------------------------------------
# AÇÕES DE NAVEGAÇÃO E SUBMISSÃO
# -----------------------------------------------------------------------------

def _go_next() -> None:
    """Valida a etapa atual antes de avançar para a próxima."""
    current_step = st.session_state.new_request_step
    error = _validate_step(current_step)

    if error:
        st.session_state.new_request_error = error
        return

    _clear_error()
    st.session_state.new_request_step = min(current_step + 1, len(_STEPS) - 1)


def _go_back() -> None:
    """Retorna para a etapa anterior sem validar a atual."""
    _clear_error()
    st.session_state.new_request_step = max(st.session_state.new_request_step - 1, 0)


def _submit_request(user: Dict[str, Any]) -> None:
    """Executa a validação global de todas as etapas e cria a reserva."""
    for step_index in range(len(_STEPS)):
        error = _validate_step(step_index)
        if error:
            st.session_state.new_request_step = step_index
            st.session_state.new_request_error = error
            return

    space = _get_selected_space()
    if not space:
        st.session_state.new_request_error = "Espaço inválido ou não selecionado."
        return

    activity = (
        st.session_state.new_request_custom_type.strip()
        if st.session_state.new_request_type == "Outro"
        else st.session_state.new_request_type
    )

    mock_data_service.create_reservation(
        {
            "requester": user.get("name", "Usuário"),
            "requester_id": user.get("id"),
            "title": f"{activity} — {space['name']}",
            "type": activity,
            "space": space["name"],
            "date": st.session_state.new_request_date.isoformat(),
            "start": st.session_state.new_request_start.strftime("%H:%M"),
            "end": st.session_state.new_request_end.strftime("%H:%M"),
            "participants": st.session_state.new_request_capacity,
            "resources": st.session_state.new_request_resources,
            "justification": st.session_state.new_request_justification.strip(),
        }
    )

    set_toast("Solicitação enviada para análise com sucesso!")
    st.session_state.new_request_submitted = True


# -----------------------------------------------------------------------------
# COMPONENTES VISUAIS
# -----------------------------------------------------------------------------

def _render_step_indicator(current_step: int) -> None:
    """Renderiza o cabeçalho de progresso das etapas."""
    labels = [
        f"{'✓' if idx < current_step else idx + 1}. {name}"
        for idx, name in enumerate(_STEPS)
    ]

    st.segmented_control(
        "Progresso da Solicitação",
        options=labels,
        default=labels[current_step],
        disabled=True,
        width="stretch",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.caption(f"Etapa {current_step + 1} de {len(_STEPS)}")
    with col2:
        percent = int(((current_step + 1) / len(_STEPS)) * 100)
        st.caption(f"**{percent}%** concluído")

    st.progress((current_step + 1) / len(_STEPS))


def _render_summary_card(step: int) -> None:
    """Exibe o painel lateral com o resumo dinâmico da solicitação."""
    space = _get_selected_space()
    start = st.session_state.new_request_start
    end = st.session_state.new_request_end

    if start and end:
        schedule_text = f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')}"
    elif start:
        schedule_text = f"{start.strftime('%H:%M')} – --:--"
    else:
        schedule_text = "Não informado"

    activity_text = st.session_state.new_request_type or "Não selecionada"
    if activity_text == "Outro" and st.session_state.new_request_custom_type:
        activity_text = f"Outro ({st.session_state.new_request_custom_type})"

    req_date = st.session_state.new_request_date
    date_text = req_date.strftime("%d/%m/%Y") if req_date else "Não informada"

    with st.container(border=True):
        st.markdown("### :material/assignment: Resumo")
        st.divider()

        st.markdown(f"**Atividade**  \n{activity_text}")
        st.markdown(f"**Data**  \n{date_text}")
        st.markdown(f"**Horário**  \n{schedule_text}")
        st.markdown(f"**Espaço**  \n{space['name'] if space else 'Não selecionado'}")

        if space:
            st.caption(f"📍 {space.get('location', '')} · 👥 {space.get('capacity', 0)} pessoas")


def _render_step_content(step: int) -> None:
    """Renderiza o formulário da etapa atual."""
    
    # ---------------------------------------------------------
    # ETAPA 1 — TIPO DE ATIVIDADE
    # ---------------------------------------------------------
    if step == 0:
        st.subheader("Qual é o tipo de atividade?")
        st.caption("Selecione a categoria que melhor descreve sua necessidade.")

        st.segmented_control(
            "Tipo de atividade",
            options=_ACTIVITY_TYPES,
            key="new_request_type",
            width="stretch",
            on_change=_clear_error,
        )

        if st.session_state.new_request_type == "Outro":
            st.text_input(
                "Especifique o tipo de atividade",
                key="new_request_custom_type",
                placeholder="Ex.: Evento institucional, Treinamento...",
                max_chars=80,
                on_change=_clear_error,
            )

    # ---------------------------------------------------------
    # ETAPA 2 — DATA E HORÁRIO
    # ---------------------------------------------------------
    elif step == 1:
        st.subheader("Quando será a atividade?")
        st.caption("Escolha a data e a janela de horário para o uso do espaço.")

        st.date_input(
            "Data da reserva",
            key="new_request_date",
            min_value=_local_today(),
            format="DD/MM/YYYY",
            on_change=_clear_error,
        )

        col_start, col_end = st.columns(2)
        with col_start:
            st.time_input(
                "Horário de início",
                value=st.session_state.new_request_start,
                key="new_request_start",
                on_change=_clear_error,
            )
        with col_end:
            st.time_input(
                "Horário de término",
                value=st.session_state.new_request_end,
                key="new_request_end",
                on_change=_clear_error,
            )

        start = st.session_state.new_request_start
        end = st.session_state.new_request_end

        if start and end and st.session_state.new_request_date:
            duration_str = _format_duration(
                st.session_state.new_request_date, start, end
            )
            if duration_str:
                st.info(f"Duração estimada: **{duration_str}**", icon=":material/schedule:")
            else:
                st.warning("O horário de término deve ser maior que o horário de início.", icon=":material/warning:")

    # ---------------------------------------------------------
    # ETAPA 3 — ESPAÇO
    # ---------------------------------------------------------
    elif step == 2:
        st.subheader("Onde será a atividade?")
        st.caption("Escolha um espaço diretamente ou filtre por características desejadas.")

        mode = st.segmented_control(
            "Modo de seleção",
            options=("Escolher espaço", "Encontrar por requisitos"),
            key="new_request_space_mode",
            width="stretch",
        )

        if mode == "Escolher espaço":
            available_spaces = _get_available_spaces()
            
            # Encontra o índice atual para manter a sincronia
            current_space = _get_selected_space()
            current_index = available_spaces.index(current_space) if current_space in available_spaces else None

            selected = st.selectbox(
                "Selecione a sala",
                options=available_spaces,
                index=current_index,
                format_func=lambda s: f"{s['name']} · {s['location']} (Capacidade: {s['capacity']})",
                placeholder="Selecione um espaço disponível...",
            )

            if selected:
                st.session_state.new_request_space_id = selected["id"]
                _clear_error()

        else:
            c_cap, c_type = st.columns(2)
            with c_cap:
                st.number_input(
                    "Capacidade mínima (pessoas)",
                    min_value=1,
                    key="new_request_capacity",
                )
            with c_type:
                st.selectbox(
                    "Tipo de ambiente",
                    options=_SPACE_TYPES,
                    key="new_request_space_type",
                )

            st.multiselect(
                "Recursos necessários",
                options=_get_resource_names(),
                key="new_request_resources",
                placeholder="Selecione os recursos desejados...",
            )

            buildings = ["Qualquer bloco"] + [
                b["name"] for b in st.session_state.get("buildings", [])
            ]
            st.selectbox(
                "Bloco / Localização",
                options=buildings,
                key="new_request_building",
            )

            matches = _get_matching_spaces()

            if not matches:
                st.warning(
                    "Nenhum espaço atende a todos os critérios selecionados.",
                    icon=":material/search_off:",
                )
            else:
                current_space = _get_selected_space()
                current_index = matches.index(current_space) if current_space in matches else None

                selected = st.selectbox(
                    f"Espaços encontrados ({len(matches)})",
                    options=matches,
                    index=current_index,
                    format_func=lambda s: f"{s['name']} · {s['location']} ({s['capacity']} lugares)",
                    placeholder="Escolha um dos espaços encontrados...",
                )

                if selected:
                    st.session_state.new_request_space_id = selected["id"]
                    _clear_error()

        # Destaque do espaço selecionado
        selected_space = _get_selected_space()
        if selected_space:
            st.success(
                f"Espaço selecionado: **{selected_space['name']}** "
                f"({selected_space['location']} · Capacidade: {selected_space['capacity']} pessoas)",
                icon=":material/check_circle:",
            )

    # ---------------------------------------------------------
    # ETAPA 4 — JUSTIFICATIVA
    # ---------------------------------------------------------
    elif step == 3:
        st.subheader("Por que você precisa deste espaço?")
        st.caption("Descreva brevemente a finalidade e as necessidades específicas do evento.")

        st.text_area(
            "Justificativa da reserva",
            key="new_request_justification",
            max_chars=600,
            height=160,
            on_change=_clear_error,
            placeholder="Ex.: Aula prática de Sistemas Operacionais. Necessário ambiente com projetor e computadores com Linux.",
        )

        char_count = len(st.session_state.new_request_justification)
        st.caption(f"{char_count} de 600 caracteres")

        st.info(
            "As solicitações passam por análise da administração. "
            "Você receberá uma notificação após a deliberação.",
            icon=":material/info:",
        )


# -----------------------------------------------------------------------------
# VIEW PRINCIPAL
# -----------------------------------------------------------------------------

def new_reservation(user: Dict[str, Any]) -> None:
    """Página principal de criação de solicitações de reserva."""
    _init_state()

    # ---------------------------------------------------------
    # TELA DE CONFIRMAÇÃO (APÓS ENVIO)
    # ---------------------------------------------------------
    if st.session_state.get("new_request_submitted"):
        space = _get_selected_space()

        st.success("Solicitação enviada com sucesso!", icon=":material/task_alt:")
        st.write("Sua reserva foi registrada no sistema e está aguardando aprovação do gestor.")

        with st.container(border=True):
            st.markdown(f"**Atividade:** {st.session_state.new_request_type}")
            st.markdown(f"**Espaço:** {space['name'] if space else 'N/A'}")
            
            d_str = st.session_state.new_request_date.strftime("%d/%m/%Y")
            s_str = st.session_state.new_request_start.strftime("%H:%M")
            e_str = st.session_state.new_request_end.strftime("%H:%M")
            st.markdown(f"**Data e Horário:** {d_str} das {s_str} às {e_str}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Voltar ao início", icon=":material/home:", use_container_width=True):
                _reset_state()
                go("solicitante_dashboard")
                st.rerun()
        with col2:
            if st.button(
                "Acompanhar solicitações",
                icon=":material/list_alt:",
                type="primary",
                use_container_width=True,
            ):
                _reset_state()
                go("minhas_reservas")
                st.rerun()

        return

    # ---------------------------------------------------------
    # CABEÇALHO DA PÁGINA
    # ---------------------------------------------------------
    if st.button("Voltar", icon=":material/arrow_back:", type="tertiary"):
        _reset_state()
        go("solicitante_dashboard")
        st.rerun()

    st.title("Nova solicitação de reserva")
    st.caption("Preencha o formulário em etapas para requisitar o uso de um ambiente.")

    step = st.session_state.new_request_step
    _render_step_indicator(step)

    # ---------------------------------------------------------
    # CORPO PRINCIPAL
    # ---------------------------------------------------------
    form_col, summary_col = st.columns([2, 1], gap="large")

    with form_col:
        with st.container(border=True):
            _render_step_content(step)

            if st.session_state.get("new_request_error"):
                st.error(st.session_state.new_request_error, icon=":material/error:")

            st.divider()

            # Botões de Navegação Inferiores
            btn_col_left, btn_col_right = st.columns([1, 1])

            with btn_col_left:
                if step > 0:
                    if st.button("Voltar", icon=":material/arrow_back:", on_click=_go_back):
                        st.rerun()

            with btn_col_right:
                if step < len(_STEPS) - 1:
                    if st.button(
                        "Continuar",
                        icon=":material/arrow_forward:",
                        type="primary",
                        on_click=_go_next,
                    ):
                        st.rerun()
                else:
                    if st.button(
                        "Solicitar reserva",
                        icon=":material/check_circle:",
                        type="primary",
                        on_click=_submit_request,
                        args=(user,),
                    ):
                        st.rerun()

    with summary_col:
        _render_summary_card(step)