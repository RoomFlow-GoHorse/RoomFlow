import streamlit as st

from controllers import mock_data_service
from views.components.ui_components import badge, page_header


def dashboard(user):
    reservations = mock_data_service.reservations()
    spaces = mock_data_service.spaces()
    metrics = (
        ("Reservas do dia", len(reservations)),
        ("Solicitações pendentes", sum(item["status"] in {"pendente", "em_analise"} for item in reservations)),
        ("Salas ocupadas", sum(item["status"] == "ocupado" for item in spaces)),
        ("Salas disponíveis", sum(item["status"] == "disponivel" for item in spaces)),
        ("Conflitos pendentes", sum(item["status"] != "resolvido" for item in st.session_state.conflicts)),
    )
    page_header("Painel do gerente", "Visão operacional das salas, reservas e situações que exigem atenção.")
    for column, (label, value) in zip(st.columns(5), metrics):
        with column:
            st.metric(label, value)
    st.subheader("Solicitações recentes")
    for reservation in reservations[:5]:
        with st.container(border=True):
            details, status = st.columns([4, 1], vertical_alignment="center")
            with details:
                st.markdown(f"**{reservation['title']}**")
                st.caption(f"{reservation['space']} · {reservation['date']} · {reservation['start']}–{reservation['end']}")
            with status:
                st.html(badge(reservation["status"]))
