import streamlit as st

from controllers import auth_controller
from services.app_state_service import go
from views.components.ui_components import logo


ROLE_REDIRECT = {
    "admin": "admin_dashboard",
    "gerente": "gerente_dashboard",
    "solicitante": "solicitante_dashboard",
    "participante": "participante_dashboard",
}

def _init_state():
    defaults = {
        "login_email": "",
        "login_password": "",
        "login_error": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _target_for(user):
    return ROLE_REDIRECT.get(user["role"], "participante_dashboard")


def _attempt_login(email, password):
    user, error = auth_controller.login(email, password)
    if error:
        st.session_state.login_error = error
        return

    st.session_state.login_error = ""
    go(_target_for(user))


def _render_styles():
    st.html(
        """
        <style>
            .stApp {
                background-color: #F7F7F9 !important;
            }

            [data-testid="stMainBlockContainer"] {
                width: 100% !important;
                max-width: 480px !important;
                min-height: 100vh !important;
                margin-left: calc(min(46vw, 560px) + ((100vw - min(46vw, 560px) - 480px) / 2)) !important;
                margin-right: auto !important;
                padding: 32px 0 40px !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: center !important;
            }

            [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
                width: 100% !important;
                min-height: calc(100vh - 72px) !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: center !important;
            }

            .rf-login-art {
                position: fixed;
                inset: 0 auto 0 0;
                width: 46%;
                max-width: 560px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                padding: 48px;
                color: #FFFFFF;
                overflow: hidden;
                background:
                    radial-gradient(circle at 15% 85%, rgba(124, 58, 237, 0.45), transparent 45%),
                    radial-gradient(circle at 90% 15%, rgba(167, 139, 250, 0.16), transparent 40%),
                    linear-gradient(145deg, #2E1065 0%, #4C1D95 55%, #2E1065 100%);
            }

            .rf-login-art::after {
                content: "";
                position: absolute;
                right: -128px;
                top: 33%;
                width: 288px;
                height: 288px;
                border-radius: 999px;
                background: rgba(212, 167, 44, 0.08);
                filter: blur(64px);
                pointer-events: none;
            }

            .rf-login-art > * {
                position: relative;
                z-index: 1;
            }

            .rf-login-art-copy {
                max-width: 448px;
            }

            .rf-login-gold-line {
                width: 40px;
                height: 4px;
                border-radius: 999px;
                margin-bottom: 28px;
                background: #D4A72C;
            }

            .rf-login-art h2 {
                margin: 0 0 24px 0;
                color: #FFFFFF;
                font-family: var(--font-display);
                font-size: 44px;
                line-height: 1.08;
                font-weight: 300;
                letter-spacing: 0;
            }

            .rf-login-art h2 span {
                color: #C4B5FD;
            }

            .rf-login-art p {
                max-width: 360px;
                margin: 0;
                color: rgba(255, 255, 255, 0.6);
                font-size: 14px;
                line-height: 1.7;
            }

            .rf-login-panel {
                width: 100%;
                max-width: 420px;
            }

            .rf-login-back-spacer {
                margin-bottom: 32px;
            }

            [data-testid="stMainBlockContainer"] .st-key-login_card {
                width: 100% !important;
                height: auto !important;
                min-height: 0 !important;
                flex: 0 0 auto !important;
                background: #FFFFFF !important;
                border: 1px solid #E4E4E7 !important;
                border-radius: 16px !important;
                padding: 28px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
            }

            [data-testid="stMainBlockContainer"] .st-key-login_card [data-testid="stVerticalBlock"] {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
            }

            .rf-login-eyebrow {
                margin: 5px 0 2px 0;
                color: #6D28D9;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.18em;
                text-transform: uppercase;
            }

            .rf-login-header h1 {
                margin: 0 0 8px 0;
                color: #171717;
                font-size: 30px;
                font-weight: 600;
                line-height: 1.2;
                letter-spacing: 0;
            }

            .rf-login-header p {
                margin: 0 0 32px 0;
                color: #737373;
                font-size: 14px;
                line-height: 1.6;
            }

            .rf-login-password-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-top: 16px;
                margin-bottom: 12px;
            }

            .rf-login-password-label {
                color: #262626;
                font-size: 14px;
                font-weight: 500;
            }

            .rf-login-forgot {
                color: #6D28D9;
                font-size: 12px;
                font-weight: 500;
                text-decoration: none;
            }

            .rf-login-forgot:hover {
                color: #4C1D95;
            }

            .rf-login-error {
                color: #991B1B;
                background: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 12px;
                padding: 12px 16px;
                margin: 4px 0 20px 0;
                font-size: 12px;
                line-height: 1.5;
            }

            .rf-login-footer {
                margin-top: 28px;
                text-align: center;
            }

            .rf-login-footer p,
            .rf-login-signup-link {
                margin: 0;
                color: #737373;
                font-size: 14px;
                text-align: center;
            }

            .rf-login-signup-link a {
                color: #6D28D9;
                font-weight: 700;
                text-decoration: none;
            }

            .rf-login-signup-link a:hover {
                color: #4C1D95;
            }

            .rf-login-footer span {
                color: #A1A1AA;
                font-size: 12px;
            }

            [data-testid="stMainBlockContainer"] .stButton > button {
                border-radius: 12px !important;
                font-size: 14px !important;
                font-weight: 600 !important;
            }

            [data-testid="stMainBlockContainer"] .stButton > button[kind="primary"] {
                height: 48px !important;
                border: none !important;
                background: #6D28D9 !important;
                color: #FFFFFF !important;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
            }

            [data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:hover {
                background: #5B21B6 !important;
                color: #FFFFFF !important;
            }

            [data-testid="stMainBlockContainer"] .stButton > button[kind="secondary"] {
                height: auto !important;
                min-height: 72px !important;
                padding: 12px !important;
                border: 1px solid #E4E4E7 !important;
                border-radius: 8px !important;
                background: #FAFAFA !important;
                color: #262626 !important;
                text-align: left !important;
                justify-content: flex-start !important;
                white-space: normal !important;
            }

            [data-testid="stMainBlockContainer"] .stButton > button[kind="secondary"]:hover {
                border-color: #A78BFA !important;
                background: #F5F3FF !important;
                color: #6D28D9 !important;
            }

            [data-testid="stMainBlockContainer"] .stButton > button[kind="tertiary"] {
                min-height: auto !important;
                height: auto !important;
                padding: 0 !important;
                border: none !important;
                border-radius: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
                font-weight: 600 !important;
            }

            [data-testid="stMainBlockContainer"] .stButton > button[kind="tertiary"] {
                color: #737373 !important;
            }

            [data-testid="stMainBlockContainer"] .stButton > button[kind="tertiary"]:hover {
                color: #4C1D95 !important;
                background: transparent !important;
            }

            [data-testid="stMainBlockContainer"] .st-key-login_forgot_password {
                display: flex !important;
                justify-content: flex-end !important;
            }

            [data-testid="stMainBlockContainer"] .st-key-login_forgot_password button[kind="tertiary"] {
                color: #6D28D9 !important;
                font-size: 12px !important;
                font-weight: 500 !important;
                text-align: right !important;
            }

            [data-testid="stMainBlockContainer"] .st-key-login_forgot_password button[kind="tertiary"]:hover {
                color: #4C1D95 !important;
            }

            [data-testid="stMainBlockContainer"] [data-testid="stTextInput"] {
                margin-bottom: 20px !important;
            }

            [data-testid="stMainBlockContainer"] [data-testid="stTextInput"] label {
                color: #262626 !important;
                font-size: 14px !important;
                font-weight: 500 !important;
                margin-bottom: 8px !important;
            }

            [data-testid="stMainBlockContainer"] [data-testid="stTextInput"] input {
                height: 48px !important;
                border: 1px solid #D4D4D8 !important;
                border-radius: 12px !important;
                background: #FFFFFF !important;
                color: #171717 !important;
                font-size: 14px !important;
                box-shadow: none !important;
            }

            [data-testid="stMainBlockContainer"] [data-testid="stTextInput"] input:focus {
                border-color: #7C3AED !important;
                box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.1) !important;
            }

            [data-testid="stMainBlockContainer"] [data-testid="stTextInput"] input::placeholder {
                color: #A1A1AA !important;
            }

            [data-testid="stMainBlockContainer"] [data-testid="column"] {
                padding: 0 !important;
            }

            @media (max-width: 1023px) {
                .rf-login-art {
                    display: none;
                }

                [data-testid="stMainBlockContainer"] {
                    max-width: 480px !important;
                    margin-left: auto !important;
                    margin-right: auto !important;
                    padding: 32px 24px 40px !important;
                    justify-content: center !important;
                }
            }

            @media (max-width: 640px) {
                [data-testid="stMainBlockContainer"] {
                    max-width: none !important;
                    padding: 40px 24px !important;
                    justify-content: flex-start !important;
                }

                [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
                    min-height: auto !important;
                    justify-content: flex-start !important;
                }

                .rf-login-back-spacer {
                    margin-bottom: 32px;
                }
            }
        </style>
        """
    )


def _render_art_panel():
    st.html(
        f"""
        <aside class="rf-login-art">
            <div>{logo(variant="light")}</div>
            <div class="rf-login-art-copy">
                <div class="rf-login-gold-line"></div>
                <h2>Gestão de espaços<br><span>simples e inteligente.</span></h2>
                <p>Centralize reservas, espaços e recursos em um único sistema pensado para tornar a gestão da sua instituição mais eficiente.</p>
            </div>
            <p>© 2026 RoomFlow</p>
        </aside>
        """
    )


def _render_header():
    st.markdown(
        """
        <div class="rf-login-header">
            <p class="rf-login-eyebrow">Bem-vindo de volta</p>
            <h1>Entrar na sua conta</h1>
            <p>Acesse o RoomFlow para gerenciar seus espaços e reservas.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def login():
    _init_state()
    _render_styles()
    _render_art_panel()

    with st.container(key="login_card"):
        if st.button("← Voltar para início", key="login_back", type="tertiary"):
            go("landing")
        st.markdown('<div class="rf-login-back-spacer"></div>', unsafe_allow_html=True)

        _render_header()

        st.text_input(
            "E-mail",
            key="login_email",
            placeholder="seu@email.com",
        )

        password_label_col, forgot_col = st.columns([2, 1], vertical_alignment="center")
        with password_label_col:
            st.markdown(
                '<span class="rf-login-password-label">Senha</span>',
                unsafe_allow_html=True,
            )
        with forgot_col:
            if st.button(
                "Esqueci minha senha",
                key="login_forgot_password",
                type="tertiary",
            ):
                go("forgot_password")

        st.text_input(
            "Senha",
            key="login_password",
            placeholder="Digite sua senha",
            type="password",
            label_visibility="collapsed",
        )

        if st.session_state.login_error:
            st.markdown(
                f'<div class="rf-login-error">{st.session_state.login_error}</div>',
                unsafe_allow_html=True,
            )

        if st.button("Entrar →", key="login_submit", type="primary", width="stretch"):
            _attempt_login(st.session_state.login_email, st.session_state.login_password)

        st.markdown(
            '<div class="rf-login-footer"><p class="rf-login-signup-link">Ainda não possui uma conta? <a href="?page=signup_choice" target="_self">Criar conta</a></p><span>Problemas para acessar? Entre em contato com a instituição.</span></div>',
            unsafe_allow_html=True,
        )
