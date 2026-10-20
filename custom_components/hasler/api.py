"""A small async client for the Hasler radio's local HTTP API.

The radio trusts its LAN: there is no login. State-changing requests must
carry ``Content-Type: application/json`` and a ``Host`` that is one of the
radio's own names or addresses (``hasler.local`` or the IP we connect to).
aiohttp derives ``Host`` from the URL, so we always talk to the same host the
user (or zeroconf) gave us and never set ``Origin``/``Referer``.
"""

from __future__ import annotations

import asyncio
from ipaddress import IPv6Address, ip_address
from typing import Any

import aiohttp

REQUEST_TIMEOUT = 10


class HaslerError(Exception):
    """Base error talking to the radio."""


class HaslerConnectionError(HaslerError):
    """The radio could not be reached or answered with garbage."""


class HaslerNotFoundError(HaslerError):
    """The radio does not have this endpoint (an older release)."""


class HaslerRequestError(HaslerError):
    """The radio refused a request (4xx/5xx)."""


def base_url(host: str, port: int) -> str:
    """``http://host:port`` with IPv6 literals bracketed."""
    try:
        if isinstance(ip_address(host), IPv6Address):
            host = f"[{host}]"
    except ValueError:
        pass
    return f"http://{host}:{port}"


class HaslerClient:
    """Talks to one radio."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int) -> None:
        self._session = session
        self.host = host
        self.port = port
        self.url = base_url(host, port)

    async def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None, *, ok_codes: tuple[int, ...] = (200,)
    ) -> Any:
        kwargs: dict[str, Any] = {}
        if method != "GET":
            # json= sets Content-Type: application/json, which the radio insists on.
            kwargs["json"] = body if body is not None else {}
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.request(method, self.url + path, **kwargs) as resp:
                    if resp.status == 404:
                        raise HaslerNotFoundError(path)
                    if resp.status not in ok_codes:
                        text = (await resp.text())[:200]
                        raise HaslerRequestError(f"{method} {path}: HTTP {resp.status} {text}".strip())
                    try:
                        return await resp.json(content_type=None)
                    except ValueError as err:
                        raise HaslerConnectionError(f"{path}: not JSON") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            raise HaslerConnectionError(f"{method} {path}: {err or type(err).__name__}") from err

    # -- reads ---------------------------------------------------------------

    async def info(self) -> dict[str, Any]:
        """``/api/info`` (id, name, version, variant, api); 404 on older radios."""
        return await self._request("GET", "/api/info")

    async def status(self) -> dict[str, Any]:
        return await self._request("GET", "/api/status")

    async def software(self) -> dict[str, Any]:
        return await self._request("GET", "/api/software")

    async def health(self) -> dict[str, Any]:
        # 503 still carries a JSON report ({"ok": false, ...}).
        return await self._request("GET", "/api/health", ok_codes=(200, 503))

    # -- writes --------------------------------------------------------------

    async def press(self, key: str, event: str = "tap") -> None:
        await self._request("POST", "/api/press", {"key": key, "event": event})

    async def stop(self) -> None:
        await self._request("POST", "/api/stop")

    async def next(self) -> None:
        await self._request("POST", "/api/next")

    async def set_volume(self, value: int) -> int | None:
        doc = await self._request("POST", "/api/volume", {"value": value})
        return doc.get("volume") if isinstance(doc, dict) else None

    async def nudge_volume(self, delta: int) -> int | None:
        doc = await self._request("POST", "/api/volume", {"delta": delta})
        return doc.get("volume") if isinstance(doc, dict) else None

    async def set_standby(self, on: bool) -> None:
        await self._request("POST", "/api/standby", {"on": on})
