# Future persistence: institutional invitations and authorized enrollments

The current API and Streamlit application use in-memory repositories. Their contents and invitation/import previews are temporary and reset when the process restarts. This document records the database contract to align with the database owner; it does not change or migrate the current schema.

## Suggested entities

### `institution_invite_codes`

- `id`
- `institution_id` foreign key to `instituicoes.id`
- `code_digest` (SHA-256 digest of a high-entropy random code; never persist the raw code)
- `created_at` and nullable `revoked_at`
- Optional `created_by_user_id` for audit
- Unique `code_digest`
- At most one active row per institution, enforced with a partial unique index or a current-code pointer

The application returns a raw code only when it creates/replaces it. A status query returns metadata only. Replacement inserts the new digest and revokes the prior active row in one transaction. Existing memberships are not changed.

### `authorized_enrollments`

- `id`
- `institution_id` foreign key to `instituicoes.id`
- `registration_number` plus a normalized value used for comparisons
- Nullable `name` and `email` for optional identity matching
- `status` (`active`, `inactive`, `used`)
- Nullable `used_by_user_id` foreign key to `usuarios.id`
- `created_at`, nullable `created_by_user_id`
- Unique `(institution_id, normalized_registration_number)`; the same registration number may exist in another institution

The institution scope must be taken from the authenticated principal. Repository methods should require an institution ID and never search globally on behalf of an admin.

## Atomic operations required

1. Import confirmation: in one transaction, re-check that every row selected from the preview is still unique, then insert all accepted rows. If any accepted row now conflicts, insert none. Invalid and duplicate preview rows are reported but never inserted.
2. Member creation (after the initial profile and activation rules are approved): lock or conditionally update one active enrollment, insert the user with that same institution and registration number, and mark the enrollment used by that user in one transaction. A conditional update/unique constraint must make two concurrent attempts produce at most one account.
3. Code replacement: revoke the old active code and activate the new digest together.
4. Email ownership: persist a short-lived, single-use verification digest or transactional outbox event. Do not make the user active or issue an authenticated session before confirmation.

## PostgreSQL schema received from main

| Commit by Abner Dascalakis | Change |
| --- | --- |
| `6651c3a` | Set up PostgreSQL with psycopg, SQLAlchemy, environment-based configuration and Alembic. Initial revision `f4466d87fc91` created `tipos_usuario` and `usuarios`. This predates the branch split. |
| `c34a38a` (PR #12) | Revision `3f28b0a5c719` added timestamped `criado_em` columns to users and institutions. Revision `5c91a6e3d204` added `espacos`, `recursos` and `espaco_recursos`, with stock and capacity checks and institution-scoped foreign keys. |
| `c34a38a` (PR #12), continued | Revision `7a4e9d2c6f10` added `reservas`, with PostgreSQL `btree_gist`, an exclusion constraint for overlapping approved bookings and triggers for reservation capacity and space capacity reductions. Revision `9d62e8a4b031` added `conflitos`, `notificacoes` and `notificacao_destinatarios`. This commit also added the profile seed. |
| `0f3b29a` (PR #13) | Added a transactional demo seed with one institution, four users with institutional links, three spaces, two resources, two allocations, three reservations, one conflict, and two notifications with recipients. Made the profile seed reusable in the same transaction. |

In `c34a38a`, Abner also renamed the ORM classes `User`, `UserType`, `Institution` and `UserInstitution` to `Usuario`, `TipoUsuario`, `Instituicao` and `UsuarioInstituicao` and updated their relationship annotations. The SQL table names stayed the same.

The intervening PR #11 added `instituicoes` and `usuario_instituicao` in revision `b82c7e4a91d3` and `usuarios.phone` in revision `b5373791b0ff`. These changes came from other contributors. The membership table stores a role, status and optional registration number. Its uniqueness constraints are per user and institution, and per institution and registration number.

## Repository integration gaps

- **Identity and authorization.** PostgreSQL uses numeric primary keys and supports more than one institution per user. The domain uses string IDs and one institution on the authenticated principal. The adapter needs a rule for selecting the active institution and for mapping the status and role of the membership alongside the legacy account fields `role` and `tipo_usuario_id`. It also needs to enforce the last-active-admin constraint within a database transaction.
- **Hashes and sessions.** The two implementations use PBKDF2-SHA256 with different encodings (hex in the PostgreSQL seed, Base64 in the authentication service). Stored hashes need compatible verification or an upgrade path. The current schema has no store for session digests and revocations.
- **Enrollment and invitations.** The registration number on a membership can represent a completed link. Invitation digests, preauthorized and normalized registrations, and pending e-mail verification need their own persistence. The domain enrollment states are `ativo`, `inativo` and `utilizado`.
- **Institutional settings.** The SQL model has contact fields but lacks address, timezone and the preferences consumed by the application. Align validation limits too, such as the SQL institution name limit of 150 versus the API registration limit of 180.
- **Rooms, resources and plants.** SQL spaces have text location and two statuses, `disponivel` and `bloqueado`. The domain uses buildings and floors, also supports `ocupado` and `inativo`, and scopes room names by floor while SQL scopes them by institution. SQL resources track stock and allocation quantities, and the domain tracks activation and a set of resource associations. Plans, private file references and room markers need persistence.
- **Audit and reporting.** There is no administrative audit table. A database adapter must persist administrative mutations and audit events in one transaction. Reservations, conflicts and notifications have SQL tables, and the current runtime still needs the corresponding adapters and queries.

The SQLAlchemy mappings and Alembic revision graph can be inspected without a database connection. SQL constraints and triggers still require PostgreSQL integration tests.
