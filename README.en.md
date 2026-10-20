[🇩🇪 Deutsch](README.md) · 🇬🇧 English · [🇳🇱 Nederlands](README.nl.md)

# FRITZ!Box Calls

Home Assistant integration for the call monitor and call lists (incoming,
outgoing, missed) of an AVM FRITZ!Box, with answering-machine messages, a
dashboard card and – new in 1.6.0 – phone numbers, alarm clock, call
forwarding and call statistics.

> **Note:** The German [README.md](README.md) is the complete reference (all
> options, card keys, spam detection, multiple answering machines, version
> history). This page covers installation, setup and everything new in 1.6.1 and 1.6.0.

## Features

- Live call monitor (ringing / dialling / talking / idle) via the FRITZ!Box call monitor (TCP port 1012).
- Sensors for incoming, outgoing and missed calls, answering-machine messages (up to 5 machines, optional on/off switch).
- Bundled dashboard card `fritzbox-anrufe-card` with a graphical editor; every category can be switched on or off.
- Spam marking, voicemail playback, events for new messages and missed calls.
- **New in 1.6.1 (pre-release):** optional Notification Center connection (missed call, new answering-machine message, connection lost, update available), switchable in the card and the options.
- **New in 1.6.0:** external and internal phone numbers, alarm clock, call forwarding (show / switch / delete / create, experimental), call statistics, version display with update hint, card texts in German, English and Dutch.

## Requirements

- Home Assistant 2025.6 or newer, an AVM FRITZ!Box.
- Call monitor enabled on the box (`#96*5*` on a connected phone).
- A FRITZ!Box user with the rights for phone, TR-064 and smart home / FRITZ!Box settings. Write actions (alarm clock, forwarding) only work for Home Assistant administrators.

## Installation

**HACS:** HACS → Custom repositories → `https://github.com/Meine-smarte-Welt/fritzbox_anrufe` → category *Integration* → download → restart Home Assistant → hard-reload the browser (Ctrl+F5).

**Manual:** copy `custom_components/fritzbox_anrufe` into your configuration folder, restart Home Assistant.

## Setup

*Settings → Devices & services → Add integration → "FRITZ!Box Anrufe"*, then enter host, user, password and the phone book. Options (history depth, spam, answering machines) are under *Configure*. The card is registered automatically; in YAML mode add the resource manually.

## What is new in 1.6.1

**Pre-release.** Version 1.6.1 is marked as a *pre-release* on GitHub. HACS only offers it if you enable "Show beta versions" for this integration.

**Test status, honestly:** the connection was tested against a *simulated* event bus (23 automated tests) and the card was checked with test data in a simulated browser. **It was not tested against a real Notification Center nor on real FRITZ!Box hardware.** Feedback is very welcome.

### Notification Center (optional)

The integration can send its messages to the **Notification Center**, a separate optional integration that collects messages from several integrations, sorts them by urgency and delivers them. This integration only *reports*; it keeps working fully without the Notification Center (no error, no log spam). Transport is the Home Assistant event bus (no MQTT, interface "schema 1"). The existing events (`fritzbox_anrufe_missed_call`, `fritzbox_anrufe_new_voicemail_message`) are unchanged.

| Message type | Urgency | When |
| --- | --- | --- |
| `connection_lost` | Warning | Call list **and** settings cannot be read; resolves when the connection returns |
| `missed_call` | Info | Missed call (live call monitor), one-off |
| `new_voicemail` | Info | New answering-machine message, one-off |
| `update_available` | Info | Newer version of this integration on GitHub; resolves after the update |

Phone numbers and names appear only as placeholders in the messages and are never written to the log. At start, existing states are only reported as initial state (no push). Texts exist in German, English, Dutch, French and Spanish; the Notification Center picks the language.

**Switches:** card → gear → "Notification Center" (master switch and one switch per message type, sorted by urgency) or *Settings → Devices & services → FRITZ!Box Anrufe → Configure → Notification Center*. Switched-off message types are not sent. With `read_only: true` in the card configuration the card hides this section's switches and only shows the state.

| Service | Purpose |
| --- | --- |
| `fritzbox_anrufe.set_notification_center` | Master switch (`enabled`) |
| `fritzbox_anrufe.set_notification_type` | Switch a message type (`nc_type`, `enabled`) |

Both for administrators only; pass `entry_id` with several FRITZ!Boxes.

Also: the version check now understands beta/RC markers (`1.0.0b1`, `1.0.0rc1`) and also considers pre-releases when a beta/RC is installed.

## What is new in 1.6.0

**Test status, honestly:** everything below was tested against a *simulated* FRITZ!Box (23 automated tests) and the card was checked in a browser with test data. **It was not tested on real FRITZ!Box hardware.**

| Feature | What it does |
| --- | --- |
| Phone numbers | Tap a telephony device in the Settings tab for a popup with connection, outgoing, incoming and internal number ("all" = rings on all numbers). Settings tab → "Numbers": external numbers (TR-064 `GetNumbers`) and internal numbers per device. IP phones/apps come via TR-064; analogue/DECT numbers still come from the box web UI and are marked "unverified". Missing values show "–". I could not confirm that FHEM shows internal numbers; the implementation follows the AVM documentation. |
| Alarm clock | Shows time, weekdays, name, state. **Switching on/off** uses the documented TR-064 call. AVM has **no** TR-064 call for time/weekdays, so *changing* an alarm (the box has fixed slots, usually 3) is **experimental** via the web UI; the result is read back and a mismatch is reported as an error. |
| Call forwarding | Shows existing rules, switches them on/off, **deletes** and **creates** them (button "New call forwarding"; two-click confirmation, admin only). **Experimental:** AVM has no TR-064 call for this, so the integration uses the same form fields as the box web UI (`callRedi` / `rul_edit`, saved via `data.lua`). Field names and values were read from the page scripts of a FRITZ!Box 5690 Pro; **saving has not been tested on real hardware.** Safeguards: values are checked against the box lists, the list is read back after saving (no match = error), a two-factor prompt is not bypassed, time control and "important caller" rules are not touched. Existing rules cannot be edited (delete and recreate). |
| Call statistics | `sensor.fritzbox_anrufe_anrufstatistik` (total, new, today, last 7/30 days, last call, last 14 days, by hour, list) and `sensor.fritzbox_anrufe_letzter_ab_anruf` (timestamp). Counts what the box currently stores on the answering machine – not all calls. Card tab "Statistics" (`show_statistik`, off by default). |
| Version and update hint | Shown in three places: card → gear → "App version", top of the card editor, options dialog. The integration checks the GitHub releases at start and every 12 hours; a newer version is highlighted in orange. If GitHub is unreachable everything keeps working. |

### Services (administrators only)

| Service | Purpose |
| --- | --- |
| `fritzbox_anrufe.set_alarm_clock_enabled` | Switch an alarm clock on/off (`index`, `enabled`) |
| `fritzbox_anrufe.set_alarm_clock` | Set time / weekdays / name / state (experimental) |
| `fritzbox_anrufe.set_deflection_enabled` | Switch a forwarding rule on/off via TR-064 (`deflection_id`, `enabled`) |
| `fritzbox_anrufe.create_call_forwarding` | Create a forwarding rule (experimental): `mode` (`to`/`from`/`all`), `target`, `from_number`, `dest_type` (`number`/`answering_machine`/`phone`), `dest`, `own_number`, `kind` |
| `fritzbox_anrufe.set_call_forwarding_enabled` | Switch a web-UI forwarding rule on/off (`uid`, `enabled`; IDs in attribute `forwardings`) |
| `fritzbox_anrufe.delete_call_forwarding` | Delete a forwarding rule (`uid`) |
| `fritzbox_anrufe.check_for_update` | Run the GitHub version check now |
| `fritzbox_anrufe.collect_diagnostics` | Raw box answers (read-only) for bug reports; returns a response |

With several FRITZ!Boxes, pass `entry_id` as well.

### Diagnostics for wrong numbers or forwarding

If internal numbers or forwarding rules are wrong or missing, run *Developer tools → Actions → `fritzbox_anrufe.collect_diagnostics`*. The response contains the raw answers of the box (TR-064 and the web pages `telDevices` and `callHan`, truncated, without session id). Attach it to a GitHub issue; it contains your phone numbers, so check and redact first. Read errors are also logged as warnings.

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

**Fix:** on FRITZ!OS 8 the page `telDev` (not `telDevices`) returns HTML with an embedded device list instead of JSON; this is now parsed. The structure was inspected on a real FRITZ!Box 5690 Pro (FRITZ!OS 8.40) and the parser tested against it; a full run inside Home Assistant is still pending. Internal numbers are shown as dialled on the box (`**610`). If no forwarding rule exists on the box (page `callRedi`, empty rule list) the list stays empty; the integration cannot create rules.

## Known limitations

- **New in 1.6.1 (pre-release):** the Notification Center connection was only tested against a simulated event bus, not a real Notification Center. `read_only` currently only affects this section of the card.
- Phone numbers, alarm clock, forwarding, statistics and the update check are **not tested on real hardware**.
- Alarm time/weekdays are written through the box web UI (undocumented form fields); read-back protects against silent failure.
- Creating/deleting forwarding rules goes through the box web UI (no AVM interface) and is **not tested on real hardware**; existing rules cannot be edited.
- Internal numbers of analogue/DECT phones may be missing depending on FRITZ!OS.
- Statistics only count answering-machine messages.
- Older card texts (call list, answering machine, telephony devices) are still German only; the new texts are translated.

## Troubleshooting

- Card not updated: hard-reload the browser (Ctrl+F5), clear the service worker / companion app cache.
- Enable debug logging for `custom_components.fritzbox_anrufe` and check *Settings → System → Logs*.
- Issues: https://github.com/Meine-smarte-Welt/fritzbox_anrufe/issues

## File integrity

Every `.py`, `.js` and `.yaml` file starts with a SHA256 comment of its content from line 2 on (`tail -n +2 file | sha256sum`). JSON files are listed here (`sha256sum file`):

| File | SHA256 (version 1.6.1) |
| --- | --- |
| `__init__.py` | `75e7a86719935258d2db5076821e287e5285f65124b048fec3370aed9c72c029` |
| `alarm.py` | `83388a40874baafbe11646aabcbc2916eb6f539a6e34b38c347f649bb2cda01a` |
| `base.py` | `8b263a8dd288006c4461a00b5d120548f1b1f7add1e3b7c9faa5f9fc1cd45986` |
| `call_forwarding.py` | `64ccd3a25fbe5256339016884ec4ad80ab1e408369b029b8d9eab6a003d15aa9` |
| `call_log.py` | `06375eae8516c56b35582eb2b12f7ae09910fc908458d7a90912a45edc19c9d5` |
| `call_stats.py` | `1f22199430beba85d4856f64da1c092ebe3b27b800d1b5bc47e9d0ac6a41476b` |
| `config_flow.py` | `8ac23232ffa3d6150e381308ce0a45d86e8c5fa45681db10e2df9fcc73cc86a6` |
| `const.py` | `5e77e3fceb364fdbf519bc939557a5de49516ba59ec668ebceab74b63bd3a53d` |
| `deflection.py` | `3d41277ea2d68fcc428493a14c926cc1b0f1ae3fb8c6b08c8404f7665bb2a3e9` |
| `http.py` | `4d98f8fb1236eb7960d0d3470f0eef1a0e3a45e48e713fe121faa1481a6b70df` |
| `notification_bridge.py` | `92a92c75fe1ebc345a644069f84b250c5f08a8b2dbbd29757fa514324e19194d` |
| `notifications.py` | `f79cbec5112878d23f7b532488daf9463e2c05967989284e0663dea431b9d27a` |
| `sensor.py` | `2e048f7708b1d98c204cc84509e34dcd3c66b2e2bd20b4e412eb09c2d9eb8fc9` |
| `settings_data.py` | `d6ca7cf1a947cbb1ea77291a8bb8f5ef53313980f6a75989f8342afc522b660e` |
| `spam.py` | `026ae8bc8890be324f074d17f5fce1269d87edbb420566bdfc1aae18cf3eea11` |
| `switch.py` | `7cdbb0e5d3c5d1c8fa3cc5cad1cba6fa1f666b6c7eb1e034fbed40861b0e73c2` |
| `tam.py` | `b569e1109b1dbc84a552dd36835fb912aa3ae5b47a29a516c523783e799e09c6` |
| `telephony.py` | `7796cf8c1d6642229f2a42894bd81911236f10b0e30ff34f7ae2e5681606e9ed` |
| `update_check.py` | `00ba17b9ebc578835bbad6ae119b23385377b92e956a28b8e98cfa49621e9461` |
| `voicemail.py` | `235fe1702db39c702d54fd7e8da3d3b9e6fdfa9aed4b877c0f425f01525052c1` |
| `services.yaml` | `ec01b97d3df7d0950cc29bf131acc099e7d7183341d389ea7805a4ae831249af` |
| `www/fritzbox-anrufe-card.js` | `b65125ded927ca5177afffeae7ffe9fe40742cea7296afc889b7addfd4034e00` |
| `manifest.json` | `ca370ff049d940e9c3d941ab02691a6eaec851b06c3c030d9d9058c9a5210c14` |
| `strings.json` | `695cf986dd8eed37f7c5eb2a5191bccf6ab5e86db57dd35921526a9a49349343` |
| `translations/de.json` | `167b377ed501a7a5b425c2ec2322827848d398ab53230babdfb2e915b75411b9` |
| `translations/en.json` | `695cf986dd8eed37f7c5eb2a5191bccf6ab5e86db57dd35921526a9a49349343` |
| `translations/nl.json` | `4366dac7fa63acc24c6e33778f5a73f34ae2eef550cae527f52f1105f2bf72a3` |
| `icons.json` | `02d3f66ee5b0422973449b912573166b921745c8cbf05f8e78487227ce82d669` |
