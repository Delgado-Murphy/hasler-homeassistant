"""Config flow for the Hasler radio: zeroconf discovery or a typed-in host."""

from __future__ import annotations

import logging
from ipaddress import IPv6Address
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import HaslerClient, HaslerError, HaslerNotFoundError
from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="hasler.local"): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
    }
)


class CannotConnect(Exception):
    """The host is not a reachable Hasler radio."""


async def _identify(client: HaslerClient) -> dict[str, Any]:
    """``/api/info``, or for older radios a ``/api/status`` sanity check (no id)."""
    try:
        info = await client.info()
        if isinstance(info, dict):
            return info
    except HaslerNotFoundError:
        pass
    except HaslerError as err:
        raise CannotConnect from err
    try:
        status = await client.status()
    except HaslerError as err:
        raise CannotConnect from err
    if not isinstance(status, dict) or "keys" not in status or "standby" not in status:
        raise CannotConnect
    return {}


class HaslerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hasler."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._name: str = DEFAULT_NAME

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A host typed in by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            client = HaslerClient(async_get_clientsession(self.hass), host, port)
            try:
                info = await _identify(client)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error identifying Hasler at %s", host)
                errors["base"] = "unknown"
            else:
                data = {CONF_HOST: host, CONF_PORT: port}
                if radio_id := info.get("id"):
                    await self.async_set_unique_id(str(radio_id))
                    self._abort_if_unique_id_configured(updates=data)
                else:
                    self._async_abort_entries_match({CONF_HOST: host})
                return self.async_create_entry(title=str(info.get("name") or DEFAULT_NAME), data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """A radio announced itself as _hasler._tcp."""
        if isinstance(discovery_info.ip_address, IPv6Address):
            return self.async_abort(reason="not_ipv4")
        props = discovery_info.properties or {}
        radio_id = props.get("id")
        if not radio_id:
            return self.async_abort(reason="no_id")
        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT

        await self.async_set_unique_id(str(radio_id))
        # Same radio, new IP: follow it.
        self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})

        # A radio added by hand from an older release (no id yet) at this host:
        # adopt the id instead of offering it twice.
        for entry in self._async_current_entries(include_ignore=False):
            if entry.unique_id is None and entry.data.get(CONF_HOST) == host:
                self.hass.config_entries.async_update_entry(entry, unique_id=str(radio_id))
                return self.async_abort(reason="already_configured")

        self._host, self._port = host, port
        self._name = str(props.get("name") or DEFAULT_NAME)
        self.context["title_placeholders"] = {CONF_NAME: self._name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask before adding a discovered radio."""
        assert self._host is not None
        if user_input is not None:
            client = HaslerClient(async_get_clientsession(self.hass), self._host, self._port)
            try:
                await _identify(client)
            except CannotConnect:
                return self.async_abort(reason="cannot_connect")
            return self.async_create_entry(
                title=self._name, data={CONF_HOST: self._host, CONF_PORT: self._port}
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={CONF_NAME: self._name, CONF_HOST: self._host},
        )
