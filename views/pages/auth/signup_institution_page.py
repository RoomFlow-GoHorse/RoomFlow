import time
import streamlit as st

from controllers.app_state_service import go
from views.components.ui_components import logo

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

def _validate_step_one():
    nome = st.session_state.signup_inst_nome.strip()
    email = st.session_state.signup_inst_email.strip()
    senha = st.session_state.signup_inst_senha
    confirm = st.session_state.signup_inst_confirm_senha

    if not nome:
        return "Informe seu nome completo."
    if not email:
        return "Informe seu e-mail."
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

def _exit_signup():
    _reset()
    go("signup_choice")
    st.rerun()

def _go_back():
    if st.session_state.signup_inst_step == 2:
        st.session_state.signup_inst_step = 1
        st.session_state.signup_inst_error = ""
        st.rerun()

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
    st.session_state.signup_inst_screen = "success"
    st.rerun()

def _render_topbar():
    col1, col2 = st.columns([1, 1], vertical_alignment="center")
    with col1:
        if st.button("← Voltar", key="signup_inst_top_back", type="tertiary"):
            _exit_signup()
    with col2:
        st.html(logo(size="small", class_name="rf-choice-logo"))

def _render_stepper():
    step = st.session_state.signup_inst_step
    check_svg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'

    st.markdown(
        f"""
        <div class="rf-stepper">
            <div class="rf-step-item">
                <div class="rf-step-circle active">
                    {check_svg if step == 2 else "1"}
                </div>
                <span class="rf-step-label {'active' if step == 1 else 'completed'}">
                    Seus dados
                </span>
            </div>
            <div class="rf-step-line {'active' if step == 2 else 'inactive'}"></div>
            <div class="rf-step-item">
                <div class="rf-step-circle {'active' if step == 2 else 'inactive'}">
                    2
                </div>
                <span class="rf-step-label {'active' if step == 2 else 'inactive'}">
                    Instituição
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _render_header():
    step = st.session_state.signup_inst_step
    user_svg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
    building_svg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><path d="M9 22v-4h6v4"></path></svg>'

    icon = user_svg if step == 1 else building_svg
    title = "Crie sua conta" if step == 1 else "Cadastre sua instituição"
    description = (
        "Comece criando sua conta de administrador da instituição."
        if step == 1
        else "Agora informe os dados da instituição que será administrada pelo RoomFlow."
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

def _render_form():
    _render_topbar()
    _render_header()
    _render_stepper()

    # Container unificado do Card de Formulário com classe CSS explícita
    with st.container():
        st.markdown('<div class="rf-inst-form-card"></div>', unsafe_allow_html=True)
        if st.session_state.signup_inst_step == 1:
            st.markdown(
                '<div class="rf-form-card-header"><div class="rf-form-card-title"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#6D28D9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg><h2>Dados do administrador</h2></div><p>Essas informações serão usadas para criar sua conta de administrador.</p></div>',
                unsafe_allow_html=True,
            )

            st.text_input("Nome completo *", key="signup_inst_nome", placeholder="Seu nome completo")

            c1, c2 = st.columns(2)
            with c1:
                st.text_input("E-mail *", key="signup_inst_email", placeholder="seu@email.com")
            with c2:
                st.text_input("Telefone", key="signup_inst_telefone", placeholder="(11) 99999-9999")

            c3, c4 = st.columns(2)
            with c3:
                st.text_input("Senha *", key="signup_inst_senha", placeholder="••••••••", type="password")
                st.markdown('<span class="rf-field-help" style="font-size:12px; color:#A1A1AA;">Mínimo de 6 caracteres.</span>', unsafe_allow_html=True)
            with c4:
                st.text_input("Confirmar senha *", key="signup_inst_confirm_senha", placeholder="••••••••", type="password")

        else:
            st.markdown(
                '<div class="rf-form-card-header"><div class="rf-form-card-title"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#6D28D9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><path d="M9 22v-4h6v4"></path></svg><h2>Dados da instituição</h2></div><p>Informe os dados oficiais da instituição que será administrada.</p></div>',
                unsafe_allow_html=True,
            )

            st.text_input("Nome da instituição *", key="signup_inst_instituicao", placeholder="Ex: Faculdade de Tecnologia XPTO")

            c1, c2 = st.columns(2)
            with c1:
                st.text_input("CNPJ *", key="signup_inst_cnpj", placeholder="00.000.000/0000-00")
            with c2:
                st.selectbox("Tipo de instituição *", ["Selecione..."] + INSTITUTION_TYPES, key="signup_inst_tipo_select")
                st.session_state.signup_inst_tipo = (
                    "" if st.session_state.signup_inst_tipo_select == "Selecione..."
                    else st.session_state.signup_inst_tipo_select
                )

            c3, c4 = st.columns(2)
            with c3:
                st.text_input("Cidade", key="signup_inst_cidade", placeholder="São Paulo")
            with c4:
                st.selectbox("Estado / UF", ["Selecione..."] + ESTADOS, key="signup_inst_estado_select")
                st.session_state.signup_inst_estado = (
                    "" if st.session_state.signup_inst_estado_select == "Selecione..."
                    else st.session_state.signup_inst_estado_select
                )

            c5, c6 = st.columns(2)
            with c5:
                st.text_input("Telefone institucional", key="signup_inst_telefone_inst", placeholder="(11) 3000-0000")
            with c6:
                st.text_input("E-mail institucional", key="signup_inst_email_inst", placeholder="contato@instituicao.edu.br")

    # Exibição de erros
    error = st.session_state.signup_inst_error
    if error:
        st.markdown(
            f'<div class="rf-form-error">{error}</div>',
            unsafe_allow_html=True,
        )

    # Botões de Ação
    if st.session_state.signup_inst_step == 1:
        if st.button("Continuar →", key="signup_inst_continue", type="primary", use_container_width=True):
            _next_step()
    else:
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("← Voltar", key="signup_inst_step_back", type="secondary", use_container_width=True):
                _go_back()
        with bc2:
            if st.button("Criar instituição →", key="signup_inst_submit", type="primary", use_container_width=True):
                _submit()

    st.markdown('<p class="rf-terms">Ao criar sua conta, você concorda com os termos de uso e a política de privacidade do RoomFlow.</p>', unsafe_allow_html=True)

def _render_verifying():
    st.markdown(
        """
        <div class="rf-state-wrapper">
            <div class="rf-state-card">
                <div class="rf-state-icon loading">
                    <div class="rf-spinner"></div>
                </div>
                <h2>Verificando sua instituição</h2>
                <p>Estamos consultando os dados informados. Isso leva apenas alguns segundos.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _finish_verification()

def _render_success():
    check_circle_svg = '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
    
    st.html(
        f"""
        <div class="rf-state-wrapper">
            <div class="rf-state-card">
                <div class="rf-state-icon success">
                    {check_circle_svg}
                </div>
                <h2>Instituição cadastrada com sucesso!</h2>
                <p>Sua instituição foi cadastrada no RoomFlow. Você agora é o administrador responsável pela plataforma.</p>

                <div class="rf-summary">
                    <div>
                        <span>Instituição</span>
                        <strong>{st.session_state.signup_inst_instituicao or "—"}</strong>
                    </div>
                    <div>
                        <span>Administrador</span>
                        <strong>{st.session_state.signup_inst_nome or "—"}</strong>
                    </div>
                    <div>
                        <span>E-mail</span>
                        <strong>{st.session_state.signup_inst_email or "—"}</strong>
                    </div>
                    <div>
                        <span>Status</span>
                        <strong class="green">Ativa</strong>
                    </div>
                </div>
            </div>
        </div>
        """,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Acessar RoomFlow →", key="signup_inst_access", type="primary", use_container_width=True):
            _reset()
            go("login")
            st.rerun()

def signup_institution():
    _init_state()
    st.html(
        """
        <style>
            /* Restringe a tela a 672px idêntico ao max-w-2xl do Figma com padding top seguro */
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

            /* TOPBAR BOTÃO VOLTAR */
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

            /* LOGO TOPBAR */
            .rf-choice-logo {
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 8px;
                font-weight: 700;
            }

            /* CONTAINER CARD DE FORMULÁRIO (FUNDO BRANCO, BORDA #E4E4E7, RADIUS 16PX) */
            [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]:has(div.rf-inst-form-card) {
                background-color: #FFFFFF !important;
                border: 1px solid #E4E4E7 !important;
                border-radius: 16px !important;
                padding: 28px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
                margin-bottom: 24px !important;
            }

            [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]:has(div.rf-inst-form-card) [data-testid="stVerticalBlock"] {
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
            }
        </style>
        """
    )
    screen = st.session_state.signup_inst_screen

    if screen == "verifying":
        _render_verifying()
        return

    if screen == "success":
        _render_success()
        return

    _render_form()
