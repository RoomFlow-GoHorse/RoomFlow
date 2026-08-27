import time

import streamlit as st

from services.app_state_service import go


INSTITUTION_TYPES = [
    "Faculdade",
    "Universidade",
    "Centro Universitário",
    "Instituto",
    "Escola",
    "Outra",
]

ESTADOS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES",
    "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
    "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
]


def _init_state():
    defaults = {
        "signup_inst_step": 1,
        "signup_inst_screen": "form",
        "signup_inst_nome": "",
        "signup_inst_email": "",
        "signup_inst_senha": "",
        "signup_inst_confirm_senha": "",
        "signup_inst_telefone": "",
        "signup_inst_instituicao": "",
        "signup_inst_cnpj": "",
        "signup_inst_tipo": "",
        "signup_inst_cidade": "",
        "signup_inst_estado": "",
        "signup_inst_telefone_inst": "",
        "signup_inst_email_inst": "",
        "signup_inst_error": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset():
    keys = [
        "signup_inst_step",
        "signup_inst_screen",
        "signup_inst_nome",
        "signup_inst_email",
        "signup_inst_senha",
        "signup_inst_confirm_senha",
        "signup_inst_telefone",
        "signup_inst_instituicao",
        "signup_inst_cnpj",
        "signup_inst_tipo",
        "signup_inst_cidade",
        "signup_inst_estado",
        "signup_inst_telefone_inst",
        "signup_inst_email_inst",
        "signup_inst_error",
    ]

    for key in keys:
        st.session_state.pop(key, None)


def _input(key, label, placeholder="", type="default"):
    return st.text_input(
        label,
        key=key,
        placeholder=placeholder,
        type=type,
        label_visibility="visible",
    )


def _validate_step_one():
    nome = st.session_state.signup_inst_nome.strip()
    email = st.session_state.signup_inst_email.strip()
    senha = st.session_state.signup_inst_senha
    confirm = st.session_state.signup_inst_confirm_senha

    if not nome:
        return "Informe o nome completo do responsável."

    if not email:
        return "Informe o e-mail do responsável."

    if not senha:
        return "Crie uma senha para continuar."

    if len(senha) < 6:
        return "A senha deve possuir pelo menos 6 caracteres."

    if not confirm:
        return "Confirme a senha para continuar."

    if senha != confirm:
        return "As senhas não coincidem. Verifique e tente novamente."

    return None


def _validate_step_two():
    instituicao = st.session_state.signup_inst_instituicao.strip()
    cnpj = st.session_state.signup_inst_cnpj.strip()
    tipo = st.session_state.signup_inst_tipo

    if not instituicao:
        return "Informe o nome da instituição."

    if not cnpj:
        return "Informe o CNPJ da instituição."

    if not tipo:
        return "Selecione o tipo da instituição."

    return None


def _go_back():
    if st.session_state.signup_inst_step == 2:
        st.session_state.signup_inst_step = 1
        st.session_state.signup_inst_error = ""
        st.rerun()

    _reset()
    go("signup_choice")


def _next_step():
    error = _validate_step_one()

    if error:
        st.session_state.signup_inst_error = error
        return

    st.session_state.signup_inst_error = ""
    st.session_state.signup_inst_step = 2
    st.rerun()


def _submit():
    error = _validate_step_two()

    if error:
        st.session_state.signup_inst_error = error
        return

    st.session_state.signup_inst_error = ""
    st.session_state.signup_inst_screen = "verifying"
    st.rerun()


def _finish_verification():
    time.sleep(2.2)

    st.session_state.signup_inst_screen = "success"
    st.rerun()


def _render_topbar():
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(
            "←  Voltar",
            key="signup_inst_top_back",
            type="tertiary",
        ):
            _go_back()

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


def _render_stepper():
    step = st.session_state.signup_inst_step

    st.markdown(
        f"""
        <div class="rf-stepper">

            <div class="rf-step-item">

                <div class="rf-step-circle active">
                    {"✓" if step == 2 else "1"}
                </div>

                <span class="rf-step-label {'active' if step == 1 else ''}">
                    Seus dados
                </span>

            </div>

            <div class="rf-step-line {'active' if step == 2 else ''}"></div>

            <div class="rf-step-item">

                <div class="rf-step-circle {'active' if step == 2 else ''}">
                    2
                </div>

                <span class="rf-step-label {'active' if step == 2 else ''}">
                    Instituição
                </span>

            </div>

        </div>

        <div class="rf-mobile-step-labels">
            <span class="{'active' if step == 1 else ''}">
                Seus dados
            </span>

            <span class="{'active' if step == 2 else ''}">
                Instituição
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_header():
    step = st.session_state.signup_inst_step

    icon = "♙" if step == 1 else "▣"

    title = (
        "Crie sua conta"
        if step == 1
        else "Cadastre sua instituição"
    )

    description = (
        "Comece criando a conta do responsável pela instituição."
        if step == 1
        else
        "Agora informe os dados da instituição que será administrada pelo RoomFlow."
    )

    st.markdown(
        f"""
        <div class="rf-page-header">

            <div class="rf-page-header-label">
                <div class="rf-page-header-icon">
                    {icon}
                </div>

                <span>Cadastro de instituição</span>
            </div>

            <h1>{title}</h1>

            <p>{description}</p>

        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_step_one():
    st.markdown(
        """
        <div class="rf-form-card-header">
            <div class="rf-form-card-title">
                <span class="rf-inline-icon">♙</span>
                <h2>Dados do responsável</h2>
            </div>

            <p>
                Essas informações serão usadas para criar sua conta de administrador.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _input(
        "signup_inst_nome",
        "Nome completo *",
        "Seu nome completo",
    )

    col1, col2 = st.columns(2)

    with col1:
        _input(
            "signup_inst_email",
            "E-mail *",
            "seu@email.com",
        )

    with col2:
        _input(
            "signup_inst_telefone",
            "Telefone",
            "(11) 99999-9999",
        )

    col1, col2 = st.columns(2)

    with col1:
        _input(
            "signup_inst_senha",
            "Senha *",
            "••••••••",
            "password",
        )

        st.markdown(
            '<span class="rf-field-help">Mínimo de 6 caracteres.</span>',
            unsafe_allow_html=True,
        )

    with col2:
        _input(
            "signup_inst_confirm_senha",
            "Confirmar senha *",
            "••••••••",
            "password",
        )


def _render_step_two():
    st.markdown(
        """
        <div class="rf-form-card-header">
            <div class="rf-form-card-title">
                <span class="rf-inline-icon">▣</span>
                <h2>Dados da instituição</h2>
            </div>

            <p>
                Informe os dados oficiais da instituição que será administrada.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _input(
        "signup_inst_instituicao",
        "Nome da instituição *",
        "Ex: Faculdade de Tecnologia XPTO",
    )

    col1, col2 = st.columns(2)

    with col1:
        _input(
            "signup_inst_cnpj",
            "CNPJ *",
            "00.000.000/0000-00",
        )

    with col2:
        st.selectbox(
            "Tipo de instituição *",
            ["Selecione..."] + INSTITUTION_TYPES,
            key="signup_inst_tipo_select",
        )

        st.session_state.signup_inst_tipo = (
            ""
            if st.session_state.signup_inst_tipo_select == "Selecione..."
            else st.session_state.signup_inst_tipo_select
        )

    col1, col2 = st.columns(2)

    with col1:
        _input(
            "signup_inst_cidade",
            "Cidade",
            "São Paulo",
        )

    with col2:
        st.selectbox(
            "Estado / UF",
            ["Selecione..."] + ESTADOS,
            key="signup_inst_estado_select",
        )

        st.session_state.signup_inst_estado = (
            ""
            if st.session_state.signup_inst_estado_select == "Selecione..."
            else st.session_state.signup_inst_estado_select
        )

    col1, col2 = st.columns(2)

    with col1:
        _input(
            "signup_inst_telefone_inst",
            "Telefone institucional",
            "(11) 3000-0000",
        )

    with col2:
        _input(
            "signup_inst_email_inst",
            "E-mail institucional",
            "contato@instituicao.edu.br",
        )


def _render_form():
    _render_topbar()

    st.markdown('<div class="rf-auth-mobile-logo">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="rf-auth-mobile-logo-inner">
            <div class="rf-logo-mark">R</div>
            <span>RoomFlow</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="rf-auth-page-container">', unsafe_allow_html=True)

    _render_header()
    _render_stepper()

    st.markdown('<div class="rf-form-card">', unsafe_allow_html=True)

    if st.session_state.signup_inst_step == 1:
        _render_step_one()
    else:
        _render_step_two()

    st.markdown("</div>", unsafe_allow_html=True)

    error = st.session_state.signup_inst_error

    if error:
        st.markdown(
            f"""
            <div class="rf-form-error">
                {error}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.signup_inst_step == 1:
        if st.button(
            "Continuar  →",
            key="signup_inst_continue",
            type="primary",
            use_container_width=True,
        ):
            _next_step()

    else:
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "←  Voltar",
                key="signup_inst_step_back",
                use_container_width=True,
            ):
                _go_back()

        with col2:
            if st.button(
                "Criar instituição  →",
                key="signup_inst_submit",
                type="primary",
                use_container_width=True,
            ):
                _submit()

    st.markdown(
        """
        <p class="rf-terms">
            Ao criar sua conta, você concorda com os termos de uso e
            a política de privacidade do RoomFlow.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_verifying():
    st.markdown(
        """
        <div class="rf-state-screen">

            <div class="rf-state-icon loading">
                <div class="rf-spinner"></div>
            </div>

            <h2>Verificando sua instituição</h2>

            <p>
                Estamos consultando os dados informados.
                Isso leva apenas alguns segundos.
            </p>

        </div>
        """,
        unsafe_allow_html=True,
    )

    _finish_verification()


def _render_success():
    st.markdown(
        f"""
        <div class="rf-state-wrapper">

            <div class="rf-state-card">

                <div class="rf-state-icon success">
                    ✓
                </div>

                <h2>Instituição cadastrada com sucesso!</h2>

                <p>
                    Sua instituição foi cadastrada no RoomFlow.
                    Você agora é o administrador responsável pela plataforma.
                </p>

                <div class="rf-summary">

                    <div>
                        <span>Instituição</span>
                        <strong>
                            {st.session_state.signup_inst_instituicao or "—"}
                        </strong>
                    </div>

                    <div>
                        <span>Responsável</span>
                        <strong>
                            {st.session_state.signup_inst_nome or "—"}
                        </strong>
                    </div>

                    <div>
                        <span>E-mail</span>
                        <strong>
                            {st.session_state.signup_inst_email or "—"}
                        </strong>
                    </div>

                    <div>
                        <span>Status</span>
                        <strong class="success-text">Ativa</strong>
                    </div>

                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "Acessar RoomFlow  →",
        key="signup_inst_access",
        type="primary",
        use_container_width=True,
    ):
        _reset()
        go("login")


def signup_institution():
    _init_state()

    screen = st.session_state.signup_inst_screen

    if screen == "verifying":
        _render_verifying()
        return

    if screen == "success":
        _render_success()
        return

    _render_form()