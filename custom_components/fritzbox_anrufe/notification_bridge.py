# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 92a92c75fe1ebc345a644069f84b250c5f08a8b2dbbd29757fa514324e19194d
"""Brücke zum optionalen Notification Center (Schnittstelle Schema 1).

Identisch in allen Integrationen. Nur aus dem Event-Loop aufrufen.
Payloads (Rufnummern, Namen) werden nie geloggt.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)

SCHEMA = 1
EVENT_REPORT = "notification_center_report"
EVENT_REGISTER = "notification_center_register"
EVENT_SYNC = "notification_center_sync"
EVENT_PING = "notification_center_ping"
SEVERITIES = ("critical", "warning", "info", "ok")
LANGUAGES = ("de", "en", "nl", "fr", "es")
OPT_ENABLED = "nc_enabled"
OPT_TYPES = "nc_types"

StateProvider = Callable[[], dict[str, list[dict[str, Any]]]]


class NotificationBridge:
    """Sendet Meldungen ans Notification Center, falls eingeschaltet."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        source: str,
        name: str,
        version: str,
        icon: str,
        catalog: list[dict[str, Any]],
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.source = source
        self.name = name
        self.version = version
        self.icon = icon
        self._provider: StateProvider | None = None
        self._catalog: dict[str, dict[str, Any]] = {}
        for item in catalog:
            if item["severity"] not in SEVERITIES:
                raise ValueError(f"Ungültige Dringlichkeit: {item['type']}")
            missing = [lang for lang in LANGUAGES if lang not in item["texts"]]
            if missing:
                raise ValueError(f"Sprachen fehlen bei {item['type']}: {missing}")
            self._catalog[item["type"]] = item

    # --- Zustand -----------------------------------------------------
    @property
    def master_enabled(self) -> bool:
        return bool(self.entry.options.get(OPT_ENABLED, True))

    def type_enabled(self, type_: str) -> bool:
        item = self._catalog.get(type_)
        if item is None or not self.master_enabled:
            return False
        chosen = self.entry.options.get(OPT_TYPES, {})
        return bool(chosen.get(type_, item.get("enabled_default", True)))

    @property
    def available(self) -> bool:
        """True, wenn das Notification Center installiert und geladen ist."""
        return bool(self.hass.config_entries.async_loaded_entries("notification_center"))

    def snapshot(self) -> dict[str, Any]:
        """Für die Karte: Katalog nach Dringlichkeit sortiert mit Schalterstand."""
        order = {s: i for i, s in enumerate(SEVERITIES)}
        types = sorted(self._catalog.values(), key=lambda t: order[t["severity"]])
        return {
            "available": self.available,
            "enabled": self.master_enabled,
            "types": [
                {
                    "type": t["type"],
                    "severity": t["severity"],
                    "icon": t.get("icon"),
                    "enabled": self.type_enabled(t["type"]),
                    "labels": {lang: t["texts"][lang]["label"] for lang in LANGUAGES},
                }
                for t in types
            ],
        }

    # --- Lebenszyklus ------------------------------------------------
    def set_state_provider(self, provider: StateProvider) -> None:
        """Liefert {type: [{"key", "subject", "placeholders"}, ...]} der aktiven Zustände."""
        self._provider = provider

    @callback
    def async_start(self) -> None:
        """Nach dem ersten erfolgreichen Datenabruf aufrufen."""
        self.entry.async_on_unload(self.hass.bus.async_listen(EVENT_PING, self._handle_ping))
        self.async_register()
        self.async_sync()

    @callback
    def _handle_ping(self, _event: Event) -> None:
        self.async_register()
        self.async_sync()

    @callback
    def async_options_changed(self) -> None:
        self.async_register()
        self.async_sync()

    # --- Senden ------------------------------------------------------
    @callback
    def async_register(self) -> None:
        self.hass.bus.async_fire(
            EVENT_REGISTER,
            {
                "schema": SCHEMA,
                "source": self.source,
                "entry_id": self.entry.entry_id,
                "name": self.name,
                "version": self.version,
                "icon": self.icon,
                "enabled": self.master_enabled,
                "types": [
                    {**item, "enabled": self.type_enabled(item["type"])}
                    for item in self._catalog.values()
                ],
            },
        )

    @callback
    def report(
        self,
        type_: str,
        key: str,
        state: str,
        *,
        subject: dict[str, Any] | None = None,
        placeholders: dict[str, Any] | None = None,
        severity: str | None = None,
        initial: bool = False,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Eine Meldung senden (active) oder schließen (resolved)."""
        if not self.type_enabled(type_):
            return
        if state not in ("active", "resolved"):
            _LOGGER.debug("Ungültiger Zustand für Meldungsart %s", type_)
            return
        level = severity or self._catalog[type_]["severity"]
        if level not in SEVERITIES:
            level = self._catalog[type_]["severity"]
        self.hass.bus.async_fire(
            EVENT_REPORT,
            {
                "schema": SCHEMA,
                "source": self.source,
                "entry_id": self.entry.entry_id,
                "type": type_,
                "key": str(key),
                "state": state,
                "severity": level,
                "subject": subject or {},
                "placeholders": placeholders or {},
                "initial": initial,
                "data": data or {},
            },
        )

    @callback
    def async_sync(self) -> None:
        """Ausgangszustand melden und das NC abgleichen lassen."""
        active = self._provider() if self._provider else {}
        for type_, item in self._catalog.items():
            if not item.get("resolvable", True):
                continue
            items = active.get(type_, []) if self.type_enabled(type_) else []
            for entry in items:
                self.report(
                    type_,
                    entry["key"],
                    "active",
                    subject=entry.get("subject"),
                    placeholders=entry.get("placeholders"),
                    initial=True,
                )
            self.hass.bus.async_fire(
                EVENT_SYNC,
                {
                    "schema": SCHEMA,
                    "source": self.source,
                    "entry_id": self.entry.entry_id,
                    "type": type_,
                    "active_keys": [str(e["key"]) for e in items],
                },
            )
