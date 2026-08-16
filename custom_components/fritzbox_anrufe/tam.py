# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): b569e1109b1dbc84a552dd36835fb912aa3ae5b47a29a516c523783e799e09c6
"""Wrapper around the FRITZ!Box answering machine (TAM) TR-064 API.

EXPERIMENTAL - message list confirmed working on real hardware; audio
download is a third attempt, see :func:`FritzTam.get_download_url` below
-------------------------------------------------------------------------
This module was written by researching AVM's TR-064 service description
for the ``X_AVM-DE_TAM1`` service and the ``GetMessageList`` action, and by
mirroring the *exact same* download pattern that :mod:`fritzconnection`
itself already uses for the (confirmed working, real-hardware-tested) call
list in :mod:`fritzconnection.lib.fritzcall`:

1. Call a SOAP action that returns a session-authenticated URL to an XML
   document (``GetCallList`` -> ``NewCallListURL`` for calls; here
   ``GetMessageList`` -> presumably ``NewURL`` for TAM messages).
2. Download that URL using the already-authenticated
   :class:`~fritzconnection.core.fritzconnection.FritzConnection` session
   (``fc.session``, a :class:`requests.Session` with FRITZ!Box digest auth
   already attached) via :func:`fritzconnection.core.utils.get_xml_root`.
3. Parse the resulting XML into plain Python objects using
   :mod:`fritzconnection`'s own generic node processor
   (:mod:`fritzconnection.core.processor`), exactly like ``CallCollection``
   does for calls.

This part (message list) has been confirmed working against real hardware.
AVM's own documentation and third-party references are inconsistent about
the exact name of ``GetMessageList``'s output parameter - some call it
``NewURL``, others ``NewMessageListURL``. :meth:`FritzTam._message_list_url`
therefore checks both names defensively.

DOWNLOADING the actual recording is a separate problem and has gone through
several revisions:

1. GET ``download.lua?path=...`` with a classic-web-UI sid as a query
   parameter - 404 on real hardware.
2. POST to the same ``download.lua`` with the sid as form body data
   instead - identical 404 on real hardware. Since switching GET/POST and
   the sid mechanism didn't change the *symptom* at all, the endpoint
   itself was suspect, not just the auth details.
3. GET ``/cgi-bin/luacgi_notimeout?sid=...&script=/lua/photo.lua&
   myabfile=...`` (the recording's raw path as ``myabfile`` - this is also
   how FRITZ!Box serves e.g. files from USB storage; ``photo.lua`` is a
   generic binary-file-serving script, not literally photo-specific),
   still resolved against the *TR-064* origin (the host:port that
   ``GetMessageList`` itself replied from, typically port 49000) - not
   independently confirmed working before shipping, so status unclear.
4. **Current approach**: same ``luacgi_notimeout``/``photo.lua`` endpoint
   as (3), found independently in three places - FHEM's mature
   ``72_FBTAM.pm`` module, a real-world writeup (FRITZ!Box 7530, FRITZ!OS
   7.57, https://kynan.github.io/blog/2023/12/28/save-all-voicebox-messages-from-your-fritzbox),
   and a working bash script posted in an iobroker forum thread
   (https://forum.iobroker.net/topic/49269) - but resolved against the
   FRITZ!Box's normal *web-UI* origin (port 80/443, i.e. the same
   host:port :class:`~fritzconnection.core.fritzhttp.FritzHttp` itself
   uses for the classic login) rather than the TR-064 port. TR-064 (port
   49000) serves SOAP/XML only; ``/cgi-bin/...`` is a classic web-UI path
   that most likely never existed on that port to begin with, which would
   explain why attempt (3) could fail even with the right endpoint and a
   right-looking sid.

   The three sources above also disagree on where the sid itself should
   come from: FBTAM and the blog extract it from ``GetMessageList``'s own
   response URL, while the iobroker script performs a completely separate
   classic-web-UI login (the same challenge-response flow ``FritzHttp``
   already implements). Rather than gamble on a fourth single theory,
   :meth:`FritzTamCoordinator.fetch_audio` in ``voicemail.py`` now tries
   both, in order (the embedded sid first since it costs no extra login,
   then a fresh ``FritzHttp`` login as fallback) against the corrected
   web-UI origin, and only gives up once every combination has failed.

This is still not confirmed against the user's actual hardware - please
open a GitHub issue (ideally with the resulting HTTP status code for each
attempt, visible in the Home Assistant log) if it still fails.
"""

from __future__ import annotations

import datetime
import logging
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

from fritzconnection.core.fritzconnection import FritzConnection
from fritzconnection.core.processor import (
    InstanceAttributeFactory,
    Storage,
    process_node,
    processor,
)
from fritzconnection.core.utils import get_xml_root

_LOGGER = logging.getLogger(__name__)

SERVICE = "X_AVM-DE_TAM1"
ACTION_GET_MESSAGE_LIST = "GetMessageList"
# DeleteMessage: same X_AVM-DE_TAM1 service as GetMessageList above, per
# AVM's own TR-064 service description (fritz.support/resources/
# TR-064_TAM.pdf) - takes the TAM index plus the message's own Index and
# deletes it permanently (no undo/trash on the FRITZ!Box itself).
# Independently corroborated by multiple real-hardware reports using the
# exact same arguments (forum.iobroker.net/topic/14288, FRITZ!Box 7530/6590,
# FRITZ!OS 7.20) - but NOT yet confirmed against this integration's own
# users' hardware, same "experimental" status as the rest of this module.
ACTION_DELETE_MESSAGE = "DeleteMessage"
# MarkMessage: same X_AVM-DE_TAM1 service and AVM spec as DeleteMessage
# above - arguments NewIndex/NewMessageIndex plus NewMarkedAsRead ("1"/"0").
# Mirrors exactly the "New" field TamMessage.new already reads. No separate
# independent real-hardware report was found for this specific action (the
# ioBroker thread above only covers DeleteMessage), but it comes from the
# identical, otherwise-confirmed service description - same "experimental,
# not yet confirmed against this integration's own users' hardware" status.
ACTION_MARK_MESSAGE = "MarkMessage"
# SetEnable (seit v1.1.0): NICHT unabhängig über AVM's offizielle
# TR-064-Spezifikation oder eine Community-Referenz bestätigt - jeder
# Versuch, dies zu verifizieren (AVM-PDF, FHEM's 72_FRITZBOX.pm,
# ip-phone-forum.de, forum.iobroker.net), scheiterte an
# PROVENANCE_REQUIRED/ROBOTS_DISALLOWED-Fehlern in dieser Sandbox - selbe
# Situation wie bereits bei GetInfo (siehe Projekthistorie zu v1.0.5b0 und
# v1.0.6b1, deshalb wird GetInfo hier weiterhin bewusst NICHT verwendet).
# Stattdessen rein durch die starke, innerhalb desselben X_AVM-DE_TAM1-
# Diensts wiederholt bestätigte Namenskonvention hergeleitet: jede bereits
# bestätigte Aktion dieses Diensts (GetMessageList/DeleteMessage/
# MarkMessage) verwendet "NewIndex" für den TAM-Index und genau EIN
# "New<Konzept>"-Argument für die eigentliche Nutzlast - "SetEnable" mit
# "NewEnable" ("1"/"0", exakt dieselbe Konvention wie NewMarkedAsRead) folgt
# diesem Muster exakt. EXPERIMENTELL, noch nicht an echter Hardware von
# Nutzern dieser Integration bestätigt - siehe switch.py, das diese
# Unsicherheit bewusst nie versucht durch eine Zustands-Rücklesung
# (GetInfo) aufzulösen, sondern stattdessen als assumed_state-Schalter ohne
# Rücklesung modelliert ist.
ACTION_SET_ENABLE = "SetEnable"

# Some FRITZ!OS versions expose more than one answering machine ("TAM
# index" 0, 1, ...). We only support the first/default one for now.
DEFAULT_TAM_INDEX = "0"

# Seit v1.0.6b1: optionaler zweiter Anrufbeantworter (CONF_SECOND_TAM in
# const.py). Reuses the already-hardware-confirmed GetMessageList action
# (see FritzTam below) with a different NewIndex - deliberately avoids
# calling GetInfo, whose exact output argument names could not be
# confirmed (see project history). If a FRITZ!Box has no second TAM at
# this index, GetMessageList simply returns no usable URL and the second
# sensor ends up unavailable - same graceful-failure behaviour as the
# primary TAM, never blocks integration setup.
SECOND_TAM_INDEX = "1"

# Seit v1.1.1: bis zu 5 Anrufbeantworter (const.py:MAX_TAM_COUNT). Slot-Index
# (0-basiert) = Listenindex hier - DEFAULT_TAM_INDEX/SECOND_TAM_INDEX oben
# entsprechen exakt TAM_INDICES[0]/TAM_INDICES[1] und bleiben als eigene,
# benannte Konstanten bestehen, da sie bereits an anderer Stelle referenziert
# werden. Indizes 2-4 (dritter bis fünfter Anrufbeantworter) sind - wie
# bereits Index 1 - eine reine Annahme (fortlaufende TAM-Indizierung),
# NICHT unabhängig bestätigt; siehe README/Projekthistorie zu v1.1.1.
TAM_INDICES = (DEFAULT_TAM_INDEX, SECOND_TAM_INDEX, "2", "3", "4")

# See the module docstring: the exact output parameter name of
# GetMessageList could not be confirmed against real hardware, so both
# known candidates are checked, in order of how likely they are correct
# (mirroring GetCallList's "NewCallListURL" naming convention).
_URL_RESULT_KEYS = ("NewURL", "NewMessageListURL")

# See the module docstring, download approach 3: the classic-web-UI
# endpoint actually used for TAM recordings on modern FRITZ!OS, and the
# sid regex used to pull the session id straight out of GetMessageList's
# own response URL (e.g. ".../tamcalllist.lua?sid=2400874c61e0ae6e&...").
_DOWNLOAD_PATH = "/cgi-bin/luacgi_notimeout"
_DOWNLOAD_SCRIPT = "/lua/photo.lua"
_SID_RE = re.compile(r"[?&]sid=([a-fA-F0-9]+)")


def _datetime_converter(date_string: str | None) -> datetime.datetime | str | None:
    if not date_string:
        return date_string
    return datetime.datetime.strptime(date_string, "%d.%m.%y %H:%M")


def _timedelta_converter(duration_string: str | None) -> datetime.timedelta | str | None:
    if not duration_string:
        return duration_string
    hours, minutes = (int(part) for part in duration_string.split(":", 1))
    return datetime.timedelta(hours=hours, minutes=minutes)


def _bool_converter(value: str | None) -> bool:
    return str(value) == "1"


class _AttributeConverter:
    """Data descriptor returning a converted attribute value (read-only)."""

    def __init__(self, attribute_name: str, converter=str) -> None:
        self.attribute_name = attribute_name
        self.converter = converter

    def __set__(self, obj, value):
        return NotImplemented

    def __get__(self, obj, objtype):
        attr = getattr(obj, self.attribute_name)
        try:
            return self.converter(attr)
        except (TypeError, ValueError):
            return attr


@processor
class TamMessage:
    """One answering-machine message.

    Instance attributes are named exactly like the XML nodes AVM is
    expected to use (mirroring how :class:`fritzconnection.lib.fritzcall.Call`
    is modeled): ``Index``, ``Number``, ``Date``, ``Duration``, ``Name``,
    ``Path`` (as delivered by the box, e.g.
    ``"/download.lua?path=/data/tam/rec/rec.0.009"`` - kept verbatim, NOT a
    directly-fetchable URL; see :meth:`FritzTam.get_download_url` for how
    the actual recording is downloaded), ``New`` ("1"/"0") and ``Count``.
    Lowercase convenience properties expose converted values: ``date``
    (datetime), ``duration`` (timedelta), ``new`` (bool).
    """

    date = _AttributeConverter("Date", _datetime_converter)
    duration = _AttributeConverter("Duration", _timedelta_converter)
    new = _AttributeConverter("New", _bool_converter)

    def __init__(self) -> None:
        self.Index: str | None = None
        self.Number: str | None = None
        self.Date: str | None = None
        self.Duration: str | None = None
        self.Name: str | None = None
        self.Path: str | None = None
        self.New: str | None = None
        self.Count: str | None = None


class TamMessageCollection(Storage):
    """Container for a sequence of :class:`TamMessage` instances."""

    Message = InstanceAttributeFactory(TamMessage)

    def __init__(self, root) -> None:
        self.messages: list[TamMessage] = []
        super().__init__(self.messages)
        process_node(self, root)

    def __iter__(self):
        return iter(self.messages)


class FritzTam:
    """Access the FRITZ!Box answering-machine message list via TR-064."""

    def __init__(self, fc: FritzConnection, index: str = DEFAULT_TAM_INDEX) -> None:
        """Initialize with an already-authenticated FritzConnection.

        Reuses the same connection/session the rest of the integration
        already opened (see ``__init__.py``), so no extra FRITZ!Box login
        is required for the answering machine.
        """
        self.fc = fc
        self.index = index

    def _message_list_url(self) -> str | None:
        """Call GetMessageList and return the message-list XML URL, if any."""
        result = self.fc.call_action(
            SERVICE, ACTION_GET_MESSAGE_LIST, arguments={"NewIndex": self.index}
        )
        for key in _URL_RESULT_KEYS:
            url = result.get(key)
            if url:
                return str(url)
        _LOGGER.warning(
            "Anrufbeantworter: GetMessageList lieferte keinen der erwarteten"
            " URL-Schlüssel (%s) zurück - Antwort war: %s. Bitte als GitHub"
            " Issue melden, damit die Anrufbeantworter-Anbindung an die"
            " tatsächliche FRITZ!OS-Version angepasst werden kann.",
            _URL_RESULT_KEYS,
            sorted(result.keys()),
        )
        return None

    def get_messages(self) -> list[TamMessage]:
        """Return all answering-machine messages, as delivered by the box."""
        url = self._message_list_url()
        if not url:
            return []
        root = get_xml_root(url, session=self.fc.session)
        return list(TamMessageCollection(root))

    def delete_message(self, index: str) -> None:
        """Permanently delete one answering-machine message.

        EXPERIMENTAL, not yet confirmed against this integration's own
        users' hardware - see module docstring above and
        :meth:`FritzTamCoordinator.delete_message` in ``voicemail.py`` for
        the caller-facing wrapper. There is no undo: the FRITZ!Box itself
        has no trash/recycle bin for answering-machine messages.
        """
        self.fc.call_action(
            SERVICE,
            ACTION_DELETE_MESSAGE,
            arguments={"NewIndex": self.index, "NewMessageIndex": index},
        )

    def mark_message(self, index: str, *, read: bool = True) -> None:
        """Mark one answering-machine message as read/unread via TR-064.

        EXPERIMENTAL, not yet confirmed against this integration's own
        users' hardware - see module docstring above and
        :meth:`FritzTamCoordinator.maybe_auto_mark_read` in ``voicemail.py``
        for the caller-facing wrapper. Mirrors directly the same ``New``
        field :attr:`TamMessage.new` reads: ``read=True`` clears the "Neu"
        flag, ``read=False`` sets it again.
        """
        self.fc.call_action(
            SERVICE,
            ACTION_MARK_MESSAGE,
            arguments={
                "NewIndex": self.index,
                "NewMessageIndex": index,
                "NewMarkedAsRead": "1" if read else "0",
            },
        )

    def set_enable(self, enabled: bool) -> None:
        """Turn this answering machine on/off via TR-064.

        EXPERIMENTAL, ``NewEnable`` inferred by naming-convention analogy
        only - see the ``ACTION_SET_ENABLE`` comment above for details, and
        :mod:`.switch` for the caller-facing entity, which deliberately
        never tries to read this state back from the box (no confirmed
        ``GetInfo`` - see the module docstring - so ``assumed_state`` is
        used instead).
        """
        self.fc.call_action(
            SERVICE,
            ACTION_SET_ENABLE,
            arguments={"NewIndex": self.index, "NewEnable": "1" if enabled else "0"},
        )

    def get_message_list_sid(self) -> str | None:
        """Issue a fresh GetMessageList call and return its embedded sid.

        One of two candidate sids tried for downloading a recording - see
        the module docstring. A fresh call is made (rather than reusing
        one from an earlier ``get_messages()``) so the sid is as current
        as possible; TAM-related sids are not expected to be long-lived.
        """
        list_url = self._message_list_url()
        if not list_url:
            return None
        sid_match = _SID_RE.search(list_url)
        if not sid_match:
            _LOGGER.warning(
                "Anrufbeantworter: konnte keine sid aus der GetMessageList-"
                "Antwort-URL (%s) extrahieren.",
                list_url,
            )
            return None
        return sid_match.group(1)

    def build_download_url(
        self, message: TamMessage, sid: str, origin: str
    ) -> str | None:
        """Build one candidate download URL for a message, given a sid.

        ``origin`` supplies the scheme+host+port the (path-only)
        ``/cgi-bin/luacgi_notimeout`` endpoint is resolved against - pass
        the FRITZ!Box's normal web-UI address (port 80/443), NOT the
        TR-064 port; see the module docstring for why.
        """
        if not message.Path:
            return None

        # message.Path is normally "/download.lua?path=<raw file path>" -
        # pull just the raw path back out. Fall back to using message.Path
        # itself (minus any query string) if a FRITZ!OS version ever
        # delivers a bare path with no "download.lua?path=" wrapper.
        parsed = urlsplit(message.Path)
        raw_path = parse_qs(parsed.query).get("path", [None])[0] or parsed.path

        download_query = urlencode(
            {"sid": sid, "script": _DOWNLOAD_SCRIPT, "myabfile": raw_path}
        )
        return urljoin(origin, f"{_DOWNLOAD_PATH}?{download_query}")
