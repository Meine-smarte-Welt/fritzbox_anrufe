# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 7cdbb0e5d3c5d1c8fa3cc5cad1cba6fa1f666b6c7eb1e034fbed40861b0e73c2
"""Switch to turn the FRITZ!Box answering machine (TAM) on/off.

EXPERIMENTAL, seit v1.1.0 - siehe den Modul-Docstring in ``tam.py`` für die
allgemeinen Einschränkungen dieser Integration beim TR-064-Zugriff, und
konkret den Kommentar bei ``ACTION_SET_ENABLE`` dort: das hier verwendete
``NewEnable``-Argument ist NICHT unabhängig gegen AVMs offizielle
Dokumentation oder eine Community-Referenz bestätigt, trotz mehrerer
Versuche (siehe Projekthistorie). Es wurde ausschließlich durch die starke
Namenskonvention innerhalb desselben ``X_AVM-DE_TAM1``-Diensts hergeleitet.

Wegen dieser Unsicherheit - und weil diese Integration bewusst niemals die
unbestätigte ``GetInfo``-Aktion aufruft (siehe tam.py/README - zwei frühere
Versuche, sie zu nutzen, wurden aus demselben Grund verworfen) - kann dieser
Schalter den tatsächlichen Ein/Aus-Zustand des Anrufbeantworters NICHT
zuverlässig von der FRITZ!Box zurücklesen. Er ist deshalb so aufgebaut, wie
Home Assistant ein rein schreibendes Gerät modelliert erwartet:

* ``assumed_state = True`` - teilt der Oberfläche mit, dass der angezeigte
  Zustand KEINE bestätigte Rücklesung ist, sodass zwei getrennte "An"/
  "Aus"-Schaltflächen statt eines einzelnen (potenziell lügenden) Toggles
  angezeigt werden.
* :class:`~homeassistant.helpers.restore_state.RestoreEntity` - stellt den
  zuletzt von Home Assistant selbst gesetzten Zustand nach einem Neustart
  wieder her, ohne einen zusätzlichen (unbestätigten) Abruf von der Box.
* Optimistisches Setzen mit Rückgängigmachen bei Fehler - dasselbe Muster,
  das bereits beim Löschen von Nachrichten verwendet wird (siehe sensor.py/
  den Modul-Docstring der Karte): der Schalter reagiert sofort beim
  Antippen und springt nur zurück, wenn der TR-064-Aufruf selbst fehlschlägt.
"""

from __future__ import annotations

import logging
from typing import Any, override

from fritzconnection.core.exceptions import FritzConnectionException
from requests.exceptions import ConnectionError as RequestsConnectionError

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import FritzBoxCallMonitorConfigEntry, FritzBoxRuntimeData
from .base import build_device_info
from .const import (
    CALL_TYPES_VOICEMAIL,
    CONF_PHONEBOOK,
    SERIAL_NUMBER,
    SWITCH_TRANSLATION_KEYS_VOICEMAIL,
)
from .voicemail import FritzTamCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: FritzBoxCallMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the fritzbox_anrufe answering-machine on/off switch(es).

    Seit v1.1.1: ein Schalter pro konfiguriertem Anrufbeantworter-Slot (bis
    zu 5, siehe const.py:MAX_TAM_COUNT/CALL_TYPES_VOICEMAIL) - vormals fest
    ein oder zwei Schalter. Mirrors exakt dieselbe, per Schleife über
    runtime_data.tam_coordinators aufgebaute Struktur wie sensor.py für die
    Anrufbeantworter-Sensoren - alle Schalter teilen sich dasselbe Home
    Assistant Gerät wie jede andere Entity dieses Accounts.
    """
    runtime_data: FritzBoxRuntimeData = config_entry.runtime_data
    fritzbox_phonebook = runtime_data.phonebook
    phonebook_id: int = config_entry.data[CONF_PHONEBOOK]
    serial_number: str = config_entry.data[SERIAL_NUMBER]

    unique_id = f"{serial_number}-{phonebook_id}"
    device_info = build_device_info(fritzbox_phonebook, unique_id)

    entities: list[SwitchEntity] = []

    for slot, coordinator in enumerate(runtime_data.tam_coordinators):
        call_type = CALL_TYPES_VOICEMAIL[slot]
        entities.append(
            FritzBoxTamSwitch(
                coordinator=coordinator,
                unique_id=f"{unique_id}-{call_type}-switch",
                phonebook_name=config_entry.title,
                device_info=device_info,
                translation_key=SWITCH_TRANSLATION_KEYS_VOICEMAIL[slot],
            )
        )

    async_add_entities(entities)


class FritzBoxTamSwitch(RestoreEntity, SwitchEntity):
    """On/off switch for one FRITZ!Box answering machine (TAM) - EXPERIMENTAL.

    See the module docstring for why this is an ``assumed_state`` switch
    with no state readback from the FRITZ!Box.
    """

    _attr_has_entity_name = True
    _attr_assumed_state = True
    _attr_icon = "mdi:answering-machine"

    def __init__(
        self,
        coordinator: FritzTamCoordinator,
        unique_id: str,
        phonebook_name: str,
        device_info: DeviceInfo,
        translation_key: str,
    ) -> None:
        """Initialize the answering-machine switch."""
        self._coordinator = coordinator
        self._attr_translation_key = translation_key
        self._attr_translation_placeholders = {"phonebook_name": phonebook_name}
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info
        # Optimistic-only state (see module/class docstring) - stays None
        # until either a previous Home Assistant state is restored on
        # startup, or the user flips the switch for the first time; the
        # entity then reports as "unknown" rather than guessing "on"/"off".
        self._attr_is_on: bool | None = None

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the last known (optimistic) state after a restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in ("on", "off"):
            self._attr_is_on = last_state.state == "on"

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the answering machine on."""
        await self._async_set_enabled(True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the answering machine off."""
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        """Optimistically flip state, call TR-064, revert on failure.

        Mirrors the optimistic-update-with-revert pattern already used
        elsewhere in this integration for message deletion (see the module
        docstring) - the UI reacts immediately, and only snaps back if the
        FRITZ!Box call itself fails, so a real failure stays visible to the
        user instead of silently reporting a state the box never reached.
        """
        previous_state = self._attr_is_on
        self._attr_is_on = enabled
        self.async_write_ha_state()
        try:
            await self._coordinator.async_set_enabled(enabled)
        except (FritzConnectionException, RequestsConnectionError) as ex:
            self._attr_is_on = previous_state
            self.async_write_ha_state()
            action = "eingeschaltet" if enabled else "ausgeschaltet"
            raise HomeAssistantError(
                f"Anrufbeantworter konnte nicht {action} werden: {ex}"
            ) from ex
