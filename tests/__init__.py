"""RoomFlow tests."""

import os

# Production defaults to PostgreSQL; unit/UI tests explicitly use the demo runtime.
os.environ.setdefault("APP_ENV", "test")

os.environ.setdefault("ROOMFLOW_PERSISTENCE", "memory")
