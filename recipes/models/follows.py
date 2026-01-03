"""Legacy follow relationship table without reverse accessors.

Kept solely so historical migrations can import _uuid7_or_4 for defaults.
The runtime app no longer registers this model.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q, F
from recipes.utils.uuid import uuid7_or_4


# Backward compat for migrations pointing at this module-level name
_uuid7_or_4 = uuid7_or_4

# Model intentionally removed from runtime; left for migration imports only.
