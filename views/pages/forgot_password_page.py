import streamlit as st

from services.app_state_service import go


def forgot_password():
    st.html('<div class="rf-section">')
    st.title("Recuperar senha")
    st.write("Informe seu e-mail institucional para receber orientacoes de acesso.")
    email = st.text_input("E-mail")
    if st.button("Enviar instrucoes", type="primary"):
        st.success(f"Se {email or 'este e-mail'} estiver cadastrado, as instrucoes serao enviadas.")
    if st.button("Voltar para login"):
        go("login")
    st.html("</div>")
