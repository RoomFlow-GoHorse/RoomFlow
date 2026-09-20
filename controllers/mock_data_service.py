from datetime import date

import streamlit as st


def reservations(status=None, requester_id=None):
    items = st.session_state.reservations
    if status and status != "Todas":
        items = [item for item in items if item["status"] == status]
    if requester_id:
        items = [item for item in items if item["requester_id"] == requester_id]
    return items


def update_reservation_status(reservation_id, status):
    for item in st.session_state.reservations:
        if item["id"] == reservation_id:
            item["status"] = status
            return item
    return None


def create_reservation(data):
    data["id"] = f"r{len(st.session_state.reservations) + 1}"
    data.setdefault("status", "pendente")
    data.setdefault("priority", "media")
    st.session_state.reservations.append(data)
    return data


def buildings():
    return st.session_state.get("buildings", [])


def floors(building_id=None):
    items = st.session_state.get("floors", [])
    if building_id:
        return [f for f in items if f.get("buildingId") == building_id]
    return items


def plans():
    return st.session_state.get("plans", {})


def spaces(status=None, query="", building=None, floor=None):
    items = st.session_state.get("spaces", [])
    if status and status != "Todos":
        items = [item for item in items if item["status"] == status]
    if building:
        items = [item for item in items if item.get("building") == building]
    if floor:
        items = [item for item in items if item.get("floor") == floor]
    if query:
        q = query.lower()
        items = [
            item for item in items
            if q in item["name"].lower()
            or q in item.get("building", "").lower()
            or q in item.get("location", "").lower()
        ]
    return items


def toggle_space(space_id):
    for item in st.session_state.spaces:
        if item["id"] == space_id:
            item["status"] = "disponivel" if item["status"] == "bloqueado" else "bloqueado"
            return item
    return None


def notifications_for(role):
    return [item for item in st.session_state.notifications if role in item["audiences"]]


def mark_notification_read(notification_id=None, role=None):
    for item in st.session_state.notifications:
        matches_notification = notification_id is None or item["id"] == notification_id
        matches_role = role is None or role in item["audiences"]
        if matches_notification and matches_role:
            item["read"] = True


def users():
    return st.session_state.users


def resources():
    return st.session_state.resources


def institutions():
    return st.session_state.institutions


def toggle_user(user_id):
    for item in st.session_state.users:
        if item["id"] == user_id:
            item["status"] = "ativo" if item["status"] == "inativo" else "inativo"
            return item
    return None


def agenda_events(space="Todos", event_type="Todos"):
    items = [item for item in st.session_state.reservations if item["status"] in {"aprovada", "pendente", "em_analise", "conflito"}]
    if space != "Todos":
        items = [item for item in items if item["space"] == space]
    if event_type != "Todos":
        items = [item for item in items if item["type"] == event_type]
    return sorted(items, key=lambda item: (item["date"], item["start"]))


def resolve_conflict(conflict_id, decision):
    for item in st.session_state.conflicts:
        if item["id"] == conflict_id:
            item["status"] = "em_analise" if decision == "alterar" else "resolvido"
            item["decision"] = decision
            return item
    return None


def dashboard_stats(role, user_id=None):
    res = reservations(requester_id=user_id if role == "solicitante" else None)
    return {
        "reservas": len(res),
        "aprovadas": len([r for r in res if r["status"] == "aprovada"]),
        "pendentes": len([r for r in res if r["status"] in {"pendente", "em_analise"}]),
        "conflitos": len(st.session_state.conflicts),
        "espacos_livres": len([s for s in st.session_state.spaces if s["status"] == "disponivel"]),
        "usuarios": len(st.session_state.users),
        "hoje": date.today().strftime("%d/%m/%Y"),
    }
