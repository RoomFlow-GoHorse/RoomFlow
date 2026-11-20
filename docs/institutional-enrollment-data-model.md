# Future persistence: institutional invitations and authorized enrollments

The current API and Streamlit application use in-memory repositories. Their contents and invitation/import previews are temporary and reset when the process restarts. This document records the database contract to align with the database owner; it does not change or migrate the current schema.

## Suggested entities

### `institution_invite_codes`

- `id`
- `institution_id` foreign key to `institutions.id`
- `code_digest` (SHA-256 digest of a high-entropy random code; never persist the raw code)
- `created_at` and nullable `revoked_at`
- Optional `created_by_user_id` for audit
- Unique `code_digest`
- At most one active row per institution, enforced with a partial unique index or a current-code pointer

The application returns a raw code only when it creates/replaces it. A status query returns metadata only. Replacement inserts the new digest and revokes the prior active row in one transaction. Existing memberships are not changed.

### `authorized_enrollments`

- `id`
- `institution_id` foreign key to `institutions.id`
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

## Existing schema alignment needed

The current SQLAlchemy models and migration do not contain an institution table, institutional membership relation, invitation codes, authorized enrollments, or a matricula field on users. The database owner should align those entities/columns and constraints with the existing `usuarios` and `tipos_usuario` tables. The domain currently models one institution ID on a user; confirm whether memberships are one-to-many before choosing the final foreign-key shape. Keep the single domain concept `Profile` and map it to the existing `role` and `tipo_usuario_id` only after that mapping is agreed.
