import streamlit as st

from services.app_state_service import go
from views.components.ui_components import logo


def signup_choice():
    st.html(
        """
        <style>
            .stApp {
                background-color: #F7F7F9 !important;
            }

            [data-testid="stMainBlockContainer"] {
                width: 100% !important;
                max-width: 820px !important;
                min-height: 100vh !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding: 32px 24px 40px !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: center !important;
            }

            [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
                width: 100% !important;
                min-height: calc(100vh - 72px) !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: center !important;
            }

            [data-testid="stMainBlockContainer"] .st-key-signup_choice_card {
                width: 100% !important;
                height: auto !important;
                min-height: 0 !important;
                flex: 0 0 auto !important;
                background-color: transparent !important;
                border: none !important;
                border-radius: 0 !important;
                padding: 0 !important;
                box-shadow: none !important;
            }

            [data-testid="stMainBlockContainer"] .st-key-signup_choice_card [data-testid="stVerticalBlock"] {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
            }

            .rf-choice-logo {
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 8px;
                font-weight: 700;
            }

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

            .rf-choice-header {
                text-align: center;
                margin-top: 16px;
                margin-bottom: 64px;
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

            .rf-choice-footer {
                text-align: center;
                margin-top: 38px;
                font-size: 14px;
                color: #737373;
            }

            .rf-choice-login-link {
                margin: 38px 0 0 0;
                color: #737373;
                font-size: 14px;
                text-align: center;
                padding-top: 15px;
            }

            .rf-choice-login-link a {
                color: #6D28D9;
                font-weight: 700;
                text-decoration: none;
            }

            .rf-choice-login-link a:hover {
                color: #4C1D95;
            }

            @media (max-width: 768px) {
                [data-testid="stMainBlockContainer"] {
                    max-width: none !important;
                    padding: 40px 18px !important;
                    justify-content: flex-start !important;
                }

                [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
                    min-height: auto !important;
                    justify-content: flex-start !important;
                }

                [data-testid="stMainBlockContainer"] .st-key-signup_choice_card {
                    padding: 0 !important;
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

    with st.container(key="signup_choice_card"):
        col_tb1, col_tb2 = st.columns([1, 1], vertical_alignment="center")

        with col_tb1:
            if st.button("← Voltar", key="signup_choice_top_back", type="tertiary"):
                go("landing")

        with col_tb2:
            st.html(logo(size="small", class_name="rf-choice-logo"))

        st.markdown(
            '<div class="rf-choice-header"><p class="rf-choice-eyebrow">Bem-vindo ao RoomFlow</p><h1 class="rf-choice-title">Criar sua conta</h1><p class="rf-choice-subtitle">Escolha como você deseja utilizar o RoomFlow.</p></div>',
            unsafe_allow_html=True,
        )

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

        st.markdown(
            '<p class="rf-choice-login-link">Já possui uma conta? <a href="?page=login" target="_self">Entrar</a></p>',
            unsafe_allow_html=True,
        )
