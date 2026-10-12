# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 7796cf8c1d6642229f2a42894bd81911236f10b0e30ff34f7ae2e5681606e9ed
"""TR-064-Hilfen für Telefonie-Daten (Rufnummern, Telefone, Weckruf, Rufumleitung).

Neu in v1.6.0. Dieses Modul importiert bewusst NICHT Home Assistant, damit sich
die Auswertung ohne Home Assistant testen lässt.

Warum ein „Resolver“?
---------------------
AVM benennt die Aktionen und Argumente dieser Dienste uneinheitlich
(``X_AVM-DE_GetClients`` vs. ``GetDeflections``; Argumente teils mit dem Präfix
``NewX_AVM-DE_``, teils nur mit ``New``). Statt Namen zu raten, liest
:func:`resolve` die Beschreibung, die die FRITZ!Box selbst liefert
(``fc.services``), und ordnet die gewünschte Aktion samt ihren Argumenten
daraus zu. Gibt es die Aktion auf der Box nicht, wird
:class:`TelephonyUnavailable` ausgelöst - es wird NIE blind aufgerufen.

Ohne echte Hardware getestet wurde die Zuordnung mit einer simulierten
Dienstbeschreibung (siehe tests/), nicht gegen eine echte FRITZ!Box.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree

from fritzconnection.core.exceptions import FritzConnectionException
from requests.exceptions import RequestException

# Präfixe, die beim Vergleich von Aktions- und Argumentnamen ignoriert werden.
_ARGUMENT_PREFIXES = ("NewX_AVM-DE_", "NewX_AVM_DE_", "New")
_ACTION_PREFIXES = ("X_AVM-DE_", "X_AVM_DE_")

# Ausnahmen, die ein Aufruf gegen die Box auslösen kann.
CALL_ERRORS = (FritzConnectionException, RequestException, ValueError, KeyError, AttributeError)


class TelephonyUnavailable(Exception):
    """Die gewünschte Aktion existiert auf dieser FRITZ!Box nicht oder schlug fehl."""


def norm_key(key: object) -> str:
    """Argument-/Feldnamen ohne ``New``/``NewX_AVM-DE_`` kleingeschrieben."""
    text = str(key)
    for prefix in _ARGUMENT_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.lower()


def norm_action(name: object) -> str:
    """Aktionsname ohne ``X_AVM-DE_``-Präfix, kleingeschrieben."""
    text = str(name)
    for prefix in _ACTION_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.lower()


def pick(result: Any, *names: str, default: str = "") -> str:
    """Wert aus einer Antwort/Liste nach (normalisiertem) Namen, sonst ``default``."""
    if not isinstance(result, dict):
        return default
    wanted = {norm_key(name) for name in names}
    for key, value in result.items():
        if norm_key(key) in wanted:
            return "" if value is None else str(value).strip()
    return default


def truthy(value: object) -> bool:
    """``"1"``/``"true"``/``True`` → True (FRITZ!Box liefert Wahrheitswerte als Text)."""
    return str(value).strip().lower() in ("1", "true", "yes", "on", "enabled")


def xml_items(raw: object) -> list[dict[str, str]]:
    """Zerlege eine XML-Liste der Box in flache Dicts (ein Dict je Eintrag).

    Tolerant gegenüber dem Namen des Listen-/Eintragselements. Verschachtelte
    Elemente (z. B. mehrere eingehende Nummern) werden mit ", " verbunden.
    Nicht parsebare oder leere Eingaben ergeben eine leere Liste.
    """
    if not raw or not str(raw).strip():
        return []
    try:
        root = ElementTree.fromstring(str(raw).strip())
    except ElementTree.ParseError:
        return []
    entries = [element for element in root if len(element)]
    if not entries and len(root):
        entries = [root]
    items: list[dict[str, str]] = []
    for entry in entries:
        row: dict[str, str] = {}
        for child in entry:
            name = child.tag.rsplit("}", 1)[-1]
            parts = [text.strip() for text in child.itertext() if text and text.strip()]
            row[name] = ", ".join(parts)
        items.append(row)
    return items


def _services(fc: Any) -> dict[str, Any]:
    try:
        services = fc.services
    except Exception:  # noqa: BLE001 - Verbindung ohne Dienstliste
        return {}
    return services if isinstance(services, dict) else {}


def resolve(
    fc: Any, action: str, prefer_service: str | None = None
) -> tuple[str, str, dict[str, str]] | None:
    """Finde ``action`` (ohne ``X_AVM-DE_``) auf der Box.

    Liefert ``(Dienstname, echter Aktionsname, {normalisiert: echter Argumentname})``
    für die EINGABE-Argumente oder ``None``. Dienste, deren Name mit
    ``prefer_service`` beginnt, werden zuerst durchsucht.
    """
    wanted = norm_action(action)
    services = _services(fc)
    ordered = sorted(
        services.items(),
        key=lambda item: 0
        if prefer_service and item[0].lower().startswith(prefer_service.lower())
        else 1,
    )
    for service_name, service in ordered:
        actions = getattr(service, "actions", None) or {}
        for action_name, action_obj in actions.items():
            if norm_action(action_name) != wanted:
                continue
            arguments = getattr(action_obj, "arguments", None) or {}
            inputs = {
                norm_key(arg.name): arg.name
                for arg in arguments.values()
                if str(getattr(arg, "direction", "in")).lower() == "in"
            }
            return service_name, action_name, inputs
    return None


def call(
    fc: Any, action: str, prefer_service: str | None = None, **values: object
) -> dict[str, Any]:
    """Rufe ``action`` mit Kurznamen-Argumenten auf (z. B. ``Index=0``).

    Werte werden als Text übergeben (``bool`` → ``"1"``/``"0"``), passend zur
    bereits in tam.py bestätigten Konvention. Nicht vorhandene Aktion oder
    Argumente → :class:`TelephonyUnavailable`; Fehler der Box werden ebenfalls
    darin verpackt (Originalfehler als ``__cause__``).
    """
    found = resolve(fc, action, prefer_service)
    if found is None:
        raise TelephonyUnavailable(f"Aktion {action} nicht auf dieser FRITZ!Box vorhanden")
    service_name, action_name, inputs = found
    arguments: dict[str, str] = {}
    for short, value in values.items():
        real = inputs.get(norm_key(short))
        if real is None:
            raise TelephonyUnavailable(
                f"Aktion {action_name} kennt das Argument {short} nicht (bekannt: {sorted(inputs)})"
            )
        arguments[real] = ("1" if value else "0") if isinstance(value, bool) else str(value)
    try:
        result = fc.call_action(service_name, action_name, arguments=arguments)
    except CALL_ERRORS as ex:
        raise TelephonyUnavailable(f"{service_name}/{action_name} fehlgeschlagen: {ex}") from ex
    return result if isinstance(result, dict) else {}


# --- Rufnummern und Telefone -------------------------------------------------


def normalize_number_list(raw: object) -> list[dict[str, str]]:
    """``X_AVM-DE_GetNumbers``-Liste → ``[{number, type, name}]`` (nur mit Nummer)."""
    numbers: list[dict[str, str]] = []
    for item in xml_items(raw):
        number = pick(item, "Number")
        if not number:
            continue
        numbers.append(
            {"number": number, "type": pick(item, "Type"), "name": pick(item, "Name")}
        )
    return numbers


def normalize_client(entry: dict[str, Any]) -> dict[str, str]:
    """Ein IP-Telefon/eine App (``GetClient3``/Eintrag von ``GetClients``)."""
    return {
        "name": pick(entry, "PhoneName", "ClientUsername"),
        "client_id": pick(entry, "ClientId"),
        "outgoing": pick(entry, "OutGoingNumber"),
        "incoming": pick(entry, "InComingNumbers"),
        "intern": pick(entry, "InternalNumber"),
    }


def read_numbers(fc: Any) -> list[dict[str, str]]:
    """Externe Rufnummern der Box (MSN/Anschlussnummern).

    Zuerst ``GetNumbers`` im VoIP-Dienst (laut AVM-Dokumentation dort zu
    Hause), dann - wie bisher bis v1.5.0 - im OnTel-Dienst. Leer, wenn keine
    der beiden Varianten funktioniert.
    """
    for prefer in ("X_VoIP", "X_AVM-DE_OnTel"):
        try:
            result = call(fc, "GetNumbers", prefer_service=prefer)
        except TelephonyUnavailable:
            continue
        numbers = normalize_number_list(pick(result, "NumberList"))
        if numbers:
            return numbers
    return []


def read_clients(fc: Any) -> list[dict[str, str]]:
    """IP-Telefone/Apps inkl. interner Nummer (620-629) per TR-064.

    Gilt laut AVM NUR für IP-Telefone/Apps - analoge FON-Anschlüsse und
    DECT-Mobilteile stehen hier nicht. Erst ``GetClients`` (eine Abfrage),
    ersatzweise ``GetNumberOfClients`` + ``GetClient3``/``GetClient2``.
    """
    try:
        result = call(fc, "GetClients", prefer_service="X_VoIP")
        clients = [normalize_client(item) for item in xml_items(pick(result, "ClientList"))]
        return [client for client in clients if client["name"] or client["intern"]]
    except TelephonyUnavailable:
        pass
    try:
        count = int(pick(call(fc, "GetNumberOfClients", prefer_service="X_VoIP"), "NumberOfClients") or 0)
    except (TelephonyUnavailable, ValueError):
        return []
    clients = []
    for index in range(count):
        for action in ("GetClient3", "GetClient2"):
            try:
                result = call(fc, action, prefer_service="X_VoIP", ClientIndex=index)
            except TelephonyUnavailable:
                continue
            client = normalize_client(result)
            if client["name"] or client["intern"]:
                clients.append(client)
            break
    return clients


_DIAG_KEYWORDS = ("deflection", "alarm", "client", "numbers", "numberof", "calllist")


def diagnostics(fc: Any) -> dict[str, Any]:
    """Rohe TR-064-Antworten zu Rufnummern/Telefonen/Umleitungen/Weckruf einsammeln.

    Nur lesende Aktionen. Fehler werden als Text festgehalten statt ausgelöst.
    Gedacht für Fehlermeldungen (Service ``collect_diagnostics``).
    """
    result: dict[str, Any] = {"actions": {}, "calls": {}}
    for service_name, service in _services(fc).items():
        names = sorted(
            name
            for name in (getattr(service, "actions", None) or {})
            if any(word in name.lower() for word in _DIAG_KEYWORDS)
        )
        if names:
            result["actions"][service_name] = names
    plan: list[tuple[str, dict[str, object]]] = [
        ("GetNumbers", {}),
        ("GetNumberOfClients", {}),
        ("GetClients", {}),
        ("GetNumberOfDeflections", {}),
        ("GetDeflections", {}),
        ("GetNumberOfAlarmClocks", {}),
    ]
    plan += [("GetDeflection", {"DeflectionId": i}) for i in range(3)]
    plan += [("GetAlarmClock", {"Index": i}) for i in range(4)]
    plan += [("GetClient3", {"Index": i}) for i in range(3)]
    for action, values in plan:
        key = action + (str(sorted(values.items())) if values else "")
        try:
            result["calls"][key] = call(fc, action, **values)
        except TelephonyUnavailable as ex:
            result["calls"][key] = f"nicht verfügbar/Fehler: {ex}"
        except Exception as ex:  # noqa: BLE001 - Diagnose darf nie abbrechen
            result["calls"][key] = f"Fehler: {ex!r}"
    return result
