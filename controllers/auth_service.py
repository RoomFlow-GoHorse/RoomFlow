
import streamlit as st

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from config.database import SessionLocal
from models.database_models import User
from controllers.password_service import verify_password


def login(email, password):
    email = (email or "").strip().lower()

    if not email or not password:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."

    try:
        with SessionLocal() as session:
            user = session.scalar(select(User).where(User.email == email))

            if not user:
                return None, "Não encontramos uma conta com esses dados. Confirme seu cadastro com a instituição."

            if not verify_password(password, user.password_hash):
                return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."

            if user.status != "ativo":
                return None, "Esta conta está inativa. Entre em contato com a instituição."

            session_user = {
                "id": f"u{user.id}",
                "database_id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "status": user.status,
                "tipo_usuario_id": user.tipo_usuario_id,
            }

        st.session_state.user = session_user
        return session_user, ""

    except SQLAlchemyError:
        return None, "Não foi possível acessar o banco de dados. Tente novamente mais tarde."


def logout():
    st.session_state.user = None
    st.session_state.page = "landing"
    st.query_params.clear()
    st.query_params["page"] = "landing"
    st.rerun()
