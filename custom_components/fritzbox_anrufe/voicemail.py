# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 564dc067bc31355e96e5521884969f228cf27bba73cae7bfb1b6d8ac9633a7f0
"""Coordinator + audio access for the FRITZ!Box answering machine (TAM).

EXPERIMENTAL - see the module docstring in :mod:`.tam` for details on what
could and could not be verified against real hardware while building this.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import mimetypes

from fritzconnection.core.exceptions import FritzConnectionException, FritzSecurityError
from fritzconnection.core.fritzhttp import FritzHttp
from requests.exceptions import ConnectionError as RequestsConnectionError, RequestException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_AUTO_MARK_READ,
    CONF_SPAM_NAME_PREFIXES,
    CONF_SPAM_NUMBERS,
    DEFAULT_AUTO_MARK_READ,
    EVENT_NEW_VOICEMAIL_MESSAGE,
    TAM_MEDIA_URL_BASE,
)
from .spam import is_spam_name, is_spam_number, parse_name_markers, parse_spam_patterns
from .tam import FritzTam, TamMessage

_LOGGER = logging.getLogger(__name__)

TAM_UPDATE_INTERVAL = timedelta(minutes=5)
_DEFAULT_CONTENT_TYPE = "audio/wav"


class FritzTamCoordinator(DataUpdateCoordinator[list[TamMessage]]):
    """Coordinator that periodically fetches the FRITZ!Box answering-machine list.

    Also doubles as the (blocking, executor-job-only) audio fetcher for the
    HTTP proxy view in ``http.py``, since it already holds the
    authenticated :class:`~.tam.FritzTam`/``FritzConnection`` reference.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        fritz_tam: FritzTam,
        media_url_base: str = TAM_MEDIA_URL_BASE,
        tam_label: str = "1",
    ) -> None:
        """Initialize the TAM coordinator.

        ``media_url_base``/``tam_label`` (seit v1.0.6b1) unterscheiden eine
        Instanz für den zweiten Anrufbeantworter (siehe __init__.py) von der
        primären, bereits an echter Hardware bestätigten Instanz - Default-
        Werte entsprechen exakt dem bisherigen Verhalten für den ersten
        Anrufbeantworter, damit bestehende Setups unverändert bleiben.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"fritzbox_anrufe tam {tam_label}",
            update_interval=TAM_UPDATE_INTERVAL,
        )
        self.config_entry = config_entry
        self._fritz_tam = fritz_tam
        self._media_url_base = media_url_base
        self._tam_label = tam_label
        # Only used as a *fallback* sid source for recording downloads
        # (see fetch_audio/_sid_candidates below) - also conveniently
        # provides router_url, the FRITZ!Box's normal web-UI origin
        # (port 80/443), which is needed for every download attempt
        # regardless of which sid ends up working.
        self._http = FritzHttp(fritz_tam.fc)

    async def _async_update_data(self) -> list[TamMessage]:
        """Fetch the current answering-machine messages (executor job).

        ``self.data`` still holds the *previous* successful result while
        this runs (the base class only overwrites it once this coroutine
        returns) - captured up front so newly-arrived messages can be
        detected by comparing against it, see :meth:`_fire_new_message_events`.
        """
        previous_messages = self.data
        try:
            messages = await self.hass.async_add_executor_job(self._fritz_tam.get_messages)
        except FritzSecurityError as ex:
            raise UpdateFailed(
                "Dem FRITZ!Box-Konto fehlt die Berechtigung 'Sprachnachrichten,"
                " Faxnachrichten, FRITZ!App Fon und Anrufliste' für den Zugriff"
                f" auf den Anrufbeantworter: {ex}"
            ) from ex
        except (FritzConnectionException, RequestsConnectionError) as ex:
            raise UpdateFailed(
                f"Fehler beim Abrufen der Anrufbeantworter-Nachrichten: {ex}"
            ) from ex
        # Seit v1.0.6b1: siehe spam.py/call_log.py - für Nachrichten gibt es
        # kein REJECTED_CALL_TYPE-Äquivalent, hier zählt der Abgleich gegen die
        # vom Nutzer gepflegte Spam-Nummernliste sowie (seit v1.2.3) gegen die
        # Namens-Marker (z. B. "SPAM:" von externen Blockern wie PhoneBlock).
        spam_patterns = parse_spam_patterns(self.config_entry.options.get(CONF_SPAM_NUMBERS))
        spam_name_markers = parse_name_markers(
            self.config_entry.options.get(CONF_SPAM_NAME_PREFIXES)
        )
        for message in messages:
            message.spam = is_spam_number(message.Number, spam_patterns) or is_spam_name(
                getattr(message, "Name", None), spam_name_markers
            )
        if previous_messages is not None:
            self._fire_new_message_events(previous_messages, messages)
        return messages

    def _fire_new_message_events(
        self, previous_messages: list[TamMessage], current_messages: list[TamMessage]
    ) -> None:
        """Fire EVENT_NEW_VOICEMAIL_MESSAGE for every genuinely new message.

        "New" here means: its ``Index`` was not present in the *previous*
        successful poll - deliberately independent of the FRITZ!Box's own
        "New"/unread flag (:attr:`TamMessage.new`), which could in theory
        already be cleared again by the time this poll runs (e.g. someone
        listened to it directly on the FRITZ!Box in between, or
        ``auto_mark_read`` cleared it after a playback through this
        integration). Comparing message IDs against the previous poll is
        what actually answers "did a message arrive since we last looked",
        which is what this event promises - not "is currently unread".

        Only called when ``previous_messages`` is not ``None`` (see
        :meth:`_async_update_data`), i.e. never on the very first poll
        after a (re)start - otherwise every message already sitting on the
        FRITZ!Box, however old, would fire an event on every Home
        Assistant restart.
        """
        previous_ids = {
            message.Index for message in previous_messages if message.Index is not None
        }
        for message in current_messages:
            if message.Index is not None and message.Index not in previous_ids:
                self._fire_new_message_event(message)

    def _fire_new_message_event(self, message: TamMessage) -> None:
        """Fire one EVENT_NEW_VOICEMAIL_MESSAGE for a newly-arrived message."""
        media_url = (
            f"{self._media_url_base}/{self.config_entry.entry_id}/{message.Index}"
            if message.Path
            else None
        )
        self.hass.bus.async_fire(
            EVENT_NEW_VOICEMAIL_MESSAGE,
            {
                "entry_id": self.config_entry.entry_id,
                "message_id": message.Index,
                "number": message.Number or None,
                "name": message.Name or None,
                "date": message.date.isoformat() if isinstance(message.date, datetime) else None,
                "duration": str(message.duration)
                if isinstance(message.duration, timedelta)
                else None,
                "media_url": media_url,
                # Seit v1.0.6b1 - siehe __init__.py (tam_label unterscheidet
                # ersten/zweiten Anrufbeantworter) und spam.py (spam-Flag,
                # additive Felder, brechen bestehende Automatisierungen nicht).
                "tam": self._tam_label,
                "spam": getattr(message, "spam", False),
            },
        )

    def get_message(self, message_id: str) -> TamMessage | None:
        """Look up one currently-known message by its raw ``Index`` string."""
        for message in self.data or []:
            if message.Index == message_id:
                return message
        return None

    async def delete_message(self, message_id: str) -> None:
        """Delete one message and refresh so the UI reflects it promptly.

        Called from the ``fritzbox_anrufe.delete_voicemail_message`` entity
        service (see ``sensor.py``). Runs the actual TR-064 call in the
        executor (see ``_fritz_tam.delete_message``, blocking); any
        FRITZ!Box-side error propagates to the service caller as-is (Home
        Assistant surfaces it as a failed service call) rather than being
        swallowed, since - unlike playback - a failed delete needs to be
        visible: the card's own optimistic UI (see the card's module
        docstring) reverts the row back into view if this raises.
        """
        await self.hass.async_add_executor_job(self._fritz_tam.delete_message, message_id)
        await self.async_request_refresh()

    async def async_set_enabled(self, enabled: bool) -> None:
        """Turn this answering machine on/off. BLOCKING call runs in executor.

        EXPERIMENTAL, see :mod:`.tam` (``FritzTam.set_enable``) and
        :mod:`.switch` for the caller-facing entity. Deliberately does NOT
        call :meth:`async_request_refresh` afterwards, unlike
        :meth:`delete_message` above - there is no confirmed way to read
        this state back from the box (no ``GetInfo``, see project history),
        so a coordinator refresh would not reflect it anyway. ``switch.py``
        tracks its own optimistic on/off state instead. Any FRITZ!Box-side
        error propagates to the caller as-is, exactly like ``delete_message``,
        so the switch's own optimistic-update-with-revert logic can react to it.
        """
        await self.hass.async_add_executor_job(self._fritz_tam.set_enable, enabled)

    def maybe_auto_mark_read(self, message: TamMessage) -> None:
        """BLOCKING - run in executor, right after a successful ``fetch_audio``.

        If the ``auto_mark_read`` option (Options-Flow, default OFF - see
        const.py) is enabled, clears the message's "New" flag on the
        FRITZ!Box itself once it has actually been played back through this
        integration - matching what happens when a message is played back on
        a real FRITZ!Box device/app. Deliberately swallows every exception
        (logged as a WARNING only): a failure here must never turn an
        otherwise-successful playback into an error response, and this is
        still EXPERIMENTELL/unconfirmed territory (see tam.py). No-op if the
        message is already read, or the option is off - avoids an
        unnecessary TR-064 round-trip and a pointless coordinator refresh on
        every single playback.
        """
        if not self.config_entry.options.get(CONF_AUTO_MARK_READ, DEFAULT_AUTO_MARK_READ):
            return
        if not message.new:
            return
        try:
            self._fritz_tam.mark_message(message.Index, read=True)
        except Exception as ex:  # noqa: BLE001 - must never break playback, see docstring
            _LOGGER.warning(
                "Anrufbeantworter: Nachricht %s konnte nach der Wiedergabe nicht"
                " automatisch als gelesen markiert werden (%s: %s)",
                message.Index,
                type(ex).__name__,
                ex,
            )
            return
        # Cross-thread hand-off (this runs in an executor job, not the event
        # loop) - same pattern as sensor.py's post-call refresh
        # (call_soon_threadsafe), but hass.add_job() already does that
        # thread-safety internally, so no extra callback indirection is
        # needed here.
        self.hass.add_job(self.async_request_refresh)

    def fetch_audio(self, message: TamMessage) -> tuple[bytes, str]:
        """Download one message's audio recording. BLOCKING - run in executor.

        Tries multiple (sid, origin) candidates in order until one returns
        HTTP 200 - see :meth:`_sid_candidates` and the module docstring in
        ``tam.py`` for why more than one candidate exists. The browser only
        ever needs a valid Home Assistant session to play a recording,
        never FRITZ!Box credentials directly - this whole exchange happens
        server-side.

        Real-world bug fixed here (reported via a user of Thorsten's,
        HTTP 500 instead of the intended 502): determining ``origin``
        (:attr:`FritzHttp.router_url`, which can trigger its own TR-064 call
        if the configured host uses ``https://``) and iterating the
        fallback classic-web-UI login in :meth:`_sid_candidates`
        (``FritzHttp._get_sid`` - not confirmed against every FRITZ!OS/
        network configuration, e.g. HTTPS-only web-UI access) were not
        wrapped in any exception handling at all. Any failure there -
        anything from a TR-064 permission error to an XML parse error on an
        unexpected login-page response - propagated all the way out of the
        executor job as an *unhandled* exception, which ``http.py``'s
        ``except RequestException`` could never catch, so it surfaced to
        the browser as a raw, undiagnosable HTTP 500 instead of the
        intended 502 (with a descriptive WARNING log line). Both spots are
        now wrapped broadly (not just the two specific exception types used
        elsewhere in this method) precisely because this fallback path is
        still unconfirmed territory - see the module docstring in
        ``tam.py`` - so an unanticipated exception type is expected to
        surface here sooner or later.
        """
        if not message.Path:
            raise RequestException("message has no audio path")

        try:
            origin = self._http.router_url
        except Exception as ex:  # noqa: BLE001 - see docstring above
            raise RequestException(
                "Anrufbeantworter-Download: konnte FRITZ!Box-Webadresse nicht"
                f" ermitteln ({type(ex).__name__}: {ex})"
            ) from ex

        last_status: int | None = None
        tried = 0
        sid_candidates = self._sid_candidates()

        while True:
            try:
                sid = next(sid_candidates)
            except StopIteration:
                break
            except Exception as ex:  # noqa: BLE001 - see docstring above
                _LOGGER.warning(
                    "Anrufbeantworter-Download: Sitzungs-ID konnte nicht"
                    " ermittelt werden (%s: %s)",
                    type(ex).__name__,
                    ex,
                )
                continue

            url = self._fritz_tam.build_download_url(message, sid, origin)
            if not url:
                raise RequestException("message has no audio path")
            tried += 1
            try:
                response = self._fritz_tam.fc.session.get(url)
            except (FritzConnectionException, RequestsConnectionError) as ex:
                raise RequestException(
                    f"Anrufbeantworter-Download fehlgeschlagen: {ex}"
                ) from ex
            if response.status_code == 200:
                content_type = (
                    response.headers.get("Content-Type")
                    or mimetypes.guess_type(url)[0]
                    or _DEFAULT_CONTENT_TYPE
                )
                return response.content, content_type
            last_status = response.status_code

        if tried == 0:
            raise RequestException(
                "konnte keine sid für den Anrufbeantworter-Download ermitteln"
            )
        raise RequestException(
            f"Anrufbeantworter-Download fehlgeschlagen (HTTP {last_status})"
            f" nach {tried} Versuch(en) mit unterschiedlichen Sitzungen"
        )

    def _sid_candidates(self):
        """Yield sid candidates to try for a recording download, in order.

        First the sid embedded in a fresh ``GetMessageList`` response (no
        extra login needed), then - only if that candidate exists but the
        caller hasn't already succeeded with it - a full classic-web-UI
        login via ``FritzHttp`` (up to two sids: cached-or-fresh, then
        regenerated once). See the module docstring in ``tam.py`` for why
        both mechanisms are tried rather than picking one.
        """
        try:
            embedded_sid = self._fritz_tam.get_message_list_sid()
        except FritzConnectionException:
            embedded_sid = None
        if embedded_sid:
            yield embedded_sid
        yield from self._http._get_sid()  # noqa: SLF001 - see class docstring
