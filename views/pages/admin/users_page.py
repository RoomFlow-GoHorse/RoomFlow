import streamlit as st

from config.constants import ROLE_LABELS
from controllers import mock_data_service
from controllers.app_state_service import set_toast
from views.components.badges import badge
from views.components.tables import operational_table_container
from views.components.ui_components import page_header


# =========================================================
# HELPERS VISUAIS
# =========================================================

def _avatar_html(initials: str) -> str:
    return (
        f'<span style="'
        f"display:inline-flex; align-items:center; justify-content:center;"
        f"width:32px; height:32px; border-radius:50%;"
        f"background:var(--brand-light); color:var(--brand);"
        f"font-size:12px; font-weight:700; flex-shrink:0;"
        f'">{initials}</span>'
    )


def _role_badge_html(role: str) -> str:
    return badge(role, category="role")


def _status_badge_html(status: str) -> str:
    return badge(status, category="status")


# =========================================================
# DIALOG: CRIAR / EDITAR USUÁRIO
# =========================================================

@st.dialog("Usuário")
def _user_dialog(editing_user: dict | None = None):
    is_edit = editing_user is not None
    title = "Editar usuário" if is_edit else "Novo usuário"
    st.subheader(title)

    default_name  = editing_user.get("name", "")  if is_edit else ""
    default_email = editing_user.get("email", "") if is_edit else ""
    default_role  = editing_user.get("role", "solicitante") if is_edit else "solicitante"

    name  = st.text_input("Nome completo", value=default_name,  placeholder="Ex: Carlos Andrade", disabled=is_edit)
    email = st.text_input("E-mail",        value=default_email, placeholder="usuario@instituicao.com", disabled=is_edit)

    role_options = list(ROLE_LABELS.keys())
    role_labels  = [ROLE_LABELS[r] for r in role_options]
    role_index   = role_options.index(default_role) if default_role in role_options else 0
    selected_role_label = st.selectbox("Perfil de acesso", options=role_labels, index=role_index)
    selected_role = role_options[role_labels.index(selected_role_label)]

    if not is_edit:
        st.text_input("Senha temporária", type="password", placeholder="••••••••")

    # Dica de perfis com variáveis de tema
    st.html("""
        <div style="
            background:var(--brand-light); border:1px solid var(--stroke);
            border-radius:8px; padding:10px 12px; margin-top:4px;
        ">
            <p style="margin:0 0 4px; font-size:12px; color:var(--brand); font-weight:600;">
                Sobre os perfis
            </p>
            <p style="margin:0; font-size:12px; color:var(--graphite-soft); line-height:1.5;">
                Gerente: gestão operacional · Administrador: governança ·
                Solicitante: reservas · Participante: consulta
            </p>
        </div>
    """)

    col_cancel, col_save = st.columns(2)

    with col_cancel:
        if st.button("Cancelar", width="stretch"):
            st.rerun()

    with col_save:
        label = "Salvar alterações" if is_edit else "Criar usuário"
        if st.button(label, type="primary", width="stretch"):
            if not is_edit and (not name.strip() or not email.strip()):
                st.warning("Preencha nome e e-mail.")
                return

            if is_edit:
                # Atualiza o usuário no session_state
                for u in st.session_state.users:
                    if u["id"] == editing_user["id"]:
                        u["role"]  = selected_role
                        break
                set_toast("Usuário atualizado com sucesso.")
            else:
                # Cria novo usuário mock
                new_id = f"u{len(st.session_state.users) + 1}"
                parts  = name.strip().split()
                initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else parts[0][:2].upper()
                st.session_state.users.append({
                    "id":       new_id,
                    "name":     name.strip(),
                    "email":    email.strip(),
                    "role":     selected_role,
                    "status":   "ativo",
                    "initials": initials,
                })
                set_toast("Usuário criado. Convite enviado por e-mail.")

            st.rerun()


# =========================================================
# TABELA DE USUÁRIOS
# =========================================================

def _render_users_table(filtered: list):
    """Renderiza a tabela de usuários com avatar, badges e botões com Material Symbols."""

    if not filtered:
        st.info("Nenhum usuário encontrado.")
        return

    # Cabeçalho com colunas nativas para ter botões de ação funcionais
    header = st.columns([3, 3, 2, 2, 1, 1])
    header[0].caption("**Usuário**")
    header[1].caption("**E-mail**")
    header[2].caption("**Perfil**")
    header[3].caption("**Status**")
    header[4].caption("**Editar**")
    header[5].caption("**Ação**")

    st.divider()

    for u in filtered:
        cols = st.columns([3, 3, 2, 2, 1, 1], vertical_alignment="center")

        # Nome + avatar
        with cols[0]:
            initials = u.get("initials", u["name"][:2].upper())
            st.html(
                f'<div style="display:flex; align-items:center; gap:10px; padding:4px 0;">'
                f'{_avatar_html(initials)}'
                f'<span style="font-size:13px; font-weight:600; color:var(--graphite);">{u["name"]}</span>'
                f'</div>'
            )

        # E-mail
        with cols[1]:
            st.html(f'<p style="font-size:12px; color:var(--graphite-muted); margin:0;">{u["email"]}</p>')

        # Perfil
        with cols[2]:
            st.html(f'<div style="padding:4px 0;">{_role_badge_html(u["role"])}</div>')

        # Status
        with cols[3]:
            st.html(f'<div style="padding:4px 0;">{_status_badge_html(u["status"])}</div>')

        # Botão Editar (Material Symbol)
        with cols[4]:
            if st.button("", key=f"edit_{u['id']}", icon=":material/edit:", help="Editar usuário"):
                _user_dialog(editing_user=u)

        # Botão Ativar / Desativar (Material Symbol)
        with cols[5]:
            if u["status"] == "ativo":
                if st.button("", key=f"toggle_{u['id']}", icon=":material/block:", help="Desativar usuário"):
                    mock_data_service.toggle_user(u["id"])
                    set_toast(f"{u['name']} foi desativado.")
                    st.rerun()
            else:
                if st.button("", key=f"toggle_{u['id']}", icon=":material/check_circle:", help="Ativar usuário"):
                    mock_data_service.toggle_user(u["id"])
                    set_toast(f"{u['name']} foi ativado.")
                    st.rerun()


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def users_page(user):
    # ---------------------------------------------------------
    # Cabeçalho
    # ---------------------------------------------------------
    col_header, col_action = st.columns([5, 1], vertical_alignment="bottom")
    with col_header:
        page_header(
            "Usuários",
            "Gerencie contas, perfis e acesso ao sistema.",
        )
    with col_action:
        if st.button("Novo usuário", type="primary", icon=":material/person_add:", width="stretch"):
            _user_dialog(editing_user=None)

    # ---------------------------------------------------------
    # Filtros
    # ---------------------------------------------------------
    col_search, col_role = st.columns([3, 1])

    with col_search:
        search = st.text_input(
            "Buscar",
            placeholder="Buscar por nome ou e-mail…",
            label_visibility="collapsed",
            key="users_search",
        )

    with col_role:
        role_options = ["Todos os perfis"] + list(ROLE_LABELS.values())
        role_filter  = st.selectbox(
            "Perfil",
            options=role_options,
            label_visibility="collapsed",
            key="users_role_filter",
        )

    # ---------------------------------------------------------
    # Filtragem
    # ---------------------------------------------------------
    all_users = mock_data_service.users()

    filtered = [
        u for u in all_users
        if (
            search.lower() in u["name"].lower()
            or search.lower() in u["email"].lower()
        )
        and (
            role_filter == "Todos os perfis"
            or ROLE_LABELS.get(u["role"]) == role_filter
        )
    ]

    # ---------------------------------------------------------
    # Tabela
    # ---------------------------------------------------------
    with operational_table_container("rf_users_table"):
        _render_users_table(filtered)
