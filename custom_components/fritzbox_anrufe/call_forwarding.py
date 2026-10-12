# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 64ccd3a25fbe5256339016884ec4ad80ab1e408369b029b8d9eab6a003d15aa9
"""Rufumleitungen der Web-Oberfläche („Rufbehandlung“ → Rufumleitung) verwalten.

Neu in v1.6.0. Grundlage ist die Web-Oberfläche der FRITZ!Box (FRITZ!OS 8.x):
Die Seite ``callRedi`` liefert die Liste (``rul_list``), ``rul_edit`` ist das
Formular zum Anlegen. Gespeichert wird - wie in der Oberfläche selbst - per
``POST /data.lua`` mit dem Feld ``apply`` (Anlegen), ``setRufActive``
(Ein-/Ausschalten) bzw. ``delete`` (Löschen).

Das ist KEINE dokumentierte AVM-Schnittstelle. Deshalb:

* alle Werte werden gegen die Auswahllisten der Box geprüft,
* nach jedem Schreibzugriff wird die Liste zurückgelesen und das Ergebnis
  geprüft (sonst gibt es einen Fehler statt einer falschen Erfolgsmeldung),
* Zwei-Faktor-Bestätigungen der Box werden nicht umgangen.

Dieses Modul importiert Home Assistant nicht (testbar ohne). ``post`` ist eine
Funktion ``dict -> dict | None`` (Antwort-JSON von ``data.lua``).
"""

from __future__ import annotations

import re
from typing import Any, Callable

Post = Callable[[dict[str, str]], "dict | None"]

_NUMBER_RE = re.compile(r"^[0-9+*#]{1,20}$")
MODES = ("to", "from", "all")
DEST_TYPES = ("number", "answering_machine", "phone")


class ForwardingError(Exception):
    """Rufumleitung konnte nicht gelesen/geändert werden (Text für Nutzer)."""


def _data(payload: Any) -> dict:
    if not isinstance(payload, dict):
        return {}
    inner = payload.get("data")
    return inner if isinstance(inner, dict) else payload


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def parse_rules(payload: Any) -> list[dict[str, Any]]:
    """``rul_list`` der Seite ``callRedi`` in eine einheitliche Liste umsetzen."""
    rows = _data(payload).get("rul_list")
    result: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, dict) or not row.get("uid"):
            continue
        rule_type = str(row.get("type", ""))
        # Wie die Oberfläche: "Wichtiger Anrufer"-Einträge und Zeilen ohne Ziel
        # (rub/action 2) sind nicht schaltbar.
        if rule_type == "rub" and str(row.get("action", "")) == "1":
            continue
        result.append(
            {
                "uid": str(row["uid"]),
                "type": rule_type,
                "active": bool(row.get("active")),
                "from": str(row.get("from") or row.get("portname") or row.get("name") or ""),
                "to": str(row.get("to") or ""),
                "over": str(row.get("over") or ""),
                "mode": str(row.get("mode") or ""),
                "time_ctrl": bool(row.get("time_ctrl")),
                "switchable": rule_type in ("rul", "rub") and str(row.get("action", "0")) != "2",
            }
        )
    return result


def parse_options(payload: Any) -> dict[str, Any]:
    """Auswahllisten aus ``rul_edit`` (``vars.rul``) lesen."""
    rul = (_data(payload).get("vars") or {}).get("rul") or {}

    def pairs(key: str) -> list[dict[str, str]]:
        items = rul.get(key)
        out = []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("value") not in (None, ""):
                    out.append({"value": str(item["value"]), "display": str(item.get("display", item["value"]))})
        return out

    kinds = (rul.get("listOfKinds") or {}).get("options") or {}

    def kind_list(key: str) -> list[dict[str, str]]:
        return [
            {"value": str(i["value"]), "display": str(i.get("display", i["value"]))}
            for i in (kinds.get(key) or [])
            if isinstance(i, dict) and i.get("value")
        ]

    return {
        "editable": bool((rul.get("page") or {}).get("editable", True)),
        "targets": pairs("listOfTo"),
        "phones": pairs("listOfFons"),
        "answering_machines": pairs("listOfTams"),
        "own_numbers": pairs("ownNumbers"),
        "kinds_msn": kind_list("msn"),
        "kinds_port": kind_list("port"),
    }


def read_rules(post: Post) -> list[dict[str, Any]] | None:
    """Regeln lesen; ``None``, wenn die Seite nicht lesbar ist."""
    payload = post({"page": "callRedi", "xhr": "1", "xhrId": "all"})
    if payload is None:
        return None
    return parse_rules(payload)


def read_options(post: Post) -> dict[str, Any]:
    payload = post({"page": "rul_edit", "uid": "new", "backToPage": "callRedi", "xhr": "1"})
    if payload is None:
        raise ForwardingError("Das Formular „Neue Rufumleitung“ ist auf der FRITZ!Box nicht lesbar.")
    return parse_options(payload)


def _check_number(value: Any, what: str) -> str:
    text = str(value or "").strip().replace(" ", "")
    if not _NUMBER_RE.match(text):
        raise ForwardingError(f"{what}: nur Ziffern sowie + * # sind erlaubt (max. 20 Zeichen).")
    return text


def _in(options: list[dict[str, str]], value: Any, what: str) -> str:
    text = str(value or "").strip()
    if text not in {o["value"] for o in options}:
        shown = ", ".join(f"{o['value']} ({o['display']})" for o in options) or "keine"
        raise ForwardingError(f"{what}: „{text}“ ist nicht möglich. Erlaubt: {shown}.")
    return text


def build_create_form(options: dict[str, Any], **p: Any) -> dict[str, str]:
    """Formularfelder für „Neue Rufumleitung“ bauen und gegen die Box-Listen prüfen.

    Parameter: ``mode`` (to/from/all), ``target`` (bei ``to``: Wert aus ``targets``),
    ``from_number`` (bei ``from``; leer = anonym), ``dest_type`` (number/
    answering_machine/phone), ``dest`` (Rufnummer bzw. Wert aus der jeweiligen
    Liste), ``own_number`` (Standard ``*`` = automatisch), ``kind`` (Art).
    """
    if not options.get("editable", True):
        raise ForwardingError("Die FRITZ!Box erlaubt hier keine Änderung (keine Berechtigung).")
    mode = str(p.get("mode") or "")
    if mode not in MODES:
        raise ForwardingError("mode muss 'to', 'from' oder 'all' sein.")
    dest_type = str(p.get("dest_type") or "")
    if dest_type not in DEST_TYPES:
        raise ForwardingError("dest_type muss 'number', 'answering_machine' oder 'phone' sein.")

    form: dict[str, str] = {
        "page": "rul_edit",
        "uid": "new",
        "back_to_page": "callRedi",
        "callsToBeRedirected": {"to": "call_to", "from": "call_from", "all": "all"}[mode],
    }
    is_port = False
    if mode == "to":
        target = _in(options["targets"], p.get("target"), "target")
        form["listTo"] = target
        is_port = target.startswith("FON")
    elif mode == "from":
        from_number = str(p.get("from_number") or "").strip()
        if from_number:
            form["listFrom"] = "number"
            form["num_from"] = _check_number(from_number, "from_number")
        else:
            form["listFrom"] = "anonymous"
        form["listOverSpecificNumber"] = "*"

    if dest_type == "number":
        dest = _check_number(p.get("dest"), "dest")
        form.update({"callsDestination": "num", "listNum": "new_num", "num_to": dest, "connectTo": dest})
    elif dest_type == "answering_machine":
        form.update(
            {"callsDestination": "tam", "listTam": _in(options["answering_machines"], p.get("dest"), "dest")}
        )
    else:
        form.update({"callsDestination": "phone", "listPhone": _in(options["phones"], p.get("dest"), "dest")})

    if not is_port and dest_type != "answering_machine":
        own = p.get("own_number") or "*"
        form["ownNumber"] = _in(options["own_numbers"], own, "own_number")

    kind = p.get("kind")
    if mode == "to":
        kinds = options["kinds_port"] if is_port else options["kinds_msn"]
        form["kind_port" if is_port else "kind_msn"] = _in(kinds, kind or "NOW", "kind")
    form["apply"] = ""
    return form


def _result(payload: dict | None) -> tuple[str, dict]:
    data = _data(payload)
    for key in ("apply", "delete", "setRufActive"):
        if key in data:
            return str(data[key]), data
    return "", data


def _raise_for(status: str, data: dict) -> None:
    if status == "valerror":
        alert = (data.get("valerror") or {}).get("alert") or "ungültige Eingabe"
        raise ForwardingError(f"Die FRITZ!Box lehnt die Eingabe ab: {alert}")
    if status == "saveerror":
        msg = (data.get("saveerror") or {}).get("msg") or "Speichern nicht möglich"
        raise ForwardingError(f"Die FRITZ!Box konnte nicht speichern: {msg}")
    if status == "twofactor":
        raise ForwardingError(
            "Die FRITZ!Box verlangt eine Bestätigung am Gerät (Zwei-Faktor). "
            "Bitte lege die Rufumleitung in der FRITZ!Box-Oberfläche an."
        )


def _submit(post: Post, form: dict[str, str]) -> dict:
    payload = post(form)
    if payload is None:
        raise ForwardingError("Keine Antwort der FRITZ!Box (Web-Anmeldung nicht möglich?).")
    status, data = _result(payload)
    if status == "confirm":
        payload = post({**form, "confirmed": ""})
        if payload is None:
            raise ForwardingError("Keine Antwort der FRITZ!Box auf die Rückfrage.")
        status, data = _result(payload)
    _raise_for(status, data)
    if status != "ok":
        raise ForwardingError(f"Unerwartete Antwort der FRITZ!Box ({status or 'leer'}).")
    return data


def create_rule(post: Post, **params: Any) -> dict[str, Any]:
    """Neue Rufumleitung anlegen und prüfen, dass sie in der Liste erscheint."""
    options = read_options(post)
    form = build_create_form(options, **params)
    before = read_rules(post) or []
    known = {r["uid"] for r in before}
    _submit(post, form)
    after = read_rules(post)
    if after is None:
        raise ForwardingError("Die Rufumleitung wurde gesendet, die Liste ist aber nicht lesbar.")
    new = [r for r in after if r["uid"] not in known]
    if not new:
        raise ForwardingError(
            "Die FRITZ!Box hat zwar geantwortet, es erscheint aber keine neue Rufumleitung in der Liste."
        )
    return new[0]


def set_rule_enabled(post: Post, uid: str, enabled: bool) -> dict[str, Any]:
    rules = read_rules(post)
    if rules is None:
        raise ForwardingError("Die Rufumleitungen sind auf der FRITZ!Box nicht lesbar.")
    rule = next((r for r in rules if r["uid"] == str(uid)), None)
    if rule is None:
        raise ForwardingError(f"Rufumleitung „{uid}“ gibt es auf dieser FRITZ!Box nicht.")
    if not rule["switchable"]:
        raise ForwardingError("Diese Rufumleitung lässt sich nicht ein-/ausschalten.")
    _submit(
        post,
        {"page": "callRedi", "setRufActive": str(uid), "ruf_value": "1" if enabled else "0"},
    )
    for r in read_rules(post) or []:
        if r["uid"] == str(uid):
            if r["active"] != enabled:
                raise ForwardingError("Die FRITZ!Box hat den Zustand der Rufumleitung nicht geändert.")
            return r
    raise ForwardingError("Die Rufumleitung ist nach dem Schalten nicht mehr lesbar.")


def delete_rule(post: Post, uid: str) -> None:
    rules = read_rules(post)
    if rules is None:
        raise ForwardingError("Die Rufumleitungen sind auf der FRITZ!Box nicht lesbar.")
    if not any(r["uid"] == str(uid) for r in rules):
        raise ForwardingError(f"Rufumleitung „{uid}“ gibt es auf dieser FRITZ!Box nicht.")
    _submit(post, {"page": "callRedi", "delete": str(uid)})
    if any(r["uid"] == str(uid) for r in read_rules(post) or []):
        raise ForwardingError("Die FRITZ!Box hat die Rufumleitung nicht gelöscht.")
