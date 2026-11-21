import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from controllers.streamlit_runtime import get_streamlit_runtime, uses_roomflow_api
from controllers.roomflow_api import ApiUnavailable
from views.components.reservation_forms import RESERVATION_ERRORS
from views.components.ui_components import page_header


FILTERS = {
    "unread": "Não lidas", "all": "Todas", "reserva": "Reservas",
    "alteracao": "Alterações", "conflito": "Conflitos",
}
CATEGORY_LABELS = {"reserva": "Reserva", "alteracao": "Alteração", "conflito": "Conflito"}
PAGE_SIZE = 25
LOGGER = logging.getLogger(__name__)


def _render_styles():
    st.html("""
        <style>
        [class*="st-key-rf_notif_card_"], [class*="st-key-rf_notif_unread_"] {
            background-color: var(--surface-card);
            border: 1px solid var(--stroke);
            border-radius: 10px;
        }
        [class*="st-key-rf_notif_unread_"] {
            border-left: 4px solid var(--brand, #6D28D9);
        }
        </style>
        """)


def _set_offset(value):
    st.session_state["notification_offset"] = value


def _render_notification_card(item, api, zone):
    notification_id = item["id"]
    unread = item["read_at"] is None
    prefix = "rf_notif_unread_" if unread else "rf_notif_card_"
    with st.container(border=True, key=f"{prefix}{notification_id}"):
        metadata, date_column = st.columns([3, 1], vertical_alignment="center")
        category = CATEGORY_LABELS.get(item["category"], "Notificação")
        badge = " :violet[● Não lida]" if unread else ""
        created = datetime.fromisoformat(item["created_at"]).astimezone(zone)
        metadata.caption(f"**{category.upper()}**{badge}")
        date_column.caption(f":material/schedule: {created:%d/%m/%Y %H:%M}")
        st.subheader(item["title"], anchor=False)
        st.text(item["message"])
        if unread and st.button("Marcar como lida", key=f"btn_read_{notification_id}",
                                icon=":material/check_circle:"):
            try:
                api.mark_read(notification_id)
            except (*RESERVATION_ERRORS, ApiUnavailable) as error:
                LOGGER.warning("Could not mark notification %s as read: %s", notification_id, error)
                st.error("Não foi possível atualizar a notificação. Tente novamente.")
            else:
                st.rerun()


def notifications(user=None):
    if not uses_roomflow_api():
        page_header("Notificações", "Consulte as atualizações da sua instituição.")
        st.error("Não foi possível carregar suas notificações. Tente novamente.")
        return

    _render_styles()
    try:
        api = get_streamlit_runtime().notifications
    except ApiUnavailable as error:
        LOGGER.warning("Could not connect to the notification service: %s", error)
        page_header("Notificações", "Consulte as atualizações da sua instituição.")
        st.error("Não foi possível carregar suas notificações. Tente novamente.")
        return
    header = st.container()
    selection = st.segmented_control(
        "Filtrar notificações", list(FILTERS), default="unread", format_func=FILTERS.__getitem__,
        label_visibility="collapsed", key="notification_filter", on_change=_set_offset, args=(0,),
    )
    offset = st.session_state.get("notification_offset", 0)
    try:
        result = api.inbox(
            unread_only=selection == "unread", category=selection if selection in CATEGORY_LABELS else None,
            limit=PAGE_SIZE, offset=offset,
        )
    except (*RESERVATION_ERRORS, ApiUnavailable) as error:
        LOGGER.warning("Could not load the authenticated user's notifications: %s", error)
        st.error("Não foi possível carregar suas notificações. Tente novamente.")
        return

    unread = result["unread_count"]
    with header:
        title, action = st.columns([3, 1], vertical_alignment="center")
        with title:
            subtitle = f"{unread} não lida" + ("s" if unread != 1 else "") if unread else "Todas as notificações estão lidas"
            page_header("Notificações", subtitle)
        if unread and action.button("Marcar todas como lidas", key="btn_mark_all_read",
                                    icon=":material/done_all:", width="stretch"):
            try:
                api.mark_all_read()
            except (*RESERVATION_ERRORS, ApiUnavailable) as error:
                LOGGER.warning("Could not mark all notifications as read: %s", error)
                st.error("Não foi possível atualizar as notificações. Tente novamente.")
            else:
                _set_offset(0)
                st.rerun()

    if offset and offset >= result["total"]:
        _set_offset(max(0, (result["total"] - 1) // PAGE_SIZE * PAGE_SIZE))
        st.rerun()

    if not result["items"]:
        if selection == "unread":
            empty_message = "Você não possui notificações não lidas no momento."
        elif selection == "all":
            empty_message = "Você não possui notificações no momento."
        else:
            empty_message = "Não há notificações nessa categoria."
        st.info(empty_message, icon=":material/notifications_off:")
        return
    zone = ZoneInfo(result["timezone"])
    for item in result["items"]:
        _render_notification_card(item, api, zone)
    if result["total"] > PAGE_SIZE:
        previous, following = st.columns(2)
        previous.button("Anterior", key="notification_previous", on_click=_set_offset, args=(offset - PAGE_SIZE,),
                        disabled=offset == 0)
        following.button("Próxima", key="notification_next", on_click=_set_offset, args=(offset + PAGE_SIZE,),
                         disabled=offset + PAGE_SIZE >= result["total"])
