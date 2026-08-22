# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 026ae8bc8890be324f074d17f5fce1269d87edbb420566bdfc1aae18cf3eea11
"""Shared spam-number matching for calls and answering-machine messages.

Seit v1.0.6b1 - Hintergrund/Recherche-Ergebnis
-----------------------------------------------
Die FRITZ!Box selbst liefert über TR-064 (``GetCallList``) KEIN natives
Spam-/KI-Erkennungsfeld - anders als man beim Stichwort "Spam-Erkennung"
vielleicht annehmen könnte. Es gibt kein automatisches Datenbank- oder
KI-basiertes Tagging einzelner Anrufe als Spam in der Anrufliste. Das
einzige tatsächlich native Signal ist ``REJECTED_CALL_TYPE`` (10) - Anrufe,
die die Box bereits über ihre eigene Telefonbuch-/Sperrliste-Regel
blockiert hat (call_log.py:_classify_call). Diese Sperrliste kann ihrerseits
manuell oder über Drittanbieter-Tools wie PhoneBlock/SpamBlockUp befüllt
worden sein.

Diese Version kombiniert daher zwei Signale zu einem Gesamturteil
"ist das Spam" (siehe call_log.py/voicemail.py):

1. Die FRITZ!Box hat den Anruf bereits selbst blockiert (REJECTED_CALL_TYPE).
2. Die Nummer stimmt mit einer vom Nutzer im Options-Flow gepflegten
   Liste von Spam-Nummern/-Vorwahlen überein (CONF_SPAM_NUMBERS in
   const.py) - Präfix-Abgleich, damit sowohl vollständige Nummern als
   auch Vorwahlen als Muster funktionieren.

Absichtlich als eigenständiges Modul ohne Abhängigkeiten zu call_log.py
oder voicemail.py, damit beide Module diese Funktionen importieren können,
ohne einen Circular Import zu erzeugen (call_log.py importiert bereits aus
voicemail.py).
"""

from __future__ import annotations

import re

_NON_NUMBER_RE = re.compile(r"[^\d+]")


def normalize_number(value: str | None) -> str:
    """Strip everything except digits and a leading '+' for comparison."""
    if not value:
        return ""
    return _NON_NUMBER_RE.sub("", value)


def parse_spam_patterns(raw_numbers: list[str] | None) -> list[str]:
    """Normalize a raw (Options-Flow) spam-number/prefix list for matching."""
    if not raw_numbers:
        return []
    return [pattern for pattern in (normalize_number(v) for v in raw_numbers) if pattern]


def is_spam_number(number: str | None, patterns: list[str]) -> bool:
    """Return True if ``number`` matches (as a prefix) any configured pattern."""
    if not patterns:
        return False
    normalized = normalize_number(number)
    if not normalized:
        return False
    return any(normalized.startswith(pattern) for pattern in patterns)


def parse_name_markers(raw_markers: list[str] | None) -> list[str]:
    """Normalize a raw (Options-Flow) list of name-prefix spam markers.

    Seit v1.2.3 (siehe const.py:CONF_SPAM_NAME_PREFIXES) - für externe
    Blocker wie PhoneBlock, die dem Anrufernamen einen Marker wie "SPAM:"
    voranstellen. Anders als bei Nummern (:func:`normalize_number`) bleibt der
    Text ansonsten unverändert - ein Marker enthält bewusst Zeichen außerhalb
    von Ziffern. Für den späteren, case-insensitiven Abgleich wird hier auf
    Kleinschreibung vereinheitlicht, umschließender Leerraum entfernt und
    leere Einträge verworfen.
    """
    if not raw_markers:
        return []
    return [marker.strip().lower() for marker in raw_markers if marker and marker.strip()]


def is_spam_name(name: str | None, markers: list[str]) -> bool:
    """Return True if ``name`` starts (case-insensitively) with any marker.

    Abgleich bewusst nur am ANFANG des (getrimmten) Namens - genau so, wie
    Tools wie PhoneBlock den Marker voranstellen (z. B. "SPAM: 0123..."). Ein
    leerer Marker-Liste (Standard) bedeutet: Erkennung aus, immer ``False``.
    """
    if not markers or not name:
        return False
    normalized = name.strip().lower()
    if not normalized:
        return False
    return any(normalized.startswith(marker) for marker in markers)
