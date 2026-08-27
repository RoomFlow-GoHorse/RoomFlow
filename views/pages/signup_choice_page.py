import streamlit as st
from services.app_state_service import go


def signup_choice():
    # ==========================================================
    # 1. CSS EXCLUSIVO DA ROTA DE SELEÇÃO DE CADASTRO
    # ==========================================================
    st.html(
        """
        <style>
            /* Ajuste preciso de padding-top para o topo não ser cortado pela barra de ferramentas fixa do Streamlit */
            [data-testid="stMainBlockContainer"] {
                max-width: 800px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-top: 80px !important;
                padding-bottom: 32px !important;
                padding-left: 24px !important;
                padding-right: 24px !important;
            }

            .stApp {
                background-color: #F7F7F9 !important;
            }

            /* TOPBAR */
            .rf-choice-logo {
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 8px;
                font-weight: 700;
            }

            .rf-logo-mark {
                width: 28px;
                height: 28px;
                border-radius: 8px;
                background-color: var(--brand, #6D28D9);
                color: #FFFFFF;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                font-weight: 700;
            }

            .rf-logo-text {
                font-size: 16px;
                font-weight: 700;
                color: #171717;
            }

            /* BOTÕES STREAMLIT ESTILIZADOS COMO LINKS ROXOS */
            [data-testid="stMainBlockContainer"] .stButton > button {
                background: transparent !important;
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
                outline: none !important;
                color: var(--brand, #6D28D9) !important;
                font-size: 14px !important;
                font-weight: 600 !important;
                padding: 4px 0 !important;
                height: auto !important;
                min-height: 30px !important;
                width: auto !important;
                cursor: pointer !important;
                transition: color 0.2s ease, opacity 0.2s ease !important;
            }

            [data-testid="stMainBlockContainer"] .stButton > button:hover {
                color: var(--brand-hover, #5B21B6) !important;
                background: transparent !important;
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
                opacity: 0.9;
            }

            /* HEADER */
            .rf-choice-header {
                text-align: center;
                margin-top: 16px;
                margin-bottom: 28px;
            }

            .rf-choice-eyebrow {
                color: var(--brand, #6D28D9);
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.18em;
                text-transform: uppercase;
                margin-bottom: 8px;
            }

            .rf-choice-title {
                font-size: 30px;
                font-weight: 600;
                color: #171717;
                margin: 0 0 8px 0;
            }

            .rf-choice-subtitle {
                font-size: 14px;
                color: #737373;
                margin: 0;
            }

            /* CARDS */
            .rf-choice-card-content {
                background-color: #FFFFFF;
                border: 2px solid #E4E4E7;
                border-radius: 16px;
                padding: 28px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
                transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
                min-height: 220px;
                box-sizing: border-box;
                margin-bottom: 8px;
            }

            .rf-choice-card-content:hover {
                box-shadow: 0 10px 25px -5px rgba(109, 40, 217, 0.12);
                transform: translateY(-2px);
            }

            .rf-card-icon {
                width: 44px;
                height: 44px;
                border-radius: 12px;
                background-color: var(--brand-lighter, #F5F3FF);
                color: var(--brand, #6D28D9);
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 20px;
            }

            .rf-choice-card-content h2 {
                font-size: 16px;
                font-weight: 600;
                line-height: 1.4;
                color: #171717;
                margin: 0 0 8px 0;
            }

            .rf-choice-card-content p {
                font-size: 14px;
                color: #737373;
                line-height: 1.6;
                margin: 0;
            }

            /* RESPONSIVIDADE */
            @media (max-width: 768px) {
                [data-testid="stMainBlockContainer"] {
                    padding-top: 64px !important;
                    padding-left: 18px !important;
                    padding-right: 18px !important;
                }

                .rf-choice-title {
                    font-size: 26px;
                }

                .rf-choice-card-content {
                    min-height: auto;
                }
            }
        </style>
        """
    )

    # ==========================================================
    # 2. TOPBAR
    # ==========================================================
    col_tb1, col_tb2 = st.columns([1, 1], vertical_alignment="center")

    with col_tb1:
        if st.button("← Voltar", key="signup_choice_top_back", type="tertiary"):
            go("landing")

    with col_tb2:
        st.markdown(
            '<div class="rf-choice-logo"><div class="rf-logo-mark">R</div><span class="rf-logo-text">RoomFlow</span></div>',
            unsafe_allow_html=True,
        )

    # ==========================================================
    # 3. HEADER CENTRALIZADO
    # ==========================================================
    st.markdown(
        '<div class="rf-choice-header"><p class="rf-choice-eyebrow">Bem-vindo ao RoomFlow</p><h1 class="rf-choice-title">Criar sua conta</h1><p class="rf-choice-subtitle">Escolha como você deseja utilizar o RoomFlow.</p></div>',
        unsafe_allow_html=True,
    )

    # ==========================================================
    # 4. CARDS DE ESCOLHA
    # ==========================================================
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown(
            '<div class="rf-choice-card-content"><div><div class="rf-card-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><path d="M9 22v-4h6v4"></path><path d="M8 6h.01"></path><path d="M12 6h.01"></path><path d="M16 6h.01"></path><path d="M8 10h.01"></path><path d="M12 10h.01"></path><path d="M16 10h.01"></path><path d="M8 14h.01"></path><path d="M12 14h.01"></path><path d="M16 14h.01"></path></svg></div><h2>Sou responsável pela instituição</h2><p>Cadastre sua instituição no RoomFlow e torne-se responsável pela administração da plataforma.</p></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Cadastrar instituição →", key="signup_choice_institution", type="tertiary"):
            go("signup_institution")

    with c2:
        st.markdown(
            '<div class="rf-choice-card-content"><div><div class="rf-card-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg></div><h2>Sou membro da instituição</h2><p>Já faço parte de uma instituição cadastrada e quero criar minha conta para utilizar o RoomFlow.</p></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Criar conta →", key="signup_choice_member", type="tertiary"):
            go("signup_member")

    # ==========================================================
    # 5. RODAPÉ
    # ==========================================================
    st.markdown('<div style="text-align: center; margin-top: 38px; font-size: 14px; color: #737373;">Já possui uma conta?</div>', unsafe_allow_html=True)

    footer_left, footer_center, footer_right = st.columns([2, 1, 2])

    with footer_center:
        if st.button("Entrar", key="signup_choice_login", type="tertiary", use_container_width=True):
            go("login")