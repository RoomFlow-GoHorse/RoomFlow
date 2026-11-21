import os
import secrets
from html import escape

import streamlit as st

from application.services.enrollment_management_service import (
    MemberIdentityNotConfirmed,
    TooManyEnrollmentAttempts,
)
from application.services.member_signup_service import InvalidEmailVerification
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource
from controllers.app_state_service import go
from controllers.streamlit_runtime import get_streamlit_runtime, uses_roomflow_api
from views.components.ui_components import logo

def _init_state():
    defaults = {
        "signup_member_screen": "form",
        "signup_member_nome": "",
        "signup_member_email": "",
        "signup_member_ra": "",
        "signup_member_instituicao": "",
        "signup_member_codigo_institucional": "",
        "signup_member_attempt_key": secrets.token_urlsafe(12),
        "signup_member_senha": "",
        "signup_member_confirm_senha": "",
        "signup_member_error": "",
    }

    for key, value in defaults.items():
        if st.session_state.get("signup_member_screen", "form") == "form":
            st.session_state.setdefault(key, value)
        else:
            # Keep form values while the confirmation steps hide their widgets.
            st.session_state[key] = st.session_state.get(key, value)

def _reset():
    keys = [
        "signup_member_screen",
        "signup_member_nome",
        "signup_member_email",
        "signup_member_ra",
        "signup_member_instituicao",
        "signup_member_codigo_institucional",
        "signup_member_attempt_key",
        "signup_member_senha",
        "signup_member_confirm_senha",
        "signup_member_error",
        "signup_member_token",
    ]

    for key in keys:
        st.session_state.pop(key, None)

def _validate():
    nome = st.session_state.signup_member_nome.strip()
    email = st.session_state.signup_member_email.strip()
    ra = st.session_state.signup_member_ra.strip()
    institutional_code = st.session_state.signup_member_codigo_institucional.strip()
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
    if not institutional_code:
        return "Informe o código institucional recebido da sua instituição."
    if not senha:
        return "Crie uma senha para continuar."
    if len(senha) < 8:
        return "A senha deve possuir pelo menos 8 caracteres."
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
            st.rerun()

    with col2:
        st.html(logo(size="small", variant="dark", class_name="rf-choice-logo"))

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

        st.text_input(
            "C\u00f3digo institucional *",
            key="signup_member_codigo_institucional",
            max_chars=200,
            help="Solicite o c\u00f3digo ao administrador da sua institui\u00e7\u00e3o.",
        )

        c3, c4 = st.columns(2)
        with c3:
            st.text_input(
                "Senha *",
                key="signup_member_senha",
                placeholder="••••••••",
                type="password",
            )
            st.markdown('<span class="rf-field-help" style="font-size:12px; color:#A1A1AA;">Mínimo de 8 caracteres.</span>', unsafe_allow_html=True)
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
                <div class="rf-state-icon loading"><div class="rf-spinner"></div></div>
                <h2>Validando seu vínculo</h2>
                <p>Estamos conferindo o código institucional e sua matrícula.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    try:
        preview = get_streamlit_runtime().enrollment_management.preview_member_institution(
            raw_code=st.session_state.signup_member_codigo_institucional.strip(),
            registration_number=st.session_state.signup_member_ra.strip(),
            name=st.session_state.signup_member_nome.strip(),
            email=st.session_state.signup_member_email.strip(),
            attempt_key=st.session_state.signup_member_attempt_key,
        )
    except TooManyEnrollmentAttempts:
        st.session_state.signup_member_error = "Muitas tentativas. Aguarde e tente novamente."
        st.session_state.signup_member_screen = "error"
    except MemberIdentityNotConfirmed:
        st.session_state.signup_member_error = "N\u00e3o foi poss\u00edvel confirmar os dados informados. Verifique com sua institui\u00e7\u00e3o."
        st.session_state.signup_member_screen = "error"
    except (DomainAuthorizationError, ValueError) as exc:
        st.session_state.signup_member_error = str(exc)
        st.session_state.signup_member_screen = "error"
    else:
        st.session_state.signup_member_instituicao = preview.institution_name
        st.session_state.signup_member_screen = "confirm"
    st.rerun()


def _render_confirm():
    st.markdown(
        f"""
        <div class="rf-state-wrapper">
            <div class="rf-state-card">
                <h2>Confirme sua instituição</h2>
                <p>Encontramos o vínculo com <strong>{escape(st.session_state.signup_member_instituicao)}</strong>.</p>
                <p>Confira se esta \u00e9 a instituição correta antes de continuar.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Confirmar instituição", key="signup_member_confirm_institution", type="primary", width="stretch"):
        try:
            preview = get_streamlit_runtime().enrollment_management.preview_member_institution(
                raw_code=st.session_state.signup_member_codigo_institucional.strip(),
                registration_number=st.session_state.signup_member_ra.strip(),
                name=st.session_state.signup_member_nome.strip(),
                email=st.session_state.signup_member_email.strip(),
                attempt_key=st.session_state.signup_member_attempt_key,
            )
        except (MemberIdentityNotConfirmed, TooManyEnrollmentAttempts, DomainAuthorizationError, ValueError):
            st.session_state.signup_member_error = "N\u00e3o foi poss\u00edvel confirmar os dados informados. Verifique com sua institui\u00e7\u00e3o."
            st.session_state.signup_member_screen = "error"
        else:
            try:
                started = get_streamlit_runtime().member_signup.start(
                    name=st.session_state.signup_member_nome.strip(),
                    email=st.session_state.signup_member_email.strip(),
                    registration_number=st.session_state.signup_member_ra.strip(),
                    institutional_code=st.session_state.signup_member_codigo_institucional.strip(),
                    password=st.session_state.signup_member_senha,
                    attempt_key=st.session_state.signup_member_attempt_key,
                )
            except (MemberIdentityNotConfirmed, TooManyEnrollmentAttempts, DuplicateResource, ValueError):
                st.session_state.signup_member_error = "N\u00e3o foi poss\u00edvel iniciar o cadastro. Verifique os dados e tente novamente."
                st.session_state.signup_member_screen = "error"
            except DomainAuthorizationError as exc:
                st.session_state.signup_member_error = str(exc)
                st.session_state.signup_member_screen = "error"
            else:
                st.session_state.signup_member_instituicao = started.institution_name
                st.session_state.signup_member_screen = "email_pending"
                st.session_state.pop("signup_member_senha", None)
                st.session_state.pop("signup_member_confirm_senha", None)
        st.rerun()


def _render_email_pending():
    st.info(
        f"Enviamos uma confirma\u00e7\u00e3o para {st.session_state.signup_member_email}. "
        "Confirme o e-mail para ativar sua conta.",
        icon=":material/mark_email_unread:",
    )
    environment = os.getenv("APP_ENV", "development").strip().lower()
    token = ""
    if uses_roomflow_api():
        token = st.text_input("Código recebido por e-mail", type="password", max_chars=200).strip()
    elif environment in {"development", "test"}:
        message = get_streamlit_runtime().simulated_email_sender.latest_for(
            st.session_state.signup_member_email
        )
        if message:
            st.caption("Caixa de e-mail simulada para desenvolvimento:")
            st.code(message.verification_token)
            token = message.verification_token
    if not st.button("Confirmar e-mail", type="primary", key="signup_member_verify_email", disabled=not token):
        return
    try:
        registered = get_streamlit_runtime().member_signup.verify_email(
            token, st.session_state.signup_member_attempt_key,
        )
    except InvalidEmailVerification:
        st.error("Token inválido, expirado ou já utilizado.")
    except TooManyEnrollmentAttempts:
        st.error("Muitas tentativas. Aguarde e tente novamente.")
    except (DomainAuthorizationError, ValueError) as exc:
        st.error(str(exc))
    else:
        st.session_state.signup_member_nome = registered.user.name
        st.session_state.signup_member_email = registered.user.email
        st.session_state.signup_member_screen = "success"
        st.rerun()


def _render_success():
    check_circle_svg = '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'

    st.html(
        f"""
        <div class="rf-state-wrapper">
            <div class="rf-state-card">
                <div class="rf-state-icon success">
                    {check_circle_svg}
                </div>
                <h2>Conta criada com sucesso!</h2>
                <p>Seu vínculo com <strong>{escape(st.session_state.signup_member_instituicao)}</strong> foi confirmado. Sua conta está pronta para uso.</p>

                <div class="rf-summary">
                    <div>
                        <span>Nome</span>
                        <strong>{escape(st.session_state.signup_member_nome)}</strong>
                    </div>
                    <div>
                        <span>E-mail</span>
                        <strong>{escape(st.session_state.signup_member_email)}</strong>
                    </div>
                    <div>
                        <span>Instituição</span>
                        <strong>{escape(st.session_state.signup_member_instituicao)}</strong>
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
            :where(html:has(#rf-public-theme)) [data-testid="stMainBlockContainer"] {
                max-width: 672px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-top: 80px !important;
                padding-bottom: 40px !important;
                padding-left: 24px !important;
                padding-right: 24px !important;
            }

            :where(html:has(#rf-public-theme)) [data-testid="stMainBlockContainer"] div[data-testid="stColumn"]:first-child button {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                color: #737373 !important;
                font-weight: 500 !important;
                font-size: 14px !important;
                padding: 0 !important;
            }

            :where(html:has(#rf-public-theme)) [data-testid="stMainBlockContainer"] div[data-testid="stColumn"]:first-child button:hover {
                color: var(--brand, #6D28D9) !important;
            }

            :where(html:has(#rf-public-theme)) [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]:has(div.rf-member-form-card) {
                background-color: #FFFFFF !important;
                border: 1px solid #E4E4E7 !important;
                border-radius: 16px !important;
                padding: 28px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
                margin-bottom: 24px !important;
            }

            :where(html:has(#rf-public-theme)) [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]:has(div.rf-member-form-card) [data-testid="stVerticalBlock"] {
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

    if screen == "confirm":
        _render_confirm()
        return

    if screen == "email_pending":
        _render_email_pending()
        return

    if screen == "success":
        _render_success()
        return

    if screen == "error":
        _render_error()
        return

    _render_form()
