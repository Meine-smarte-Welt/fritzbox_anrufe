# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): a75f0afd54dead47a0b04776a215d8a805c754f87d84f6016d2c8204ae576aa0
"""Constants for the AVM Fritz!Box call monitor integration."""

from enum import StrEnum
from typing import Final

from homeassistant.const import Platform


class FritzState(StrEnum):
    """Fritz!Box call states."""

    RING = "RING"
    CALL = "CALL"
    CONNECT = "CONNECT"
    DISCONNECT = "DISCONNECT"


ATTR_PREFIXES = "prefixes"

FRITZ_ATTR_NAME = "name"
FRITZ_ATTR_SERIAL_NUMBER = "Serial"

# Anzeigename für Anrufer/Angerufene ohne Telefonbuch-Eintrag - erscheint
# so direkt in Sensor-Attributen (calls[].name, Live-Attribute from_name/
# to_name/with_name) und damit auch in der Dashboard-Karte.
UNKNOWN_NAME = "Unbekannt"
SERIAL_NUMBER = "serial_number"
REGEX_NUMBER = r"[^\d\+]"

CONF_PHONEBOOK = "phonebook"
CONF_PHONEBOOK_NAME = "phonebook_name"
CONF_PREFIXES = "prefixes"

DEFAULT_HOST = "169.254.1.1"  # IP valid for all Fritz!Box routers
DEFAULT_PORT = 1012
DEFAULT_USERNAME = "admin"
DEFAULT_PHONEBOOK = 0
DEFAULT_NAME = "Phone"

DOMAIN: Final = "fritzbox_anrufe"
MANUFACTURER: Final = "FRITZ!"

PLATFORMS = [Platform.SENSOR]

# --- Anruflisten-Verlaufssensoren (fritzbox_anrufe_eingehend/ausgehend/verpasst) ---
# sowie der Live-Callmonitor-Sensor (fritzbox_anrufe_live). Diese Suffixe
# werden nur für den *translation_key* (übersetzter Anzeigename + Icon)
# verwendet, nicht für die technische entity_id - siehe Kommentar in
# sensor.py für Details, warum Home Assistant das nicht anders unterstützt.

CALL_TYPE_INCOMING = "eingehend"
CALL_TYPE_OUTGOING = "ausgehend"
CALL_TYPE_MISSED = "verpasst"
CALL_TYPE_LIVE = "live"

CALL_TYPES = (CALL_TYPE_INCOMING, CALL_TYPE_OUTGOING, CALL_TYPE_MISSED)

# --- Anrufbeantworter-Sensor (fritzbox_anrufe_anrufbeantworter) - EXPERIMENTELL ---
# Deckt nur Anrufbeantworter/Sprachnachrichten ab, bewusst kein Fax (siehe
# tam.py/voicemail.py). Kein Bestandteil von CALL_TYPES, da dieser Sensor
# keine eigene Anzahl/Tage-Verlaufskonfiguration hat (siehe config_flow.py).
CALL_TYPE_VOICEMAIL = "anrufbeantworter"

# Basis-URL des authentifizierten HTTP-Proxys, über den Anrufbeantworter-
# Aufnahmen im Dashboard abgespielt werden (siehe http.py). Vollständiger
# Pfad: f"{TAM_MEDIA_URL_BASE}/{config_entry_id}/{message_index}".
TAM_MEDIA_URL_BASE = "/api/fritzbox_anrufe/tam_media"

# Analoge Proxy-Route für Sprachnachrichten, die über einen Eintrag der
# Anruflisten-Sensoren (nicht über den Anrufbeantworter-Sensor) erreicht
# werden - siehe http.py:FritzBoxCallMediaView und die "Weiterverarbeitung"
# in der Dashboard-Karte (CALL_OUTCOME_VOICEMAIL). Vollständiger Pfad:
# f"{CALL_MEDIA_URL_BASE}/{config_entry_id}/{call_type}/{call_id}".
CALL_MEDIA_URL_BASE = "/api/fritzbox_anrufe/call_media"

# --- "Weiterverarbeitung" (optionale Zusatzzeile pro Anruf in der Karte) --
# Klassifiziert, wie ein einzelner Anruf ausgegangen ist - zusätzlich zur
# (weiterhin bestehenden) Zuordnung zu genau einem der drei
# Anruflisten-Sensoren (eingehend/ausgehend/verpasst). Siehe call_log.py
# für die Klassifizierungslogik und ihre Grenzen (Fehlerbehebung in der
# README).
#
# Der von der FRITZ!Box selbst gemeldete "Gerät"-Wert (Call.Device) für
# einen an den eingebauten Anrufbeantworter weitergeleiteten Anruf - von
# Thorsten an echter Hardware bestätigt. Zuverlässigeres Signal für "ging
# zum Anrufbeantworter" als das bloße Vorhandensein von Call.Path (das bei
# solchen Anrufen nicht immer gesetzt ist), siehe call_log.py:_classify_call.
DEVICE_ANSWERING_MACHINE = "Anrufbeantworter"

# Eingehend: nur "beantwortet" möglich (per Person angenommen) - Anrufe,
# die zum Anrufbeantworter gingen (Device == DEVICE_ANSWERING_MACHINE) oder
# abgewiesen wurden, zählen seit Version 1.0.3 komplett als "verpasst",
# nicht mehr als "eingehend".
CALL_OUTCOME_ANSWERED = "beantwortet"
# Verpasst, mit aufgenommener Nachricht vs. ohne: seit 1.0.3 nicht mehr nur
# anhand von Call.Path entschieden, sondern zusätzlich anhand eines
# Datum/Uhrzeit- (und, falls vorhanden, Rufnummer-)Abgleichs mit den
# tatsächlichen Anrufbeantworter-Nachrichten (siehe
# call_log.py:_find_matching_tam_message) - ein deutlich verlässlicheres
# Signal als das call-list-eigene Path-Feld allein.
CALL_OUTCOME_VOICEMAIL = "anrufbeantworter"
# Ging zum Anrufbeantworter (Device == DEVICE_ANSWERING_MACHINE), aber es
# wurde keine Nachricht gefunden - z. B. weil der Anrufer aufgelegt hat,
# bevor die Ansage zu Ende war. Getrennt von CALL_OUTCOME_UNREACHED (siehe
# unten), seit Thorsten darauf hinwies, dass der bisherige gemeinsame Text
# "Nicht erreicht" für diesen Fall irreführend war - der Anruf KAM ja beim
# Anrufbeantworter an, nur eben ohne Sprachnachricht.
CALL_OUTCOME_NO_VOICEMAIL = "keine_nachricht"
# Ging NICHT zum Anrufbeantworter (z. B. von der FRITZ!Box abgewiesen, oder
# schlicht nie angenommen und kein Anrufbeantworter aktiv/erreichbar) - hier
# bleibt "nicht erreicht" zutreffend. Die FRITZ!Box-Anrufliste unterscheidet
# innerhalb von CALL_OUTCOME_NO_VOICEMAIL weiterhin nicht zuverlässig
# zwischen "vor dem Anrufbeantworter aufgelegt" und "Anrufbeantworter
# erreicht, aber keine Nachricht hinterlassen" - siehe README.
CALL_OUTCOME_UNREACHED = "nicht_erreicht"
# Ausgehend: nur Verbindungsdauer > 0 ist zuverlässig auswertbar - eine
# Unterscheidung zwischen "besetzt" und "niemand nimmt ab" liefert die
# FRITZ!Box-Anrufliste nicht (siehe README, Fehlerbehebung).
CALL_OUTCOME_CONNECTED = "verbunden"
CALL_OUTCOME_NOT_CONNECTED = "nicht_verbunden"

# --- Zusätzliche Aktualisierung nach einem Gespräch --------------------
# Neben der regulären 5-Minuten-Pollingintervalle beider Coordinator
# (CALL_LOG_UPDATE_INTERVAL/TAM_UPDATE_INTERVAL) löst der Live-Callmonitor-
# Sensor (FritzBoxCallSensor, siehe sensor.py) zusätzlich eine gezielte
# Aktualisierung aus, sobald sein Zustand nach einem Klingeln/Wählen/
# Gespräch wieder auf "idle" wechselt - deckt damit auch verpasste Anrufe
# ab, nicht nur tatsächlich geführte Gespräche. Die kurze Verzögerung gibt
# der FRITZ!Box Zeit, den Anrufliste-Eintrag zu finalisieren bzw. eine ggf.
# aufgezeichnete Nachricht zu verarbeiten, bevor abgefragt wird.
POST_CALL_REFRESH_DELAY_SECONDS: Final = 5

# Konfigurierbare Verlaufstiefe der drei Anruflisten-Sensoren - jeder Typ
# (eingehend/ausgehend/verpasst) hat seine EIGENEN, unabhängig einstellbaren
# Optionen (Options-Flow UND bereits bei der Erst-Einrichtung).
CALL_LOG_LIMIT_COUNT: Final = "count"
CALL_LOG_LIMIT_DAYS: Final = "days"

DEFAULT_CALL_LOG_LIMIT_TYPE = CALL_LOG_LIMIT_COUNT
DEFAULT_CALL_LOG_COUNT = 10
DEFAULT_CALL_LOG_DAYS = 7

MIN_CALL_LOG_DAYS = 1
MAX_CALL_LOG_DAYS = 90

# Feste Auswahlwerte für das "Anzahl"-Dropdown (pro Sensor).
CALL_LOG_COUNT_PRESETS: Final[tuple[int, ...]] = (5, 10, 20, 50, 100, 200)

# Wie viele Tage Rohdaten (alle Anruftypen gemischt) pro Aktualisierung von
# der FRITZ!Box geladen werden, bevor sie clientseitig je Sensor nach dessen
# eigener Einstellung (Anzahl oder Tage) gefiltert werden. Die FRITZ!Box/
# fritzconnection-API kennt keinen "letzte N Anrufe von Typ X"-Parameter,
# sondern begrenzt immer den gemischten Gesamtabruf - siehe call_log.py.
SHARED_CALL_LOG_FETCH_DAYS: Final = MAX_CALL_LOG_DAYS


def conf_call_log_limit_type(call_type: str) -> str:
    """Options-Key: Anzahl- oder Tage-Modus für einen Anruflisten-Sensor."""
    return f"call_log_limit_type_{call_type}"


def conf_call_log_count(call_type: str) -> str:
    """Options-Key: max. Anzahl Einträge für einen Anruflisten-Sensor."""
    return f"call_log_count_{call_type}"


def conf_call_log_days(call_type: str) -> str:
    """Options-Key: Tage-Fenster für einen Anruflisten-Sensor."""
    return f"call_log_days_{call_type}"


# Options-Flow-Schalter (seit v1.0.5b4): Nachricht nach Wiedergabe ÜBER
# DIESE INTEGRATION automatisch auf der FRITZ!Box selbst als gelesen
# markieren (MarkMessage, siehe tam.py), genau wie beim Abhören an einem
# FRITZ!Box-eigenen Gerät. Standardmäßig AUS - anders als rein optische
# Darstellungs-Schalter (show_*) verändert dies tatsächlich gemeinsam
# genutzten Zustand auf der Box selbst (z. B. auch die Anzahl ungelesener
# Nachrichten in FRITZ!App Fon), nicht nur diese eine Dashboard-Karte.
# Bewusst auf Integrations- statt Karten-Ebene angesiedelt - siehe README.
CONF_AUTO_MARK_READ = "auto_mark_read"
DEFAULT_AUTO_MARK_READ = False

# Event (seit v1.0.6b0): gefeuert von FritzTamCoordinator, sobald beim
# Abruf der Anrufbeantworter-Nachrichtenliste eine gegenüber dem
# vorherigen Abruf neue Nachrichten-ID entdeckt wird - siehe voicemail.py.
# Bewusst NICHT beim allerersten Abruf nach einem (Neu-)Start gefeuert,
# sonst gäbe es bei jedem Home-Assistant-Neustart Events für längst
# bekannte, nur noch nicht abgehörte Nachrichten. Direkt als
# Automations-Auslöser nutzbar, ohne die messages-Attributliste selbst per
# Vorlage auf neu hinzugekommene Einträge vergleichen zu müssen - siehe
# README.
EVENT_NEW_VOICEMAIL_MESSAGE = f"{DOMAIN}_new_voicemail_message"

# --- Spam-Erkennung (seit v1.0.6b1) -------------------------------------
# Die FRITZ!Box liefert über TR-064 KEIN natives Spam-/KI-Erkennungsfeld -
# siehe spam.py für die ausführliche Begründung. CONF_SPAM_NUMBERS ist eine
# vom Nutzer im Options-Flow gepflegte Liste von Nummern/Vorwahlen
# (Präfix-Abgleich), analog zu CONF_PREFIXES oben - bewusst keine eigene
# DEFAULT_SPAM_NUMBERS-Konstante, options.get() liefert dann None/leer.
CONF_SPAM_NUMBERS = "spam_numbers"

# --- Zweiter Anrufbeantworter (seit v1.0.6b1) ---------------------------
# Manche FRITZ!Box-Modelle/-Konfigurationen erlauben einen zweiten
# Anrufbeantworter ("TAM-Index" 1) zusätzlich zum ersten (Index 0, siehe
# tam.py:DEFAULT_TAM_INDEX). Standardmäßig AUS, da die meisten Nutzer nur
# einen Anrufbeantworter eingerichtet haben - siehe config_flow.py.
CONF_SECOND_TAM = "second_tam_enabled"
DEFAULT_SECOND_TAM = False

# Zweiter Anrufbeantworter-Sensor (fritzbox_anrufe_anrufbeantworter_2) -
# eigener translation_key/Icon, siehe sensor.py/strings.json/icons.json.
CALL_TYPE_VOICEMAIL_2 = "anrufbeantworter_2"

# Eigene Proxy-Route für den zweiten Anrufbeantworter (siehe http.py:
# FritzBoxTam2MediaView) - bewusst getrennt von TAM_MEDIA_URL_BASE, damit
# der bereits an echter Hardware bestätigte Wiedergabe-Pfad des ersten
# Anrufbeantworters unangetastet bleibt.
TAM2_MEDIA_URL_BASE = "/api/fritzbox_anrufe/tam2_media"
