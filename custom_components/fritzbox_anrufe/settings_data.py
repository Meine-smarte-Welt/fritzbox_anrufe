# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 7cf4f58426505d673f0980182b7d341d7478a1c77731044d8a2d23df29ee3813
"""Telefonie-/Gerätedaten für die Einstellungen-Kategorie.

EXPERIMENTELL (seit v1.3.0b0, erweitert in v1.3.0b2) - siehe README. Diese
Daten füttern den optionalen „Einstellungen"-Tab (Zahnrad) der Dashboard-Karte.

Ziel (seit v1.3.0b2): die **Telefoniegeräte-Tabelle** der FRITZ!Box-Oberfläche
nachbilden - je Gerät (Anrufbeantworter, FRITZ!App Fon, DECT-Mobilteile,
FON-Telefone) mit Anschluss, ausgehender/ankommender Rufnummer und interner
Nummer (**6xx). Das Telefonbuch wird bewusst NICHT mehr angezeigt (nicht
editierbar und nicht vollständig darstellbar - Nutzerwunsch).

Datenquellen (in dieser Reihenfolge zusammengeführt):

1. **Weboberflächen-Seite ``data.lua?page=fondevices``** (EXPERIMENTELL, seit
   v1.3.0b2). Genau diese Seite baut die FRITZ!Box-Oberfläche selbst für die
   Telefoniegeräte-Tabelle zusammen; sie liefert die pro Gerät zugeordneten
   ausgehenden/ankommenden Rufnummern und die internen **6xx-Nummern, die über
   die dokumentierten TR-064-Aktionen NICHT abrufbar sind. Der Zugriff nutzt
   dieselbe klassische Web-UI-Anmeldung (sid) wie der Anrufbeantworter-
   Download (:class:`~fritzconnection.core.fritzhttp.FritzHttp`, siehe
   ``voicemail.py``/``tam.py``). Das JSON-Format dieser Seite ist NICHT
   unabhängig bestätigt und variiert je FRITZ!OS-Version - :func:`parse_fon_devices`
   ist daher bewusst tolerant (mehrere Kandidaten-Schlüssel) und liefert bei
   unbekanntem Aufbau lieber weniger Felder als eine Ausnahme. Bei HTTP 200
   ohne verwertbaren Inhalt werden die obersten JSON-Schlüssel protokolliert
   (wie bei ``tam.py``), damit sich der Abrufweg gezielt an echte Hardware
   anpassen lässt.

2. **TR-064** als robuster Zusatz/Fallback (dieselbe Berechtigung wie die
   bereits funktionierende Anrufliste):
     - ``GetNumbers``          → Liste der Rufnummern (MSN) mit Namen/Typ
     - ``GetDECTHandsetList``  → IDs der angemeldeten DECT-Mobilteile
     - ``GetDECTHandsetInfo``  → Name je Mobilteil
   Liefert ``fondevices`` keine Gerätezeilen (Seite unbekannt, Rechte fehlen,
   HTTPS-only-Web-UI …), werden aus DECT-Mobilteilen + Rufnummern trotzdem
   minimale Gerätezeilen erzeugt, damit der Tab nicht leer bleibt.

Alle Netzabrufe sind defensiv gekapselt: Schlägt eine Teil-Abfrage fehl, bleibt
der betroffene Teil leer, statt den Sensor/das Setup scheitern zu lassen. Nur
wenn ausnahmslos ALLES fehlschlägt, meldet der Coordinator ``UpdateFailed``.
"""

from __future__ import annotations

from datetime import timedelta
import logging
from xml.etree import ElementTree

from fritzconnection.core.exceptions import FritzConnectionException
from fritzconnection.core.fritzhttp import FritzHttp
from requests.exceptions import RequestException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .base import FritzBoxPhonebook

_LOGGER = logging.getLogger(__name__)

SETTINGS_UPDATE_INTERVAL = timedelta(minutes=30)

_ONTEL_SERVICE = "X_AVM-DE_OnTel:1"

# Weboberflächen-Seite, die die Telefoniegeräte-Tabelle liefert. Reihenfolge =
# Versuchsreihenfolge (verschiedene FRITZ!OS-Stände benennen sie leicht anders).
_FON_DEVICE_PAGES = ("fondevices", "fonDevices", "dectRegDev")

# Kandidaten-Schlüssel, unter denen die Geräteliste im data.lua-JSON stehen kann.
_DEVICE_LIST_KEYS = ("fonDevices", "fondevices", "devices", "handsets", "mobiles", "rows")

# Kandidaten-Feldnamen je Gerät (defensiv, FRITZ!OS-abhängig).
_NAME_KEYS = ("name", "device_name", "devicename", "displayname", "title")
_TYPE_KEYS = ("type", "devtype", "kind", "class")
_OUTGOING_KEYS = ("outgoing", "out", "outgoingNumber", "msnOutgoing", "ausgehend")
_INCOMING_KEYS = (
    "incoming",
    "inComming",
    "incomming",
    "in",
    "incomingNumbers",
    "msnIncoming",
    "ankommend",
)
_INTERN_KEYS = ("intern", "internal", "internalNumbers", "internnumber", "internalnumber")

# Rohe Gerätetypen, die einen Anrufbeantworter kennzeichnen (Schalter anzeigen).
_TAM_TYPE_TOKENS = ("tam", "answer", "anrufbeantworter")


def parse_numbers_xml(raw: str | None) -> list[dict[str, str]]:
    """Parse the ``NewNumberList`` XML from ``GetNumbers`` into plain dicts.

    Erwartetes Format (FRITZ!OS):
        <List><Item><Number>...</Number><Type>...</Type><Name>...</Name></Item>…</List>
    Unbekannte/fehlende Felder werden übersprungen bzw. leer gelassen; ein
    nicht parsebarer String ergibt eine leere Liste (defensiv).
    """
    if not raw or not raw.strip():
        return []
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        return []
    numbers: list[dict[str, str]] = []
    for item in root.iter("Item"):
        number = (item.findtext("Number") or "").strip()
        if not number:
            continue
        numbers.append(
            {
                "number": number,
                "type": (item.findtext("Type") or "").strip(),
                "name": (item.findtext("Name") or "").strip(),
            }
        )
    return numbers


def parse_dect_id_list(raw: str | None) -> list[str]:
    """Zerlege ``NewDectIDList`` ("1,2,3") in eine bereinigte ID-Liste."""
    if not raw:
        return []
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def build_dect_handsets(
    ids: list[str], info_by_id: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    """Kombiniere DECT-IDs mit ihren (bereits abgerufenen) Info-Feldern."""
    handsets: list[dict[str, str]] = []
    for dect_id in ids:
        info = info_by_id.get(dect_id, {})
        handsets.append(
            {
                "id": dect_id,
                "name": (info.get("name") or f"DECT {dect_id}").strip(),
            }
        )
    return handsets


def _first(entry: dict, keys: tuple[str, ...]) -> str:
    """Erster nicht-leerer String unter den Kandidaten-Schlüsseln (rekursiv-tolerant)."""
    for key in keys:
        if key not in entry:
            continue
        value = entry[key]
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            joined = ", ".join(str(v).strip() for v in value if str(v).strip())
            if joined:
                return joined
            continue
        if isinstance(value, dict):
            # gelegentlich {"number": "..."} o. ä.
            nested = _first(value, ("number", "value", "msn", "name"))
            if nested:
                return nested
            continue
        text = str(value).strip()
        if text and text.lower() not in ("none", "null"):
            return text
    return ""


def _looks_like_device(entry: dict) -> bool:
    """Heuristik: sieht dieser Dict wie eine Telefoniegeräte-Zeile aus?"""
    if not isinstance(entry, dict):
        return False
    has_name = bool(_first(entry, _NAME_KEYS))
    has_phone_field = any(
        key in entry for key in (*_OUTGOING_KEYS, *_INCOMING_KEYS, *_INTERN_KEYS, *_TYPE_KEYS)
    )
    return has_name and has_phone_field


def _find_device_lists(obj: object, depth: int = 0) -> list[list[dict]]:
    """Suche im JSON rekursiv nach Listen, die wie Gerätezeilen aussehen.

    Zuerst über die bekannten Schlüssel (:data:`_DEVICE_LIST_KEYS`), dann als
    letzte Rückfalllösung rekursiv über die gesamte Struktur - immer nur Listen,
    deren Elemente die :func:`_looks_like_device`-Heuristik erfüllen.
    """
    found: list[list[dict]] = []
    if depth > 6:
        return found
    if isinstance(obj, dict):
        for key in _DEVICE_LIST_KEYS:
            value = obj.get(key)
            if isinstance(value, list) and any(_looks_like_device(v) for v in value):
                found.append([v for v in value if isinstance(v, dict)])
        for value in obj.values():
            found.extend(_find_device_lists(value, depth + 1))
    elif isinstance(obj, list):
        if any(_looks_like_device(v) for v in obj):
            found.append([v for v in obj if isinstance(v, dict)])
        else:
            for value in obj:
                found.extend(_find_device_lists(value, depth + 1))
    return found


_TYPE_ANSCHLUSS = {
    "dect": "DECT",
    "fon": "FON",
    "pots": "FON",
    "isdn": "S0",
    "app": "LAN/WLAN",
    "iptv": "LAN/WLAN",
    "tam": "Anrufbeantworter",
}


def _anschluss_for(raw_type: str, name: str) -> str:
    """Menschlich lesbaren Anschluss aus rohem Typ/Namen ableiten (best effort)."""
    token = (raw_type or "").lower()
    for key, label in _TYPE_ANSCHLUSS.items():
        if key in token:
            return label
    low = (name or "").lower()
    if "anrufbeantworter" in low or low.startswith("ab"):
        return "Anrufbeantworter"
    if "mobilteil" in low or "dect" in low:
        return "DECT"
    if "app" in low:
        return "LAN/WLAN"
    return raw_type.strip() if raw_type else ""


def parse_fon_devices(payload: object) -> list[dict[str, object]]:
    """Normalisiere die (rohe) ``data.lua``-Geräteliste in Kartenzeilen.

    Tolerant gegenüber unterschiedlichen FRITZ!OS-Formaten: sucht die
    Geräteliste über bekannte Schlüssel bzw. per Heuristik und liest je Gerät
    Name/Typ/ausgehende/ankommende/interne Nummer aus mehreren Kandidaten-
    Feldnamen. Unbekanntes ergibt eine leere Liste (kein Fehler).
    """
    lists = _find_device_lists(payload)
    # Nimm die längste plausible Liste (die eigentliche Gerätetabelle ist i. d. R.
    # länger als z. B. eine Basis-Info-Liste).
    devices: list[dict] = max(lists, key=len) if lists else []
    rows: list[dict[str, object]] = []
    tam_index = 0
    for entry in devices:
        name = _first(entry, _NAME_KEYS)
        if not name:
            continue
        raw_type = _first(entry, _TYPE_KEYS)
        outgoing = _first(entry, _OUTGOING_KEYS)
        incoming = _first(entry, _INCOMING_KEYS)
        intern = _first(entry, _INTERN_KEYS)
        low = f"{raw_type} {name}".lower()
        is_tam = any(tok in low for tok in _TAM_TYPE_TOKENS)
        if is_tam:
            tam_index += 1
        rows.append(
            {
                "name": name,
                "type": raw_type,
                "anschluss": _anschluss_for(raw_type, name),
                "outgoing": outgoing,
                "incoming": incoming,
                "intern": intern,
                "is_tam": is_tam,
                # 1-basierter Index NUR unter den Anrufbeantwortern, damit die
                # Karte die Zeile dem passenden Ein/Aus-Schalter zuordnen kann
                # (entity_tam_switch / entity_tam_switch_N).
                "tam_index": tam_index if is_tam else 0,
            }
        )
    return rows


class FritzSettingsCoordinator(DataUpdateCoordinator[dict]):
    """Liest Telefonie-/Gerätedaten (EXPERIMENTELL, seit v1.3.0b0)."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        fritzbox_phonebook: FritzBoxPhonebook,
    ) -> None:
        """Initialize the settings coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="fritzbox_anrufe settings",
            update_interval=SETTINGS_UPDATE_INTERVAL,
        )
        self.config_entry = config_entry
        self._phonebook = fritzbox_phonebook
        # Nur für den EXPERIMENTELLEN data.lua-Weg (Web-UI-sid + router_url),
        # exakt wie in voicemail.py für den Anrufbeantworter-Download.
        self._http = FritzHttp(fritzbox_phonebook.fph.fc)

    # --- TR-064-Geräte/-Nummern (blocking, executor) ------------------------
    def _fetch_numbers(self) -> list[dict[str, str]]:
        try:
            result = self._phonebook.fph.fc.call_action(_ONTEL_SERVICE, "GetNumbers")
        except (FritzConnectionException, RequestException, ValueError, KeyError) as ex:
            _LOGGER.debug("GetNumbers nicht verfügbar: %s", ex)
            return []
        return parse_numbers_xml(result.get("NewNumberList"))

    def _fetch_dect_handsets(self) -> list[dict[str, str]]:
        try:
            listing = self._phonebook.fph.fc.call_action(_ONTEL_SERVICE, "GetDECTHandsetList")
        except (FritzConnectionException, RequestException, ValueError, KeyError) as ex:
            _LOGGER.debug("GetDECTHandsetList nicht verfügbar: %s", ex)
            return []
        ids = parse_dect_id_list(listing.get("NewDectIDList"))
        info_by_id: dict[str, dict[str, str]] = {}
        for dect_id in ids:
            try:
                info = self._phonebook.fph.fc.call_action(
                    _ONTEL_SERVICE, "GetDECTHandsetInfo", NewDectID=int(dect_id)
                )
            except (FritzConnectionException, RequestException, ValueError, KeyError) as ex:
                _LOGGER.debug("GetDECTHandsetInfo(%s) nicht verfügbar: %s", dect_id, ex)
                continue
            info_by_id[dect_id] = {
                "name": str(info.get("NewHandsetName", "")).strip(),
            }
        return build_dect_handsets(ids, info_by_id)

    def _fetch_fon_devices(self) -> list[dict[str, object]]:
        """Hole die Telefoniegeräte-Tabelle über ``data.lua`` (EXPERIMENTELL).

        Broad gekapselt (wie ``voicemail.py:fetch_audio``), da dieser Web-UI-
        Weg noch nicht an echter Hardware bestätigt ist: jede Ausnahme führt zu
        einer leeren Liste (der Sensor fällt dann auf die TR-064-Daten zurück),
        niemals zu einem Setup-/Sensor-Fehler.
        """
        try:
            origin = self._http.router_url
        except Exception as ex:  # noqa: BLE001 - unbestätigter Pfad, siehe Docstring
            _LOGGER.debug("Einstellungen: FRITZ!Box-Webadresse unklar (%s)", ex)
            return []

        session = self._phonebook.fph.fc.session
        for sid in self._sid_candidates():
            if not sid:
                continue
            for page in _FON_DEVICE_PAGES:
                try:
                    response = session.post(
                        f"{origin}/data.lua",
                        data={
                            "sid": sid,
                            "page": page,
                            "lang": "de",
                            "xhr": "1",
                            "xhrId": "all",
                        },
                        timeout=15,
                    )
                except Exception as ex:  # noqa: BLE001 - siehe Docstring
                    _LOGGER.debug("data.lua?page=%s fehlgeschlagen: %s", page, ex)
                    continue
                if response.status_code != 200:
                    continue
                text = (response.text or "").strip()
                if not text.startswith("{"):
                    continue
                try:
                    payload = response.json()
                except ValueError:
                    continue
                rows = parse_fon_devices(payload)
                if rows:
                    return rows
                # HTTP 200, aber kein verwertbarer Aufbau: oberste Schlüssel
                # protokollieren, damit sich das Format gezielt ergänzen lässt
                # (wie tam.py bei GetMessageList).
                top = sorted(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
                _LOGGER.debug(
                    "Einstellungen: data.lua?page=%s ohne erkennbare Geräteliste"
                    " (oberste Schlüssel: %s) - bitte als GitHub-Issue melden.",
                    page,
                    top,
                )
        return []

    def _sid_candidates(self):
        """Web-UI-sids zum Probieren liefern (wie voicemail.py._sid_candidates)."""
        try:
            yield from self._http._get_sid()  # noqa: SLF001 - siehe voicemail.py
        except Exception as ex:  # noqa: BLE001 - unbestätigter Login-Pfad
            _LOGGER.debug("Einstellungen: Web-UI-Anmeldung fehlgeschlagen (%s)", ex)
            return

    def _fallback_devices(
        self, handsets: list[dict[str, str]], numbers: list[dict[str, str]]
    ) -> list[dict[str, object]]:
        """Minimale Gerätezeilen aus TR-064-DECT/Rufnummern, falls data.lua leer.

        Ohne die ausgehende/ankommende/interne Zuordnung (die liefert nur
        ``fondevices``) - aber besser als eine leere Tabelle.
        """
        rows: list[dict[str, object]] = []
        for handset in handsets:
            rows.append(
                {
                    "name": handset.get("name") or f"DECT {handset.get('id', '')}",
                    "type": "dect",
                    "anschluss": "DECT",
                    "outgoing": "",
                    "incoming": "",
                    "intern": "",
                    "is_tam": False,
                    "tam_index": 0,
                }
            )
        return rows

    def _fetch(self) -> dict:
        numbers = self._fetch_numbers()
        dect = self._fetch_dect_handsets()
        devices = self._fetch_fon_devices()
        used_fallback = False
        if not devices:
            devices = self._fallback_devices(dect, numbers)
            used_fallback = bool(devices)
        # Nur wenn ALLES leer ist, gilt die Aktualisierung als gescheitert.
        if not numbers and not dect and not devices:
            raise UpdateFailed(
                "Keine Telefonie-/Gerätedaten abrufbar"
                " (Aktion nicht unterstützt oder fehlende Berechtigung)"
            )
        return {
            "numbers": numbers,
            "dect_handsets": dect,
            "devices": devices,
            # True, wenn die Gerätezeilen nur aus dem TR-064-Fallback stammen
            # (also OHNE ausgehende/ankommende/interne Nummern) - die Karte
            # zeigt dann einen entsprechenden Hinweis.
            "devices_fallback": used_fallback,
            "repeaters": [],
        }

    async def _async_update_data(self) -> dict:
        """Fetch settings data (executor job)."""
        return await self.hass.async_add_executor_job(self._fetch)
