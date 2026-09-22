"""Small, domain-specific card primitives used by internal RoomFlow pages."""

from html import escape

from views.components.badges import badge


def metric_card(label, value, subtext=""):
    return (
        '<div class="rf-card rf-metric-card">'
        f'<div class="rf-stat-label">{escape(str(label))}</div>'
        f'<div class="rf-stat-value">{escape(str(value))}</div>'
        f'<div class="rf-stat-subtext">{escape(str(subtext))}</div>'
        '</div>'
    )


def reservation_card(item):
    """Return the compact reservation-card markup used in manager lists."""
    title = escape(str(item.get("title", "Reserva")))
    details = " - ".join(escape(str(item.get(key, ""))) for key in ("space", "date", "start", "end"))
    justification = escape(str(item.get("justification", "")))
    status = badge(item.get("status", ""))
    priority = badge(item["priority"], category="priority") if item.get("priority") else ""
    return (
        '<div class="rf-card rf-reservation-card">'
        '<div style="display:flex;justify-content:space-between;gap:12px">'
        f'<div><strong>{title}</strong><br><span style="color:var(--muted)">{details}</span></div>'
        f'<div>{status} {priority}</div></div>'
        f'<p style="color:var(--soft)">{justification}</p></div>'
    )
