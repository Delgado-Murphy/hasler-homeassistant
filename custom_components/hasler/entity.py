"""Base entity for the Hasler radio."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import base_url
from .const import DEFAULT_NAME, DOMAIN, MANUFACTURER
from .coordinator import HaslerCoordinator


class HaslerEntity(CoordinatorEntity[HaslerCoordinator]):
    """Everything here belongs to one radio device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HaslerCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        # entry_id, not the radio id: a hand-added radio from an older release
        # gains its id later (zeroconf) and its entities must not move.
        radio_id = entry.entry_id
        self._attr_unique_id = f"{radio_id}_{key}"
        info = coordinator.info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, radio_id)},
            manufacturer=MANUFACTURER,
            model=str(info.get("variant") or DEFAULT_NAME),
            name=str(info.get("name") or entry.title or DEFAULT_NAME),
            sw_version=coordinator.sw_version,
            configuration_url=base_url(coordinator.client.host, coordinator.client.port) + "/",
        )
