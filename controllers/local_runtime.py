"""Streamlit controllers: direct service calls, with identity resolved per action.

Only the service runtime is cached. These lightweight controllers never store an
actor or a token; the callback reads the current Streamlit session on each call.
"""
from dataclasses import asdict
from datetime import date, datetime, time
from enum import Enum
from functools import wraps

from sqlalchemy.exc import SQLAlchemyError

from application.services.authentication_service import InvalidSession
from application.ports.email_sender import EmailDeliveryUnavailable
from controllers.operation_payloads import ReservationPayload, ReservationEditPayload, DecisionPayload, ResolutionPayload
from controllers.operation_presenters import reservation_response, conflict_response, room_response
from controllers.runtime_errors import RuntimeUnavailable, SessionExpired
from models.domain.entities.reservation import ReservationPeriod, ReservationStatus, review_decisions
from models.domain.entities.reservation_conflict import ConflictStatus


def presentation(value):
    """Keep the existing view contract without serializing through HTTP."""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: presentation(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [presentation(item) for item in value]
    return value


class ServiceController:
    def __init__(self, service, actor=None):
        self._service, self._actor = service, actor

    def __getattr__(self, name):
        method = getattr(self._service, name)

        @wraps(method)
        def call(*args, **kwargs):
            try:
                if self._actor is not None:
                    actor = self._actor()
                    if args:
                        args = (actor, *args[1:])
                    else:
                        kwargs['actor'] = actor
                return method(*args, **kwargs)
            except EmailDeliveryUnavailable:
                raise RuntimeUnavailable("Não foi possível enviar o e-mail. Confira a configuração SMTP e tente novamente.") from None
            except SQLAlchemyError:
                raise RuntimeUnavailable('Não foi possível acessar o PostgreSQL. Confira a conexão e tente novamente.') from None
        return call


class LocalRuntime:
    def __init__(self, services, token):
        self._services, self._token = services, token
        for name in ('user_management', 'admin_audit', 'invite_codes', 'space_management',
                     'floor_plan_management', 'admin_dashboard'):
            setattr(self, name, ServiceController(getattr(services, name), self.actor))
        self.authentication = ServiceController(AuthenticationController(self))
        self.institution_management = ServiceController(InstitutionController(self))
        self.enrollment_management = ServiceController(EnrollmentController(self))
        self.member_signup = ServiceController(services.member_signup)
        self.password_recovery = ServiceController(services.password_recovery)
        self.resource_management = ServiceController(ResourceController(self))
        self.reservation_service = ServiceController(ReservationController(self))
        self.conflict_service = ServiceController(ConflictController(self))
        self.manager_operations = ServiceController(OperationsController(self))
        self.notifications = ServiceController(NotificationController(self))

    def actor(self):
        try:
            token = self._token()
            if not token:
                raise InvalidSession
            return self._services.authentication.authenticate(token)
        except InvalidSession:
            raise SessionExpired('Sessão expirada. Entre novamente.') from None


class AuthenticationController:
    def __init__(self, runtime):
        self.runtime = runtime

    def __getattr__(self, name):
        return getattr(self.runtime._services.authentication, name)

    def change_password(self, user_id, current_password, new_password):
        actor = self.runtime.actor()
        return self.runtime._services.authentication.change_password(
            actor.id, current_password, new_password, actor.institution_id,
        )


class InstitutionController:
    def __init__(self, runtime):
        self.runtime = runtime

    def register(self, registration):
        services = self.runtime._services
        return services.institution_management.register_with_invitation(registration, services.invite_codes)

    def get_own(self, actor):
        return self.runtime._services.institution_management.get_own(self.runtime.actor())

    def update_own(self, actor, update):
        return self.runtime._services.institution_management.update_own(self.runtime.actor(), update)


class EnrollmentController:
    def __init__(self, runtime):
        self.runtime = runtime

    def __getattr__(self, name):
        service = self.runtime._services.enrollment_management
        if name == 'preview_member_institution':
            return getattr(service, name)
        return getattr(ServiceController(service, self.runtime.actor), name)


class ResourceController:
    def __init__(self, runtime):
        self.runtime = runtime

    def __getattr__(self, name):
        return getattr(ServiceController(self.runtime._services.resource_management, self.runtime.actor), name)

    def update_space_configuration(self, space_id, capacity, resource_ids, *, name=None, room_type=None):
        actor = self.runtime.actor()
        services = self.runtime._services
        with services.admin_audit.atomic():
            services.space_management.update_space(actor, space_id, name=name, room_type=room_type, capacity=capacity)
            return services.resource_management.set_space_resources(actor, space_id, resource_ids)


class ReservationController:
    def __init__(self, runtime):
        self.runtime = runtime
        self.service = runtime._services.reservation_service

    def catalog_settings(self):
        institution = self.service.catalog_settings(self.runtime.actor())
        return {'timezone': institution.timezone,
                'justification_required': institution.preferences.reservations.justification_required}

    def catalog(self, start=None, end=None):
        if (start is None) != (end is None):
            raise ValueError('Informe início e fim juntos.')
        institution, spaces = self.service.catalog(self.runtime.actor(), ReservationPeriod(start, end) if start else None)
        return {'timezone': institution.timezone,
                'justification_required': institution.preferences.reservations.justification_required,
                'spaces': [{**room_response(room), 'resources': list(room.resources)} for room in spaces]}

    def create(self, payload):
        return presentation(reservation_response(self.service.create(self.runtime.actor(), ReservationPayload(**payload).to_request())))

    def eligible_participants(self):
        return presentation([asdict(user) for user in self.service.eligible_participants(self.runtime.actor())])

    def list_own(self):
        return presentation([reservation_response(item) for item in self.service.list_own(self.runtime.actor())])

    def list_institution(self):
        return presentation([reservation_response(item) for item in self.service.list_institution(self.runtime.actor())])

    def list_participating(self):
        return presentation([
            {**reservation_response(item), "participation_status": item.participation_status}
            for item in self.service.list_participating(self.runtime.actor())
        ])

    def participating_detail(self, reservation_id):
        item, status = self.service.participating_detail(self.runtime.actor(), reservation_id)
        return presentation({**reservation_response(item), 'participation_status': status})

    def respond_participation(self, reservation_id, status):
        item, status = self.service.respond_participation(self.runtime.actor(), reservation_id, status)
        return presentation({**reservation_response(item), 'participation_status': status})

    def detail_own(self, reservation_id):
        item, history = self.service.detail_own(self.runtime.actor(), reservation_id)
        actor = self.runtime.actor()
        participants = self.service.participants(actor, reservation_id)
        return presentation({**reservation_response(item), 'participant_ids': [link.user_id for link in participants],
                             'history': [asdict(event) for event in history]})

    def detail(self, reservation_id):
        item, history = self.service.detail(self.runtime.actor(), reservation_id)
        return presentation({**reservation_response(item), 'reviewed_by': item.reservation.reviewed_by,
                             'can_edit': self.service.can_edit(item.reservation),
                             'available_decisions': review_decisions(item.reservation.status),
                             'history': [asdict(event) for event in history]})

    def edit(self, reservation_id, payload):
        data = ReservationEditPayload(**payload)
        return presentation(reservation_response(self.service.edit(self.runtime.actor(), reservation_id, data.to_request(), data.reason)))

    def cancel(self, reservation_id, reason=None):
        return presentation(reservation_response(self.service.cancel(self.runtime.actor(), reservation_id, reason)))

    def review(self, reservation_id, status, reason=None):
        data = DecisionPayload(status=status, reason=reason)
        return presentation(reservation_response(self.service.review(self.runtime.actor(), reservation_id, data.status, data.reason)))


class ConflictController:
    def __init__(self, runtime):
        self.runtime = runtime
        self.service = runtime._services.conflict_service

    def list(self, status=None, query=''):
        zone, items = self.service.list_conflicts(self.runtime.actor(), ConflictStatus(status) if status else None, query)
        return presentation({'timezone': zone, 'items': [conflict_response(item) for item in items]})

    def detect(self):
        return {'updated': self.service.detect(self.runtime.actor())}

    def detail(self, conflict_id):
        item, actions = self.service.detail(self.runtime.actor(), conflict_id)
        return presentation({**conflict_response(item), 'available_actions': actions})

    def alternatives(self, conflict_id):
        result = self.service.alternatives(self.runtime.actor(), conflict_id)
        return {key: [room_response(room) for room in rooms] for key, rooms in result.items()}

    def resolve(self, conflict_id, payload):
        data = ResolutionPayload(**payload)
        item, actions = self.service.resolve(self.runtime.actor(), conflict_id, data.action, data.reason, data.reservation_id, data.space_id)
        return presentation({**conflict_response(item), 'available_actions': actions})


class OperationsController:
    def __init__(self, runtime):
        self.runtime = runtime
        self.service = runtime._services.manager_operations

    def context(self):
        result = self.service.context(self.runtime.actor())
        return presentation({'timezone': result.timezone, 'today': result.today, 'opens_at': result.opens_at,
                             'closes_at': result.closes_at,
                             'buildings': [{'id': item.id, 'name': item.name} for item in result.buildings],
                             'spaces': [room_response(room) for room in result.spaces]})

    def report(self, **filters):
        if filters.get('status') is not None:
            filters['status'] = ReservationStatus(filters['status'])
        options = dict(start_date=None, end_date=None, building_id=None, space_id=None, status=None)
        options.update(filters)
        result = self.service.report(self.runtime.actor(), **options)
        return presentation({'timezone': result.timezone, 'start_date': result.start_date, 'end_date': result.end_date,
                             'opens_at': result.opens_at, 'closes_at': result.closes_at, 'metrics': asdict(result.metrics),
                             'occupancy_rate': result.occupancy_rate, 'space_counts': result.space_counts,
                             'spaces': [{**room_response(row.room), 'status': row.status, 'occupancy_rate': row.rate,
                                         'usable_seconds': row.usable_seconds, 'occupied_seconds': row.occupied_seconds,
                                         'blocked_seconds': row.blocked_seconds} for row in result.spaces],
                             'reservations': [reservation_response(row) for row in result.reservations]})


class NotificationController:
    def __init__(self, runtime):
        self.runtime = runtime
        self.service = runtime._services.notifications

    def inbox(self, *, unread_only=False, category=None, limit=25, offset=0):
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError('Paginação inválida.')
        items, total, unread, zone = self.service.inbox(self.runtime.actor(), unread_only=unread_only,
                                                       category=category, limit=limit, offset=offset)
        return presentation({'items': [asdict(item) for item in items], 'total': total, 'unread_count': unread, 'timezone': zone})

    def unread_count(self):
        return self.service.unread_count(self.runtime.actor())

    def mark_read(self, notification_id):
        return presentation({'read_at': self.service.mark_read(self.runtime.actor(), notification_id)})

    def mark_all_read(self):
        return {'updated': self.service.mark_all_read(self.runtime.actor())}
