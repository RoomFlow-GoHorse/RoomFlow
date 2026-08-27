import time

import streamlit as st

from services import mock_data_service
from services.app_state_service import go, set_toast


def signup_choice():
    st.html('<div class="rf-section">')
    st.caption("CADASTRO")
    st.title("Criar sua conta")
    col1, col2 = st.columns(2)
    with col1:
        st.html('<div class="rf-card"><h3>Sou responsavel pela instituicao</h3><p>Crie a instituicao e acesse como Administrador.</p></div>')
        if st.button("Cadastrar instituicao", type="primary"):
            go("signup_institution")
    with col2:
        st.html('<div class="rf-card"><h3>Sou membro da instituicao</h3><p>Entre vinculado a uma instituicao ja cadastrada.</p></div>')
        if st.button("Cadastrar membro"):
            go("signup_member")
    if st.button("Voltar"):
        go("landing")
    st.html("</div>")


def signup_institution():
    st.html('<div class="rf-section">')
    st.title("Cadastro da instituicao")
    with st.form("institution"):
        st.subheader("Dados do responsavel")
        name = st.text_input("Nome completo")
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        st.subheader("Dados da instituicao")
        inst = st.text_input("Nome da instituicao")
        cnpj = st.text_input("CNPJ")
        kind = st.selectbox("Tipo", ["Faculdade", "Universidade", "Centro Universitario", "Instituto", "Escola", "Outra"])
        submitted = st.form_submit_button("Criar instituicao", type="primary")
    if submitted:
        if not all([name, email, password, inst, cnpj, kind]):
            st.error("Preencha os campos obrigatorios.")
        else:
            with st.spinner("Verificando dados da instituicao..."):
                time.sleep(.8)
            set_toast("Instituicao cadastrada. Acesse pelo login.")
            go("login")
    if st.button("Voltar"):
        go("signup_choice")
    st.html("</div>")


def signup_member():
    st.html('<div class="rf-section">')
    st.title("Cadastro de membro")
    with st.form("member"):
        name = st.text_input("Nome")
        email = st.text_input("E-mail institucional")
        ra = st.text_input("RA/Matricula")
        institution = st.selectbox("Instituicao", mock_data_service.institutions())
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Criar conta", type="primary")
    if submitted:
        if ra.upper().startswith("ERR"):
            st.error("Nao foi possivel validar seu vinculo. Contate a instituicao.")
        elif all([name, email, ra, institution, password]):
            set_toast("Conta criada. Aguarde liberacao da instituicao.")
            go("login")
        else:
            st.error("Preencha os campos obrigatorios.")
    if st.button("Voltar"):
        go("signup_choice")
    st.html("</div>")
