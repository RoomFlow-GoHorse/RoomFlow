import html
from pathlib import Path

import streamlit as st

from config.constants import ROLE_LABELS, STATUS_LABELS


def load_css_file(path):
    st.html(Path(path))


def load_css():
    load_css_file("css/global.css")
    load_css_file("css/signup_pages.css")


def esc(value):
    return html.escape(str(value))


def badge(value):
    label = STATUS_LABELS.get(value, value.replace("_", " ").title())
    return f'<span class="rf-badge {esc(value)}">{esc(label)}</span>'


def role_label(role):
    return ROLE_LABELS.get(role, role)


def logo(light=False):
    color = "#fff" if light else "var(--graphite)"
    return f'<div class="rf-logo" style="color:{color}"><span class="rf-logo-mark">R</span><span>RoomFlow</span></div>'


def page_header(title, subtitle="", action_html=""):
    st.html(
        f"""
        <div class="rf-page-header">
          <div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>
          <div>{action_html}</div>
        </div>
        """
    )


def stat_card(label, value, subtext=""):
    return (
        '<div class="rf-card">'
        f'<div class="rf-stat-label">{esc(label)}</div>'
        f'<div class="rf-stat-value">{esc(value)}</div>'
        f'<div style="color:var(--muted);font-size:13px;margin-top:4px">{esc(subtext)}</div>'
        "</div>"
    )


def cards_grid(cards, columns=4):
    klass = "rf-grid two" if columns == 2 else "rf-grid"
    st.html(f'<div class="{klass}">' + "".join(cards) + "</div>")


def table(headers, rows):
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
    st.html(f'<div class="rf-table-wrap"><table class="rf-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


def empty_state(title, body):
    st.html(
        f"""
        <div class="rf-card" style="text-align:center;padding:36px">
          <div class="rf-avatar" style="width:56px;height:56px;margin:auto">!</div>
          <h3>{esc(title)}</h3>
          <p style="color:var(--muted)">{esc(body)}</p>
        </div>
        """
    )


def toast():
    message = st.session_state.get("toast")
    if message:
        st.success(message)
        st.session_state.toast = ""
