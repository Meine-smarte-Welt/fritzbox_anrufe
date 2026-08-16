# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): a5823e4d0838b8783484179dbdbe17290bd484017ccc38001a29e57463d999cf
"""Authenticated proxy view for FRITZ!Box answering-machine (TAM) audio.

EXPERIMENTAL - see :mod:`.tam`. The FRITZ!Box audio recording itself
requires a FRITZ!Box-session-authenticated request (not a Home Assistant
one), so it cannot simply be linked to directly from a dashboard. This
view fetches the audio bytes server-side, using the FRITZ!Box session the
integration already opened, and streams them to the browser - the browser
only ever needs to be authenticated with Home Assistant
(``requires_auth = True``).
"""

from __future__ import annotations

import logging

from aiohttp import web
from requests.exceptions import RequestException

from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import CALL_MEDIA_URL_BASE, DOMAIN, TAM_MEDIA_URL_BASE, TAM_MEDIA_URL_BASES

_LOGGER = logging.getLogger(__name__)


async def _serve_tam_message(hass, tam_coordinator, message_id: str) -> web.Response:
    """Shared fetch/response logic for one TAM coordinator's message audio.

    Seit v1.0.6b1 aus FritzBoxTamMediaView.get() herausgezogen, damit
    FritzBoxTam2MediaView (zweiter Anrufbeantworter) dieselbe, bereits an
    echter Hardware bestätigte Logik nutzen kann, ohne
    FritzBoxTamMediaView selbst (bzw. dessen URL-Schema) anzufassen.
    ``tam_coordinator`` kann ``None`` sein (z. B. wenn der zweite
    Anrufbeantworter nicht aktiviert ist) - liefert dann schlicht 404.
    """
    if tam_coordinator is None:
        return web.Response(status=404)

    message = tam_coordinator.get_message(message_id)
    if message is None or not message.Path:
        return web.Response(status=404)

    try:
        audio_bytes, content_type = await hass.async_add_executor_job(
            tam_coordinator.fetch_audio, message
        )
    except RequestException as ex:
        _LOGGER.warning(
            "Fehler beim Abrufen der Anrufbeantworter-Nachricht %s: %s",
            message_id,
            ex,
        )
        return web.Response(status=502)

    # Seit v1.0.5b4, EXPERIMENTELL (siehe tam.py) - no-op, falls
    # auto_mark_read (Options-Flow) nicht aktiviert ist; schlägt niemals
    # fehl (siehe maybe_auto_mark_read-Docstring), daher kein try/except
    # hier nötig.
    await hass.async_add_executor_job(tam_coordinator.maybe_auto_mark_read, message)

    return web.Response(body=audio_bytes, content_type=content_type)


class FritzBoxTamMediaView(HomeAssistantView):
    """Stream one answering-machine message's audio recording."""

    url = f"{TAM_MEDIA_URL_BASE}/{{entry_id}}/{{message_id}}"
    name = "api:fritzbox_anrufe:tam_media"
    requires_auth = True

    async def get(
        self, request: web.Request, entry_id: str, message_id: str
    ) -> web.Response:
        """Return the audio bytes for one TAM message, if available."""
        hass = request.app[KEY_HASS]

        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            return web.Response(status=404)

        tam_coordinators = getattr(entry.runtime_data, "tam_coordinators", [])
        tam_coordinator = tam_coordinators[0] if tam_coordinators else None
        return await _serve_tam_message(hass, tam_coordinator, message_id)


class _FritzBoxTamSlotMediaView(HomeAssistantView):
    """Stream one message's audio recording from TAM slot 2-5 (seit v1.1.1).

    Generalisiert die vormals fest ausprogrammierte, nur für Slot 2
    existierende ``FritzBoxTam2MediaView`` auf bis zu 5 Slots
    (const.py:MAX_TAM_COUNT) - eine Instanz pro zusätzlichem Slot,
    registriert von :func:`register_additional_tam_views` unten. Bewusst
    weiterhin als eigene View mit eigenem, festem URL-Schema PRO SLOT
    (nicht ein einziger dynamischer ``{tam_slot}``-URL-Parameter), damit der
    bereits an echter Hardware bestätigte Wiedergabe-Pfad des ersten
    Anrufbeantworters (:class:`FritzBoxTamMediaView` oben) unangetastet
    bleibt.
    """

    requires_auth = True

    def __init__(self, slot_index: int, media_url_base: str) -> None:
        """``slot_index`` ist 0-basiert (1 = zweiter AB, ..., 4 = fünfter AB)."""
        self._slot_index = slot_index
        self.url = f"{media_url_base}/{{entry_id}}/{{message_id}}"
        self.name = f"api:fritzbox_anrufe:tam{slot_index + 1}_media"

    async def get(
        self, request: web.Request, entry_id: str, message_id: str
    ) -> web.Response:
        """Return the audio bytes for one message of this TAM slot, if any."""
        hass = request.app[KEY_HASS]

        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            return web.Response(status=404)

        tam_coordinators = getattr(entry.runtime_data, "tam_coordinators", [])
        tam_coordinator = (
            tam_coordinators[self._slot_index]
            if len(tam_coordinators) > self._slot_index
            else None
        )
        return await _serve_tam_message(hass, tam_coordinator, message_id)


def register_additional_tam_views(hass: HomeAssistant) -> None:
    """Register the (always-present, 404-until-configured) views for slot 2-5.

    Aufgerufen von ``__init__.py:_async_register_tam_view`` - immer alle 4
    zusätzlichen Slots registriert, unabhängig von der tatsächlich
    konfigurierten Anzahl (``tam_count``), damit eine spätere Erhöhung per
    Options-Flow ohne HA-Neustart sofort funktioniert.
    """
    for slot_index, media_url_base in enumerate(TAM_MEDIA_URL_BASES[1:], start=1):
        hass.http.register_view(_FritzBoxTamSlotMediaView(slot_index, media_url_base))


class FritzBoxCallMediaView(HomeAssistantView):
    """Stream the recording linked from a call-list entry (since v1.0.3).

    EXPERIMENTAL, same caveat as FritzBoxTamMediaView / see tam.py's module
    docstring: reuses ``FritzTamCoordinator.fetch_audio()`` completely
    unchanged - it only ever reads a ``.Path`` attribute, and
    fritzconnection's call-list ``Call`` objects carry a ``Path`` in the
    same "/download.lua?path=..." format as an answering-machine
    ``TamMessage`` (both ultimately point at the same kind of recording
    file on the box). This has NOT been separately confirmed against real
    hardware - please open a GitHub issue with the resulting HTTP status
    (visible in the Home Assistant log) if a link here 404s/502s while the
    "echte" Anrufbeantworter-Sensor-Wiedergabe still works.
    """

    url = f"{CALL_MEDIA_URL_BASE}/{{entry_id}}/{{call_type}}/{{call_id}}"
    name = "api:fritzbox_anrufe:call_media"
    requires_auth = True

    async def get(
        self, request: web.Request, entry_id: str, call_type: str, call_id: str
    ) -> web.Response:
        """Return the audio bytes for one call-list entry's recording, if any."""
        hass = request.app[KEY_HASS]

        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            return web.Response(status=404)

        call_log_coordinator = getattr(entry.runtime_data, "call_log_coordinator", None)
        tam_coordinators = getattr(entry.runtime_data, "tam_coordinators", [])
        tam_coordinator = tam_coordinators[0] if tam_coordinators else None
        if call_log_coordinator is None or tam_coordinator is None:
            return web.Response(status=404)

        call = call_log_coordinator.get_call(call_type, call_id)
        if call is None or not call.Path:
            return web.Response(status=404)

        try:
            audio_bytes, content_type = await hass.async_add_executor_job(
                tam_coordinator.fetch_audio, call
            )
        except RequestException as ex:
            _LOGGER.warning(
                "Fehler beim Abrufen der Anruf-Aufnahme %s/%s: %s",
                call_type,
                call_id,
                ex,
            )
            return web.Response(status=502)

        # Seit v1.0.5b4, EXPERIMENTELL (siehe tam.py) - nur möglich, wenn
        # dieser Anruf beim letzten Abgleich eindeutig einer echten
        # TamMessage zugeordnet werden konnte (call_log.py:
        # _find_matching_tam_message); `call` selbst ist ein Call-Objekt
        # ohne eigenen TAM-Index. Ohne Zuordnung bleibt die "Neu"-Markierung
        # unangetastet - kein Fehler, einfach nichts zu tun.
        tam_message = getattr(call, "tam_message", None)
        if tam_message is not None:
            await hass.async_add_executor_job(
                tam_coordinator.maybe_auto_mark_read, tam_message
            )

        return web.Response(body=audio_bytes, content_type=content_type)
