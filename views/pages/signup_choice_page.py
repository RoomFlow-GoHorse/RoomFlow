import streamlit as st
from services.app_state_service import go

def signup_choice():
    # 1. CSS Exclusivo da Rota de Seleção de Cadastro (signup_choice)
    st.html(
        """
        <style>
            /* Restringe o container principal do Streamlit a exatamente 800px no centro */
            [data-testid="stMainBlockContainer"] {
                max-width: 800px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding: 32px 24px !important;
            }

            .stApp {
                background-color: #F7F7F9 !important;
            }

            /* Estilo dos Cards do Figma */
            .rf-choice-card-content {
                background-color: #FFFFFF;
                border: 2px solid #E4E4E7;
                border-radius: 16px;
                padding: 28px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                transition: all 0.2s ease;
                min-height: 180px;
                box-sizing: border-box;
                margin-bottom: 16px;
            }

            .rf-choice-card-content:hover {
                border-color: var(--brand, #6D28D9);
                box-shadow: 0 10px 25px -5px rgba(109, 40, 217, 0.1);
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
                color: #171717;
                margin: 0 0 8px 0;
            }

            .rf-choice-card-content p {
                font-size: 14px;
                color: #737373;
                line-height: 1.6;
                margin: 0;
            }

            /* 
               Mapeamento preciso do nó de botão do BaseWeb renderizado pelo Streamlit
            */
            [data-testid="stMainBlockContainer"] button,
            [data-testid="stMainBlockContainer"] [data-testid="stBaseButton-secondary"],
            [data-testid="stMainBlockContainer"] [data-testid="stBaseButton-tertiary"],
            [data-testid="stMainBlockContainer"] [data-baseweb="button"] {
                background: transparent !important;
                background-color: transparent !important;
                border: none !important;
                border-style: none !important;
                border-width: 0 !important;
                box-shadow: none !important;
                outline: none !important;
                color: var(--brand, #6D28D9) !important;
                font-weight: 600 !important;
                font-size: 14px !important;
                padding: 0 !important;
                margin: 0 !important;
                height: auto !important;
                min-height: initial !important;
                width: auto !important;
                cursor: pointer !important;
                display: inline-flex !important;
                align-items: center !important;
                gap: 4px !important;
                transition: color 0.2s ease !important;
            }

            [data-testid="stMainBlockContainer"] button:hover,
            [data-testid="stMainBlockContainer"] [data-testid="stBaseButton-secondary"]:hover,
            [data-testid="stMainBlockContainer"] [data-testid="stBaseButton-tertiary"]:hover,
            [data-testid="stMainBlockContainer"] [data-baseweb="button"]:hover {
                color: var(--brand-hover, #5B21B6) !important;
                background: transparent !important;
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }

            /* Botão Voltar Topbar */
            .rf-choice-topbar button,
            .rf-choice-topbar [data-baseweb="button"] {
                color: #737373 !important;
                font-weight: 500 !important;
            }

            .rf-choice-topbar button:hover,
            .rf-choice-topbar [data-baseweb="button"]:hover {
                color: var(--brand, #6D28D9) !important;
            }

            /* Footer Login alinhado horizontalmente */
            .rf-choice-footer {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                margin-top: 36px;
                font-size: 14px;
                color: #737373;
            }
        </style>
        """
    )

    # 2. TOPBAR (Alinhada dentro do container de 800px)
    col_tb1, col_tb2 = st.columns([1, 1])
    with col_tb1:
        st.markdown('<div class="rf-choice-topbar">', unsafe_allow_html=True)
        if st.button("← Voltar", key="choice_top_back", type="tertiary"):
            go("landing")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_tb2:
        st.markdown(
            """
            <div style="display: flex; justify-content: flex-end; align-items: center; gap: 8px; font-weight: 700;">
                <div class="rf-logo-mark" style="width:28px; height:28px; font-size:14px; border-radius:8px; background-color:var(--brand, #6D28D9); color:white; display:flex; align-items:center; justify-content:center;">R</div>
                <span style="font-size: 16px; color: #171717;">RoomFlow</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. HEADER CENTRALIZADO
    st.markdown(
        """
        <div style="text-align: center; margin-top: 16px; margin-bottom: 28px;">
            <p style="color: var(--brand, #6D28D9); font-size: 12px; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; margin-bottom: 8px;">Bem-vindo ao RoomFlow</p>
            <h1 style="font-size: 30px; font-weight: 600; color: #171717; margin: 0 0 8px 0;">Criar sua conta</h1>
            <p style="font-size: 14px; color: #737373; margin: 0;">Escolha como você deseja utilizar o RoomFlow.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4. CARDS E LINKS ROXOS
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
            <div class="rf-choice-card-content">
                <div>
                    <div class="rf-card-icon">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect>
                            <path d="M9 22v-4h6v4"></path>
                            <path d="M8 6h.01"></path>
                            <path d="M16 6h.01"></path>
                            <path d="M12 6h.01"></path>
                            <path d="M12 10h.01"></path>
                            <path d="M12 14h.01"></path>
                            <path d="M16 10h.01"></path>
                            <path d="M16 14h.01"></path>
                            <path d="M8 10h.01"></path>
                            <path d="M8 14h.01"></path>
                        </svg>
                    </div>
                    <h2>Sou responsável pela instituição</h2>
                    <p>Cadastre sua instituição no RoomFlow e torne-se responsável pela administração da plataforma.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="rf-choice-action-btn">', unsafe_allow_html=True)
        if st.button("Cadastrar instituição →", key="btn_choice_inst"):
            go("signup_institution")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown(
            """
            <div class="rf-choice-card-content">
                <div>
                    <div class="rf-card-icon">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                            <circle cx="9" cy="7" r="4"></circle>
                            <path d="M23 21v-2a4 4 0 0 1 0 7.75"></path>
                            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                        </svg>
                    </div>
                    <h2>Sou membro da instituição</h2>
                    <p>Já faço parte de uma instituição cadastrada e quero criar minha conta para utilizar o RoomFlow.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="rf-choice-action-btn">', unsafe_allow_html=True)
        if st.button("Criar conta →", key="btn_choice_member"):
            go("signup_member")
        st.markdown('</div>', unsafe_allow_html=True)

    # 5. FOOTER LOGIN ALINHADO HORIZONTALMENTE
    st.markdown('<div class="rf-choice-footer"><span>Já possui uma conta?</span>', unsafe_allow_html=True)
    if st.button("Entrar", key="choice_goto_login", type="tertiary"):
        go("login")
    st.markdown('</div>', unsafe_allow_html=True)