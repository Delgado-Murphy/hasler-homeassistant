"""Read-only software update entity: what runs and what the radio could install."""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity, UpdateEntityFeature
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import HaslerConfigEntry, HaslerCoordinator
from .entity import HaslerEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: HaslerConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([HaslerUpdate(entry.runtime_data)])


class HaslerUpdate(HaslerEntity, UpdateEntity):
    """The radio installs its own updates (with a press on the radio); this only reports."""

    _attr_translation_key = "software"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_supported_features = UpdateEntityFeature.RELEASE_NOTES

    def __init__(self, coordinator: HaslerCoordinator) -> None:
        super().__init__(coordinator, "software")

    @property
    def _software(self) -> dict[str, Any]:
        return self.coordinator.data.software or {}

    @property
    def _available(self) -> dict[str, Any] | None:
        avail = self._software.get("available")
        return avail if isinstance(avail, dict) and avail.get("version") else None

    @property
    def installed_version(self) -> str | None:
        return self._software.get("version") or self.coordinator.sw_version

    @property
    def latest_version(self) -> str | None:
        if self._available:
            return str(self._available["version"])
        return self.installed_version

    @property
    def release_summary(self) -> str | None:
        notes = (self._available or {}).get("notes") or ""
        return notes[:255] or None

    @property
    def in_progress(self) -> bool:
        return bool(self._software.get("busy"))

    async def async_release_notes(self) -> str | None:
        return (self._available or {}).get("notes") or None
