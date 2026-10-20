# Hasler Radio for Home Assistant

<sub>D E L G A D O &nbsp;<i>&amp;</i>&nbsp; M U R P H Y</sub>

A Home Assistant integration for the **Hasler** internet radio. It talks to the
radio's own web API on your network: no cloud, no account, no add-on.

## What you get

One device per radio (manufacturer *Delgado & Murphy*, model = the radio's
variant, software version kept current) with:

| Entity | What it does |
| --- | --- |
| `media_player` | Playing / idle / off (standby). Play, stop, next, volume set and up/down, turn on/off (standby and wake). **Sources are the radio's preset keys** (`1 · Radio Swiss Jazz`, …): selecting one presses that key. Title, artist, album, station and cover art come from what the radio plays (radio, YouTube Music, Bluetooth). |
| `update` | Installed version, the latest release the radio has found and its release notes. Read-only: installing still needs a press on the radio, as always. |
| `binary_sensor` *Health problem* | On when the radio's own health report fails; lists the failing checks. |
| `sensor` *Update channel* | The release channel the radio follows. |
| `sensor` *Software started* | When the radio's software last (re)started. |

The radio is polled locally: status every 5 s, health every minute, software
every 5 minutes.

## Install (HACS)

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/Delgado-Murphy/hasler-homeassistant`, type **Integration**.
2. Find **Hasler Radio** in HACS, **Download**, then restart Home Assistant.
3. Settings → Devices & services. A radio that announces itself (`_hasler._tcp`)
   shows up as **Discovered** – click **Add**. Otherwise **Add integration →
   Hasler Radio** and type `hasler.local` (or the radio's IP), port `8080`.

If the radio's IP changes, discovery follows it automatically.

Manual install: copy `custom_components/hasler` into your Home Assistant
`config/custom_components/` and restart.

## Good to know

- **Don't add Home Assistant's MPD integration for the radio.** The radio uses
  MPD internally and drives it itself; a second controller fights it (stopping,
  changing playlists, resetting volume). This integration is the way in.
- The radio trusts its local network (no login, like its web page). Home
  Assistant must reach it on port 8080 by the same name or IP you configure.
- Older radios without `/api/info` work too; they are matched to discovery
  once they are updated.

## Development

```sh
python3.14 -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest -q                                    # mocked radio
HASLER_LIVE_HOST=192.168.1.50 .venv/bin/pytest -q -s tests/test_live.py   # read-only, real radio
```

MIT licensed.

<sub>Delgado &amp; Murphy</sub>
