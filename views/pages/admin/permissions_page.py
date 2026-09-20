import streamlit as st

from views.components.ui_components import page_header


# =========================================================
# DADOS
# =========================================================

# Níveis: "full" | "own" | "none"
# full → acesso completo
# own  → apenas os próprios registros
# none → sem acesso

PERMISSION_MATRIX = [
    # (funcionalidade,                    admin,   gerente,  solicitante, participante)
    ("Gerenciar usuários",                "full",  "none",   "none",      "none"),
    ("Gerenciar permissões",              "full",  "none",   "none",      "none"),
    ("Configurações do sistema",          "full",  "none",   "none",      "none"),
    ("Gerenciar espaços",                 "full",  "full",   "none",      "none"),
    ("Gerenciar recursos",                "full",  "full",   "none",      "none"),
    ("Tipos de reserva",                  "full",  "full",   "none",      "none"),
    ("Criar reservas",                    "full",  "full",   "own",       "none"),
    ("Aprovar / rejeitar reservas",       "full",  "full",   "none",      "none"),
    ("Cancelar reservas",                 "full",  "full",   "own",       "none"),
    ("Resolver conflitos",                "full",  "full",   "none",      "none"),
    ("Bloquear espaços",                  "full",  "full",   "none",      "none"),
    ("Consultar agenda",                  "full",  "full",   "full",      "full"),
    ("Localizar espaços",                 "full",  "full",   "full",      "full"),
    ("Histórico de reservas",             "full",  "full",   "own",       "none"),
    ("Relatórios de ocupação",            "full",  "full",   "none",      "none"),
]

ROLES = [
    ("admin",        "Administrador"),
    ("gerente",      "Gerente"),
    ("solicitante",  "Solicitante"),
    ("participante", "Participante"),
]


# =========================================================
# HELPERS
# =========================================================

def _cell_html(level: str) -> str:
    """Retorna o HTML do ícone/símbolo para cada nível de permissão."""
    if level == "full":
        return (
            '<span title="Acesso completo" style="'
            "color: #16A34A;"
            "font-size: 16px;"
            "display: flex; align-items: center; justify-content: center;"
            '">✓</span>'
        )
    if level == "own":
        return (
            '<span title="Apenas os próprios" style="'
            "color: #B45309;"
            "font-size: 14px;"
            "display: flex; align-items: center; justify-content: center;"
            '">◎</span>'
        )
    # none
    return (
        '<span title="Sem acesso" style="'
        "color: #A1A1AA;"
        "opacity: 0.5;"
        "font-size: 14px;"
        "display: flex; align-items: center; justify-content: center;"
        '">—</span>'
    )


def _render_legend():
    """Renderiza a barra de legenda dos níveis de permissão."""
    st.html("""
        <div style="
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
            padding: 10px 14px;
            background: #EDE9FE;
            border: 1px solid rgba(109,40,217,0.2);
            border-radius: 8px;
            margin-bottom: 16px;
        ">
            <span style="font-size:12px; color:#6D28D9; font-weight:600;">Legenda:</span>

            <span style="display:inline-flex; align-items:center; gap:6px; font-size:12px; color:#52525B;">
                <span style="color:#16A34A; font-size:15px; font-weight:700;">✓</span>
                Acesso completo
            </span>

            <span style="display:inline-flex; align-items:center; gap:6px; font-size:12px; color:#52525B;">
                <span style="color:#B45309; font-size:13px;">◎</span>
                Apenas os próprios
            </span>

            <span style="display:inline-flex; align-items:center; gap:6px; font-size:12px; color:#52525B;">
                <span style="color:#A1A1AA; font-size:13px; opacity:0.6;">—</span>
                Sem acesso
            </span>
        </div>
    """)


def _render_table():
    """Renderiza a matriz de permissões como tabela HTML."""

    # Cabeçalho — badges por perfil
    ROLE_BADGE_STYLE = {
        "admin":        "background:#EDE9FE; color:#6D28D9;",
        "gerente":      "background:#FEF3C7; color:#B45309;",
        "solicitante":  "background:#F4F4F5; color:#52525B;",
        "participante": "background:#F4F4F5; color:#52525B;",
    }

    badge_style_base = (
        "display:inline-block;"
        "padding:3px 10px;"
        "border-radius:999px;"
        "font-size:11px;"
        "font-weight:600;"
        "white-space:nowrap;"
    )

    header_cells = '<th style="text-align:left; padding:10px 14px; font-size:11px; font-weight:600; color:#A1A1AA; width:260px; border-bottom:1px solid #E4E1DB;">Funcionalidade</th>'
    for role_key, role_label in ROLES:
        badge_s = ROLE_BADGE_STYLE[role_key]
        header_cells += (
            f'<th style="text-align:center; padding:10px 14px; border-bottom:1px solid #E4E1DB;">'
            f'<span style="{badge_style_base}{badge_s}">{role_label}</span>'
            f"</th>"
        )

    # Linhas
    rows_html = ""
    for i, (action, admin, gerente, solicitante, participante) in enumerate(PERMISSION_MATRIX):
        row_bg = "background:#F8F7F4;" if i % 2 != 0 else ""
        cells = f'<td style="padding:10px 14px; font-size:13px; color:#1C1C2E; border-bottom:1px solid #E4E1DB;">{action}</td>'
        for level in (admin, gerente, solicitante, participante):
            cells += f'<td style="text-align:center; padding:10px 14px; border-bottom:1px solid #E4E1DB;">{_cell_html(level)}</td>'
        rows_html += f'<tr style="{row_bg}">{cells}</tr>'

    st.html(f"""
        <div style="overflow-x:auto; border:1px solid #E4E1DB; border-radius:8px;">
            <table style="width:100%; border-collapse:collapse; min-width:560px; background:white;">
                <thead>
                    <tr style="background:#F0EEE9;">
                        {header_cells}
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    """)


def _render_footer_note():
    """Renderiza a nota de atenção no rodapé da página."""
    st.html("""
        <div style="
            margin-top: 16px;
            padding: 14px 16px;
            background: white;
            border: 1px solid #E4E1DB;
            border-radius: 8px;
        ">
            <p style="margin:0; font-size:12px; color:#52525B; line-height:1.6;">
                <strong style="color:#1C1C2E;">Atenção:</strong>
                apenas o Administrador pode editar a matriz de permissões.
                Alterações afetam todos os usuários do perfil selecionado imediatamente.
                Auditoria de mudanças é registrada no histórico.
            </p>
        </div>
    """)


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def permissions(user):
    page_header(
        "Permissões",
        "Matriz de permissões por perfil de usuário no sistema.",
    )

    _render_legend()
    _render_table()
    _render_footer_note()
