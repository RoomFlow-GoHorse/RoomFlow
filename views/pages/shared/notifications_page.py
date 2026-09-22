import streamlit as st

from controllers import mock_data_service
from views.components.ui_components import badge, page_header


def notifications(user):
    page_header("Notificacoes", "Mensagens filtradas por perfil.")
    items = mock_data_service.notifications_for(user["role"])
    if st.button("Marcar todas como lidas"):
        mock_data_service.mark_notification_read(role=user["role"])
        st.rerun()
    for item in items:
        st.html(
            f'<div class="rf-card"><strong>{item["title"]}</strong> {badge("ativo" if not item["read"] else "inativo")}<p>{item["body"]}</p></div>',
        )
        if not item["read"] and st.button("Marcar como lida", key=f"read_{item['id']}"):
            mock_data_service.mark_notification_read(item["id"])
            st.rerun()
