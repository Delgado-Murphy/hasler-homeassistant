"""The Hasler radio integration."""

from __future__ import annotations

import logging

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HaslerClient, HaslerConnectionError, HaslerError, HaslerNotFoundError
from .const import DEFAULT_PORT
from .coordinator import HaslerConfigEntry, HaslerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
    Platform.UPDATE,
]


async def async_setup_entry(hass: HomeAssistant, entry: HaslerConfigEntry) -> bool:
    """Set up a radio from a config entry."""
    client = HaslerClient(
        async_get_clientsession(hass), entry.data[CONF_HOST], entry.data.get(CONF_PORT, DEFAULT_PORT)
    )
    try:
        info = await client.info()
    except HaslerNotFoundError:
        info = {}  # an older radio without /api/info: status still works
    except HaslerConnectionError as err:
        raise ConfigEntryNotReady(f"Hasler at {client.host} is not reachable: {err}") from err
    except HaslerError:
        info = {}
    if not isinstance(info, dict):
        info = {}

    coordinator = HaslerCoordinator(hass, entry, client, info)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    @callback
    def _sync_sw_version() -> None:
        version = coordinator.sw_version
        registry = dr.async_get(hass)
        for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
            if version and device.sw_version != version:
                registry.async_update_device(device.id, sw_version=version)

    entry.async_on_unload(coordinator.async_add_listener(_sync_sw_version))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaslerConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
