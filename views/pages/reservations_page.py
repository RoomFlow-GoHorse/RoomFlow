from controllers import reservation_controller, space_controller
import streamlit as st

from services.app_state_service import go, set_toast
from views.components.reservation_cards import reservation_cards
from views.components.ui_components import badge, page_header, table


def reservations_admin(user):
    page_header("Reservas e solicitacoes", "Filtre, aprove, rejeite ou analise detalhes.")
    status = st.selectbox("Status", ["Todas", "pendente", "aprovada", "rejeitada", "conflito", "em_analise"])
    items = reservation_controller.reservations(status=status)
    rows = [
        [r["requester"], r["type"], r["space"], r["date"], f'{r["start"]}-{r["end"]}', badge(r["status"]), badge(r["priority"])]
        for r in items
    ]
    table(["Solicitante", "Tipo", "Espaco", "Data", "Horario", "Status", "Prioridade"], rows)
    for item in items:
        with st.expander(f"{item['title']} - {item['requester']}"):
            st.write(item["justification"])
            c1, c2, c3 = st.columns(3)
            if item["status"] in {"pendente", "em_analise"} and c1.button("Aprovar", key=f"approve_{item['id']}"):
                reservation_controller.update_reservation_status(item["id"], "aprovada")
                set_toast("Reserva aprovada.")
                st.rerun()
            if item["status"] in {"pendente", "em_analise"} and c2.button("Rejeitar", key=f"reject_{item['id']}"):
                reservation_controller.update_reservation_status(item["id"], "rejeitada")
                set_toast("Reserva rejeitada.")
                st.rerun()
            if c3.button("Marcar em analise", key=f"review_{item['id']}"):
                reservation_controller.update_reservation_status(item["id"], "em_analise")
                st.rerun()


def new_reservation(user):
    page_header("Nova reserva", "Solicite um espaco disponivel.")
    with st.form("new_reservation"):
        title = st.text_input("Titulo")
        space = st.selectbox("Espaco", [s["name"] for s in space_controller.spaces() if s["status"] != "bloqueado"])
        day = st.date_input("Data")
        c1, c2 = st.columns(2)
        start = c1.time_input("Inicio")
        end = c2.time_input("Fim")
        kind = st.selectbox("Tipo", ["Aula", "Banca", "Workshop", "Reuniao", "Monitoria"])
        participants = st.number_input("Participantes", min_value=1, value=12)
        justification = st.text_area("Justificativa")
        submitted = st.form_submit_button("Solicitar reserva", type="primary")
    if submitted:
        reservation_controller.create_reservation(
            {
                "requester": user["name"],
                "requester_id": user["id"],
                "title": title,
                "space": space,
                "date": day.isoformat(),
                "start": start.strftime("%H:%M"),
                "end": end.strftime("%H:%M"),
                "type": kind,
                "participants": participants,
                "justification": justification,
            }
        )
        set_toast("Reserva enviada para analise.")
        go("minhas_reservas")


def minhas_reservas(user):
    page_header("Minhas reservas", "Acompanhe suas solicitacoes.")
    items = reservation_controller.reservations(requester_id=user["id"])
    reservation_cards(items)
    for item in items:
        if item["status"] in {"pendente", "aprovada"} and st.button(f"Cancelar {item['title']}", key=f"cancel_{item['id']}"):
            reservation_controller.update_reservation_status(item["id"], "rejeitada")
            set_toast("Reserva cancelada no mock.")
            st.rerun()
