import streamlit as st

from views.components.ui_components import load_css_file, logo


def landing():
    load_css_file("css/landing_page.css")
    st.html(
        f"""
        <div class="rf-landing">

            <!-- =====================================================
                 HERO
            ====================================================== -->

            <section class="rf-landing-hero">

                <!-- =================================================
                     HEADER
                ================================================== -->

                <header class="rf-landing-header">
                    <div class="rf-container rf-header-content">

                        <!-- Logo -->
                        <div class="rf-header-logo">
                            {logo()}
                        </div>

                        <!-- Navegação -->
                        <nav class="rf-landing-nav">
                            <a href="#funcionalidades">
                                Funcionalidades
                            </a>

                            <a href="#beneficios">
                                Benefícios
                            </a>

                            <a href="#como-funciona">
                                Para quem é
                            </a>
                        </nav>

                        <!-- Ações -->
                        <div class="rf-header-actions">

                            <a
                                href="?page=login"
                                class="rf-nav-login"
                            >
                                Entrar
                            </a>

                            <a
                                href="?page=signup_choice"
                                class="rf-nav-signup"
                            >
                                Criar conta
                            </a>

                        </div>

                    </div>
                </header>


                <!-- =================================================
                     HERO PRINCIPAL
                ================================================== -->

                <div class="rf-container rf-hero-main">

                    <div class="rf-hero-text">

                        <!-- Badge -->
                        <div class="rf-hero-badge">

                            <span class="rf-badge-dot"></span>

                            <span>
                                Sistema de Gestão de Espaços
                            </span>

                        </div>


                        <!-- Título -->
                        <h1>
                            O espaço certo
                            <br />

                            <span class="rf-hero-highlight">
                                para cada
                            </span>

                            <br />

                            momento.
                        </h1>


                        <!-- Descrição -->
                        <p class="rf-hero-description">
                            O RoomFlow centraliza reservas, salas,
                            recursos, reuniões, eventos e ocupação
                            em uma única plataforma — para que sua
                            instituição funcione sem fricção.
                        </p>


                        <!-- Botões -->
                        <div class="rf-hero-actions">

                            <a
                                href="?page=login"
                                class="rf-hero-primary"
                            >
                                <span>
                                    Começar agora
                                </span>

                                <span class="rf-arrow">
                                    →
                                </span>
                            </a>


                            <a
                                href="#funcionalidades"
                                class="rf-hero-secondary"
                            >
                                Conhecer o RoomFlow
                            </a>

                        </div>


                        <!-- Benefícios rápidos -->
                        <div class="rf-quick-benefits">

                            <div class="rf-quick-benefit">
                                <span class="rf-check">
                                    ✓
                                </span>

                                <span>
                                    Zero configuração complexa
                                </span>
                            </div>


                            <div class="rf-quick-benefit">
                                <span class="rf-check">
                                    ✓
                                </span>

                                <span>
                                    4 perfis de acesso
                                </span>
                            </div>


                            <div class="rf-quick-benefit">
                                <span class="rf-check">
                                    ✓
                                </span>

                                <span>
                                    Detecção de conflitos
                                </span>
                            </div>

                        </div>

                    </div>


                    <!-- =================================================
                         DASHBOARD
                    ================================================== -->

                    <div class="rf-dashboard-wrapper">

                        <div class="rf-dashboard-glow"></div>


                        <!-- Dashboard -->
                        <div class="rf-dashboard-mock">


                            <!-- Barra navegador -->
                            <div class="rf-browser-bar">

                                <div class="rf-browser-dots">

                                    <span class="rf-dot-red"></span>

                                    <span class="rf-dot-yellow"></span>

                                    <span class="rf-dot-green"></span>

                                </div>


                                <span class="rf-browser-title">
                                    RoomFlow — Dashboard
                                </span>

                            </div>


                            <!-- Conteúdo -->
                            <div class="rf-dashboard-content">


                                <!-- Cards superiores -->
                                <div class="rf-dashboard-stats">


                                    <div class="rf-dashboard-stat">

                                        <strong class="rf-success">
                                            5
                                        </strong>

                                        <span>
                                            Espaços livres
                                        </span>

                                    </div>


                                    <div class="rf-dashboard-stat">

                                        <strong class="rf-brand">
                                            3
                                        </strong>

                                        <span>
                                            Ocupados
                                        </span>

                                    </div>


                                    <div class="rf-dashboard-stat">

                                        <strong class="rf-mustard">
                                            2
                                        </strong>

                                        <span>
                                            Pendentes
                                        </span>

                                    </div>

                                </div>


                                <!-- Área principal -->
                                <div class="rf-dashboard-grid">


                                    <!-- Próximas reservas -->
                                    <div class="rf-dashboard-panel">

                                        <div class="rf-panel-header">

                                            <strong>
                                                Próximas reservas
                                            </strong>

                                            <span>
                                                Ver agenda
                                            </span>

                                        </div>


                                        <!-- Reserva 1 -->
                                        <div class="rf-reservation">

                                            <span class="rf-reservation-dot"></span>

                                            <div class="rf-reservation-info">

                                                <strong>
                                                    Sala 204
                                                </strong>

                                                <small>
                                                    08:00–10:00
                                                </small>

                                            </div>


                                            <span class="rf-reservation-type">
                                                Aula
                                            </span>

                                        </div>


                                        <!-- Reserva 2 -->
                                        <div class="rf-reservation">

                                            <span
                                                class="rf-reservation-dot
                                                rf-light-dot"
                                            ></span>

                                            <div class="rf-reservation-info">

                                                <strong>
                                                    Sala de Reuniões A
                                                </strong>

                                                <small>
                                                    10:00–12:00
                                                </small>

                                            </div>


                                            <span class="rf-reservation-type">
                                                Reunião
                                            </span>

                                        </div>


                                        <!-- Reserva 3 -->
                                        <div class="rf-reservation">

                                            <span
                                                class="rf-reservation-dot
                                                rf-success-dot"
                                            ></span>

                                            <div class="rf-reservation-info">

                                                <strong>
                                                    Auditório Principal
                                                </strong>

                                                <small>
                                                    14:00–18:00
                                                </small>

                                            </div>


                                            <span class="rf-reservation-type">
                                                Evento
                                            </span>

                                        </div>

                                    </div>


                                    <!-- Ocupação -->
                                    <div class="rf-dashboard-panel">

                                        <div class="rf-occupation-title">
                                            Ocupação dos espaços
                                        </div>


                                        <!-- Salas -->
                                        <div class="rf-progress-item">

                                            <div class="rf-progress-label">

                                                <span>
                                                    Salas
                                                </span>

                                                <strong>
                                                    72%
                                                </strong>

                                            </div>


                                            <div class="rf-progress">

                                                <div
                                                    class="rf-progress-bar"
                                                    style="width:72%"
                                                ></div>

                                            </div>

                                        </div>


                                        <!-- Auditórios -->
                                        <div class="rf-progress-item">

                                            <div class="rf-progress-label">

                                                <span>
                                                    Auditórios
                                                </span>

                                                <strong>
                                                    54%
                                                </strong>

                                            </div>


                                            <div class="rf-progress">

                                                <div
                                                    class="rf-progress-bar
                                                    rf-mustard-bar"
                                                    style="width:54%"
                                                ></div>

                                            </div>

                                        </div>


                                        <!-- Laboratórios -->
                                        <div class="rf-progress-item">

                                            <div class="rf-progress-label">

                                                <span>
                                                    Laboratórios
                                                </span>

                                                <strong>
                                                    81%
                                                </strong>

                                            </div>


                                            <div class="rf-progress">

                                                <div
                                                    class="rf-progress-bar"
                                                    style="width:81%"
                                                ></div>

                                            </div>

                                        </div>


                                        <!-- Total -->
                                        <div class="rf-total-occupation">

                                            <span>
                                                Utilização geral
                                            </span>

                                            <strong>
                                                68%
                                            </strong>

                                        </div>

                                    </div>

                                </div>

                            </div>

                        </div>


                        <!-- Alerta de conflito -->
                        <div class="rf-conflict-alert">

                            <div class="rf-conflict-icon">
                                !
                            </div>


                            <div class="rf-conflict-text">

                                <strong>
                                    1 conflito detectado
                                </strong>

                                <span>
                                    Lab. Informática · 22/08
                                </span>

                            </div>

                        </div>

                    </div>

                </div>


                <!-- =================================================
                     CURVA
                ================================================== -->

                <div class="rf-hero-curve">

                    <svg
                        viewBox="0 0 1440 120"
                        preserveAspectRatio="none"
                    >

                        <path
                            d="M0,65
                            C300,120 500,115 760,95
                            C1050,72 1220,95 1440,55
                            L1440,120
                            L0,120 Z"

                            fill="#FFFFFF"
                        />

                    </svg>

                </div>

            </section>


            <!-- =====================================================
                 FUNCIONALIDADES
            ====================================================== -->

            <section
                id="funcionalidades"
                class="rf-features-section"
            >

                <div class="rf-container">

                    <div class="rf-section-heading">

                        <span class="rf-section-label">
                            FUNCIONALIDADES
                        </span>

                        <h2>
                            Tudo que sua instituição precisa,
                            em um só lugar.
                        </h2>

                        <p>
                            Do agendamento à resolução de conflitos,
                            o RoomFlow cobre cada etapa da gestão
                            de espaços.
                        </p>

                    </div>


                    <div class="rf-features-grid">


                        <article class="rf-feature-card">

                            <div class="rf-feature-icon">
                                📍
                            </div>

                            <h3>
                                Gestão de espaços
                            </h3>

                            <p>
                                Cadastre salas, auditórios e laboratórios
                                com capacidade, localização e recursos
                                disponíveis.
                            </p>

                        </article>


                        <article class="rf-feature-card">

                            <div class="rf-feature-icon">
                                📅
                            </div>

                            <h3>
                                Reservas inteligentes
                            </h3>

                            <p>
                                Solicitantes fazem reservas com fluxo
                                guiado. O sistema verifica disponibilidade
                                em tempo real.
                            </p>

                        </article>


                        <article class="rf-feature-card">

                            <div class="rf-feature-icon">
                                ⚡
                            </div>

                            <h3>
                                Controle de recursos
                            </h3>

                            <p>
                                Gerencie projetores, sistemas de áudio,
                                videoconferência e todos os recursos
                                por espaço.
                            </p>

                        </article>


                        <article class="rf-feature-card">

                            <div class="rf-feature-icon">
                                ⚠
                            </div>

                            <h3>
                                Gestão de conflitos
                            </h3>

                            <p>
                                Detecção automática de sobreposições.
                                Administradores resolvem com alternativas
                                sugeridas.
                            </p>

                        </article>


                        <article class="rf-feature-card">

                            <div class="rf-feature-icon">
                                ◷
                            </div>

                            <h3>
                                Agenda centralizada
                            </h3>

                            <p>
                                Visualize todas as atividades em calendário
                                diário, semanal ou mensal por espaço
                                ou usuário.
                            </p>

                        </article>


                        <article class="rf-feature-card">

                            <div class="rf-feature-icon">
                                ▥
                            </div>

                            <h3>
                                Histórico de ocupação
                            </h3>

                            <p>
                                Relatórios de uso por espaço, período
                                e perfil. Dados para decisões mais
                                inteligentes.
                            </p>

                        </article>

                    </div>

                </div>

            </section>


            <!-- =====================================================
                 BENEFÍCIOS
            ====================================================== -->

            <section
                id="beneficios"
                class="rf-benefits-section"
            >

                <div class="rf-container">

                    <div class="rf-section-heading">

                        <span
                            class="rf-section-label
                            rf-mustard-text"
                        >
                            BENEFÍCIOS
                        </span>

                        <h2>
                            Resultados que fazem diferença.
                        </h2>

                    </div>


                    <div class="rf-benefits-grid">


                        <article class="rf-benefit-card">

                            <strong>
                                –60%
                            </strong>

                            <h3>
                                menos conflitos de reserva
                            </h3>

                            <p>
                                Detecção automática e resolução guiada
                                eliminam sobreposições antes que virem
                                problema.
                            </p>

                        </article>


                        <article class="rf-benefit-card">

                            <strong>
                                3×
                            </strong>

                            <h3>
                                melhor aproveitamento dos espaços
                            </h3>

                            <p>
                                Visibilidade real de ocupação mostra
                                onde há espaço ocioso e onde falta
                                capacidade.
                            </p>

                        </article>


                        <article class="rf-benefit-card">

                            <strong>
                                –80%
                            </strong>

                            <h3>
                                tempo para decisões administrativas
                            </h3>

                            <p>
                                Informações centralizadas permitem
                                aprovar, rejeitar ou redirecionar
                                em segundos.
                            </p>

                        </article>


                        <article class="rf-benefit-card">

                            <strong>
                                1
                            </strong>

                            <h3>
                                plataforma para tudo
                            </h3>

                            <p>
                                Espaços, reservas, recursos,
                                conflitos e histórico em um único
                                sistema integrado.
                            </p>

                        </article>

                    </div>

                </div>

            </section>


            <!-- =====================================================
                 COMO FUNCIONA / PERFIS
            ====================================================== -->

            <section
                id="como-funciona"
                class="rf-profiles-section"
            >

                <div class="rf-container">

                    <div class="rf-profiles-heading">

                        <span>
                            COMO FUNCIONA
                        </span>

                        <h2>
                            Quatro perfis,
                            <br />

                            <strong>
                                um sistema.
                            </strong>
                        </h2>

                        <p>
                            Cada tipo de usuário tem uma experiência
                            adaptada às suas responsabilidades.
                        </p>

                    </div>


                    <div class="rf-profiles-grid">


                        <article class="rf-profile-card">

                            <span class="rf-profile-number">
                                01
                            </span>

                            <div class="rf-profile-line"></div>

                            <h3>
                                Gerente
                            </h3>

                            <p>
                                Gerencia espaços, recursos, reservas,
                                solicitações, conflitos e histórico
                                de ocupação.
                            </p>

                        </article>


                        <article class="rf-profile-card">

                            <span class="rf-profile-number">
                                02
                            </span>

                            <div class="rf-profile-line"></div>

                            <h3>
                                Administrador
                            </h3>

                            <p>
                                Configura usuários, permissões e políticas
                                de uso do sistema. Controle total da
                                governança.
                            </p>

                        </article>


                        <article class="rf-profile-card">

                            <span class="rf-profile-number">
                                03
                            </span>

                            <div class="rf-profile-line"></div>

                            <h3>
                                Solicitante
                            </h3>

                            <p>
                                Solicita reservas de espaços, acompanha
                                aprovações e gerencia suas atividades.
                            </p>

                        </article>


                        <article class="rf-profile-card">

                            <span class="rf-profile-number">
                                04
                            </span>

                            <div class="rf-profile-line"></div>

                            <h3>
                                Participante
                            </h3>

                            <p>
                                Consulta agenda, recebe notificações de
                                alterações e localiza espaços com facilidade.
                            </p>

                        </article>

                    </div>


                    <div class="rf-profiles-actions">

                        <a
                            href="?page=login"
                            class="rf-profile-primary"
                        >
                            Começar agora
                            <span>→</span>
                        </a>


                        <a
                            href="?page=signup_choice"
                            class="rf-profile-secondary"
                        >
                            Ver demonstração
                        </a>

                    </div>

                </div>

            </section>


            <!-- =====================================================
                 FOOTER
            ====================================================== -->

            <footer class="rf-landing-footer">

                <div class="rf-container rf-footer-content">

                    <div class="rf-footer-logo">
                        {logo()}
                    </div>


                    <div class="rf-footer-links">

                        <a href="#">
                            Termos de uso
                        </a>

                        <a href="#">
                            Privacidade
                        </a>

                        <a href="#">
                            Suporte
                        </a>

                    </div>


                    <p>
                        © 2026 RoomFlow. Todos os direitos reservados.
                    </p>

                </div>

            </footer>

        </div>
        """
    )
