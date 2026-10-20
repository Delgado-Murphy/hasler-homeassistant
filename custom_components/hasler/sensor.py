"""Diagnostic sensors: update channel and when the radio's software last started."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import HaslerConfigEntry, HaslerCoordinator, HaslerData
from .entity import HaslerEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class HaslerSensorDescription(SensorEntityDescription):
    value: Callable[[HaslerData], str | datetime | None]


SENSORS: tuple[HaslerSensorDescription, ...] = (
    HaslerSensorDescription(
        key="update_channel",
        translation_key="update_channel",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: (d.software or {}).get("channel"),
    ),
    HaslerSensorDescription(
        key="started",
        translation_key="started",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.started,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: HaslerConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(HaslerSensor(entry.runtime_data, desc) for desc in SENSORS)


class HaslerSensor(HaslerEntity, SensorEntity):
    entity_description: HaslerSensorDescription

    def __init__(self, coordinator: HaslerCoordinator, description: HaslerSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | datetime | None:
        return self.entity_description.value(self.coordinator.data)
