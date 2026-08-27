import streamlit as st

from config.constants import ROLE_NAV
from services import auth_service
from services.mock_data_service import notifications_for
from services.app_state_service import go
from views.components.ui_components import logo, role_label


def render_sidebar(user):
    current = st.session_state.page
    unread = len([n for n in notifications_for(user["role"]) if not n["read"]])
    nav_html = ""
    for label, page in ROLE_NAV[user["role"]]:
        active = " active" if current == page else ""
        suffix = f'<span class="rf-badge pendente">{unread}</span>' if page == "notificacoes" and unread else "<span></span>"
        nav_html += f'<div class="rf-nav-item{active}"><span>{label}</span>{suffix}</div>'
    st.html(
        f"""
        <aside class="rf-sidebar">
          {logo()}
          <div class="rf-nav">{nav_html}</div>
          <div class="rf-side-user">
            <div style="display:flex;gap:10px;align-items:center">
              <span class="rf-avatar">{user["initials"]}</span>
              <div>
                <div style="font-weight:700;font-size:14px">{user["name"]}</div>
                <div style="color:var(--muted);font-size:12px">{role_label(user["role"])}</div>
              </div>
            </div>
          </div>
        </aside>
        """
    )


def shell_start(user):
    render_sidebar(user)
    st.html('<div class="rf-shell"><main class="rf-main">')
    st.html('<div class="rf-top-actions">')
    cols = st.columns(len(ROLE_NAV[user["role"]]) + 1)
    for index, (label, page) in enumerate(ROLE_NAV[user["role"]]):
        if cols[index].button(label, key=f"top_{page}", width="stretch"):
            go(page)
    if cols[-1].button("Sair", key="top_logout", width="stretch"):
        auth_service.logout()
    st.html("</div>")


def shell_end():
    st.html("</main></div>")
