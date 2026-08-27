import time

import streamlit as st

from services import mock_data_service
from services.app_state_service import go


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

    if not nome or not email or not ra or not instituicao:
        return "Preencha todos os campos obrigatórios."

    if not senha or senha != confirm:
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
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(
            "←  Voltar",
            key="signup_member_back",
            type="tertiary",
        ):
            _reset()
            go("signup_choice")

    with col2:
        st.markdown(
            """
            <div class="rf-auth-top-logo">
                <div class="rf-logo-mark">R</div>
                <span>RoomFlow</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_form():
    _render_topbar()

    st.markdown(
        """
        <div class="rf-auth-page-container member">

            <div class="rf-page-header">

                <div class="rf-page-header-label">
                    <div class="rf-page-header-icon">
                        ♙
                    </div>

                    <span>Membro da instituição</span>
                </div>

                <h1>Criar conta</h1>

                <p>
                    Cadastre-se para utilizar o RoomFlow como membro
                    de uma instituição.
                </p>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="rf-member-form">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="rf-form-card">
        """,
        unsafe_allow_html=True,
    )

    st.text_input(
        "Nome completo *",
        key="signup_member_nome",
        placeholder="Seu nome completo",
    )

    st.text_input(
        "E-mail *",
        key="signup_member_email",
        placeholder="seu@instituicao.edu.br",
    )

    st.text_input(
        "RA / Matrícula *",
        key="signup_member_ra",
        placeholder="Ex: 202612345",
    )

    institutions = mock_data_service.institutions()

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

    st.text_input(
        "Senha *",
        key="signup_member_senha",
        placeholder="••••••••",
        type="password",
    )

    st.text_input(
        "Confirmar senha *",
        key="signup_member_confirm_senha",
        placeholder="••••••••",
        type="password",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.signup_member_error:
        st.markdown(
            f"""
            <div class="rf-form-error">
                {st.session_state.signup_member_error}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button(
        "Criar conta  →",
        key="signup_member_submit",
        type="primary",
        use_container_width=True,
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

    st.markdown("</div>", unsafe_allow_html=True)


def _render_validating():
    st.markdown(
        """
        <div class="rf-state-screen">

            <div class="rf-state-icon loading">
                <div class="rf-spinner"></div>
            </div>

            <h2>Validando seu vínculo</h2>

            <p>
                Estamos verificando seu RA/matrícula e e-mail junto
                à instituição selecionada.
            </p>

        </div>
        """,
        unsafe_allow_html=True,
    )

    time.sleep(2)

    ra = st.session_state.signup_member_ra.strip().upper()

    if ra.startswith("ERR"):
        st.session_state.signup_member_screen = "error"
    else:
        st.session_state.signup_member_screen = "success"

    st.rerun()


def _render_success():
    st.markdown(
        f"""
        <div class="rf-state-wrapper">

            <div class="rf-state-card">

                <div class="rf-state-icon success">
                    ✓
                </div>

                <h2>Conta criada com sucesso!</h2>

                <p>
                    Seu vínculo com
                    <strong>
                        {st.session_state.signup_member_instituicao}
                    </strong>
                    foi confirmado. Sua conta está pronta para uso.
                </p>

                <div class="rf-summary">

                    <div>
                        <span>Nome</span>
                        <strong>
                            {st.session_state.signup_member_nome}
                        </strong>
                    </div>

                    <div>
                        <span>E-mail</span>
                        <strong>
                            {st.session_state.signup_member_email}
                        </strong>
                    </div>

                    <div>
                        <span>Instituição</span>
                        <strong>
                            {st.session_state.signup_member_instituicao}
                        </strong>
                    </div>

                    <div>
                        <span>Status</span>
                        <strong class="success-text">
                            Ativa
                        </strong>
                    </div>

                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "Entrar no RoomFlow  →",
        key="signup_member_login",
        type="primary",
        use_container_width=True,
    ):
        _reset()
        go("login")


def _render_error():
    st.markdown(
        """
        <div class="rf-state-wrapper">

            <div class="rf-state-card">

                <div class="rf-state-icon error">
                    ×
                </div>

                <h2>
                    Não foi possível confirmar seus dados
                </h2>

                <p>
                    Verifique o número da matrícula, e-mail ou entre
                    em contato com a instituição.
                </p>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "Tentar novamente",
        key="signup_member_retry",
        use_container_width=True,
    ):
        st.session_state.signup_member_screen = "form"
        st.session_state.signup_member_error = ""
        st.rerun()


def signup_member():
    _init_state()

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