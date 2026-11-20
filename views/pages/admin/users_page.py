import pandas as pd
import streamlit as st

from config.constants import ROLE_LABELS
from controllers.streamlit_runtime import get_streamlit_actor, get_streamlit_runtime
from models.domain.entities.authorized_enrollment import EnrollmentStatus
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource, LastActiveAdministrator, ResourceNotFound
from views.components.ui_components import page_header


@st.dialog("Usuario")
def _user_dialog(actor: User, editing_user: User | None = None):
    runtime = get_streamlit_runtime()
    is_edit = editing_user is not None
    st.subheader("Editar usuario" if is_edit else "Novo usuario")
    name = st.text_input("Nome completo", value=editing_user.name if is_edit else "", disabled=is_edit)
    email = st.text_input("E-mail", value=editing_user.email if is_edit else "", disabled=is_edit)
    profile_values = [profile.value for profile in Profile]
    labels = [ROLE_LABELS[value] for value in profile_values]
    current = editing_user.profile.value if is_edit else Profile.REQUESTER.value
    selected_label = st.selectbox("Perfil de acesso", labels, index=profile_values.index(current))
    selected_profile = Profile(profile_values[labels.index(selected_label)])
    password = "" if is_edit else st.text_input("Senha inicial", type="password")
    st.caption("Somente um administrador da instituicao pode atribuir o perfil admin.")
    cancel, save = st.columns(2)
    if cancel.button("Cancelar", width="stretch"):
        st.rerun()
    if save.button("Salvar" if is_edit else "Criar usuario", type="primary", width="stretch"):
        try:
            if is_edit:
                runtime.user_management.update_profile(actor, editing_user.id, selected_profile)
            else:
                if not name.strip() or not email.strip() or len(password) < 8:
                    st.error("Informe nome, e-mail e uma senha com pelo menos 8 caracteres.")
                    return
                runtime.user_management.create_user(actor, name, email, password, selected_profile)
        except (DuplicateResource, DomainAuthorizationError, LastActiveAdministrator, ResourceNotFound, ValueError) as exc:
            st.error(str(exc))
            return
        st.rerun()


def _user_table(users: list[User]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Nome": item.name,
            "E-mail": item.email,
            "Perfil": ROLE_LABELS[item.profile.value],
            "Status": "Ativo" if item.is_active else "Inativo",
        }
        for item in users
    ])


def _invitation_codes(actor: User) -> None:
    runtime = get_streamlit_runtime()
    st.subheader("Codigo institucional")
    status = runtime.invite_codes.status_for(actor)
    st.caption("Codigo ativo" if status.active else "Nenhum codigo ativo")
    if status.created_at:
        st.caption(f"Criado em {status.created_at.astimezone().strftime('%d/%m/%Y %H:%M')}")
    state_key = f"new_invitation_code:{actor.institution_id}"
    if st.button("Gerar / substituir codigo", icon=":material/key:", key="rotate_institution_code"):
        code, _ = runtime.invite_codes.issue_or_replace(actor)
        st.session_state[state_key] = code
    if st.session_state.get(state_key):
        st.code(st.session_state[state_key], language=None)
        st.caption("O valor completo aparece somente nesta sessao. Compartilhe apenas com membros autorizados.")


def _enrollments(actor: User) -> None:
    runtime = get_streamlit_runtime()
    service = runtime.enrollment_management
    st.subheader("Matriculas autorizadas")
    with st.form("manual_enrollment", clear_on_submit=True):
        col_ra, col_name, col_email = st.columns(3)
        ra = col_ra.text_input("Matricula / RA *")
        name = col_name.text_input("Nome (opcional)")
        email = col_email.text_input("E-mail (opcional)")
        submitted = st.form_submit_button("Adicionar matricula", type="primary")
    if submitted:
        try:
            service.add_manual(actor, ra, name or None, email or None)
        except (DuplicateResource, DomainAuthorizationError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.success("Matricula adicionada.")

    upload = st.file_uploader(
        "Importar Excel (.xlsx)", type=["xlsx"], max_upload_size=10,
        key="authorized_enrollment_excel",
        help="A planilha precisa de uma coluna Matricula ou RA; nome e e-mail sao opcionais.",
    )
    if upload and st.button("Analisar planilha", key="preview_enrollment_import"):
        try:
            preview = service.preview_import(actor, upload.getvalue())
        except (DomainAuthorizationError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.session_state.enrollment_preview = preview
            st.session_state.enrollment_preview_institution = actor.institution_id

    preview = st.session_state.get("enrollment_preview")
    if preview and st.session_state.get("enrollment_preview_institution") == actor.institution_id:
        st.markdown(
            f"**Resumo:** {len(preview.valid)} validas | {len(preview.duplicates)} duplicadas | {len(preview.invalid)} invalidas"
        )
        for title, rows in (("Validas", preview.valid), ("Duplicadas", preview.duplicates), ("Invalidas", preview.invalid)):
            if rows:
                st.caption(title)
                st.dataframe(pd.DataFrame([
                    {
                        "Linha": row.row_number,
                        "Matricula": row.registration_number or "-",
                        "Nome": row.name or "-",
                        "E-mail": row.email or "-",
                        "Motivo": row.reason or "-",
                    }
                    for row in rows
                ]), hide_index=True, width="stretch")
        if st.button(
            f"Confirmar importacao de {len(preview.valid)} matricula(s)",
            type="primary", disabled=not preview.valid, key="confirm_enrollment_import",
        ):
            try:
                inserted = service.confirm_import(actor, preview.preview_id)
            except (DomainAuthorizationError, DuplicateResource, ResourceNotFound) as exc:
                st.error(str(exc))
            else:
                st.session_state.pop("enrollment_preview", None)
                st.session_state.pop("enrollment_preview_institution", None)
                st.success(f"{inserted} matricula(s) importada(s).")
                st.rerun()

    st.divider()
    search_col, status_col = st.columns([3, 1])
    query = search_col.text_input("Pesquisar matriculas", key="enrollment_search")
    status_label = status_col.selectbox(
        "Situacao", ["Todas", "Disponivel", "Vinculada", "Desativada"],
        key="enrollment_status_filter",
    )
    status_filter = {
        "Disponivel": EnrollmentStatus.ACTIVE,
        "Vinculada": EnrollmentStatus.USED,
        "Desativada": EnrollmentStatus.INACTIVE,
    }.get(status_label)
    results = service.list_enrollments(actor, query, status_filter)
    if results:
        st.dataframe(pd.DataFrame([
            {
                "Matricula": item.registration_number,
                "Nome": item.name or "-",
                "E-mail": item.email or "-",
                "Situacao": {
                    EnrollmentStatus.ACTIVE: "Disponivel",
                    EnrollmentStatus.INACTIVE: "Desativada",
                    EnrollmentStatus.USED: "Vinculada",
                }[item.status],
            }
            for item in results
        ]), hide_index=True, width="stretch")
        available = [item for item in results if item.is_available]
        if available:
            choices = {f"{item.registration_number} — {item.name or 'sem nome'}": item.id for item in available}
            selected = st.selectbox("Desativar matricula ainda disponivel", list(choices), key="enrollment_deactivate_select")
            if st.button("Desativar matricula", key="deactivate_enrollment"):
                service.deactivate(actor, choices[selected])
                st.rerun()
    else:
        st.info("Nenhuma matricula encontrada.")


def users_page(user):
    runtime = get_streamlit_runtime()
    actor = get_streamlit_actor(user)
    if actor is None or actor.profile is not Profile.ADMIN:
        st.error("Acesso nao autorizado.")
        return

    page_header("Usuarios", "Gerencie usuarios, codigos institucionais e matriculas da sua instituicao.")
    users_tab, access_tab = st.tabs(["Usuarios", "Codigos e matriculas"])
    with users_tab:
        search_col, profile_col = st.columns([3, 1])
        query = search_col.text_input("Buscar por nome ou e-mail", key="users_search")
        profile_labels = ["Todos os perfis", *ROLE_LABELS.values()]
        selected_profile = profile_col.selectbox("Perfil", profile_labels, key="users_role_filter")
        try:
            users = runtime.user_management.list_users(actor, query=query)
        except DomainAuthorizationError as exc:
            st.error(str(exc))
            return
        users = [item for item in users if selected_profile == "Todos os perfis" or ROLE_LABELS[item.profile.value] == selected_profile]
        if users:
            st.dataframe(_user_table(users), hide_index=True, width="stretch")
            choices = {f"{item.name} ({item.email})": item for item in users}
            selected = st.selectbox("Usuario", list(choices), key="managed_user_select")
            selected_user = choices[selected]
            edit_col, status_col = st.columns(2)
            if edit_col.button("Editar perfil", width="stretch"):
                _user_dialog(actor, selected_user)
            label = "Desativar" if selected_user.is_active else "Ativar"
            next_status = UserStatus.INACTIVE if selected_user.is_active else UserStatus.ACTIVE
            if status_col.button(label, width="stretch"):
                try:
                    runtime.user_management.set_status(actor, selected_user.id, next_status)
                except (DomainAuthorizationError, LastActiveAdministrator, ResourceNotFound) as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
        else:
            st.info("Nenhum usuario encontrado.")
        if st.button("Novo usuario", type="primary", icon=":material/person_add:"):
            _user_dialog(actor)

    with access_tab:
        _invitation_codes(actor)
        st.divider()
        _enrollments(actor)
