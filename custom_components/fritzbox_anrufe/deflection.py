# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 3949dfa6993bc5a6d43c17c635784b19c96d5414c70e44088813be37e5d55e98
"""Rufumleitungen („Rufbehandlung“) der FRITZ!Box lesen und ein-/ausschalten.

Neu in v1.6.0. Grundlage sind die dokumentierten TR-064-Aktionen des Dienstes
``X_AVM-DE_OnTel``: ``GetNumberOfDeflections``, ``GetDeflection``,
``GetDeflections`` und ``SetDeflectionEnable``.

Bewusste Grenze: **Anlegen neuer Umleitungen und Ändern der Zielnummer sind NICHT
umgesetzt.** AVM bietet dafür keine TR-064-Aktion, und für die
Web-Oberfläche gibt es keine belegbaren Formularfelder. Ein auf geratenen
Feldnamen beruhender Schreibzugriff könnte falsche Umleitungen in der
Telefonie-Konfiguration anlegen - das ist riskanter als bei einem Weckruf und
wird deshalb nicht angeboten. Bestehende Umleitungen lassen sich lesen und
ein-/ausschalten.

Dieses Modul importiert Home Assistant nicht (testbar ohne).
"""

from __future__ import annotations

from typing import Any

from .telephony import TelephonyUnavailable, call, pick, truthy, xml_items

_SERVICE = "X_AVM-DE_OnTel"


class DeflectionError(Exception):
    """Umleitung konnte nicht gelesen/geschaltet werden (Text für Nutzer)."""


def _deflection_dict(source: dict[str, Any], fallback_id: int | None = None) -> dict[str, Any] | None:
    raw_id = pick(source, "DeflectionId")
    try:
        deflection_id = int(raw_id) if raw_id != "" else fallback_id
    except ValueError:
        deflection_id = fallback_id
    if deflection_id is None:
        return None
    return {
        "id": deflection_id,
        "enabled": truthy(pick(source, "Enable")),
        "type": pick(source, "Type"),
        "number": pick(source, "Number"),
        "to_number": pick(source, "DeflectionToNumber"),
        "mode": pick(source, "Mode"),
        "outgoing": pick(source, "Outgoing"),
        "phonebook_id": pick(source, "PhonebookID"),
    }


def read_deflections(fc: Any) -> list[dict[str, Any]]:
    """Alle Umleitungen lesen (leer, wenn die Box keine anbietet)."""
    try:
        result = call(fc, "GetDeflections", prefer_service=_SERVICE)
        rows = [_deflection_dict(item) for item in xml_items(pick(result, "DeflectionList"))]
        return [row for row in rows if row is not None]
    except TelephonyUnavailable:
        pass
    try:
        count = int(
            pick(call(fc, "GetNumberOfDeflections", prefer_service=_SERVICE), "NumberOfDeflections") or 0
        )
    except (TelephonyUnavailable, ValueError):
        return []
    rows: list[dict[str, Any]] = []
    for deflection_id in range(count):
        try:
            result = call(fc, "GetDeflection", prefer_service=_SERVICE, DeflectionId=deflection_id)
        except TelephonyUnavailable:
            continue
        row = _deflection_dict(result, fallback_id=deflection_id)
        if row is not None:
            rows.append(row)
    return rows


def set_deflection_enabled(fc: Any, deflection_id: int, enabled: bool) -> dict[str, Any]:
    """Umleitung ein-/ausschalten und den Zustand zurücklesen.

    Gibt den zurückgelesenen Eintrag zurück; weicht der Zustand ab oder gibt
    es die Umleitung nicht, wird :class:`DeflectionError` ausgelöst.
    """
    known = {row["id"] for row in read_deflections(fc)}
    if deflection_id not in known:
        raise DeflectionError(f"Umleitung {deflection_id} gibt es auf dieser FRITZ!Box nicht.")
    try:
        call(
            fc,
            "SetDeflectionEnable",
            prefer_service=_SERVICE,
            DeflectionId=deflection_id,
            Enable=enabled,
        )
    except TelephonyUnavailable as ex:
        raise DeflectionError(f"Umleitung konnte nicht geschaltet werden: {ex}") from ex
    for row in read_deflections(fc):
        if row["id"] == deflection_id:
            if row["enabled"] != enabled:
                raise DeflectionError(
                    "Die FRITZ!Box hat den Zustand der Umleitung nicht geändert."
                )
            return row
    raise DeflectionError(f"Umleitung {deflection_id} ist nach dem Schalten nicht mehr lesbar.")
