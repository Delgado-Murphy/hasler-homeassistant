"""Opt-in, read-only: set the integration up against a real radio.

    HASLER_LIVE_HOST=192.168.1.50 pytest tests/test_live.py

Only GETs are sent (no services are called), so it is safe on a radio in use.
"""

from __future__ import annotations

import os

import pytest
import pytest_socket
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hasler.const import DOMAIN

LIVE_HOST = os.environ.get("HASLER_LIVE_HOST")

pytestmark = pytest.mark.skipif(not LIVE_HOST, reason="set HASLER_LIVE_HOST to test a real radio")


async def test_live_radio(hass: HomeAssistant, socket_enabled) -> None:
    pytest_socket.socket_allow_hosts([LIVE_HOST, "127.0.0.1"])
    entry = MockConfigEntry(domain=DOMAIN, title="Hasler", data={CONF_HOST: LIVE_HOST, CONF_PORT: 8080})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    for state in sorted(hass.states.async_all(), key=lambda s: s.entity_id):
        print(state.entity_id, state.state, dict(state.attributes))
    assert hass.states.get("media_player.hasler").state in ("playing", "idle", "off")
    assert hass.states.get("update.hasler_software").attributes["installed_version"]
    assert await hass.config_entries.async_unload(entry.entry_id)
