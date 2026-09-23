import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import boot_state
from views.components.ui_components import badge, esc, page_header


# =========================================================
# ESTILOS DA PÁGINA
# =========================================================

def _render_styles():
    st.html(
        """
        <style>
            .st-key-rf_find_map_card,
            .st-key-rf_find_details_card,
            .st-key-rf_find_directions_card {
                background: var(--surface-card) !important;
                border: 1px solid var(--stroke) !important;
                border-radius: 14px !important;
                padding: 0 !important;
                overflow: hidden !important;
            }

            .rf-map-canvas {
                position: relative;
                min-height: 480px;
                background: var(--surface-alt);
                border-bottom: 1px solid var(--stroke);
                padding: 24px;
            }

            .rf-map-grid-bg {
                position: absolute;
                inset: 0;
                opacity: 0.4;
                pointer-events: none;
                background-image: linear-gradient(var(--stroke-strong) 1px, transparent 1px), linear-gradient(90deg, var(--stroke-strong) 1px, transparent 1px);
                background-size: 32px 32px;
            }

            .rf-legend-bar {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 16px;
                padding: 12px 20px;
                background: var(--surface-card);
                font-size: 11px;
                color: var(--graphite-muted);
            }

            .rf-legend-item {
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .rf-legend-dot {
                width: 12px;
                height: 12px;
                border-radius: 3px;
                border: 1px solid;
            }
        </style>
        """
    )


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def localizar(user: dict):
    boot_state()
    _render_styles()

    b_list = mock_data_service.buildings()
    buildings = [b["name"] for b in b_list] if b_list else ["Bloco A"]

    st.session_state.setdefault("find_search", "")
    if "find_building" not in st.session_state or st.session_state.find_building not in buildings:
        st.session_state.find_building = buildings[0]

    curr_b_item = next((b for b in b_list if b["name"] == st.session_state.find_building), None)
    f_list = mock_data_service.floors(curr_b_item["id"] if curr_b_item else None)
    floors_list = [f["name"] for f in f_list] if f_list else ["Térreo"]

    if "find_floor" not in st.session_state or st.session_state.find_floor not in floors_list:
        st.session_state.find_floor = floors_list[0]

    st.session_state.setdefault("find_selected_space_id", None)
    st.session_state.setdefault("find_show_directions", False)

    all_spaces = mock_data_service.spaces()

    # 1. Cabeçalho
    page_header(
        "Localizar espaço",
        "Encontre uma sala no mapa e veja como chegar até ela.",
    )

    # 2. Barra de busca e localização
    col_search, col_action = st.columns([4, 1], vertical_alignment="center")

    with col_search:
        search_val = st.text_input(
            "Buscar sala, auditório, laboratório ou prédio...",
            key="find_search_input",
            value=st.session_state.find_search,
            placeholder="Buscar sala, auditório, laboratório ou prédio...",
            label_visibility="collapsed",
        )
        st.session_state.find_search = search_val

    with col_action:
        if st.button("📍 Minha localização", key="btn_my_location", type="secondary"):
            st.session_state.find_building = buildings[0]
            st.session_state.find_floor = floors_list[0]
            st.session_state.find_search = ""
            st.rerun()

    # 3. Resultados da Busca (se houver busca digitada)
    search_query = st.session_state.find_search.strip().lower()
    if search_query:
        filtered = [
            sp for sp in all_spaces
            if search_query in sp["name"].lower()
            or search_query in sp.get("building", "").lower()
            or search_query in sp.get("location", "").lower()
        ]

        st.html(
            f"""
            <div style="background:var(--surface-card); border:1px solid var(--stroke); border-radius:12px; padding:16px; margin-bottom:20px;">
                <p style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--graphite-muted); margin:0 0 12px 0;">
                    Resultados encontrados ({len(filtered)})
                </p>
            """
        )

        if not filtered:
            st.html(
                """
                <div style="text-align:center; padding:16px 0; color:var(--graphite-muted); font-size:13px;">
                    📍 Nenhum espaço encontrado para a busca realizada.
                </div>
                """
            )
        else:
            for sp in filtered:
                col_sp_info, col_sp_btn = st.columns([4, 1], vertical_alignment="center")
                with col_sp_info:
                    st.html(
                        f"""
                        <div style="margin-bottom:8px;">
                            <p style="font-size:14px; font-weight:600; color:var(--graphite); margin:0;">{esc(sp['name'])}</p>
                            <p style="font-size:12px; color:var(--graphite-muted); margin:2px 0 0 0;">{esc(sp.get('building', ''))} &middot; {esc(sp.get('floor', ''))} &middot; {esc(sp.get('location', ''))}</p>
                        </div>
                        """
                    )
                with col_sp_btn:
                    if st.button(f"Selecionar {sp['name']}", key=f"btn_select_search_{sp['id']}"):
                        st.session_state.find_building = sp.get("building", buildings[0])
                        st.session_state.find_floor = sp.get("floor", floors_list[0])
                        st.session_state.find_selected_space_id = sp["id"]
                        st.session_state.find_show_directions = False
                        st.session_state.find_search = ""
                        st.rerun()

        st.html("</div>")

    # 4. Controles do Mapa (Prédio + Andar)
    col_ctrl_left, col_ctrl_right = st.columns([2, 3], vertical_alignment="center")

    with col_ctrl_left:
        st.html(
            f"""
            <div>
                <p style="font-size:11px; font-weight:500; color:var(--graphite-muted); margin:0 0 2px 0;">Localização atual</p>
                <h3 style="font-size:16px; font-weight:600; color:var(--graphite); margin:0;">
                    🏢 {esc(st.session_state.find_building)} &middot; {esc(st.session_state.find_floor)}
                </h3>
            </div>
            """
        )

    with col_ctrl_right:
        c_bld, c_flr = st.columns([1, 2], vertical_alignment="center")

        with c_bld:
            sel_bld_idx = buildings.index(st.session_state.find_building) if st.session_state.find_building in buildings else 0
            sel_bld = st.selectbox(
                "Prédio",
                buildings,
                index=sel_bld_idx,
                key="find_building_select",
                label_visibility="collapsed",
            )
            if sel_bld != st.session_state.find_building:
                st.session_state.find_building = sel_bld
                new_b_item = next((b for b in b_list if b["name"] == sel_bld), None)
                new_floors = [f["name"] for f in mock_data_service.floors(new_b_item["id"] if new_b_item else None)]
                st.session_state.find_floor = new_floors[0] if new_floors else "Térreo"
                st.session_state.find_selected_space_id = None
                st.session_state.find_show_directions = False
                st.rerun()

        with c_flr:
            sel_flr = st.segmented_control(
                "Andar",
                floors_list,
                key="find_floor_control",
                default=st.session_state.find_floor if st.session_state.find_floor in floors_list else floors_list[0],
            )
            if sel_flr and sel_flr != st.session_state.find_floor:
                st.session_state.find_floor = sel_flr
                st.session_state.find_selected_space_id = None
                st.session_state.find_show_directions = False
                st.rerun()

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # Obter salas do andar selecionado
    curr_bld = st.session_state.find_building
    curr_flr = st.session_state.find_floor
    floor_spaces = mock_data_service.spaces(building=curr_bld, floor=curr_flr)

    # Obter sala selecionada no estado
    selected_space = next(
        (sp for sp in all_spaces if sp["id"] == st.session_state.find_selected_space_id),
        None,
    )

    # 5. Grid Principal (Mapa do Andar + Painel Lateral)
    col_map, col_side = st.columns([3, 2], gap="medium")

    # =====================================================
    # MAPA DO ANDAR (COLUNA ESQUERDA)
    # =====================================================
    with col_map:
        with st.container(key="rf_find_map_card"):
            # Header do mapa
            st.html(
                f"""
                <div style="padding:14px 20px; border-bottom:1px solid #E4E1DB; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <p style="font-size:14px; font-weight:600; color:#1C1C2E; margin:0;">Mapa do andar</p>
                        <p style="font-size:12px; color:#71717A; margin:2px 0 0 0;">Clique em uma sala para visualizar os detalhes</p>
                    </div>
                    <span style="padding:3px 10px; border-radius:999px; background:#F0EEE9; color:#52525B; font-size:11px; font-weight:600;">
                        {len(floor_spaces)} espaços
                    </span>
                </div>
                """
            )

            # Área interativa do Mapa
            st.html(
                """
                <div class="rf-map-canvas">
                    <div class="rf-map-grid-bg"></div>
                    <div style="position:absolute; bottom:16px; left:16px; font-size:11px; color:#71717A; background:#FFFFFF; padding:6px 12px; border-radius:8px; border:1px solid #E4E1DB;">
                        🚪 Acesso Principal (Entrada)
                    </div>
                    <div style="position:absolute; bottom:16px; right:16px; font-size:11px; color:#71717A; background:#FFFFFF; padding:6px 12px; border-radius:8px; border:1px solid #E4E1DB;">
                        🛗 Elevador / Escadas
                    </div>
                """
            )

            # Se existirem salas no andar
            if not floor_spaces:
                st.html(
                    """
                    <div style="min-height:280px; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:40px;">
                        <span style="font-size:28px;">📍</span>
                        <p style="font-size:14px; font-weight:600; color:#1C1C2E; margin:8px 0 2px 0;">Nenhum espaço neste andar</p>
                        <p style="font-size:12px; color:#71717A; margin:0;">Selecione outro andar para visualizar as salas.</p>
                    </div>
                    """
                )
            else:
                # Fileira Superior de Salas (até 3 salas)
                top_spaces = floor_spaces[:3]
                bottom_spaces = floor_spaces[3:6]

                cols_top = st.columns(3)
                for idx, sp in enumerate(top_spaces):
                    is_sel = selected_space and selected_space["id"] == sp["id"]
                    status_label = "Disponível" if sp["status"] == "disponivel" else ("Ocupado" if sp["status"] == "ocupado" else "Bloqueado")

                    with cols_top[idx]:
                        btn_type = "primary" if is_sel else "secondary"
                        if st.button(
                            f"📍 {sp['name']}\n{sp['capacity']} lugares ({status_label})",
                            key=f"map_btn_{sp['id']}",
                            use_container_width=True,
                            type=btn_type,
                        ):
                            st.session_state.find_selected_space_id = sp["id"]
                            st.session_state.find_show_directions = False
                            st.rerun()

                # Corredor Principal Central
                st.html(
                    """
                    <div style="margin:20px 0; padding:10px; background:#FFFFFF; border:1px solid #E4E1DB; border-radius:8px; text-align:center;">
                        <span style="font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.15em; color:#A1A1AA;">
                            Corredor Principal
                        </span>
                    </div>
                    """
                )

                # Fileira Inferior de Salas (até 3 salas)
                if bottom_spaces:
                    cols_bottom = st.columns(3)
                    for idx, sp in enumerate(bottom_spaces):
                        is_sel = selected_space and selected_space["id"] == sp["id"]
                        status_label = "Disponível" if sp["status"] == "disponivel" else ("Ocupado" if sp["status"] == "ocupado" else "Bloqueado")

                        with cols_bottom[idx]:
                            btn_type = "primary" if is_sel else "secondary"
                            if st.button(
                                f"📍 {sp['name']}\n{sp['capacity']} lugares ({status_label})",
                                key=f"map_btn_{sp['id']}",
                                use_container_width=True,
                                type=btn_type,
                            ):
                                st.session_state.find_selected_space_id = sp["id"]
                                st.session_state.find_show_directions = False
                                st.rerun()

            st.html("</div>")

            # Barra de Legenda do Mapa
            st.html(
                """
                <div class="rf-legend-bar">
                    <div class="rf-legend-item">
                        <div class="rf-legend-dot" style="background:#DCFCE7; border-color:#16A34A;"></div>
                        <span>Disponível</span>
                    </div>
                    <div class="rf-legend-item">
                        <div class="rf-legend-dot" style="background:#EDE9FE; border-color:#6D28D9;"></div>
                        <span>Ocupado</span>
                    </div>
                    <div class="rf-legend-item">
                        <div class="rf-legend-dot" style="background:#F4F4F5; border-color:#A1A1AA;"></div>
                        <span>Bloqueado</span>
                    </div>
                    <div class="rf-legend-item">
                        <div class="rf-legend-dot" style="background:#6D28D9; border-color:#6D28D9;"></div>
                        <span>Selecionado</span>
                    </div>
                </div>
                """
            )

    # =====================================================
    # PAINEL LATERAL (DETALHES / ROTA) (COLUNA DIREITA)
    # =====================================================
    with col_side:
        if not selected_space:
            with st.container(key="rf_find_details_card"):
                st.html(
                    """
                    <div style="padding:48px 24px; text-align:center;">
                        <div style="width:52px; height:52px; border-radius:14px; background:#F5F3FF; color:#6D28D9; display:inline-flex; align-items:center; justify-content:center; font-size:24px; margin-bottom:12px;">
                            📍
                        </div>
                        <h3 style="font-size:15px; font-weight:600; color:#1C1C2E; margin:0 0 6px 0;">Selecione um espaço</h3>
                        <p style="font-size:12px; color:#71717A; margin:0; line-height:1.5;">
                            Clique em uma sala no mapa para visualizar informações e descobrir como chegar até ela.
                        </p>
                    </div>
                    """
                )
        else:
            with st.container(key="rf_find_details_card"):
                # Header dos Detalhes com botão Fechar
                col_det_title, col_det_close = st.columns([4, 1])

                with col_det_title:
                    st.html(
                        f"""
                        <div style="padding:16px 20px 0 20px;">
                            <h2 style="font-size:16px; font-weight:700; color:#1C1C2E; margin:0 0 4px 0;">{esc(selected_space['name'])}</h2>
                            <p style="font-size:12px; color:#71717A; margin:0;">🏢 {esc(selected_space['building'])} &middot; {esc(selected_space['floor'])}</p>
                        </div>
                        """
                    )

                with col_det_close:
                    if st.button("✕", key="btn_close_details", type="tertiary"):
                        st.session_state.find_selected_space_id = None
                        st.session_state.find_show_directions = False
                        st.rerun()

                # Badges de Informação
                st.html(
                    f"""
                    <div style="padding:12px 20px; display:flex; flex-wrap:wrap; gap:8px;">
                        {badge(selected_space['status'])}
                        <span style="padding:3px 10px; border-radius:999px; background:#F0EEE9; color:#52525B; font-size:11px; font-weight:600;">
                            👥 {selected_space['capacity']} pessoas
                        </span>
                        <span style="padding:3px 10px; border-radius:999px; background:#F0EEE9; color:#52525B; font-size:11px; font-weight:600;">
                            {esc(selected_space['type'])}
                        </span>
                    </div>
                    <div style="padding:0 20px 16px 20px;">
                        <div style="background:#F8F7F4; border-radius:10px; padding:12px; margin-bottom:16px;">
                            <p style="font-size:11px; font-weight:600; text-transform:uppercase; color:#71717A; margin:0 0 4px 0;">Localização</p>
                            <p style="font-size:13px; color:#1C1C2E; margin:0 0 10px 0;">{esc(selected_space['location'])}</p>
                            <p style="font-size:11px; font-weight:600; text-transform:uppercase; color:#71717A; margin:0 0 4px 0;">Funcionamento</p>
                            <p style="font-size:13px; color:#1C1C2E; margin:0;">08:00 – 22:00</p>
                        </div>
                    </div>
                    """
                )

                # Botão Como Chegar
                col_btn_wrap = st.container()
                with col_btn_wrap:
                    if st.button("🗺️ Como chegar", key="btn_show_directions", type="primary", use_container_width=True):
                        st.session_state.find_show_directions = True
                        st.rerun()

            # Painel de Rota ("Como chegar")
            if st.session_state.find_show_directions:
                st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
                with st.container(key="rf_find_directions_card"):
                    col_dir_hdr, col_dir_cls = st.columns([4, 1])

                    with col_dir_hdr:
                        st.html(
                            f"""
                            <div style="background:#F5F3FF; padding:14px 16px; border-bottom:1px solid #EDE9FE;">
                                <h3 style="font-size:14px; font-weight:700; color:#6D28D9; margin:0;">Como chegar</h3>
                                <p style="font-size:11px; color:#71717A; margin:2px 0 0 0;">Rota até {esc(selected_space['name'])}</p>
                            </div>
                            """
                        )

                    with col_dir_cls:
                        if st.button("✕", key="btn_close_directions", type="tertiary"):
                            st.session_state.find_show_directions = False
                            st.rerun()

                    # Etapas do passo a passo
                    is_ground = selected_space["floor"] == "Térreo"
                    st.html(
                        f"""
                        <div style="padding:16px;">
                            <div style="border-left:2px dashed #6D28D9; padding-left:16px; margin-bottom:16px; position:relative;">
                                <div style="margin-bottom:12px;">
                                    <p style="font-size:10px; font-weight:700; text-transform:uppercase; color:#71717A; margin:0;">Você está aqui</p>
                                    <p style="font-size:12px; font-weight:600; color:#1C1C2E; margin:2px 0 0 0;">Entrada Principal</p>
                                </div>
                                <div>
                                    <p style="font-size:10px; font-weight:700; text-transform:uppercase; color:#6D28D9; margin:0;">Destino</p>
                                    <p style="font-size:13px; font-weight:700; color:#1C1C2E; margin:2px 0 0 0;">{esc(selected_space['name'])}</p>
                                    <p style="font-size:11px; color:#71717A; margin:2px 0 0 0;">{esc(selected_space['building'])} &middot; {esc(selected_space['floor'])}</p>
                                </div>
                            </div>

                            <p style="font-size:11px; font-weight:600; text-transform:uppercase; color:#71717A; margin:0 0 10px 0;">Passo a passo</p>

                            <div style="display:flex; flex-direction:column; gap:12px;">
                                <div>
                                    <p style="font-size:12px; font-weight:600; color:#1C1C2E; margin:0;">1. Entre pelo acesso principal</p>
                                    <p style="font-size:11px; color:#71717A; margin:2px 0 0 0;">Acesse o {esc(selected_space['building'])} pela entrada principal.</p>
                                </div>
                                <div>
                                    <p style="font-size:12px; font-weight:600; color:#1C1C2E; margin:0;">2. Siga pelo corredor principal</p>
                                    <p style="font-size:11px; color:#71717A; margin:2px 0 0 0;">Continue reto pelo corredor seguindo a sinalização.</p>
                                </div>
                                <div>
                                    <p style="font-size:12px; font-weight:600; color:#1C1C2E; margin:0;">3. {'Permaneça no térreo' if is_ground else f'Suba até o {esc(selected_space["floor"])}'}</p>
                                    <p style="font-size:11px; color:#71717A; margin:2px 0 0 0;">{'Não é necessário utilizar escadas ou elevador.' if is_ground else 'Utilize o elevador ou escadas para acessar o andar.'}</p>
                                </div>
                                <div>
                                    <p style="font-size:12px; font-weight:600; color:#1C1C2E; margin:0;">4. Procure pela {esc(selected_space['name'])}</p>
                                    <p style="font-size:11px; color:#71717A; margin:2px 0 0 0;">A sala está localizada no {esc(selected_space['floor'])}, em {esc(selected_space['location'])}.</p>
                                </div>
                            </div>
                        </div>
                        """
                    )
