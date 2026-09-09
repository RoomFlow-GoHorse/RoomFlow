from controllers import user_controller
import time
import streamlit as st

from services.app_state_service import go
from views.components.ui_components import logo

DEMO_INSTITUTIONS = [
    "Faculdade de Tecnologia XPTO",
    "Universidade Federal do Exemplo",
    "Centro Universitário ABC",
    "Instituto de Educação Superior",
]

def _init_state():
    defaults = {
        "signup_member_screen": "form",
        "signup_member_nome": "",
        "signup_member_email": "",
        "signup_member_ra": "",
        "signup_member_instituicao": "",
        "signup_member_instituicao_select": "Selecione sua instituiÃ§Ã£o...",
        "signup_member_senha": "",
        "signup_member_confirm_senha": "",
        "signup_member_error": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def _reset():
    keys = [
        "signup_member_screen",
        "signup_member_nome",
        "signup_member_email",
        "signup_member_ra",
        "signup_member_instituicao",
        "signup_member_instituicao_select",
        "signup_member_senha",
        "signup_member_confirm_senha",
        "signup_member_error",
    ]

    for key in keys:
        st.session_state.pop(key, None)

def _validate():
    nome = st.session_state.signup_member_nome.strip()
    email = st.session_state.signup_member_email.strip()
    ra = st.session_state.signup_member_ra.strip()
    instituicao = st.session_state.signup_member_instituicao
    senha = st.session_state.signup_member_senha
    confirm = st.session_state.signup_member_confirm_senha

    if not nome:
        return "Informe seu nome completo."
    if not email:
        return "Informe seu e-mail institucional."
    if "@" not in email or "." not in email.split("@")[-1]:
        return "Informe um e-mail válido."
    if not ra:
        return "Informe seu RA ou matrícula."
    if not instituicao:
        return "Selecione sua instituição."
    if not senha:
        return "Crie uma senha para continuar."
    if len(senha) < 6:
        return "A senha deve possuir pelo menos 6 caracteres."
    if not confirm:
        return "Confirme a senha para continuar."
    if senha != confirm:
        return "As senhas não coincidem. Verifique e tente novamente."

    return None

def _submit():
    error = _validate()

    if error:
        st.session_state.signup_member_error = error
        return

    st.session_state.signup_member_error = ""
    st.session_state.signup_member_screen = "validating"
    st.rerun()

def _render_topbar():
    col1, col2 = st.columns([1, 1], vertical_alignment="center")

    with col1:
        if st.button("← Voltar", key="signup_member_back", type="tertiary"):
            _reset()
            go("signup_choice")

    with col2:
        st.html(logo(size="small", class_name="rf-choice-logo"))

def _render_form():
    _render_topbar()

    users_svg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>'

    st.markdown(
        f"""
        <div class="rf-page-header">
            <div class="rf-page-header-label">
                <div class="rf-page-header-icon">
                    {users_svg}
                </div>
                <span>Membro da instituição</span>
            </div>
            <h1>Criar conta</h1>
            <p>Cadastre-se para utilizar o RoomFlow como membro de uma instituição.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="rf-member-form-card"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="rf-form-card-header"><div class="rf-form-card-title"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#6D28D9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg><h2>Dados do membro</h2></div><p>Use seus dados institucionais para confirmar o vínculo com a instituição.</p></div>',
            unsafe_allow_html=True,
        )

        st.text_input(
            "Nome completo *",
            key="signup_member_nome",
            placeholder="Seu nome completo",
        )

        c1, c2 = st.columns(2)
        with c1:
            st.text_input(
                "E-mail *",
                key="signup_member_email",
                placeholder="seu@instituicao.edu.br",
            )
        with c2:
            st.text_input(
                "RA / Matrícula *",
                key="signup_member_ra",
                placeholder="Ex: 202612345",
            )

        institutions = user_controller.institutions()
        if not institutions:
            institutions = DEMO_INSTITUTIONS

        st.selectbox(
            "Instituição *",
            ["Selecione sua instituição..."] + institutions,
            key="signup_member_instituicao_select",
        )

        if st.session_state.signup_member_instituicao_select == "Selecione sua instituição...":
            st.session_state.signup_member_instituicao = ""
        else:
            st.session_state.signup_member_instituicao = (
                st.session_state.signup_member_instituicao_select
            )

        c3, c4 = st.columns(2)
        with c3:
            st.text_input(
                "Senha *",
                key="signup_member_senha",
                placeholder="••••••••",
                type="password",
            )
            st.markdown('<span class="rf-field-help" style="font-size:12px; color:#A1A1AA;">Mínimo de 6 caracteres.</span>', unsafe_allow_html=True)
        with c4:
            st.text_input(
                "Confirmar senha *",
                key="signup_member_confirm_senha",
                placeholder="••••••••",
                type="password",
            )

    if st.session_state.signup_member_error:
        st.markdown(
            f"""
            <div class="rf-form-error">
                <span>{st.session_state.signup_member_error}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button(
        "Criar conta →",
        key="signup_member_submit",
        type="primary",
        width="stretch",
    ):
        _submit()

    st.markdown(
        """
        <p class="rf-member-help">
            Problemas com o cadastro? Entre em contato com a instituição.
        </p>
        """,
        unsafe_allow_html=True,
    )

def _render_validating():
    st.markdown(
        """
        <div class="rf-state-wrapper">
            <div class="rf-state-card">
                <div class="rf-state-icon loading">
                    <div class="rf-spinner"></div>
                </div>
                <h2>Validando seu vínculo</h2>
                <p>Estamos verificando seu RA/matrícula e e-mail junto à instituição selecionada.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    time.sleep(2.0)

    ra = st.session_state.signup_member_ra.strip().upper()
    if ra.startswith("ERR"):
        st.session_state.signup_member_screen = "error"
    else:
        st.session_state.signup_member_screen = "success"

    st.rerun()

def _render_success():
    check_circle_svg = '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'

    st.markdown(
        f"""
        <div class="rf-state-wrapper">
            <div class="rf-state-card">
                <div class="rf-state-icon success">
                    {check_circle_svg}
                </div>
                <h2>Conta criada com sucesso!</h2>
                <p>Seu vínculo com <strong>{st.session_state.signup_member_instituicao}</strong> foi confirmado. Sua conta está pronta para uso.</p>

                <div class="rf-summary">
                    <div>
                        <span>Nome</span>
                        <strong>{st.session_state.signup_member_nome}</strong>
                    </div>
                    <div>
                        <span>E-mail</span>
                        <strong>{st.session_state.signup_member_email}</strong>
                    </div>
                    <div>
                        <span>Instituição</span>
                        <strong>{st.session_state.signup_member_instituicao}</strong>
                    </div>
                    <div>
                        <span>Status</span>
                        <strong class="green">Ativa</strong>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Entrar no RoomFlow →", key="signup_member_login", type="primary", width="stretch"):
            _reset()
            go("login")

def _render_error():
    x_circle_svg = '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'

    st.markdown(
        f"""
        <div class="rf-state-wrapper">
            <div class="rf-state-card">
                <div class="rf-state-icon error">
                    {x_circle_svg}
                </div>
                <h2>Não foi possível confirmar seus dados</h2>
                <p>Verifique o número da matrícula, e-mail ou entre em contato com a instituição.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Tentar novamente", key="signup_member_retry", type="secondary", width="stretch"):
            st.session_state.signup_member_screen = "form"
            st.session_state.signup_member_error = ""
            st.rerun()

def signup_member():
    _init_state()
    st.html(
        """
        <style>
            [data-testid="stMainBlockContainer"] {
                max-width: 672px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-top: 80px !important;
                padding-bottom: 40px !important;
                padding-left: 24px !important;
                padding-right: 24px !important;
            }

            .stApp {
                background-color: #F7F7F9 !important;
            }

            [data-testid="stMainBlockContainer"] div[data-testid="stColumn"]:first-child button {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                color: #737373 !important;
                font-weight: 500 !important;
                font-size: 14px !important;
                padding: 0 !important;
            }

            [data-testid="stMainBlockContainer"] div[data-testid="stColumn"]:first-child button:hover {
                color: var(--brand, #6D28D9) !important;
            }

            .rf-choice-logo {
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 8px;
                font-weight: 700;
            }

            [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]:has(div.rf-member-form-card) {
                background-color: #FFFFFF !important;
                border: 1px solid #E4E4E7 !important;
                border-radius: 16px !important;
                padding: 28px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
                margin-bottom: 24px !important;
            }

            [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]:has(div.rf-member-form-card) [data-testid="stVerticalBlock"] {
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
            }
        </style>
        """
    )
    screen = st.session_state.signup_member_screen

    if screen == "validating":
        _render_validating()
        return

    if screen == "success":
        _render_success()
        return

    if screen == "error":
        _render_error()
        return

    _render_form()
