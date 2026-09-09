"""Valida credenciais dos usuários de demonstração."""

from data.mock_data import password_hash


def authenticate(state, email, password):
    email = email.strip().lower()

    if not email or not password:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."

    user = next((item for item in state["users"] if item["email"].lower() == email), None)
    if not user:
        return None, "Não encontramos uma conta com esses dados. Confirme seu cadastro com a instituição."
    if user.get("password_hash") != password_hash(password):
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."
    if user["status"] != "ativo":
        return None, "Esta conta está inativa. Entre em contato com a instituição."

    session_user = {key: value for key, value in user.items() if key != "password_hash"}
    return session_user, ""

