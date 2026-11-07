# Changelog

<sub><i>A Delgado &amp; Murphy restoration</i></sub>

What changed in the Hasler Radio integration for Home Assistant. The version
is `version` in `custom_components/hasler/manifest.json` and the git tag
`vX.Y.Z` HACS installs. What changed in the radio itself:
[hasler's CHANGELOG](https://github.com/Delgado-Murphy/hasler/blob/master/CHANGELOG.md).

## Unreleased

- Docs: a compatibility table (Home Assistant 2025.2.0 or later, tested on
  2026.10.2; the radio's API checked against 1.6.0), why the integration
  keeps port 8080 now that the radio's key page is on port 80, which radio
  fields are not shown yet, and the channels named **Stable** and **Bench versions**.
- Contributing guide, security policy and issue templates; radio owners are
  pointed to **Tell the makers** on the radio.

## 0.1.0 - 2026-10-20

First release.

- Found by zeroconf (`_hasler._tcp`, radio software 0.3.8 or later; the id
  comes from `/api/info`) or added by host and port; follows the radio to a
  new IP address.
- One device per radio, named after its room.
- Media player: playing, idle or off (standby); play, stop, next, volume set
  and step, turn on and off; the radio's preset keys as sources; title,
  artist, album, station and cover art (`status.art`).
- Update entity (read-only, with release notes), *Health problem* binary
  sensor (`failing_checks`), *Update channel* and *Software started* sensors.
- English and Spanish.

<sub>Delgado &amp; Murphy</sub>
