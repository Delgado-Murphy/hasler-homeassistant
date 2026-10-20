# Hasler Radio for Home Assistant

<sub><i>A Delgado &amp; Murphy restoration</i></sub>

See and control your [Hasler](https://github.com/Delgado-Murphy/hasler) radio
from Home Assistant. The integration talks to the radio's own API on your
network: no cloud, no account, no add-on.

## Install (HACS)

1. In Home Assistant, open **HACS**, tap the **⋮** menu (top right) →
   **Custom repositories**.
2. Paste `https://github.com/Delgado-Murphy/hasler-homeassistant`, choose the
   type **Integration**, and press **Add**.
3. Search HACS for **Hasler Radio**, open it and press **Download**.
4. Restart Home Assistant (Settings → System → Restart).
5. Go to **Settings → Devices & services**. Your radio shows up as
   **Discovered**: press **Add**. If it doesn't, press **Add integration**,
   choose **Hasler Radio** and type `hasler.local` (or the radio's IP),
   port `8080`.

Discovery needs radio software 0.3.8 or later; older radios can be added by
hand. If the radio's IP address changes, discovery follows it.

Without HACS: copy `custom_components/hasler` into your Home Assistant
`config/custom_components/` folder and restart.

## What you get

One device per radio, named after its room (the room name from the key page;
*Hasler* without one), made by *Delgado & Murphy*, with:

| Entity | What it does |
| --- | --- |
| Media player | Playing, idle or off (standby). Play, stop, next, volume, turn on and off. **The radio's keys are its sources**: choosing `1 · Radio Swiss Jazz` presses key 1. Shows the title, artist, album, station and cover art of what is playing. |
| Update *Software* | The installed version, the newest one the radio has found, and its release notes. Read-only: the radio installs updates itself (small ones at night when set to Automatic), and starting one by hand needs a press on the radio. |
| Binary sensor *Health problem* | On when the radio's own health check fails; the attribute `failing_checks` says which. |
| Sensor *Update channel* | `stable` or `bench`. |
| Sensor *Software started* | When the radio's software last started. |

The radio is asked locally: what it plays every 5 seconds, its health every
minute, its software every 5 minutes.

## Good to know

- **Don't add Home Assistant's *Music Player Daemon* integration for the
  radio**, even if Home Assistant offers it. The radio drives MPD itself and a
  second controller fights it (stopping, changing playlists, resetting the
  volume).
- The radio trusts its home network: there is no login, as on its key page.
  Home Assistant must reach it on port 8080 by the name or IP you gave it.
- A held key on the radio can also run a Home Assistant scene, script or light.
  That is set up on the radio's key page (Settings → This radio → Home
  Assistant), not here.
- Not yet shown in Home Assistant: multiroom groups, which Bluetooth phone is
  playing, and a room name changed after setup (it appears after a restart of
  Home Assistant).

## Development

```sh
python3.14 -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest -q                                    # mocked radio
HASLER_LIVE_HOST=192.168.1.50 .venv/bin/pytest -q -s tests/test_live.py   # read-only, real radio
```

MIT licence - see [LICENSE](LICENSE).

<sub>Delgado &amp; Murphy</sub>
