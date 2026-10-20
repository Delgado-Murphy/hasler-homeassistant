"""Polls the radio: status every 5 s, health every minute, software every 5 min."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import HaslerClient, HaslerError
from .const import DOMAIN, HEALTH_INTERVAL, SOFTWARE_INTERVAL, STATUS_INTERVAL

_LOGGER = logging.getLogger(__name__)

type HaslerConfigEntry = ConfigEntry[HaslerCoordinator]


@dataclass
class HaslerData:
    """The latest documents from the radio."""

    status: dict[str, Any]
    software: dict[str, Any] | None = None
    health: dict[str, Any] | None = None
    started: datetime | None = None
    info: dict[str, Any] = field(default_factory=dict)


class HaslerCoordinator(DataUpdateCoordinator[HaslerData]):
    """One coordinator per radio."""

    config_entry: HaslerConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: HaslerConfigEntry, client: HaslerClient, info: dict[str, Any]
    ) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=STATUS_INTERVAL
        )
        self.client = client
        self.info = info
        self._software: dict[str, Any] | None = None
        self._health: dict[str, Any] | None = None
        self._started: datetime | None = None
        self._software_at: datetime | None = None
        self._health_at: datetime | None = None
        # The last preset key that was lit, so "play" can bring it back.
        self.last_key: str | None = None

    def _due(self, last: datetime | None, every: timedelta, now: datetime) -> bool:
        return last is None or now - last >= every

    async def _async_update_data(self) -> HaslerData:
        try:
            status = await self.client.status()
        except HaslerError as err:
            raise UpdateFailed(f"Hasler at {self.client.host} did not answer: {err}") from err
        if not isinstance(status, dict):
            raise UpdateFailed("Hasler sent an unexpected status document")
        if status.get("current_key"):
            self.last_key = status["current_key"]

        now = dt_util.utcnow()
        if self._due(self._health_at, HEALTH_INTERVAL, now):
            await self._refresh_health(now)
        if self._due(self._software_at, SOFTWARE_INTERVAL, now):
            await self._refresh_software(now)

        return HaslerData(
            status=status,
            software=self._software,
            health=self._health,
            started=self._started,
            info=self.info,
        )

    async def _refresh_health(self, now: datetime) -> None:
        try:
            health = await self.client.health()
        except HaslerError as err:
            _LOGGER.debug("Hasler health check failed: %s", err)
            self._health = None
        else:
            self._health = health if isinstance(health, dict) else None
            uptime = (self._health or {}).get("uptime_s")
            if isinstance(uptime, (int, float)) and not isinstance(uptime, bool):
                started = now - timedelta(seconds=uptime)
                # Keep the timestamp steady across polls; move it only on a restart.
                if self._started is None or abs((started - self._started).total_seconds()) > 120:
                    self._started = started.replace(microsecond=0)
        self._health_at = now

    async def _refresh_software(self, now: datetime) -> None:
        try:
            software = await self.client.software()
        except HaslerError as err:
            _LOGGER.debug("Hasler software status failed: %s", err)
        else:
            self._software = software if isinstance(software, dict) else None
        self._software_at = now

    async def async_refresh_software(self) -> None:
        """Re-read /api/software now (after the radio installs something)."""
        await self._refresh_software(dt_util.utcnow())

    @property
    def sw_version(self) -> str | None:
        for doc in (self._software, self._health, self.info):
            if doc and doc.get("version"):
                return str(doc["version"])
        return None
