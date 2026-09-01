# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 9e86228658be8a5df0604ee556df9e61e0d62fa56daa1c3357035a439e8a973f
"""Telefonie-/Geräte- und Telefonbuch-Daten für die Einstellungen-Kategorie.

EXPERIMENTELL (seit v1.3.0b0) - siehe README. Diese Daten füttern den neuen
optionalen „Einstellungen"-Tab (Zahnrad) der Dashboard-Karte. Zwei Quellen:

1. Telefonie-/DECT-Geräte über die dokumentierten TR-064-Aktionen des Diensts
   ``X_AVM-DE_OnTel``:
     - ``GetNumbers``          → Liste der Rufnummern (MSN) mit Namen/Typ
     - ``GetDECTHandsetList``  → IDs der angemeldeten DECT-Mobilteile
     - ``GetDECTHandsetInfo``  → Name (und Telefonbuch-Zuordnung) je Mobilteil
   Die vollständige „Telefoniegeräte"-Tabelle der FRITZ!Box-Oberfläche (inkl.
   FON/App-Geräten, interner **6xx-Nummern und der ausgehenden/ankommenden
   Rufnummern-Zuordnung PRO GERÄT) ist über TR-064 nicht sauber abrufbar - die
   FRITZ!Box-Weboberfläche baut sie aus ``data.lua`` zusammen. Diese b0 nutzt
   bewusst nur den robusten, dokumentierten TR-064-Weg (dieselbe Berechtigung
   wie die bereits funktionierende Anrufliste); der reichere ``data.lua``-Weg
   (wie ihn z. B. FRITZ-Portal nutzt) ist ein möglicher Ausbau für eine spätere
   Beta. DECT-Repeater werden über TR-064 hier ebenfalls nicht separat
   ausgewiesen (kein bestätigter Weg) - daher vorerst leer.

2. Telefonbuch (nur LESEN in dieser b0) über :class:`fritzconnection.lib.
   fritzphonebook.FritzPhonebook`.

Alle Netzabrufe sind defensiv gekapselt: Schlägt eine Teil-Abfrage fehl (z. B.
weil das FRITZ!OS die Aktion nicht kennt oder dem Konto die Rechte fehlen),
bleibt der betroffene Teil leer, statt den Sensor/das Setup scheitern zu
lassen. Nur wenn ausnahmslos ALLES fehlschlägt, meldet der Coordinator
``UpdateFailed`` (der Sensor wird dann „nicht verfügbar").
"""

from __future__ import annotations

from datetime import timedelta
import logging
from xml.etree import ElementTree

from fritzconnection.core.exceptions import FritzConnectionException
from requests.exceptions import RequestException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .base import FritzBoxPhonebook

_LOGGER = logging.getLogger(__name__)

SETTINGS_UPDATE_INTERVAL = timedelta(minutes=30)

_ONTEL_SERVICE = "X_AVM-DE_OnTel:1"


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
    # Sowohl <Item> direkt als auch verschachtelt tolerieren.
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
                "phonebook_id": info.get("phonebook_id", ""),
            }
        )
    return handsets


class FritzSettingsCoordinator(DataUpdateCoordinator[dict]):
    """Liest Telefonie-/Geräte- und Telefonbuchdaten (EXPERIMENTELL, seit v1.3.0b0)."""

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
                "phonebook_id": str(info.get("NewPhonebookID", "")).strip(),
            }
        return build_dect_handsets(ids, info_by_id)

    def _fetch_phonebook(self) -> tuple[int | None, list[dict[str, object]]]:
        try:
            ids = self._phonebook.get_phonebook_ids() or []
        except (FritzConnectionException, RequestException, ValueError, KeyError) as ex:
            _LOGGER.debug("Telefonbuch-IDs nicht verfügbar: %s", ex)
            return None, []
        book_id = self.config_entry.data.get("phonebook", ids[0] if ids else 0)
        if book_id not in ids and ids:
            book_id = ids[0]
        try:
            entries = self._phonebook.fph.get_all_name_numbers(book_id)
        except (FritzConnectionException, RequestException, ValueError, KeyError) as ex:
            _LOGGER.debug("Telefonbuch %s nicht lesbar: %s", book_id, ex)
            return book_id, []
        contacts: list[dict[str, object]] = []
        for entry in entries or []:
            # get_all_name_numbers liefert (name, [numbers]) Tupel.
            try:
                name, numbers = entry
            except (TypeError, ValueError):
                continue
            contacts.append(
                {"name": str(name), "numbers": [str(n) for n in (numbers or [])]}
            )
        contacts.sort(key=lambda c: str(c["name"]).lower())
        return book_id, contacts

    def _fetch(self) -> dict:
        numbers = self._fetch_numbers()
        dect = self._fetch_dect_handsets()
        book_id, contacts = self._fetch_phonebook()
        # Nur wenn ALLES leer/fehlgeschlagen ist, gilt die Aktualisierung als
        # gescheitert - sonst zeigt die Karte, was verfügbar war.
        if not numbers and not dect and not contacts and book_id is None:
            raise UpdateFailed(
                "Weder Telefonie-/DECT-Geräte noch Telefonbuch abrufbar"
                " (Aktion nicht unterstützt oder fehlende Berechtigung)"
            )
        return {
            "numbers": numbers,
            "dect_handsets": dect,
            "repeaters": [],  # via TR-064 hier nicht bestätigt ermittelbar
            "phonebook_id": book_id,
            "contacts": contacts,
        }

    async def _async_update_data(self) -> dict:
        """Fetch settings data (executor job)."""
        return await self.hass.async_add_executor_job(self._fetch)
