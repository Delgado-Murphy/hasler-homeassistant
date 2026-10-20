"""Constants for the Hasler radio integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "hasler"
MANUFACTURER: Final = "Delgado & Murphy"
DEFAULT_PORT: Final = 8080
DEFAULT_NAME: Final = "Hasler"

STATUS_INTERVAL: Final = timedelta(seconds=5)
HEALTH_INTERVAL: Final = timedelta(seconds=60)
SOFTWARE_INTERVAL: Final = timedelta(minutes=5)

# How much one volume_up / volume_down moves the radio's 0-100 knob scale.
VOLUME_STEP: Final = 5

# Sources that own the speaker without an MPD preset playing.
RENDERER_SOURCES: Final = frozenset({"spotify", "airplay", "bluetooth"})
