"""Entities against a mocked radio."""

from __future__ import annotations

import copy
from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_VOLUME_LEVEL,
    SERVICE_SELECT_SOURCE,
)
from homeassistant.components.media_player import (
    DOMAIN as MP_DOMAIN,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_STOP,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.hasler.const import DOMAIN

from .conftest import STATUS, URL, mock_radio

MP = "media_player.hasler"


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def posts(aioclient_mock: AiohttpClientMocker) -> list[tuple[str, object]]:
    return [(str(c[1]).removeprefix(URL), c[2]) for c in aioclient_mock.mock_calls if c[0] == "POST"]


async def test_setup_and_device(hass: HomeAssistant, radio, config_entry) -> None:
    await setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    [device] = dr.async_entries_for_config_entry(dr.async_get(hass), config_entry.entry_id)
    assert (DOMAIN, config_entry.entry_id) in device.identifiers
    assert device.manufacturer == "Delgado & Murphy"
    assert device.model == "Hasler HAT v1"
    assert device.sw_version == "0.3.5"
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_not_ready_when_unreachable(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    aioclient_mock.get(f"{URL}/api/info", exc=TimeoutError)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_media_player_state(hass: HomeAssistant, radio, config_entry) -> None:
    await setup(hass, config_entry)
    state = hass.states.get(MP)
    assert state.state == STATE_PLAYING
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.26
    assert state.attributes[ATTR_MEDIA_TITLE] == "Radio Swiss Jazz"
    assert state.attributes["media_channel"] == "Radio Swiss Jazz"
    # Only keys that play a preset are sources; k4 ("Next") is not.
    assert state.attributes[ATTR_INPUT_SOURCE_LIST] == [
        "1 · Rosalia", "2 · Radio Swiss Jazz", "3 · RNE Radio 3", "PU · Espresso Macchiato radio",
    ]
    assert state.attributes[ATTR_INPUT_SOURCE] == "2 · Radio Swiss Jazz"


async def test_media_player_ytm_track_and_standby(
    hass: HomeAssistant, aioclient_mock, config_entry, freezer: FrozenDateTimeFactory
) -> None:
    status = copy.deepcopy(STATUS)
    status.update(source="ytm", current_key="k1",
                  playing={"n": 6, "name": "Rosalia", "source": "ytm", "uri": "x", "shuffle": True},
                  track={"title": "Despechá", "artist": "Rosalía", "album": "Motomami", "thumb": "https://i.ytimg.com/x.jpg"})
    mock_radio(aioclient_mock, status=status)
    await setup(hass, config_entry)
    state = hass.states.get(MP)
    assert state.attributes[ATTR_MEDIA_TITLE] == "Despechá"
    assert state.attributes["media_artist"] == "Rosalía"
    assert state.attributes["media_album_name"] == "Motomami"
    assert state.attributes["entity_picture"]

    status = copy.deepcopy(STATUS)
    status.update(standby=True, playing=None, current_key=None)
    mock_radio(aioclient_mock, status=status)
    freezer.tick(timedelta(seconds=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(MP).state == STATE_OFF


async def test_media_player_commands(hass: HomeAssistant, radio, config_entry) -> None:
    await setup(hass, config_entry)
    radio.clear_requests()
    mock_radio(radio)

    async def call(service: str, **data) -> None:
        await hass.services.async_call(MP_DOMAIN, service, {ATTR_ENTITY_ID: MP, **data}, blocking=True)

    await call(SERVICE_SELECT_SOURCE, **{ATTR_INPUT_SOURCE: "3 · RNE Radio 3"})
    await call(SERVICE_VOLUME_SET, **{ATTR_MEDIA_VOLUME_LEVEL: 0.4})
    await call(SERVICE_VOLUME_UP)
    await call(SERVICE_MEDIA_NEXT_TRACK)
    await call(SERVICE_MEDIA_STOP)
    await call(SERVICE_MEDIA_PLAY)
    await call(SERVICE_TURN_OFF)
    await call(SERVICE_TURN_ON)
    assert posts(radio) == [
        ("/api/press", {"key": "k3", "event": "tap"}),
        ("/api/volume", {"value": 40}),
        ("/api/volume", {"delta": 5}),
        ("/api/next", {}),
        ("/api/stop", {}),
        ("/api/press", {"key": "k2", "event": "tap"}),   # the last lit key
        ("/api/standby", {"on": True}),
        ("/api/standby", {"on": False}),
    ]


async def test_writes_send_json_content_type(hass: HomeAssistant, socket_enabled) -> None:
    """The radio refuses writes without Content-Type: application/json (a real request)."""
    from aiohttp import ClientSession, web
    from aiohttp.test_utils import TestServer

    from custom_components.hasler.api import HaslerClient

    seen = {}

    async def handler(request: web.Request) -> web.Response:
        seen["ctype"] = request.headers.get("Content-Type", "")
        seen["host"] = request.headers.get("Host", "")
        seen["origin"] = request.headers.get("Origin")
        seen["body"] = await request.json()
        return web.json_response({"ok": True, "standby": True})

    app = web.Application()
    app.router.add_post("/api/standby", handler)
    server = TestServer(app, host="127.0.0.1")
    await server.start_server()
    port = server.port
    try:
        async with ClientSession() as session:
            await HaslerClient(session, "127.0.0.1", port).set_standby(True)
    finally:
        await server.close()
    assert seen["ctype"].split(";")[0] == "application/json"
    # The radio accepts a Host that is the address it was reached on.
    assert seen["host"] == f"127.0.0.1:{port}"
    assert seen["origin"] is None
    assert seen["body"] == {"on": True}


async def test_update_entity(hass: HomeAssistant, radio, config_entry) -> None:
    await setup(hass, config_entry)
    state = hass.states.get("update.hasler_software")
    assert state.state == STATE_ON
    assert state.attributes["installed_version"] == "0.3.5"
    assert state.attributes["latest_version"] == "0.3.6"
    assert state.attributes["release_summary"].startswith("Quieter fan.")


async def test_diagnostics(hass: HomeAssistant, radio, config_entry) -> None:
    await setup(hass, config_entry)
    assert hass.states.get("binary_sensor.hasler_health_problem").state == STATE_OFF
    assert hass.states.get("sensor.hasler_update_channel").state == "stable"
    assert hass.states.get("sensor.hasler_software_started").state not in ("unknown", "unavailable")


async def test_health_problem(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    mock_radio(aioclient_mock, health={"version": "0.3.5", "ok": False, "uptime_s": 10,
                                       "checks": {"mpd": False, "panel": "ok", "web": True}})
    await setup(hass, config_entry)
    state = hass.states.get("binary_sensor.hasler_health_problem")
    assert state.state == STATE_ON
    assert state.attributes["failing_checks"] == ["mpd"]
