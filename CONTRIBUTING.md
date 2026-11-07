# Contributing

<sub><i>A Delgado &amp; Murphy restoration</i></sub>

Thanks for helping. The integration is small on purpose: it shows what the
radio reports and sends the few commands its keys and knob already have.

**Own a radio and the radio itself misbehaves?** Use **Settings →
Something's wrong? → Tell the makers** on its key page; an issue here is for
what Home Assistant shows or does.

## Set up

Python 3.14 (what the pinned Home Assistant needs):

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt   # pytest-homeassistant-custom-component, which pins Home Assistant
.venv/bin/pytest -q                              # all tests, against a mocked radio
```

- `tests/conftest.py` holds the mocked radio: `INFO`, `STATUS`, `SOFTWARE`,
  `HEALTH` copy the shape of the radio's `/api/info`, `/api/status`,
  `/api/software`, `/api/health`. When the radio adds a field you use, add it
  there first.
- `tests/test_live.py` sets the integration up against a real radio, GETs
  only, so it is safe on a radio that is playing:
  `HASLER_LIVE_HOST=192.168.1.50 .venv/bin/pytest -q -s tests/test_live.py`.
- To try it in a real Home Assistant, copy (or symlink)
  `custom_components/hasler` into its `config/custom_components/` and restart.

CI (`.github/workflows/validate.yml`) runs hassfest, the HACS check and
pytest on every pull request.

## The radio's API

The integration uses `/api/info`, `/api/status`, `/api/software`,
`/api/health` and the commands `/api/press`, `/api/stop`, `/api/next`,
`/api/volume`, `/api/standby` on port 8080. The radio's side and its fields
are documented in `daemon/haslerd/web/integration.py` and
`daemon/haslerd/web/server.py` in
[hasler](https://github.com/Delgado-Murphy/hasler). Two rules:

- State-changing requests need `Content-Type: application/json` and a `Host`
  that is the radio's own name or address - never set `Origin`/`Referer`.
- New radio fields are optional: a radio a few releases older must still
  work (treat missing keys as unknown).

## Pull requests

- One topic each, tests included, `pytest` green.
- Text a person reads goes into `translations/en.json` and `es.json`.
- A release: bump `version` in `manifest.json`, add a `CHANGELOG.md`
  section, tag `vX.Y.Z` on `main` and make a GitHub release from the tag
  (HACS offers releases). Raise `homeassistant` in `hacs.json` only when the
  code needs a newer Home Assistant.

<sub>Delgado &amp; Murphy</sub>
