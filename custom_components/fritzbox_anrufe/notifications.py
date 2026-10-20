# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): f79cbec5112878d23f7b532488daf9463e2c05967989284e0663dea431b9d27a
"""Anbindung an das optionale Notification Center (neu in v1.6.1, Schema 1).

Die Integration *meldet* nur (Home-Assistant-Event-Bus, siehe
``notification_bridge.py``), das Notification Center sammelt und stellt zu.
Ist es nicht installiert, passiert nichts. Die bisherigen Home-Assistant-
Ereignisse (``fritzbox_anrufe_missed_call`` usw.) bleiben unverändert.

Meldungsarten (nur, was die Integration tatsächlich erkennt):

* ``missed_call``      verpasster Anruf (Live-Callmonitor), einmalig
* ``new_voicemail``    neue Nachricht auf dem Anrufbeantworter, einmalig
* ``connection_lost``  FRITZ!Box nicht erreichbar, löst sich bei Wiederherstellung
* ``update_available`` neue Version dieser Integration auf GitHub

Datenschutz: Rufnummern und Namen stehen nur als Platzhalter in den Meldungen
und werden nie geloggt. Der ``key`` ist ein Hash und enthält keine Rufnummer.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, VERSION
from .notification_bridge import OPT_ENABLED, OPT_TYPES, NotificationBridge

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .call_log import FritzCallLogCoordinator
    from .settings_data import FritzSettingsCoordinator

_LOGGER = logging.getLogger(__name__)

NC_MISSED_CALL = "missed_call"
NC_NEW_VOICEMAIL = "new_voicemail"
NC_CONNECTION_LOST = "connection_lost"
NC_UPDATE_AVAILABLE = "update_available"

_KEY_CONNECTION = "fritzbox"
_KEY_UPDATE = "integration"
_UNKNOWN = "?"

NC_CATALOG: list[dict[str, Any]] = [
    {
        "type": NC_CONNECTION_LOST,
        "severity": "warning",
        "resolvable": True,
        "enabled_default": True,
        "icon": "mdi:lan-disconnect",
        "texts": {
            "de": {
                "label": "Verbindung zur FRITZ!Box verloren",
                "title": "FRITZ!Box nicht erreichbar",
                "message": "Die Verbindung zur FRITZ!Box ist verloren gegangen.",
            },
            "en": {
                "label": "Connection to the FRITZ!Box lost",
                "title": "FRITZ!Box not reachable",
                "message": "The connection to the FRITZ!Box was lost.",
            },
            "nl": {
                "label": "Verbinding met de FRITZ!Box verloren",
                "title": "FRITZ!Box niet bereikbaar",
                "message": "De verbinding met de FRITZ!Box is verbroken.",
            },
            "fr": {
                "label": "Connexion à la FRITZ!Box perdue",
                "title": "FRITZ!Box inaccessible",
                "message": "La connexion à la FRITZ!Box a été perdue.",
            },
            "es": {
                "label": "Conexión con la FRITZ!Box perdida",
                "title": "FRITZ!Box no accesible",
                "message": "Se ha perdido la conexión con la FRITZ!Box.",
            },
        },
    },
    {
        "type": NC_MISSED_CALL,
        "severity": "info",
        "resolvable": False,
        "enabled_default": True,
        "icon": "mdi:phone-missed",
        "texts": {
            "de": {
                "label": "Verpasster Anruf",
                "title": "Verpasster Anruf von {caller}",
                "message": "{caller} hat um {time} angerufen.",
            },
            "en": {
                "label": "Missed call",
                "title": "Missed call from {caller}",
                "message": "{caller} called at {time}.",
            },
            "nl": {
                "label": "Gemiste oproep",
                "title": "Gemiste oproep van {caller}",
                "message": "{caller} belde om {time}.",
            },
            "fr": {
                "label": "Appel manqué",
                "title": "Appel manqué de {caller}",
                "message": "{caller} a appelé à {time}.",
            },
            "es": {
                "label": "Llamada perdida",
                "title": "Llamada perdida de {caller}",
                "message": "{caller} llamó a las {time}.",
            },
        },
    },
    {
        "type": NC_NEW_VOICEMAIL,
        "severity": "info",
        "resolvable": False,
        "enabled_default": True,
        "icon": "mdi:voicemail",
        "texts": {
            "de": {
                "label": "Neue Nachricht auf dem Anrufbeantworter",
                "title": "Neue Nachricht von {caller}",
                "message": "{caller} hat eine Nachricht auf Anrufbeantworter {tam} hinterlassen.",
            },
            "en": {
                "label": "New answering machine message",
                "title": "New message from {caller}",
                "message": "{caller} left a message on answering machine {tam}.",
            },
            "nl": {
                "label": "Nieuw bericht op het antwoordapparaat",
                "title": "Nieuw bericht van {caller}",
                "message": "{caller} heeft een bericht achtergelaten op antwoordapparaat {tam}.",
            },
            "fr": {
                "label": "Nouveau message sur le répondeur",
                "title": "Nouveau message de {caller}",
                "message": "{caller} a laissé un message sur le répondeur {tam}.",
            },
            "es": {
                "label": "Nuevo mensaje en el contestador",
                "title": "Nuevo mensaje de {caller}",
                "message": "{caller} dejó un mensaje en el contestador {tam}.",
            },
        },
    },
    {
        "type": NC_UPDATE_AVAILABLE,
        "severity": "info",
        "resolvable": True,
        "enabled_default": True,
        "icon": "mdi:update",
        "texts": {
            "de": {
                "label": "Update für FRITZ!Box Anrufe verfügbar",
                "title": "Update für FRITZ!Box Anrufe verfügbar",
                "message": "Version {latest} ist verfügbar (installiert: {installed}).",
            },
            "en": {
                "label": "Update for FRITZ!Box Calls available",
                "title": "Update for FRITZ!Box Calls available",
                "message": "Version {latest} is available (installed: {installed}).",
            },
            "nl": {
                "label": "Update voor FRITZ!Box Oproepen beschikbaar",
                "title": "Update voor FRITZ!Box Oproepen beschikbaar",
                "message": "Versie {latest} is beschikbaar (geïnstalleerd: {installed}).",
            },
            "fr": {
                "label": "Mise à jour de FRITZ!Box Appels disponible",
                "title": "Mise à jour de FRITZ!Box Appels disponible",
                "message": "La version {latest} est disponible (installée : {installed}).",
            },
            "es": {
                "label": "Actualización de FRITZ!Box Llamadas disponible",
                "title": "Actualización de FRITZ!Box Llamadas disponible",
                "message": "La versión {latest} está disponible (instalada: {installed}).",
            },
        },
    },
]

NC_TYPE_IDS: list[str] = [item["type"] for item in NC_CATALOG]


def _hash_key(*parts: Any) -> str:
    """Stabiler, kurzer Schlüssel ohne Klartext (keine Rufnummer im Key)."""
    raw = "|".join(str(p or "") for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]  # noqa: S324 - kein Sicherheitszweck


def _time_text(value: str | None) -> str:
    """``2026-10-20T06:31:12`` → ``06:31``; sonst Platzhalter."""
    if not value:
        return _UNKNOWN
    try:
        return datetime.fromisoformat(str(value)).strftime("%H:%M")
    except ValueError:
        return _UNKNOWN


class FritzNotifications:
    """Verbindet Callmonitor, Anrufbeantworter und Coordinatoren mit dem Notification Center."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        call_log: FritzCallLogCoordinator,
        settings: FritzSettingsCoordinator | None,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self._call_log = call_log
        self._settings = settings
        self.bridge = NotificationBridge(
            hass,
            entry,
            source=DOMAIN,
            name="FRITZ!Box Anrufe",
            version=VERSION,
            icon="mdi:phone-classic",
            catalog=NC_CATALOG,
        )
        self.bridge.set_state_provider(self._active_state)
        self._lost = False
        self._update_latest: str | None = None

    # --- Zustände -------------------------------------------------------
    def _connection_lost(self) -> bool:
        """Nur „verloren“, wenn Anrufliste UND Einstellungen nicht abrufbar sind.

        Eine fehlende Berechtigung für nur eine der beiden Abfragen ist kein
        Verbindungsverlust und soll keine Meldung auslösen.
        """
        if self._call_log.last_update_success:
            return False
        if self._settings is None:
            return True
        return not self._settings.last_update_success

    def _pending_update(self) -> str | None:
        data = getattr(self._settings, "data", None) or {}
        app = data.get("app") or {}
        if app.get("update_available") and app.get("latest_version"):
            return str(app["latest_version"])
        return None

    def _active_state(self) -> dict[str, list[dict[str, Any]]]:
        state: dict[str, list[dict[str, Any]]] = {NC_CONNECTION_LOST: [], NC_UPDATE_AVAILABLE: []}
        if self._lost:
            state[NC_CONNECTION_LOST].append(self._connection_item())
        if self._update_latest:
            state[NC_UPDATE_AVAILABLE].append(self._update_item(self._update_latest))
        return state

    @staticmethod
    def _connection_item() -> dict[str, Any]:
        return {
            "key": _KEY_CONNECTION,
            "subject": {"id": _KEY_CONNECTION, "name": "FRITZ!Box", "kind": "network"},
            "placeholders": {},
        }

    @staticmethod
    def _update_item(latest: str) -> dict[str, Any]:
        return {
            "key": _KEY_UPDATE,
            "subject": {"id": DOMAIN, "name": "FRITZ!Box Anrufe", "kind": "system"},
            "placeholders": {"latest": latest, "installed": VERSION},
        }

    # --- Lebenszyklus ---------------------------------------------------
    @callback
    def async_start(self) -> None:
        """Nach dem ersten Datenabruf: Ausgangszustand merken, Listener setzen, anmelden."""
        self._lost = self._connection_lost()
        self._update_latest = self._pending_update()
        for coordinator in (self._call_log, self._settings):
            if coordinator is not None:
                self.entry.async_on_unload(coordinator.async_add_listener(self._on_update))
        self.bridge.async_start()

    @callback
    def _on_update(self) -> None:
        lost = self._connection_lost()
        if lost != self._lost:
            self._lost = lost
            self.bridge.report(
                NC_CONNECTION_LOST,
                _KEY_CONNECTION,
                "active" if lost else "resolved",
                subject=self._connection_item()["subject"],
            )
        latest = self._pending_update()
        if latest != self._update_latest:
            previous, self._update_latest = self._update_latest, latest
            if latest:
                item = self._update_item(latest)
                self.bridge.report(
                    NC_UPDATE_AVAILABLE,
                    _KEY_UPDATE,
                    "active",
                    subject=item["subject"],
                    placeholders=item["placeholders"],
                )
            elif previous:
                self.bridge.report(NC_UPDATE_AVAILABLE, _KEY_UPDATE, "resolved")

    # --- Einmalige Meldungen -------------------------------------------
    @callback
    def async_missed_call(self, info: dict[str, Any]) -> None:
        """Verpasster Anruf (Event-Loop)."""
        caller = info.get("name") or info.get("number") or _UNKNOWN
        key = _hash_key(info.get("date"), info.get("number"), info.get("own_number"))
        self.bridge.report(
            NC_MISSED_CALL,
            key,
            "active",
            subject={"id": key, "name": "", "kind": "call"},
            placeholders={"caller": str(caller), "time": _time_text(info.get("date"))},
        )

    def missed_call_threadsafe(self, info: dict[str, Any]) -> None:
        """Aus dem Callmonitor-Thread aufrufen."""
        self.hass.loop.call_soon_threadsafe(self.async_missed_call, info)

    @callback
    def async_new_voicemail(self, message_id: Any, caller: str | None, tam: str | None) -> None:
        """Neue Anrufbeantworter-Nachricht (Event-Loop)."""
        key = f"tam{tam or '1'}-{message_id}"
        self.bridge.report(
            NC_NEW_VOICEMAIL,
            key,
            "active",
            subject={"id": key, "name": "", "kind": "call"},
            placeholders={"caller": str(caller or _UNKNOWN), "tam": str(tam or "1")},
        )

    # --- Schalter (Karte und Services) ----------------------------------
    def snapshot(self) -> dict[str, Any]:
        return self.bridge.snapshot()

    def _after_change(self) -> None:
        self.bridge.async_options_changed()
        if self._settings is not None:
            self._settings.async_update_listeners()

    @callback
    def async_set_master(self, enabled: bool) -> None:
        self.hass.config_entries.async_update_entry(
            self.entry, options={**self.entry.options, OPT_ENABLED: bool(enabled)}
        )
        self._after_change()

    @callback
    def async_set_type(self, nc_type: str, enabled: bool) -> None:
        if nc_type not in NC_TYPE_IDS:
            raise ValueError(f"Unbekannte Meldungsart: {nc_type}")
        chosen = dict(self.entry.options.get(OPT_TYPES, {}))
        chosen[nc_type] = bool(enabled)
        self.hass.config_entries.async_update_entry(
            self.entry, options={**self.entry.options, OPT_TYPES: chosen}
        )
        self._after_change()
