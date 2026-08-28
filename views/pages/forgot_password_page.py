import streamlit as st

from services.app_state_service import go
from views.components.ui_components import logo


def _init_state():
    defaults = {
        "forgot_password_email": "",
        "forgot_password_success": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


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

            .rf-forgot-art {
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

            .rf-forgot-art::after {
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

            .rf-forgot-art > * {
                position: relative;
                z-index: 1;
            }

            .rf-forgot-art-copy {
                max-width: 448px;
            }

            .rf-forgot-gold-line {
                width: 40px;
                height: 4px;
                border-radius: 999px;
                margin-bottom: 28px;
                background: #D4A72C;
            }

            .rf-forgot-art h2 {
                margin: 0 0 24px 0;
                color: #FFFFFF;
                font-family: var(--font-display);
                font-size: 44px;
                line-height: 1.08;
                font-weight: 300;
                letter-spacing: 0;
            }

            .rf-forgot-art h2 span {
                color: #C4B5FD;
            }

            .rf-forgot-art p {
                max-width: 360px;
                margin: 0;
                color: rgba(255, 255, 255, 0.6);
                font-size: 14px;
                line-height: 1.7;
            }

            [data-testid="stMainBlockContainer"] .st-key-forgot_password_card {
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

            [data-testid="stMainBlockContainer"] .st-key-forgot_password_card [data-testid="stVerticalBlock"] {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
            }

            .rf-forgot-back-spacer {
                margin-bottom: 32px;
            }

            .rf-forgot-eyebrow {
                margin: 5px 0 2px 0;
                color: #6D28D9;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.18em;
                text-transform: uppercase;
            }

            .rf-forgot-header h1 {
                margin: 0 0 8px 0;
                color: #171717;
                font-size: 30px;
                font-weight: 600;
                line-height: 1.2;
                letter-spacing: 0;
            }

            .rf-forgot-header p {
                margin: 0 0 32px 0;
                color: #737373;
                font-size: 14px;
                line-height: 1.6;
            }

            .rf-forgot-success {
                color: #166534;
                background: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 12px;
                padding: 12px 16px;
                margin: 4px 0 20px 0;
                font-size: 12px;
                line-height: 1.5;
            }

            .rf-forgot-footer {
                margin-top: 28px;
                text-align: center;
            }

            .rf-forgot-footer p {
                margin: 0;
                color: #737373;
                font-size: 14px;
            }

            .rf-forgot-footer a {
                color: #6D28D9;
                font-weight: 700;
                text-decoration: none;
            }

            .rf-forgot-footer a:hover {
                color: #4C1D95;
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

            [data-testid="stMainBlockContainer"] .stButton > button[kind="tertiary"] {
                min-height: auto !important;
                height: auto !important;
                padding: 0 !important;
                border: none !important;
                border-radius: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
                color: #737373 !important;
                font-weight: 600 !important;
            }

            [data-testid="stMainBlockContainer"] .stButton > button[kind="tertiary"]:hover {
                color: #4C1D95 !important;
                background: transparent !important;
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

            @media (max-width: 1023px) {
                .rf-forgot-art {
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
            }
        </style>
        """
    )


def _render_art_panel():
    st.html(
        f"""
        <aside class="rf-forgot-art">
            <div>{logo(light=True)}</div>
            <div class="rf-forgot-art-copy">
                <div class="rf-forgot-gold-line"></div>
                <h2>Recupere o acesso<br><span>sem perder o fluxo.</span></h2>
                <p>Informe seu e-mail institucional para receber orientações de acesso e voltar ao RoomFlow.</p>
            </div>
            <p>© 2026 RoomFlow</p>
        </aside>
        """
    )


def _render_header():
    st.markdown(
        """
        <div class="rf-forgot-header">
            <p class="rf-forgot-eyebrow">Recuperação de senha</p>
            <h1>Esqueci minha senha</h1>
            <p>Informe seu e-mail institucional para receber as instruções de recuperação.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def forgot_password():
    _init_state()
    _render_styles()
    _render_art_panel()

    with st.container(key="forgot_password_card"):
        if st.button("← Voltar para login", key="forgot_password_back", type="tertiary"):
            go("login")
        st.markdown('<div class="rf-forgot-back-spacer"></div>', unsafe_allow_html=True)

        _render_header()

        st.text_input(
            "E-mail",
            key="forgot_password_email",
            placeholder="seu@email.com",
        )

        if st.button("Enviar instruções →", key="forgot_password_submit", type="primary", width="stretch"):
            email = st.session_state.forgot_password_email.strip()
            st.session_state.forgot_password_success = (
                f"Se {email or 'este e-mail'} estiver cadastrado, as instruções serão enviadas."
            )

        if st.session_state.forgot_password_success:
            st.markdown(
                f'<div class="rf-forgot-success">{st.session_state.forgot_password_success}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="rf-forgot-footer"><p>Lembrou sua senha? <a href="?page=login" target="_self">Entrar</a></p></div>',
            unsafe_allow_html=True,
        )
