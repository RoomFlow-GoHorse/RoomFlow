import streamlit as st

from config.constants import ROLE_LABELS
from controllers import auth_service
from models.mock_data import USERS, password_hash
from views.components.ui_components import page_header


SECTIONS = {
    "perfil": ("Perfil", ":material/person:"),
    "seguranca": ("Segurança", ":material/shield:"),
    "preferencias": ("Notificações", ":material/notifications:"),
    "sessao": ("Sessão", ":material/logout:"),
}

SECTION_HEADERS = {
    "perfil": (
        "Informações do perfil",
        "Edite seus dados pessoais e informações de contato.",
        ":material/person:",
    ),
    "seguranca": (
        "Segurança da conta",
        "Altere sua senha e mantenha sua conta protegida.",
        ":material/shield:",
    ),
    "preferencias": (
        "Preferências de notificação",
        "Escolha quais notificações e alertas deseja receber.",
        ":material/notifications:",
    ),
    "sessao": (
        "Sessão",
        "Consulte sua sessão atual ou encerre o acesso à conta.",
        ":material/logout:",
    ),
}

PREFERENCES = {
    "reservas": (
        "Reservas",
        "Aprovações, rejeições e novas solicitações",
    ),
    "alteracoes": (
        "Alterações de espaço",
        "Quando uma sala ou horário for alterado",
    ),
    "conflitos": (
        "Conflitos",
        "Quando houver sobreposição de reservas",
    ),
    "cancelamentos": (
        "Cancelamentos",
        "Quando uma reserva for cancelada",
    ),
    "lembretes": (
        "Lembretes",
        "Notificação 1 hora antes de cada atividade",
    ),
    "sistema": (
        "Atualizações do sistema",
        "Manutenção, novidades e avisos gerais",
    ),
}


def _load_css():
    st.markdown(
        """
        <style>
            /* Espaçamento geral */
            .account-page {
                margin-bottom: 2rem;
            }

            /* Avatar */
            .account-avatar {
                width: 64px;
                height: 64px;
                border-radius: 16px;
                background: var(--brand);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                font-weight: 600;
            }

            /* Navegação */
            div.st-key-account_nav_perfil button,
            div.st-key-account_nav_seguranca button,
            div.st-key-account_nav_preferencias button,
            div.st-key-account_nav_sessao button {
                min-height: 44px;
                justify-content: flex-start;
            }

            /* Cards de informação */
            .account-info-label {
                font-size: 11px;
                color: var(--text-muted);
                margin-bottom: 2px;
            }

            .account-info-value {
                font-size: 13px;
                font-weight: 600;
            }

            /* Remove espaço exagerado de alguns elementos */
            .account-compact {
                margin-top: -8px;
            }

            /* Sidebar - conta e sair sem negrito */
            div.st-key-rf_account button,
            div.st-key-rf_logout button {
                font-weight: 400 !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _state(user):
    st.session_state.setdefault(
        "account_section",
        "perfil",
    )

    st.session_state.setdefault(
        "account_editing",
        False,
    )

    st.session_state.setdefault(
        "account_logout_confirm",
        False,
    )

    st.session_state.setdefault(
        "account_phone",
        "(11) 98765-4321",
    )

    st.session_state.setdefault(
        "account_preferences",
        {
            "reservas": True,
            "alteracoes": True,
            "conflitos": True,
            "cancelamentos": True,
            "lembretes": False,
            "sistema": True,
        },
    )

    st.session_state.setdefault(
        "account_name",
        user["name"],
    )

    st.session_state.setdefault(
        "account_email",
        user["email"],
    )


def _avatar(initials, size=64):
    st.markdown(
        f"""
        <div
            class="account-avatar"
            style="
                width:{size}px;
                height:{size}px;
                font-size:{max(16, size // 3)}px;
            "
        >
            {initials}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _header(user):
    page_header(
        "Configurações da conta",
        "Gerencie suas informações pessoais, segurança e preferências.",
    )

    with st.container(border=True):
        avatar, details, status = st.columns(
            [1, 6, 2],
            vertical_alignment="center",
        )

        with avatar:
            _avatar(
                user.get("initials", "??"),
                64,
            )

        with details:
            st.markdown(f"**{user['name']}**")

            role = ROLE_LABELS.get(
                user["role"],
                "Usuário",
            )

            st.caption(
                f"{role} · {user['email']}"
            )

        with status:
            st.success(
                "Conta ativa",
                icon=":material/check_circle:",
            )


def _navigation():
    with st.container(border=True):
        for key, (label, icon) in SECTIONS.items():
            active = (
                st.session_state.account_section == key
            )

            if st.button(
                label,
                key=f"account_nav_{key}",
                icon=icon,
                type="primary" if active else "secondary",
                width="stretch",
            ):
                st.session_state.account_section = key
                st.rerun()


def _section_header(section):
    title, description, icon = SECTION_HEADERS[section]

    icon_col, title_col = st.columns(
        [1, 12],
        vertical_alignment="center",
    )

    with icon_col:
        st.button(
            "",
            key=f"section_icon_{section}",
            icon=icon,
            disabled=True,
        )

    with title_col:
        st.subheader(title)
        st.caption(description)


def _profile(user):
    _section_header("perfil")

    avatar_col, photo_col = st.columns(
        [1, 5],
        vertical_alignment="center",
    )

    with avatar_col:
        _avatar(
            user.get("initials", "??"),
            120,
        )

    with photo_col:
        st.markdown("**Foto de perfil**")

        upload_col, info_col = st.columns(
            [1, 2],
            vertical_alignment="center",
        )

        with upload_col:
            st.file_uploader(
                "Alterar foto",
                type=["png", "jpg", "jpeg"],
                label_visibility="collapsed",
                key="account_avatar",
            )

    st.divider()

    st.markdown("**Informações pessoais**")
    st.caption(
        "Mantenha seus dados de contato sempre atualizados."
    )

    editing = st.session_state.account_editing

    if editing:
        with st.form(
            "account_profile",
            border=False,
        ):
            left, right = st.columns(2)

            with left:
                name = st.text_input(
                    "Nome completo",
                    value=st.session_state.account_name,
                )

                phone = st.text_input(
                    "Telefone",
                    value=st.session_state.account_phone,
                )

            with right:
                email = st.text_input(
                    "E-mail",
                    value=st.session_state.account_email,
                )

                st.text_input(
                    "Perfil de acesso",
                    value=ROLE_LABELS.get(
                        user["role"],
                        "Usuário",
                    ),
                    disabled=True,
                )

            st.divider()

            save, cancel = st.columns(2)

            with save:
                submitted = st.form_submit_button(
                    "Salvar alterações",
                    type="primary",
                    icon=":material/save:",
                    width="stretch",
                )

            with cancel:
                cancelled = st.form_submit_button(
                    "Cancelar",
                    icon=":material/close:",
                    width="stretch",
                )

        if cancelled:
            st.session_state.account_editing = False
            st.rerun()

        if submitted:
            if not name.strip():
                st.error("Informe o nome completo.")
                return

            if not email.strip():
                st.error("Informe o e-mail.")
                return

            user.update(
                {
                    "name": name.strip(),
                    "email": email.strip(),
                }
            )

            for item in st.session_state.users:
                if item["id"] == user["id"]:
                    item.update(user)

            for item in USERS:
                if item["id"] == user["id"]:
                    item.update(
                        {
                            "name": user["name"],
                            "email": user["email"],
                        }
                    )

            st.session_state.account_name = user["name"]
            st.session_state.account_email = user["email"]
            st.session_state.account_phone = phone
            st.session_state.account_editing = False

            st.toast(
                "Perfil atualizado com sucesso.",
                icon=":material/check_circle:",
            )

            st.rerun()

    else:
        left, right = st.columns(2)

        with left:
            st.text_input(
                "Nome completo",
                value=user["name"],
                disabled=True,
            )

            st.text_input(
                "Telefone",
                value=st.session_state.account_phone,
                disabled=True,
            )

        with right:
            st.text_input(
                "E-mail",
                value=user["email"],
                disabled=True,
            )

            st.text_input(
                "Perfil de acesso",
                value=ROLE_LABELS.get(
                    user["role"],
                    "Usuário",
                ),
                disabled=True,
            )

        st.divider()

        if st.button(
            "Editar perfil",
            icon=":material/edit:",
        ):
            st.session_state.account_editing = True
            st.rerun()


def _security(user):
    _section_header("seguranca")

    st.info(
        "Use uma senha forte e exclusiva. "
        "Recomendamos combinar letras, números e caracteres especiais.",
        icon=":material/shield:",
    )

    st.write("")

    with st.form(
        "account_security",
        border=False,
    ):
        current = st.text_input(
            "Senha atual",
            type="password",
            placeholder="Digite sua senha atual",
        )

        new_password = st.text_input(
            "Nova senha",
            type="password",
            placeholder="Mínimo de 8 caracteres",
        )

        if new_password:
            if len(new_password) < 6:
                strength = "Fraca"
            elif len(new_password) < 10:
                strength = "Média"
            else:
                strength = "Forte"

            st.caption(
                f"Força da senha: **{strength}**"
            )

        confirm = st.text_input(
            "Confirmar nova senha",
            type="password",
            placeholder="Repita sua nova senha",
        )

        st.divider()

        submitted = st.form_submit_button(
            "Alterar senha",
            type="primary",
            icon=":material/lock:",
        )

    if not submitted:
        return

    source = next(
        (
            item
            for item in st.session_state.users
            if item["id"] == user["id"]
        ),
        None,
    )

    if not current:
        st.error("Informe a senha atual.")
        return

    if (
        not source
        or source.get("password_hash")
        != password_hash(current)
    ):
        st.error(
            "A senha atual informada não confere."
        )
        return

    if len(new_password) < 8:
        st.error(
            "A nova senha deve ter pelo menos 8 caracteres."
        )
        return

    if new_password != confirm:
        st.error("As senhas não coincidem.")
        return

    source["password_hash"] = password_hash(
        new_password
    )

    for item in USERS:
        if item["id"] == user["id"]:
            item["password_hash"] = source[
                "password_hash"
            ]

    st.success(
        "Senha alterada com sucesso.",
        icon=":material/check_circle:",
    )


def _preferences():
    _section_header("preferencias")

    preferences = st.session_state.account_preferences

    enabled = sum(
        preferences.values()
    )

    total = len(PREFERENCES)

    with st.container(border=True):
        left, right = st.columns(
            [5, 1],
            vertical_alignment="center",
        )

        with left:
            st.markdown("**Notificações ativas**")
            st.caption(
                f"Você recebe {enabled} de {total} tipos de alerta."
            )

        with right:
            st.metric(
                "Ativos",
                f"{enabled}/{total}",
            )

    st.write("")

    for key, (label, description) in PREFERENCES.items():
        with st.container(border=True):
            text, toggle = st.columns(
                [6, 1],
                vertical_alignment="center",
            )

            with text:
                st.markdown(f"**{label}**")
                st.caption(description)

            with toggle:
                preferences[key] = st.toggle(
                    label,
                    value=preferences[key],
                    key=f"account_preference_{key}",
                    label_visibility="collapsed",
                )

    st.divider()

    if st.button(
        "Salvar preferências",
        type="primary",
        icon=":material/save:",
    ):
        st.toast(
            "Preferências salvas.",
            icon=":material/check_circle:",
        )


def _session(user):
    _section_header("sessao")

    with st.container(border=True):
        st.success(
            "Sua conta está conectada neste dispositivo.",
            icon=":material/check_circle:",
        )

        st.write("")

        device, browser, location = st.columns(3)

        with device:
            st.caption("Dispositivo")
            st.markdown("**Computador**")

        with browser:
            st.caption("Navegador")
            st.markdown("**Chrome**")

        with location:
            st.caption("Localização")
            st.markdown("**São Paulo, SP**")

        st.divider()

        st.caption("Conta")
        st.markdown(f"**{user['email']}**")

    st.write("")

    with st.container(border=True):
        st.warning(
            "Encerrar sessão",
            icon=":material/logout:",
        )

        st.caption(
            "Saia da sua conta neste dispositivo. "
            "Será necessário fazer login novamente para acessar o RoomFlow."
        )

        st.write("")

        if st.session_state.account_logout_confirm:
            cancel, confirm = st.columns(2)

            with cancel:
                if st.button(
                    "Cancelar",
                    key="cancel_logout",
                    width="stretch",
                ):
                    st.session_state.account_logout_confirm = False
                    st.rerun()

            with confirm:
                if st.button(
                    "Confirmar saída",
                    key="confirm_logout",
                    type="primary",
                    icon=":material/logout:",
                    width="stretch",
                ):
                    auth_service.logout()

        else:
            if st.button(
                "Sair da conta",
                icon=":material/logout:",
            ):
                st.session_state.account_logout_confirm = True
                st.rerun()


def account(user):
    _load_css()
    _state(user)

    _header(user)

    navigation, content = st.columns(
        [1, 3],
        gap="large",
    )

    with navigation:
        _navigation()

    with content:
        with st.container(border=True):
            section = st.session_state.account_section

            if section == "perfil":
                _profile(user)

            elif section == "seguranca":
                _security(user)

            elif section == "preferencias":
                _preferences()

            elif section == "sessao":
                _session(user)

