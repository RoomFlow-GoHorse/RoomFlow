"""Badges semânticos compartilhados do RoomFlow."""

from html import escape

from config.constants import ROLE_LABELS, STATUS_LABELS


_STYLES = {
    "approved": "background:#DCFCE7; border:1px solid #BBF7D0; color:#15803D;",
    "rejected": "background:#FEE2E2; border:1px solid #FECACA; color:#B91C1C;",
    "pending": "background:#EDE9FE; border:1px solid #DDD6FE; color:#6D28D9;",
    "warning": "background:#FEF3C7; border:1px solid #FDE68A; color:#B45309;",
    "conflict": "background:#FFF7ED; border:1px solid #FED7AA; color:#C2410C;",
    "neutral": "background:#F4F4F5; border:1px solid #E4E4E7; color:#52525B;",
    "inactive": "background:#F4F4F5; border:1px solid #E4E4E7; color:#A1A1AA;",
}

_STATUS_VARIANTS = {
    "aprovada": "approved", "rejeitada": "rejected", "pendente": "pending",
    "em_analise": "warning", "conflito": "conflict", "ativo": "approved",
    "inativo": "inactive", "disponivel": "approved", "ocupado": "warning",
    "bloqueado": "rejected", "nao_resolvido": "conflict", "resolvido": "approved",
}

_ROLE_VARIANTS = {
    "admin": "pending", "gerente": "warning", "solicitante": "neutral",
    "participante": "neutral",
}


def badge(value, category="status", variant=None, label=None):
    """Return a safe HTML badge while preserving the legacy ``badge(value)`` API."""
    value = str(value)
    if label is None:
        label = ROLE_LABELS.get(value, value) if category == "role" else STATUS_LABELS.get(value, value.replace("_", " ").title())
    if variant is None:
        variant = (_ROLE_VARIANTS if category == "role" else _STATUS_VARIANTS).get(value, "neutral")
    style = _STYLES.get(variant, _STYLES["neutral"])
    return (
        f'<span class="rf-badge rf-badge--{escape(category)} rf-badge--{escape(variant)}" style="'
        f'display:inline-block; padding:2px 10px; border-radius:var(--radius-pill); '
        f'font-size:var(--text-badge); font-weight:600; white-space:nowrap; {style}">'
        f'{escape(str(label))}</span>'
    )
