"""The radio as a media player."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import HaslerError, base_url
from .const import DOMAIN, RENDERER_SOURCES, VOLUME_STEP
from .coordinator import HaslerConfigEntry, HaslerCoordinator
from .entity import HaslerEntity

PARALLEL_UPDATES = 1

SUPPORTED = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.SELECT_SOURCE
)


async def async_setup_entry(
    hass: HomeAssistant, entry: HaslerConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([HaslerMediaPlayer(entry.runtime_data)])


def source_name(key: dict[str, Any]) -> str:
    """How a preset key shows in the source list: "1 · Radio Swiss Jazz"."""
    label = str(key.get("label") or key.get("id") or "")
    name = str(key.get("name") or "").strip()
    return f"{label} · {name}" if name else label


class HaslerMediaPlayer(HaslerEntity, MediaPlayerEntity):
    """Hasler: presets on keys, a volume knob and a standby switch."""

    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = SUPPORTED
    _attr_media_content_type = MediaType.MUSIC

    def __init__(self, coordinator: HaslerCoordinator) -> None:
        super().__init__(coordinator, "media_player")

    # -- state ---------------------------------------------------------------

    @property
    def _status(self) -> dict[str, Any]:
        return self.coordinator.data.status

    @property
    def _preset_keys(self) -> list[dict[str, Any]]:
        return [k for k in self._status.get("keys") or [] if isinstance(k, dict) and k.get("n") is not None]

    @property
    def state(self) -> MediaPlayerState:
        status = self._status
        if status.get("standby"):
            return MediaPlayerState.OFF
        if status.get("playing"):
            return MediaPlayerState.PLAYING
        if status.get("source") in RENDERER_SOURCES and not status.get("waiting"):
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        volume = self._status.get("volume")
        if isinstance(volume, (int, float)) and not isinstance(volume, bool):
            return max(0.0, min(1.0, volume / 100))
        return None

    @property
    def source_list(self) -> list[str]:
        return [source_name(k) for k in self._preset_keys]

    @property
    def source(self) -> str | None:
        current = self._status.get("current_key")
        for key in self._preset_keys:
            if key.get("id") == current:
                return source_name(key)
        return None

    def _now_playing(self) -> dict[str, str]:
        status = self._status
        track = status.get("track") if isinstance(status.get("track"), dict) else None
        renderer = status.get("renderer") if isinstance(status.get("renderer"), dict) else None
        playing = status.get("playing") if isinstance(status.get("playing"), dict) else None
        out: dict[str, str] = {}
        if track and track.get("title"):
            out = {k: track.get(k) or "" for k in ("title", "artist", "album", "thumb")}
        elif renderer and renderer.get("title"):
            out = {"title": renderer.get("title") or "", "artist": renderer.get("artist") or ""}
        if playing and playing.get("name"):
            out.setdefault("title", playing["name"])
            out["channel"] = playing["name"]
        return out

    @property
    def media_title(self) -> str | None:
        return self._now_playing().get("title") or None

    @property
    def media_artist(self) -> str | None:
        return self._now_playing().get("artist") or None

    @property
    def media_album_name(self) -> str | None:
        return self._now_playing().get("album") or None

    @property
    def media_channel(self) -> str | None:
        return self._now_playing().get("channel") or None

    @property
    def media_image_url(self) -> str | None:
        # The radio's own cover endpoint ("/api/art/current?k=<hash>"): k changes
        # with the picture, so the URL (and HA's image cache key) follows it.
        art = self._status.get("art")
        if isinstance(art, str) and art:
            if art.startswith(("http://", "https://")):
                return art
            client = self.coordinator.client
            return base_url(client.host, client.port) + "/" + art.lstrip("/")
        return self._now_playing().get("thumb") or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        status = self._status
        return {
            "speaker_source": status.get("source"),
            "waiting": status.get("waiting"),
            "volume_limit": status.get("volume_limit"),
        }

    # -- commands ------------------------------------------------------------

    async def _run(self, call: Awaitable[Any]) -> None:
        try:
            await call
        except HaslerError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self._run(self.coordinator.client.set_standby(False))

    async def async_turn_off(self) -> None:
        await self._run(self.coordinator.client.set_standby(True))

    async def async_media_play(self) -> None:
        if self._status.get("standby"):
            # Waking resumes the last preset, like turning the knob on.
            await self._run(self.coordinator.client.set_standby(False))
            return
        keys = [k.get("id") for k in self._preset_keys]
        key = self.coordinator.last_key if self.coordinator.last_key in keys else (keys[0] if keys else None)
        if key is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_presets")
        await self._run(self.coordinator.client.press(key))

    async def async_media_stop(self) -> None:
        await self._run(self.coordinator.client.stop())

    async def async_media_next_track(self) -> None:
        await self._run(self.coordinator.client.next())

    async def async_set_volume_level(self, volume: float) -> None:
        await self._run(self.coordinator.client.set_volume(round(volume * 100)))

    async def async_volume_up(self) -> None:
        await self._run(self.coordinator.client.nudge_volume(VOLUME_STEP))

    async def async_volume_down(self) -> None:
        await self._run(self.coordinator.client.nudge_volume(-VOLUME_STEP))

    async def async_select_source(self, source: str) -> None:
        for key in self._preset_keys:
            if source in (source_name(key), key.get("id"), key.get("name")):
                await self._run(self.coordinator.client.press(str(key["id"])))
                return
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="unknown_source",
            translation_placeholders={"source": source},
        )
