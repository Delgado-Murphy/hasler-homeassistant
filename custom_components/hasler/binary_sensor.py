"""Health problem binary sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import HaslerConfigEntry, HaslerCoordinator
from .entity import HaslerEntity

PARALLEL_UPDATES = 0

# A check passes when it is true or "ok" (the panel reports a word).
GOOD = (True, "ok")


async def async_setup_entry(
    hass: HomeAssistant, entry: HaslerConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([HaslerHealthProblem(entry.runtime_data)])


class HaslerHealthProblem(HaslerEntity, BinarySensorEntity):
    """On when the radio's own health report says something is wrong."""

    _attr_translation_key = "health"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HaslerCoordinator) -> None:
        super().__init__(coordinator, "health")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.health is not None

    @property
    def is_on(self) -> bool | None:
        health = self.coordinator.data.health
        if health is None:
            return None
        return not health.get("ok", False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.data.health or {}
        checks = health.get("checks") if isinstance(health.get("checks"), dict) else {}
        return {"failing_checks": sorted(k for k, v in checks.items() if v not in GOOD)}
