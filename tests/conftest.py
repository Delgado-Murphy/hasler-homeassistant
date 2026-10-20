"""Fixtures: a mocked Hasler radio HTTP API."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.hasler.const import DOMAIN

HOST = "192.168.1.50"
PORT = 8080
URL = f"http://{HOST}:{PORT}"
RADIO_ID = "b8:27:eb:12:34:56"

INFO = {"id": RADIO_ID, "name": "Hasler", "version": "0.3.5", "variant": "Hasler HAT v1", "api": 1}

STATUS = {
    "pressed": [],
    "playing": {"n": 2, "name": "Radio Swiss Jazz", "source": "radio",
                "uri": "http://stream.srg-ssr.ch/m/rsj/mp3_128", "shuffle": False},
    "standby": False,
    "volume": 26,
    "source": "radio",
    "waiting": False,
    "renderer": None,
    "track": None,
    "keys": [
        {"id": "k1", "label": "1", "n": 6, "name": "Rosalia", "source": "ytm"},
        {"id": "k2", "label": "2", "n": 2, "name": "Radio Swiss Jazz", "source": "radio"},
        {"id": "k3", "label": "3", "n": 3, "name": "RNE Radio 3", "source": "radio"},
        {"id": "k4", "label": "4", "n": None, "name": "Next", "source": None},
        {"id": "pu", "label": "PU", "n": 7, "name": "Espresso Macchiato radio", "source": "ytm"},
    ],
    "current_key": "k2",
    "volume_limit": 90,
    "tone": {"value": 41, "treble_db": -2.1},
    "knob_on": True,
}

SOFTWARE = {
    "version": "0.3.5", "channel": "stable", "update_mode": "ask",
    "last_check": "2026-10-20T03:19:42Z", "check_error": None,
    "available": {"version": "0.3.6", "seq": 12, "notes": "Quieter fan.\n\nFaster start.",
                  "kind": "app", "requires_migration": False, "staged": True},
    "releases": [], "stale": False, "approved": None, "busy": False,
}

HEALTH = {
    "version": "0.3.5", "ok": True, "uptime_s": 3600,
    "checks": {"mpd": True, "audio_card": True, "panel": "ok", "lamp": True, "web": True},
    "idle": False, "standby": False, "playing": True, "last_play_s": 0,
}


def mock_radio(
    aioclient_mock: AiohttpClientMocker,
    *,
    info: dict[str, Any] | None = INFO,
    status: dict[str, Any] | None = None,
    software: dict[str, Any] | None = None,
    health: dict[str, Any] | None = None,
    url: str = URL,
) -> None:
    """Serve the radio's API; ``info=None`` plays an older radio (404)."""
    aioclient_mock.clear_requests()
    if info is None:
        aioclient_mock.get(f"{url}/api/info", status=404, text="not found")
    else:
        aioclient_mock.get(f"{url}/api/info", json=info)
    aioclient_mock.get(f"{url}/api/status", json=status or copy.deepcopy(STATUS))
    aioclient_mock.get(f"{url}/api/software", json=software or copy.deepcopy(SOFTWARE))
    aioclient_mock.get(f"{url}/api/health", json=health or copy.deepcopy(HEALTH))
    for path in ("press", "stop", "next", "standby"):
        aioclient_mock.post(f"{url}/api/{path}", json={"ok": True})
    aioclient_mock.post(f"{url}/api/volume", json={"ok": True, "volume": 50})


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, title="Hasler", unique_id=RADIO_ID, data={CONF_HOST: HOST, CONF_PORT: PORT}
    )


@pytest.fixture
def radio(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    mock_radio(aioclient_mock)
    return aioclient_mock
