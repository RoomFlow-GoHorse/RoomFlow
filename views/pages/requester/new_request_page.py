import streamlit as st

from controllers.app_state_service import go
from views.components.reservation_forms import RESERVATION_ERRORS, period_inputs, request_fields, reservation_api
from views.components.ui_components import page_header


def new_reservation(user):
    page_header("Nova solicitação de reserva", "Escolha o período e uma sala disponível.")
    api = reservation_api()
    if api is None:
        return

    try:
        settings = api.catalog_settings()
        eligible_participants = api.eligible_participants()
        timezone = settings["timezone"]
        start, end = period_inputs(timezone, "new_reservation")
        st.caption(f"Fuso horário das reservas: {timezone}")
        rooms = api.catalog(start, end)["spaces"]
    except RESERVATION_ERRORS as error:
        st.error(str(error))
        return

    resources = sorted({resource for room in rooms for resource in room["resources"]})
    types = sorted({room["type"] for room in rooms})
    buildings = sorted({room["building"] for room in rooms if room["building"]})
    capacity, building, room_type, resource = st.columns(4)
    participants = capacity.number_input("Participantes", min_value=1, max_value=10000, value=1,
                                         key="new_reservation_participants")
    building_name = building.selectbox("Prédio", [None, *buildings], format_func=lambda value: value or "Todos")
    activity_room_type = room_type.selectbox("Tipo de sala", [None, *types], format_func=lambda value: value or "Todos")
    required = resource.multiselect("Recursos", resources)
    eligible = [
        room for room in rooms
        if room["capacity"] >= participants
        and (not building_name or room["building"] == building_name)
        and (not activity_room_type or room["type"] == activity_room_type)
        and set(required).issubset(room["resources"])
    ]
    if not eligible:
        st.info("Nenhuma sala disponível para este período e filtros.")
        return

    with st.form("new_reservation"):
        payload = request_fields(
            eligible, start, end, "new_reservation",
            justification_required=settings["justification_required"], participants=participants,
            eligible_participants=eligible_participants,
        )
        submitted = st.form_submit_button("Solicitar reserva", type="primary")
    if submitted:
        try:
            result = api.create(payload)
        except RESERVATION_ERRORS as error:
            st.error(str(error))
        else:
            st.success("Reserva aprovada." if result["status"] == "aprovada" else "Solicitação enviada para análise.")
            if result["has_overlap"]:
                st.info("Há outra solicitação no mesmo período. O gerente poderá analisar a sobreposição.")
    if st.button("Minhas reservas"):
        go("minhas_reservas")
