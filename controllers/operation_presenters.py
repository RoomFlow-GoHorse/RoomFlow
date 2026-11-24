"""Presentation mappings shared by Streamlit and HTTP controllers."""
from models.domain.entities.reservation import ReservationDetails
from models.domain.entities.reservation_conflict import ConflictDetails
from models.domain.entities.space import Space

def reservation_response(details: ReservationDetails) -> dict:
    item = details.reservation
    request = item.request
    return {
        "id": item.id, "space_id": request.space_id, "space_name": details.space_name,
        "requester_name": details.requester_name, "title": request.title, "activity_type": request.activity_type,
        "start": request.period.start, "end": request.period.end, "participants": request.participants,
        "justification": request.justification, "status": item.status, "has_overlap": details.has_overlap,
        "created_at": item.created_at, "reviewed_at": item.reviewed_at, "decision_reason": item.decision_reason,
    }


def conflict_response(item: ConflictDetails) -> dict:
    conflict = item.conflict
    return {
        "id": conflict.id, "status": conflict.status, "severity": conflict.severity,
        "reason": conflict.reason, "created_at": conflict.created_at, "decision": conflict.decision,
        "resolved_at": conflict.resolved_at, "resolved_by": conflict.resolved_by,
        "resolver_name": conflict.resolver_name,
        "reservations": [reservation_response(item.reservation_a), reservation_response(item.reservation_b)],
    }


def room_response(room: Space) -> dict:
    return {
        "id": room.id, "name": room.name, "building_id": room.building_id, "building": room.building,
        "location": room.location, "capacity": room.capacity, "type": room.type,
    }
