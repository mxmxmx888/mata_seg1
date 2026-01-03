"""UUID helpers."""

import uuid


def uuid7_or_4() -> uuid.UUID:
    """Return uuid7 when available, else uuid4 (used for primary keys)."""
    return getattr(uuid, "uuid7", uuid.uuid4)()
