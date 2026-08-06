# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 2e300431c40ce61953fc92a4e92e661caa7c825b26683a3ce6d70c6ebc04872b
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
