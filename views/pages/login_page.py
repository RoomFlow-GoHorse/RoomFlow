import streamlit as st

from services import auth_service
from services.app_state_service import go
from views.components.ui_components import logo


def login():
    st.html(
        f"""
        <div class="rf-login-wrap">
          <aside class="rf-login-art">{logo(light=True)}<h1>Entre na sua rotina de salas sem perder o ritmo.</h1><small>RoomFlow 2026</small></aside>
          <section class="rf-form-panel"><div class="rf-form-card">
        """
    )
    st.caption("ACESSO")
    st.title("Entrar na sua conta")
    email = st.text_input("E-mail", value="admin@roomflow.com")
    password = st.text_input("Senha", type="password", value="demo")
    if st.button("Entrar", type="primary", width="stretch"):
        user, error = auth_service.login(email, password)
        if error:
            st.error(error)
        else:
            target = {
                "admin": "admin_dashboard",
                "gerente": "gerente_dashboard",
                "solicitante": "solicitante_dashboard",
                "participante": "participante_dashboard",
            }[user["role"]]
            go(target)
    st.write("Acessos demo")
    cols = st.columns(4)
    demos = [
        ("Gerente", "admin@roomflow.com"),
        ("Administrador", "gerente@roomflow.com"),
        ("Solicitante", "solicitante@roomflow.com"),
        ("Participante", "participante@roomflow.com"),
    ]
    for col, (label, demo_email) in zip(cols, demos):
        if col.button(label, width="stretch"):
            user, _ = auth_service.login(demo_email, "demo")
            go(
                {
                    "admin": "admin_dashboard",
                    "gerente": "gerente_dashboard",
                    "solicitante": "solicitante_dashboard",
                    "participante": "participante_dashboard",
                }[user["role"]]
            )
    if st.button("Criar conta"):
        go("signup_choice")
    if st.button("Esqueci minha senha"):
        go("forgot_password")
    st.html("</div></section></div>")
