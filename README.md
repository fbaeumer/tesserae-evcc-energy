# EVCC, Energy

Tesserae widget for [evcc](https://evcc.io). Live house energy plus a two-day PV chart that overlays **actual** production (15-minute history) on the **forecast**.

Plugin id: `evcc_energy` · Catalog name: **EVCC, Energy**

## Install

**From the Tesserae catalog** (once listed): Settings → Widgets → Browse catalog → *EVCC, Energy*.

**From this repo:** copy the folder into `plugins/evcc_energy/` and restart Tesserae.

Then set **EVCC URL** to your instance, e.g. `http://192.168.1.10:7070`.

The widget calls only that host: `GET /api/state` and `GET /api/history/energy`. No evcc API key. The URL is a cell option, so `requires: network:*` is required (LAN IPs and hostnames vary).

## Options

| Option | Meaning |
| --- | --- |
| EVCC URL | Base URL (`http` or `https`) |
| Loadpoint index | Charger to show (`0` = first) |
| Title | Header text; empty uses Energy / Energie |
| Language | Deutsch or English (numbers follow the locale) |
| Vehicle name | Fallback when evcc has no connected car |
| Show vehicle | Footer vehicle panel |
| Show forecast footer | Tomorrow / day-after totals |

## Layout

- Chart: today + tomorrow, forecast (dashed) and actual (solid)
- Stats: PV, house, battery, grid — power now, kWh today
- Footer: PV forecast tomorrow & day-after, optional vehicle

## Develop

```sh
# from a Tesserae checkout, with this folder at plugins/evcc_energy/
.venv/bin/python -m pytest plugins/evcc_energy/tests -q
```

Preview: `/_test/render?plugin=evcc_energy&size=lg`

## Catalog

See [`catalog-entry.json`](catalog-entry.json) for the `widgets.json` snippet. After tagging a release:

```sh
curl -sL https://github.com/<you>/tesserae-evcc-energy/archive/refs/tags/v1.0.0.tar.gz | shasum -a 256
```

## License

[AGPL-3.0-or-later](LICENSE), same as Tesserae.
