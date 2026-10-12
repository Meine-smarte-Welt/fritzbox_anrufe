# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 83388a40874baafbe11646aabcbc2916eb6f539a6e34b38c347f649bb2cda01a
"""Weckruf der FRITZ!Box lesen und steuern.

Neu in v1.6.0.

* **Lesen** und **Ein-/Ausschalten** gehen über die dokumentierten TR-064-Aktionen
  ``GetNumberOfAlarmClocks``, ``GetAlarmClock`` und ``SetAlarmClockEnable``.
* **Uhrzeit, Wochentage und Namen setzen** (also einen Weckruf „anlegen“) bietet
  TR-064 NICHT. Dafür wird EXPERIMENTELL die Web-Oberfläche der FRITZ!Box
  angesprochen (``/cgi-bin/webcm`` mit ``telcfg:settings/AlarmClock<n>/...``).
  Diese Schreibwege sind nicht an echter Hardware bestätigt. Deshalb liest
  :func:`set_alarm_clock` nach dem Schreiben den Weckruf per TR-064 zurück und
  meldet einen Fehler, wenn das Ergebnis nicht dem Gewünschten entspricht -
  es wird nie „Erfolg“ gemeldet, ohne dass die Box den Wert bestätigt.

Die FRITZ!Box kennt feste Weckruf-Plätze (üblicherweise 3); „anlegen“ bedeutet
hier, einen Platz zu konfigurieren.

Dieses Modul importiert Home Assistant nicht (testbar ohne).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from typing import Any

from .telephony import TelephonyUnavailable, call, pick, truthy

_LOGGER = logging.getLogger(__name__)

# Bitmaske der Wochentage in telcfg (Mo=1 ... So=64) - nur als Lese-/Schreib-
# format genutzt, wenn die Box den Wert selbst als Zahl liefert.
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_FULL_NAMES = {
    "monday": "mon",
    "tuesday": "tue",
    "wednesday": "wed",
    "thursday": "thu",
    "friday": "fri",
    "saturday": "sat",
    "sunday": "sun",
    "montag": "mon",
    "dienstag": "tue",
    "mittwoch": "wed",
    "donnerstag": "thu",
    "freitag": "fri",
    "samstag": "sat",
    "sonntag": "sun",
}
_SHORT = set(_WEEKDAYS)
_NAMES_EN = dict(zip(_WEEKDAYS, ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")))
_NAMES_DE = dict(zip(_WEEKDAYS, ("montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag")))
_TIME_RE = re.compile(r"^(\d{1,2}):?(\d{2})(?::?\d{2})?$")


class AlarmError(Exception):
    """Weckruf konnte nicht gelesen/gesetzt werden (Text ist für Nutzer gedacht)."""


def normalize_time(value: str) -> str:
    """``"0730"``/``"7:30"``/``"07:30"`` → ``"07:30"``; sonst leer."""
    match = _TIME_RE.match((value or "").strip())
    if not match:
        return ""
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return ""
    return f"{hour:02d}:{minute:02d}"


def parse_weekdays(raw: str) -> list[str]:
    """Wochentagsangabe der Box → Liste aus ``mon..sun`` (leer, wenn unbekannt)."""
    text = (raw or "").strip().lower()
    if not text:
        return []
    if text.isdigit():
        mask = int(text)
        return [day for bit, day in enumerate(_WEEKDAYS) if mask & (1 << bit)]
    days: list[str] = []
    for token in re.split(r"[,;\s]+", text):
        day = _FULL_NAMES.get(token) or (token[:3] if token[:3] in _SHORT else "")
        if day and day not in days:
            days.append(day)
    return days


def format_weekdays(days: Iterable[str], template: str) -> str:
    """Wochentage im selben Format schreiben, in dem die Box sie liefert.

    ``template`` ist der aktuell gelesene Rohwert. Zahl → Bitmaske; Namen →
    Namen im gleichen Stil (Sprache, Groß-/Kleinschreibung, Trennzeichen).
    Ist das Format nicht erkennbar, wird :class:`AlarmError` ausgelöst, statt
    ein Format zu raten.
    """
    wanted = [day for day in _WEEKDAYS if day in set(days)]
    text = (template or "").strip()
    if text.isdigit():
        return str(sum(1 << _WEEKDAYS.index(day) for day in wanted))
    tokens = [token for token in re.split(r"[,;\s]+", text) if token]
    if tokens:
        first = tokens[0].lower()
        table = next((t for t in (_NAMES_EN, _NAMES_DE) if first in t.values()), None)
        if table is not None:
            names = [table[day] for day in wanted]
            sample = tokens[0]
            if sample.isupper():
                names = [name.upper() for name in names]
            elif sample[:1].isupper():
                names = [name.capitalize() for name in names]
            return ("," if "," in text else " ").join(names)
    raise AlarmError(
        "Das Wochentagsformat der FRITZ!Box ist unbekannt"
        f" (gelesen: {text!r}) - Wochentage werden nicht geschrieben."
    )


def _alarm_dict(index: int, result: dict[str, Any]) -> dict[str, Any]:
    weekdays_raw = pick(result, "AlarmClockWeekdays")
    return {
        "index": index,
        "enabled": truthy(pick(result, "AlarmClockEnable")),
        "name": pick(result, "AlarmClockName"),
        "time": normalize_time(pick(result, "AlarmClockTime")) or pick(result, "AlarmClockTime"),
        "weekdays": parse_weekdays(weekdays_raw),
        "weekdays_raw": weekdays_raw,
        "phone": pick(result, "AlarmClockPhoneName"),
    }


def read_alarm_clocks(fc: Any) -> list[dict[str, Any]]:
    """Alle Weckrufe lesen. Leere Liste, wenn die Box keine anbietet.

    Der Startindex (0 oder 1) ist in der AVM-Dokumentation nicht angegeben und
    wird daher ausprobiert; der verwendete Index steht in jedem Eintrag
    (``index``) und wird beim Schalten wieder verwendet.
    """
    try:
        count = int(pick(call(fc, "GetNumberOfAlarmClocks", prefer_service="X_VoIP"), "NumberOfAlarmClocks") or 0)
    except (TelephonyUnavailable, ValueError):
        return []
    for indexes in (range(count), range(1, count + 1)):
        alarms: list[dict[str, Any]] = []
        try:
            for index in indexes:
                result = call(fc, "GetAlarmClock", prefer_service="X_VoIP", Index=index)
                alarms.append(_alarm_dict(index, result))
        except TelephonyUnavailable:
            continue
        return alarms
    return []


def _find(alarms: list[dict[str, Any]], index: int) -> dict[str, Any]:
    for alarm in alarms:
        if alarm["index"] == index:
            return alarm
    raise AlarmError(f"Weckruf {index} gibt es auf dieser FRITZ!Box nicht.")


def set_alarm_enabled(fc: Any, index: int, enabled: bool) -> None:
    """Weckruf per TR-064 ein-/ausschalten (dokumentierte Aktion)."""
    try:
        call(fc, "SetAlarmClockEnable", prefer_service="X_VoIP", Index=index, AlarmClockEnable=enabled)
    except TelephonyUnavailable as ex:
        raise AlarmError(f"Weckruf konnte nicht geschaltet werden: {ex}") from ex


def write_alarm_webui(
    post: Callable[[dict[str, str]], bool], webui_index: int, fields: dict[str, str]
) -> None:
    """Felder über die Web-Oberfläche schreiben (EXPERIMENTELL, unbestätigt).

    ``post`` sendet das fertige Formular (inkl. ``sid``) und gibt zurück, ob
    die Box mit HTTP 200 geantwortet hat. ``webui_index`` ist der 0-basierte
    Platz (``AlarmClock0`` ... ``AlarmClock2``).
    """
    form = {
        f"telcfg:settings/AlarmClock{webui_index}/{key}": value for key, value in fields.items()
    }
    form["getpage"] = "../html/index_inhalt.html"
    if not post(form):
        raise AlarmError(
            "Die FRITZ!Box-Oberfläche hat das Speichern des Weckrufs nicht angenommen"
            " (Anmeldung/Berechtigung oder FRITZ!OS ohne diesen Schreibweg)."
        )


def set_alarm_clock(
    fc: Any,
    post: Callable[[dict[str, str]], bool],
    *,
    index: int,
    time: str | None = None,
    weekdays: Iterable[str] | None = None,
    name: str | None = None,
    enabled: bool | None = None,
    first_index: int | None = None,
) -> dict[str, Any]:
    """Weckruf konfigurieren und das Ergebnis per TR-064 prüfen.

    ``enabled`` allein läuft komplett über die dokumentierte TR-064-Aktion.
    Zeit/Wochentage/Name gehen über den experimentellen Web-Weg; danach wird
    zurückgelesen und bei Abweichung :class:`AlarmError` ausgelöst.
    Liefert den zurückgelesenen Weckruf.
    """
    alarms = read_alarm_clocks(fc)
    current = _find(alarms, index)
    base = first_index if first_index is not None else min(a["index"] for a in alarms)

    fields: dict[str, str] = {}
    expected_time = None
    if time is not None:
        expected_time = normalize_time(time)
        if not expected_time:
            raise AlarmError(f"Ungültige Uhrzeit: {time!r} (erwartet HH:MM).")
        fields["Time"] = expected_time.replace(":", "")
    expected_days = None
    if weekdays is not None:
        expected_days = [day for day in _WEEKDAYS if day in set(weekdays)]
        if not expected_days:
            raise AlarmError("Mindestens ein Wochentag ist nötig.")
        fields["Weekdays"] = format_weekdays(expected_days, current["weekdays_raw"])
    if name is not None:
        fields["Name"] = name.strip()[:31]

    if fields:
        if enabled is not None:
            fields["Active"] = "1" if enabled else "0"
        elif time is not None:
            # Wer eine Zeit setzt, will den Weckruf in der Regel auch aktiv haben.
            fields["Active"] = "1"
        write_alarm_webui(post, index - base, fields)
    elif enabled is not None:
        set_alarm_enabled(fc, index, enabled)
    else:
        raise AlarmError("Nichts zu ändern angegeben.")

    after = _find(read_alarm_clocks(fc), index)
    problems = []
    if expected_time and after["time"] != expected_time:
        problems.append(f"Uhrzeit ist {after['time'] or '?'} statt {expected_time}")
    if expected_days is not None and sorted(after["weekdays"]) != sorted(expected_days):
        problems.append("Wochentage stimmen nicht überein")
    if name is not None and after["name"] != name.strip()[:31]:
        problems.append("Name stimmt nicht überein")
    wanted_enabled = fields.get("Active")
    if enabled is not None and after["enabled"] != enabled:
        problems.append("Aktiv-Zustand stimmt nicht überein")
    elif wanted_enabled is not None and enabled is None and after["enabled"] != (wanted_enabled == "1"):
        problems.append("Aktiv-Zustand stimmt nicht überein")
    if problems:
        _LOGGER.warning(
            "Weckruf %s: Rücklesung weicht ab (%s). Gelesen: %s", index, "; ".join(problems), after
        )
        raise AlarmError(
            "Die FRITZ!Box hat die Änderung nicht übernommen: " + "; ".join(problems)
            + ". (Schreibweg ist experimentell, siehe README.)"
        )
    return after


__all__ = [
    "AlarmError",
    "format_weekdays",
    "normalize_time",
    "parse_weekdays",
    "read_alarm_clocks",
    "set_alarm_clock",
    "set_alarm_enabled",
    "write_alarm_webui",
]
