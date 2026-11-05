import pandas as pd
import streamlit as st

from config.constants import ROLE_LABELS
from controllers import mock_data_service
from controllers.app_state_service import set_toast
from views.components.ui_components import page_header

# Mapeamento de rótulos visuais para o DataFrame
STATUS_LABELS = {
    "ativo": "Ativo",
    "inativo": "Inativo",
}


# =========================================================
# DIALOG: CRIAR / EDITAR USUÁRIO
# =========================================================

@st.dialog("Usuário")
def _user_dialog(editing_user: dict | None = None):
    is_edit = editing_user is not None
    title = "Editar usuário" if is_edit else "Novo usuário"
    st.subheader(title)

    default_name = editing_user.get("name", "") if is_edit else ""
    default_email = editing_user.get("email", "") if is_edit else ""
    default_role = editing_user.get("role", "solicitante") if is_edit else "solicitante"

    name = st.text_input("Nome completo", value=default_name, placeholder="Ex: Carlos Andrade", disabled=is_edit)
    email = st.text_input("E-mail", value=default_email, placeholder="usuario@instituicao.com", disabled=is_edit)

    role_options = list(ROLE_LABELS.keys())
    role_labels = [ROLE_LABELS[r] for r in role_options]
    role_index = role_options.index(default_role) if default_role in role_options else 0
    selected_role_label = st.selectbox("Perfil de acesso", options=role_labels, index=role_index)
    selected_role = role_options[role_labels.index(selected_role_label)]

    if not is_edit:
        st.text_input("Senha temporária", type="password", placeholder="••••••••")

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
                for u in st.session_state.users:
                    if u["id"] == editing_user["id"]:
                        u["role"] = selected_role
                        break
                set_toast("Usuário atualizado com sucesso.")
            else:
                new_id = f"u{len(st.session_state.users) + 1}"
                parts = name.strip().split()
                initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else parts[0][:2].upper()
                st.session_state.users.append({
                    "id": new_id,
                    "name": name.strip(),
                    "email": email.strip(),
                    "role": selected_role,
                    "status": "ativo",
                    "initials": initials,
                })
                set_toast("Usuário criado. Convite enviado por e-mail.")

            st.rerun()


# =========================================================
# HELPERS DE DADOS
# =========================================================

def _users_dataframe(users_list: list) -> pd.DataFrame:
    """Converte a lista de usuários filtrados no DataFrame padronizado."""
    return pd.DataFrame(
        [
            {
                "Usuário": u["name"],
                "E-mail": u["email"],
                "Perfil": ROLE_LABELS.get(u["role"], u["role"]),
                "Status": STATUS_LABELS.get(u["status"], u["status"]),
            }
            for u in users_list
        ]
    )


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
        role_filter = st.selectbox(
            "Perfil",
            options=role_options,
            label_visibility="collapsed",
            key="users_role_filter",
        )

    # ---------------------------------------------------------
    # Filtragem dos dados
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
    # Tabela (Estilo padronizado com st.dataframe)
    # ---------------------------------------------------------
    if not filtered:
        st.info("Nenhum usuário encontrado.")
        return

    # Container informativo padronizado
    with st.container(border=True):
        st.caption(
            ":material/info: Selecione um usuário abaixo no menu de ações para editar suas permissões ou alterar seu status de acesso."
        )

    # Exibição da tabela identica à página de permissões
    df_users = _users_dataframe(filtered)
    st.dataframe(
        df_users,
        column_config={
            "Usuário": st.column_config.TextColumn("Usuário", width="large", pinned=True),
            "E-mail": st.column_config.TextColumn("E-mail", width="medium"),
            "Perfil": st.column_config.TextColumn("Perfil", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        hide_index=True,
        width="stretch",
    )

    # ---------------------------------------------------------
    # Painel de Ações Operacionais sobre a seleção
    # ---------------------------------------------------------
    col_select, col_edit, col_toggle = st.columns([3, 1, 1], vertical_alignment="bottom")
    
    user_map = {f"{u['name']} ({u['email']})": u for u in filtered}
    
    with col_select:
        selected_user_label = st.selectbox(
            "Ações do usuário",
            options=list(user_map.keys()),
            help="Selecione um usuário para editar dados ou alterar status",
        )
        selected_user = user_map[selected_user_label]

    with col_edit:
        if st.button("Editar", icon=":material/edit:", width="stretch"):
            _user_dialog(editing_user=selected_user)

    with col_toggle:
        if selected_user["status"] == "ativo":
            if st.button("Desativar", icon=":material/block:", width="stretch"):
                mock_data_service.toggle_user(selected_user["id"])
                set_toast(f"{selected_user['name']} foi desativado.")
                st.rerun()
        else:
            if st.button("Ativar", icon=":material/check_circle:", width="stretch"):
                mock_data_service.toggle_user(selected_user["id"])
                set_toast(f"{selected_user['name']} foi ativado.")
                st.rerun()

    st.info(
        "Alterações de perfil e status são refletidas imediatamente nos acessos do usuário no sistema.",
        icon=":material/shield:",
    )