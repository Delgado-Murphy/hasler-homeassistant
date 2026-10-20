"""Config flow: manual host, /api/info fallback, zeroconf discovery."""

from __future__ import annotations

from ipaddress import ip_address
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.hasler.const import DOMAIN

from .conftest import HOST, INFO, PORT, RADIO_ID, URL, mock_radio


@pytest.fixture(autouse=True)
def no_setup():
    with patch("custom_components.hasler.async_setup_entry", return_value=True):
        yield


def zeroconf_info(host: str = HOST) -> ZeroconfServiceInfo:
    # What avahi announces: no id/name, only where to ask.
    props = {"api": "1", "path": "/api/info"}
    return ZeroconfServiceInfo(
        ip_address=ip_address(host), ip_addresses=[ip_address(host)], port=PORT,
        hostname="hasler.local.", type="_hasler._tcp.local.", name="Hasler._hasler._tcp.local.",
        properties=props,
    )


async def test_user_flow_with_info(hass: HomeAssistant, radio: AiohttpClientMocker) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Hasler"
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: PORT}
    assert result["result"].unique_id == RADIO_ID


async def test_user_flow_older_radio_falls_back_to_status(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    mock_radio(aioclient_mock, info=None)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id is None
    assert any(str(call[1]).endswith("/api/status") for call in aioclient_mock.mock_calls)


async def test_user_flow_cannot_connect(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{URL}/api/info", exc=TimeoutError)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_not_a_hasler(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{URL}/api/info", status=404)
    aioclient_mock.get(f"{URL}/api/status", json={"hello": "world"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, radio: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_discovery(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    mock_radio(aioclient_mock, info={**INFO, "name": "Kitchen Hasler"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=zeroconf_info()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kitchen Hasler"
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: PORT}
    assert result["result"].unique_id == RADIO_ID


async def test_zeroconf_updates_host(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    mock_radio(aioclient_mock, url="http://192.168.1.77:8080")
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=zeroconf_info(host="192.168.1.77")
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "192.168.1.77"


async def test_zeroconf_adopts_hand_added_radio(hass: HomeAssistant, radio: AiohttpClientMocker) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST, CONF_PORT: PORT})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=zeroconf_info()
    )
    assert result["reason"] == "already_configured"
    assert entry.unique_id == RADIO_ID


async def test_zeroconf_info_without_id(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    mock_radio(aioclient_mock, info={"name": "Hasler", "api": 1})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=zeroconf_info()
    )
    assert result["reason"] == "no_id"


async def test_zeroconf_unreachable(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{URL}/api/info", exc=TimeoutError)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=zeroconf_info()
    )
    assert result["reason"] == "cannot_connect"
