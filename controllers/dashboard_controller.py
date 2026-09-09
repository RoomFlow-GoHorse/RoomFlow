"""Prepara os indicadores apresentados pelo dashboard."""

from datetime import date

from controllers import conflict_controller, reservation_controller, space_controller, user_controller


def dashboard_stats(role, user_id=None):
    res = reservation_controller.reservations(requester_id=user_id if role == "solicitante" else None)
    return {
        "reservas": len(res),
        "aprovadas": len([r for r in res if r["status"] == "aprovada"]),
        "pendentes": len([r for r in res if r["status"] in {"pendente", "em_analise"}]),
        "conflitos": len(conflict_controller.conflicts()),
        "espacos_livres": len([s for s in space_controller.spaces() if s["status"] == "disponivel"]),
        "usuarios": len(user_controller.users()),
        "hoje": date.today().strftime("%d/%m/%Y"),
    }
