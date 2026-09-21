import base64
import html
from functools import lru_cache
from pathlib import Path

import streamlit as st

from config.constants import ROLE_LABELS, STATUS_LABELS


# ============================================================
# ASSETS
# ============================================================

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"

LOGO_FILES = {
    "dark": "logo-preta.png",
    "light": "logo-branca.png",
    "mark": "logo-icone.png",
}

LOGO_SIZES = {
    "small": "110px",
    "medium": "150px",
    "large": "210px",
    "mark": "38px",
}


# ============================================================
# CSS
# ============================================================

@lru_cache
def _read_css_content(path):
    content = Path(path).read_text(encoding="utf-8")
    return f"<style>\n{content}\n</style>"


def load_css_file(path):
    st.html(_read_css_content(path))


def load_css():
    load_css_file("css/global.css")
    load_css_file("css/sidebar.css")


def load_auth_css():
    """Loads styles that are exclusive to the public authentication flow."""
    load_css_file("css/signup_pages.css")


# ============================================================
# UTILITÁRIOS
# ============================================================

def esc(value):
    return html.escape(str(value))


# ============================================================
# COMPONENTES
# ============================================================

def badge(value):
    label = STATUS_LABELS.get(value, value.replace("_", " ").title())
    return f'<span class="rf-badge {esc(value)}">{esc(label)}</span>'


def role_label(role):
    return ROLE_LABELS.get(role, role)


# ============================================================
# LOGO
# ============================================================

@lru_cache
def _logo_data_uri(variant):
    """
    Carrega a imagem da logo e transforma em Base64.

    O resultado fica em cache para evitar ler o arquivo
    novamente a cada renderização do Streamlit.
    """

    if variant not in LOGO_FILES:
        raise ValueError(
            f"Variante de logo inválida: {variant}. "
            f"Use: {', '.join(LOGO_FILES)}"
        )

    image_path = ASSETS_DIR / LOGO_FILES[variant]

    if not image_path.exists():
        raise FileNotFoundError(
            f"Arquivo da logo não encontrado: {image_path}"
        )

    encoded_image = base64.b64encode(
        image_path.read_bytes()
    ).decode("ascii")

    return f"data:image/png;base64,{encoded_image}"


def logo(size="medium", variant="dark", class_name=""):
    """
    Retorna a logo do RoomFlow em HTML.

    Parâmetros:
        size:
            "small"  -> logo pequena
            "medium" -> logo média
            "large"  -> logo grande
            "mark"   -> somente o ícone

        variant:
            "dark"  -> logo preta
            "light" -> logo branca
            "mark"  -> somente o ícone

        class_name:
            Classe CSS adicional opcional.
    """

    if size not in LOGO_SIZES:
        raise ValueError(
            f"Tamanho de logo inválido: {size}. "
            f"Use: {', '.join(LOGO_SIZES)}"
        )

    if variant not in LOGO_FILES:
        raise ValueError(
            f"Variante de logo inválida: {variant}. "
            f"Use: {', '.join(LOGO_FILES)}"
        )

    extra_class = (
        f' {html.escape(class_name, quote=True)}'
        if class_name
        else ""
    )

    alt_text = (
        "Ícone RoomFlow"
        if variant == "mark"
        else "RoomFlow"
    )

    image_uri = _logo_data_uri(variant)

    return (
        f'<div class="rf-logo rf-logo--{size}{extra_class}">'
        f'<img '
        f'class="rf-logo__image" '
        f'src="{image_uri}" '
        f'alt="{alt_text}" '
        f'style="width:{LOGO_SIZES[size]};">'
        f'</div>'
    )


# ============================================================
# HEADER
# ============================================================

def page_header(title, subtitle="", action_html=""):
    st.html(
        f"""
        <div class="rf-page-header">
          <div>
            <h1>{esc(title)}</h1>
            <p>{esc(subtitle)}</p>
          </div>
          <div>{action_html}</div>
        </div>
        """
    )


# ============================================================
# CARDS
# ============================================================

def stat_card(label, value, subtext=""):
    return (
        '<div class="rf-card">'
        f'<div class="rf-stat-label">{esc(label)}</div>'
        f'<div class="rf-stat-value">{esc(value)}</div>'
        f'<div style="color:var(--muted);font-size:13px;margin-top:4px">'
        f'{esc(subtext)}'
        f'</div>'
        "</div>"
    )


def cards_grid(cards, columns=4):
    klass = "rf-grid two" if columns == 2 else "rf-grid"

    st.html(
        f'<div class="{klass}">'
        + "".join(cards)
        + "</div>"
    )


# ============================================================
# TABELAS
# ============================================================

def table(headers, rows):
    head = "".join(
        f"<th>{esc(item)}</th>"
        for item in headers
    )

    body = ""

    for row in rows:
        body += (
            "<tr>"
            + "".join(f"<td>{cell}</td>" for cell in row)
            + "</tr>"
        )

    st.html(
        f"""
        <div class="rf-table-wrap">
          <table class="rf-table">
            <thead>
              <tr>{head}</tr>
            </thead>
            <tbody>
              {body}
            </tbody>
          </table>
        </div>
        """
    )


# ============================================================
# EMPTY STATE
# ============================================================

def empty_state(title, body):
    st.html(
        f"""
        <div class="rf-card" style="text-align:center;padding:36px">
          <div class="rf-avatar"
               style="width:56px;height:56px;margin:auto">
            !
          </div>

          <h3>{esc(title)}</h3>

          <p style="color:var(--muted)">
            {esc(body)}
          </p>
        </div>
        """
    )


# ============================================================
# TOAST
# ============================================================

def toast(width="stretch", aligned_right=False):
    message = st.session_state.get("toast")

    if message:
        if aligned_right:
            with st.container(horizontal_alignment="right"):
                st.success(message, width=width)
        else:
            st.success(message, width=width)
        st.session_state.toast = ""
