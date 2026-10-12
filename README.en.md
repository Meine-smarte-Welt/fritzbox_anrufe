[🇩🇪 Deutsch](README.md) · 🇬🇧 English · [🇳🇱 Nederlands](README.nl.md)

# FRITZ!Box Calls

Home Assistant integration for the call monitor and call lists (incoming,
outgoing, missed) of an AVM FRITZ!Box, with answering-machine messages, a
dashboard card and – new in 1.6.0 – phone numbers, alarm clock, call
forwarding and call statistics.

> **Note:** The German [README.md](README.md) is the complete reference (all
> options, card keys, spam detection, multiple answering machines, version
> history). This page covers installation, setup and everything new in 1.6.0.

## Features

- Live call monitor (ringing / dialling / talking / idle) via the FRITZ!Box call monitor (TCP port 1012).
- Sensors for incoming, outgoing and missed calls, answering-machine messages (up to 5 machines, optional on/off switch).
- Bundled dashboard card `fritzbox-anrufe-card` with a graphical editor; every category can be switched on or off.
- Spam marking, voicemail playback, events for new messages and missed calls.
- **New in 1.6.0:** external and internal phone numbers, alarm clock, call forwarding (show / switch), call statistics, version display with update hint, card texts in German, English and Dutch.

## Requirements

- Home Assistant 2025.6 or newer, an AVM FRITZ!Box.
- Call monitor enabled on the box (`#96*5*` on a connected phone).
- A FRITZ!Box user with the rights for phone, TR-064 and smart home / FRITZ!Box settings. Write actions (alarm clock, forwarding) only work for Home Assistant administrators.

## Installation

**HACS:** HACS → Custom repositories → `https://github.com/Meine-smarte-Welt/fritzbox_anrufe` → category *Integration* → download → restart Home Assistant → hard-reload the browser (Ctrl+F5).

**Manual:** copy `custom_components/fritzbox_anrufe` into your configuration folder, restart Home Assistant.

## Setup

*Settings → Devices & services → Add integration → "FRITZ!Box Anrufe"*, then enter host, user, password and the phone book. Options (history depth, spam, answering machines) are under *Configure*. The card is registered automatically; in YAML mode add the resource manually.

## What is new in 1.6.0

**Test status, honestly:** everything below was tested against a *simulated* FRITZ!Box (19 automated tests) and the card was checked in a browser with test data. **It was not tested on real FRITZ!Box hardware.**

| Feature | What it does |
| --- | --- |
| Phone numbers | Settings tab → "Numbers": external numbers (TR-064 `GetNumbers`) and internal numbers per device. IP phones/apps come via TR-064; analogue/DECT numbers still come from the box web UI and are marked "unverified". Missing values show "–". I could not confirm that FHEM shows internal numbers; the implementation follows the AVM documentation. |
| Alarm clock | Shows time, weekdays, name, state. **Switching on/off** uses the documented TR-064 call. AVM has **no** TR-064 call for time/weekdays, so *changing* an alarm (the box has fixed slots, usually 3) is **experimental** via the web UI; the result is read back and a mismatch is reported as an error. |
| Call forwarding | Shows existing rules and switches them on/off (two-click confirmation, admin only, read-back). **Creating rules and changing the target number is deliberately not implemented** – AVM offers no interface and guessing form fields could create wrong rules. Use *Telephony → Call handling* on the box. |
| Call statistics | `sensor.fritzbox_anrufe_anrufstatistik` (total, new, today, last 7/30 days, last call, last 14 days, by hour, list) and `sensor.fritzbox_anrufe_letzter_ab_anruf` (timestamp). Counts what the box currently stores on the answering machine – not all calls. Card tab "Statistics" (`show_statistik`, off by default). |
| Version and update hint | Shown in three places: card → gear → "App version", top of the card editor, options dialog. The integration checks the GitHub releases at start and every 12 hours; a newer version is highlighted in orange. If GitHub is unreachable everything keeps working. |

### Services (administrators only)

| Service | Purpose |
| --- | --- |
| `fritzbox_anrufe.set_alarm_clock_enabled` | Switch an alarm clock on/off (`index`, `enabled`) |
| `fritzbox_anrufe.set_alarm_clock` | Set time / weekdays / name / state (experimental) |
| `fritzbox_anrufe.set_deflection_enabled` | Switch a forwarding rule on/off (`deflection_id`, `enabled`) |
| `fritzbox_anrufe.check_for_update` | Run the GitHub version check now |

With several FRITZ!Boxes, pass `entry_id` as well.

### Card keys

`show_statistik` (default `false`), `show_settings_numbers`, `show_settings_alarms`, `show_settings_deflections` (default `true`), `entity_stats`, `entry_id`, `color_icon_statistik`. Example:

```yaml
type: custom:fritzbox-anrufe-card
entity_eingehend: sensor.fritzbox_anrufe_eingehend
entity_ausgehend: sensor.fritzbox_anrufe_ausgehend
entity_verpasst: sensor.fritzbox_anrufe_verpasst
show_einstellungen: true
show_statistik: true
```

## Known limitations

- Phone numbers, alarm clock, forwarding, statistics and the update check are **not tested on real hardware**.
- Alarm time/weekdays are written through the box web UI (undocumented form fields); read-back protects against silent failure.
- Forwarding rules cannot be created and their target cannot be changed.
- Internal numbers of analogue/DECT phones may be missing depending on FRITZ!OS.
- Statistics only count answering-machine messages.
- Older card texts (call list, answering machine, telephony devices) are still German only; the new texts are translated.

## Troubleshooting

- Card not updated: hard-reload the browser (Ctrl+F5), clear the service worker / companion app cache.
- Enable debug logging for `custom_components.fritzbox_anrufe` and check *Settings → System → Logs*.
- Issues: https://github.com/Meine-smarte-Welt/fritzbox_anrufe/issues

## File integrity

Every `.py`, `.js` and `.yaml` file starts with a SHA256 comment of its content from line 2 on (`tail -n +2 file | sha256sum`). JSON files are listed here (`sha256sum file`):

| File | SHA256 (version 1.6.0) |
| --- | --- |
| `__init__.py` | `208eb4a9910087daf8a2dc7001bc38ce84a76d83d12ef5a7713c117cb6e0c8b2` |
| `alarm.py` | `83388a40874baafbe11646aabcbc2916eb6f539a6e34b38c347f649bb2cda01a` |
| `base.py` | `8b263a8dd288006c4461a00b5d120548f1b1f7add1e3b7c9faa5f9fc1cd45986` |
| `call_log.py` | `06375eae8516c56b35582eb2b12f7ae09910fc908458d7a90912a45edc19c9d5` |
| `call_stats.py` | `1f22199430beba85d4856f64da1c092ebe3b27b800d1b5bc47e9d0ac6a41476b` |
| `config_flow.py` | `05f952f04180995f565d3efd765ee2781948e11b725bc620427d319b820879d4` |
| `const.py` | `cef8a0326ca6dcf343b8ec1eabc020dc8317e716f2acbeed76c70c805b557cbb` |
| `deflection.py` | `3949dfa6993bc5a6d43c17c635784b19c96d5414c70e44088813be37e5d55e98` |
| `http.py` | `4d98f8fb1236eb7960d0d3470f0eef1a0e3a45e48e713fe121faa1481a6b70df` |
| `sensor.py` | `77de2f6e7e1a085ae3ef12232faefefbfae8e8ab9c14ff13e03ae491d42f11d2` |
| `settings_data.py` | `28bd262ad9c688caec2d99866c36e0b4cd49bc3d0b7fd54571f3eabd317387a8` |
| `spam.py` | `026ae8bc8890be324f074d17f5fce1269d87edbb420566bdfc1aae18cf3eea11` |
| `switch.py` | `7cdbb0e5d3c5d1c8fa3cc5cad1cba6fa1f666b6c7eb1e034fbed40861b0e73c2` |
| `tam.py` | `b569e1109b1dbc84a552dd36835fb912aa3ae5b47a29a516c523783e799e09c6` |
| `telephony.py` | `8c1faec0cb58d198a68d133689b564516ca95680b71869af927d4730ee92762a` |
| `update_check.py` | `119559a29413fd478bb94053336f6e90e150a3c2737d2966371b7800e4e508c6` |
| `voicemail.py` | `564dc067bc31355e96e5521884969f228cf27bba73cae7bfb1b6d8ac9633a7f0` |
| `services.yaml` | `2f3c794bf601f4e765950e72a1f261c8819c7384187280a4b04c57706026c941` |
| `www/fritzbox-anrufe-card.js` | `0f09b0cefd3c83f0bbe38cdf09aefb687d56b21ba1e942c29260a1bf415b2861` |
| `manifest.json` | `b3f4ed0a2a922bdcc2c67699116f1261aba317d463b0011fe9d1f902005223a3` |
| `strings.json` | `2aaa2e8a4a8f6c71f438bfef33fa1b93252cf4bf7b692f72a274c1a8f112d407` |
| `translations/de.json` | `4bd7cf62ba3a6216754fb28e5653440970ced12cf1e169f0c5962091fb763b64` |
| `translations/en.json` | `2aaa2e8a4a8f6c71f438bfef33fa1b93252cf4bf7b692f72a274c1a8f112d407` |
| `translations/nl.json` | `c4c1a621e53677648e1c433300b1784db8e286a1a5a939ed95acf186f845b426` |
| `icons.json` | `8b2283029eee6310b46153248f2261bbf5cf1f42a84f56e2da8544fbc743515d` |
