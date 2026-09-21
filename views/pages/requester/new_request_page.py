"""Assistente de criação de reservas para o perfil solicitante."""

from datetime import date, datetime, time

import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go, set_toast


_STEPS = ("Tipo", "Data e horário", "Espaço", "Justificativa", "Revisão")
_ACTIVITY_TYPES = ("Aula", "Banca", "Workshop", "Reunião", "Monitoria")


def _state():
    defaults = {
        "new_request_step": 0,
        "new_request_type": None,
        "new_request_date": date.today(),
        "new_request_start": time(9, 0),
        "new_request_end": time(11, 0),
        "new_request_space_mode": "Escolher espaço",
        "new_request_space_id": None,
        "new_request_capacity": 1,
        "new_request_resources": [],
        "new_request_space_type": "Qualquer tipo",
        "new_request_building": "Qualquer bloco",
        "new_request_justification": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _duration(start: time, end: time) -> str:
    minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    if minutes <= 0:
        return "Horário inválido"
    hours, remaining = divmod(minutes, 60)
    return f"{hours}h" if remaining == 0 else f"{hours}h {remaining}min"


def _selected_space():
    selected_id = st.session_state.new_request_space_id
    return next((space for space in st.session_state.spaces if space["id"] == selected_id), None)


def _available_spaces():
    return [space for space in st.session_state.spaces if space["status"] == "disponivel"]


def _resource_names():
    return [resource["name"] if isinstance(resource, dict) else resource for resource in st.session_state.resources]


def _matching_spaces():
    required = st.session_state.new_request_resources
    capacity = st.session_state.new_request_capacity
    space_type = st.session_state.new_request_space_type
    building = st.session_state.new_request_building
    return [
        space for space in _available_spaces()
        if space["capacity"] >= capacity
        and (space_type == "Qualquer tipo" or space["type"] == space_type)
        and (building == "Qualquer bloco" or space["building"] == building)
        and all(resource in space.get("resources", []) for resource in required)
    ]


def _step_indicator(step: int):
    labels = [f"{'✓' if index < step else index + 1}. {name}" for index, name in enumerate(_STEPS)]
    st.segmented_control("Etapas da solicitação", labels, default=labels[step], disabled=True, width="stretch", label_visibility="collapsed")
    st.caption(f"Etapa {step + 1} de {len(_STEPS)}")
    st.progress((step + 1) / len(_STEPS))


def _summary(step: int):
    space = _selected_space()
    with st.container(border=True):
        st.markdown("#### :material/calendar_month: Resumo")
        st.caption("Sua solicitação")
        st.markdown(f"**Atividade**  \n{st.session_state.new_request_type or 'Não selecionada'}")
        st.markdown(f"**Data**  \n{st.session_state.new_request_date.strftime('%d/%m/%Y')}")
        st.markdown(f"**Horário**  \n{st.session_state.new_request_start.strftime('%H:%M')}–{st.session_state.new_request_end.strftime('%H:%M')}")
        st.markdown(f"**Espaço**  \n{space['name'] if space else 'Não selecionado'}")
        st.caption(f"Progresso: {round((step + 1) / len(_STEPS) * 100)}%")


def _validate(step: int) -> str | None:
    if step == 0 and not st.session_state.new_request_type:
        return "Selecione o tipo de atividade para continuar."
    if step == 1:
        if st.session_state.new_request_start >= st.session_state.new_request_end:
            return "O horário de término deve ser posterior ao horário de início."
    if step == 2 and not _selected_space():
        return "Selecione um espaço para continuar."
    if step == 3 and not st.session_state.new_request_justification.strip():
        return "Informe uma justificativa para continuar."
    return None


def _go_next():
    step = st.session_state.new_request_step
    error = _validate(step)
    if error:
        st.session_state.new_request_error = error
        return
    st.session_state.new_request_error = ""
    st.session_state.new_request_step = min(step + 1, len(_STEPS) - 1)


def _submit(user):
    error = _validate(3)
    if error:
        st.error(error)
        return
    space = _selected_space()
    activity = st.session_state.new_request_type
    mock_data_service.create_reservation({
        "requester": user["name"], "requester_id": user["id"],
        "title": f"{activity} — {space['name']}", "type": activity,
        "space": space["name"], "date": st.session_state.new_request_date.isoformat(),
        "start": st.session_state.new_request_start.strftime("%H:%M"),
        "end": st.session_state.new_request_end.strftime("%H:%M"),
        "participants": st.session_state.new_request_capacity,
        "resources": st.session_state.new_request_resources,
        "justification": st.session_state.new_request_justification.strip(),
    })
    set_toast("Solicitação enviada para análise.")
    st.session_state.new_request_submitted = True


def _reset():
    for key in list(st.session_state):
        if key.startswith("new_request_"):
            del st.session_state[key]


def _render_step(step: int):
    if step == 0:
        st.subheader("Qual é o tipo de atividade?")
        st.caption("Selecione a finalidade principal da reserva.")
        st.segmented_control("Tipo de atividade", _ACTIVITY_TYPES, key="new_request_type", width="stretch")
    elif step == 1:
        st.subheader("Quando será a atividade?")
        st.caption("Informe a data e o período necessário.")
        st.date_input("Data", key="new_request_date", min_value=date.today())
        start, end = st.columns(2)
        start.time_input("Horário de início", key="new_request_start")
        end.time_input("Horário de término", key="new_request_end")
        st.info(f"Duração da reserva: **{_duration(st.session_state.new_request_start, st.session_state.new_request_end)}**", icon=":material/schedule:")
    elif step == 2:
        st.subheader("Onde será a atividade?")
        st.caption("Escolha uma sala específica ou encontre uma que atenda aos seus requisitos.")
        mode = st.segmented_control("Como deseja escolher?", ("Escolher espaço", "Encontrar por requisitos"), key="new_request_space_mode", width="stretch")
        if mode == "Escolher espaço":
            choices = _available_spaces()
            selected = st.selectbox("Espaço disponível", choices, format_func=lambda item: f"{item['name']} · {item['location']} · {item['capacity']} pessoas", index=None, placeholder="Selecione uma sala")
            if selected:
                st.session_state.new_request_space_id = selected["id"]
        else:
            capacity, space_type = st.columns(2)
            capacity.number_input("Capacidade mínima", min_value=1, key="new_request_capacity")
            space_type.selectbox("Tipo de espaço", ("Qualquer tipo", "Sala de aula", "Sala de reuniões", "Auditório", "Laboratório"), key="new_request_space_type")
            st.multiselect("Recursos necessários", _resource_names(), key="new_request_resources", placeholder="Selecione os recursos")
            st.selectbox("Localização preferida", ("Qualquer bloco",) + tuple(item["name"] for item in st.session_state.buildings), key="new_request_building")
            matches = _matching_spaces()
            if not matches:
                st.warning("Nenhum espaço disponível atende aos requisitos informados.", icon=":material/search_off:")
            else:
                selected = st.selectbox("Espaço encontrado", matches, format_func=lambda item: f"{item['name']} · {item['location']} · {item['capacity']} pessoas", index=None, placeholder="Escolha um espaço")
                if selected:
                    st.session_state.new_request_space_id = selected["id"]
        selected_space = _selected_space()
        if selected_space:
            st.success(f"Espaço selecionado: **{selected_space['name']}** — {selected_space['location']} · {selected_space['capacity']} pessoas", icon=":material/check_circle:")
    elif step == 3:
        st.subheader("Por que você precisa do espaço?")
        st.caption("Explique brevemente a finalidade da reserva.")
        st.text_area("Justificativa", key="new_request_justification", max_chars=600, height=180, placeholder="Ex.: Aula de Cálculo II para turma do 3º semestre. Necessidade de projetor para apresentação de slides.")
        st.caption(f"{len(st.session_state.new_request_justification)} de 600 caracteres")
    else:
        space = _selected_space()
        st.subheader("Revise sua solicitação")
        st.caption("Confira todas as informações antes de enviar.")
        with st.container(border=True):
            st.markdown(f"**Tipo de atividade**  \n{st.session_state.new_request_type}")
            st.markdown(f"**Data**  \n{st.session_state.new_request_date.strftime('%d/%m/%Y')}")
            st.markdown(f"**Horário**  \n{st.session_state.new_request_start.strftime('%H:%M')} às {st.session_state.new_request_end.strftime('%H:%M')} · {_duration(st.session_state.new_request_start, st.session_state.new_request_end)}")
            st.markdown(f"**Espaço**  \n{space['name'] if space else 'Não informado'}")
            if st.session_state.new_request_resources:
                st.markdown("**Recursos necessários**  \n" + " · ".join(st.session_state.new_request_resources))
            st.markdown(f"**Justificativa**  \n{st.session_state.new_request_justification}")
        st.info("Sua solicitação será encaminhada para análise do gerente. Você receberá uma notificação quando houver uma decisão.", icon=":material/info:")


def new_reservation(user):
    _state()
    if st.session_state.get("new_request_submitted"):
        space = _selected_space()
        st.success("Solicitação enviada!", icon=":material/check_circle:")
        st.write("Sua solicitação foi registrada com sucesso e será analisada pelo administrador.")
        with st.container(border=True):
            st.markdown(f"**Tipo de atividade:** {st.session_state.new_request_type}")
            st.markdown(f"**Espaço:** {space['name'] if space else 'Não informado'}")
            st.markdown(f"**Data e horário:** {st.session_state.new_request_date.strftime('%d/%m/%Y')} · {st.session_state.new_request_start.strftime('%H:%M')}–{st.session_state.new_request_end.strftime('%H:%M')}")
        with st.container(horizontal=True):
            if st.button("Voltar ao início", icon=":material/home:"):
                _reset(); go("solicitante_dashboard"); st.rerun()
            if st.button("Acompanhar solicitação", icon=":material/list_alt:", type="primary"):
                _reset(); go("minhas_reservas"); st.rerun()
        return

    if st.button("Voltar ao início", icon=":material/arrow_back:", type="tertiary"):
        _reset(); go("solicitante_dashboard"); st.rerun()
    st.title("Nova solicitação de reserva")
    st.caption("Preencha as informações abaixo para solicitar uma sala.")
    step = st.session_state.new_request_step
    _step_indicator(step)
    form_column, summary_column = st.columns([2, 1], gap="large")
    with form_column:
        with st.container(border=True):
            _render_step(step)
            if st.session_state.get("new_request_error"):
                st.error(st.session_state.new_request_error)
            with st.container(horizontal=True, horizontal_alignment="right"):
                if step > 0 and st.button("Voltar", icon=":material/arrow_back:"):
                    st.session_state.new_request_step -= 1; st.session_state.new_request_error = ""; st.rerun()
                if step < len(_STEPS) - 1:
                    if st.button("Continuar", icon=":material/arrow_forward:", type="primary"):
                        _go_next(); st.rerun()
                elif st.button("Enviar solicitação", icon=":material/check_circle:", type="primary"):
                    _submit(user); st.rerun()
    with summary_column:
        _summary(step)
