import streamlit as st

from services.app_state_service import go


def signup_choice():
    st.html("""
        <div class="rf-auth-page">

            <header class="rf-auth-topbar">

                <button
                    type="button"
                    class="rf-auth-back"
                    onclick="this.closest('form')?.submit()"
                >
                    <span class="rf-auth-back-icon">←</span>
                    <span>Voltar</span>
                </button>

                <div class="rf-auth-logo">
                    <div class="rf-logo-mark">R</div>
                    <span>RoomFlow</span>
                </div>

            </header>

            <main class="rf-auth-content">

                <div class="rf-auth-container">

                    <div class="rf-auth-header">

                        <p class="rf-auth-eyebrow">
                            Bem-vindo ao RoomFlow
                        </p>

                        <h1>Criar sua conta</h1>

                        <p class="rf-auth-description">
                            Escolha como você deseja utilizar o RoomFlow.
                        </p>

                    </div>

                    <div class="rf-signup-options">

                        <div class="rf-signup-card">
                            <div class="rf-signup-card-icon">
                                <span>▣</span>
                            </div>

                            <h2>
                                Sou responsável pela instituição
                            </h2>

                            <p>
                                Cadastre sua instituição no RoomFlow e
                                torne-se responsável pela administração
                                da plataforma.
                            </p>

                            <div class="rf-signup-card-action">
                                <span>Cadastrar instituição</span>
                                <span>→</span>
                            </div>
                        </div>

                        <div class="rf-signup-card">
                            <div class="rf-signup-card-icon">
                                <span>♙</span>
                            </div>

                            <h2>
                                Sou membro da instituição
                            </h2>

                            <p>
                                Já faço parte de uma instituição cadastrada
                                e quero criar minha conta para utilizar
                                o RoomFlow.
                            </p>

                            <div class="rf-signup-card-action">
                                <span>Criar conta</span>
                                <span>→</span>
                            </div>
                        </div>

                    </div>

                    <div class="rf-auth-login-link">
                        <span>Já possui uma conta?</span>
                    </div>

                </div>

            </main>

        </div>
    """)

    # Navegação real do Streamlit
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(
            "Cadastrar instituição",
            key="signup_institution",
            use_container_width=True,
        ):
            go("signup_institution")

    with col2:
        if st.button(
            "Criar conta",
            key="signup_member",
            use_container_width=True,
        ):
            go("signup_member")

    if st.button(
        "Entrar",
        key="signup_login",
    ):
        go("login")

    if st.button(
        "Voltar",
        key="signup_back",
    ):
        go("landing")