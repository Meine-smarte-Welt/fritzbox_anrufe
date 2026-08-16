# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 35737922b8f7d03479393539a9b61dedd6bfbae758d5f8a11f132d2b704d5bce
"""Config flow for fritzbox_anrufe."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
import logging
from typing import Any, cast, override

from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import FritzConnectionException, FritzSecurityError
from requests.exceptions import ConnectionError as RequestsConnectionError
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .base import FritzBoxPhonebook
from .const import (
    CALL_LOG_COUNT_PRESETS,
    CALL_LOG_LIMIT_COUNT,
    CALL_LOG_LIMIT_DAYS,
    CALL_TYPES,
    CONF_AUTO_MARK_READ,
    CONF_PHONEBOOK,
    CONF_PREFIXES,
    CONF_SPAM_NUMBERS,
    CONF_TAM_COUNT,
    DEFAULT_AUTO_MARK_READ,
    DEFAULT_CALL_LOG_COUNT,
    DEFAULT_CALL_LOG_DAYS,
    DEFAULT_CALL_LOG_LIMIT_TYPE,
    DEFAULT_HOST,
    DEFAULT_PHONEBOOK,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
    FRITZ_ATTR_NAME,
    FRITZ_ATTR_SERIAL_NUMBER,
    MAX_CALL_LOG_DAYS,
    MAX_TAM_COUNT,
    MIN_CALL_LOG_DAYS,
    MIN_TAM_COUNT,
    SERIAL_NUMBER,
    conf_call_log_count,
    conf_call_log_days,
    conf_call_log_limit_type,
    migrated_tam_count,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA_USER = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConnectResult(StrEnum):
    """FritzBoxPhonebook connection result."""

    INVALID_AUTH = "invalid_auth"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    MALFORMED_PREFIXES = "malformed_prefixes"
    NO_DEVIES_FOUND = "no_devices_found"
    UNKNOWN = "unknown"
    SUCCESS = "success"


def _history_schema_dict(current_options: Mapping[str, Any]) -> dict[Any, Any]:
    """Build the repeated (Modus/Anzahl/Tage) schema fields, one set per call type.

    Shared between the config flow's own "history" step (asked once at
    initial setup) and the options flow (so it can be changed again later,
    independently for each of the three call-list sensors).
    """
    schema: dict[Any, Any] = {}
    for call_type in CALL_TYPES:
        schema[
            vol.Optional(
                conf_call_log_limit_type(call_type),
                default=current_options.get(
                    conf_call_log_limit_type(call_type), DEFAULT_CALL_LOG_LIMIT_TYPE
                ),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[CALL_LOG_LIMIT_COUNT, CALL_LOG_LIMIT_DAYS],
                translation_key="call_log_limit_type",
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
        schema[
            vol.Optional(
                conf_call_log_count(call_type),
                default=str(
                    current_options.get(conf_call_log_count(call_type), DEFAULT_CALL_LOG_COUNT)
                ),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[str(preset) for preset in CALL_LOG_COUNT_PRESETS],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
        schema[
            vol.Optional(
                conf_call_log_days(call_type),
                default=current_options.get(conf_call_log_days(call_type), DEFAULT_CALL_LOG_DAYS),
            )
        ] = vol.All(vol.Coerce(int), vol.Range(min=MIN_CALL_LOG_DAYS, max=MAX_CALL_LOG_DAYS))
    return schema


def _parse_history_input(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Extract and coerce the per-call-type history fields from form input."""
    parsed: dict[str, Any] = {}
    for call_type in CALL_TYPES:
        parsed[conf_call_log_limit_type(call_type)] = user_input[conf_call_log_limit_type(call_type)]
        parsed[conf_call_log_count(call_type)] = int(user_input[conf_call_log_count(call_type)])
        parsed[conf_call_log_days(call_type)] = int(user_input[conf_call_log_days(call_type)])
    return parsed


class FritzBoxCallMonitorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a fritzbox_anrufe config flow."""

    VERSION = 1

    _entry: ConfigEntry
    _host: str
    _port: int
    _username: str
    _password: str
    _phonebook_name: str
    _phonebook_id: int
    _phonebook_ids: list[int]
    _fritzbox_phonebook: FritzBoxPhonebook
    _serial_number: str
    _history_options: dict[str, Any]

    def __init__(self) -> None:
        """Initialize flow."""
        self._phonebook_names: list[str] | None = None

    def _get_config_entry(self) -> ConfigFlowResult:
        """Create and return an config entry."""
        return self.async_create_entry(
            title=self._phonebook_name,
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_PHONEBOOK: self._phonebook_id,
                SERIAL_NUMBER: self._serial_number,
            },
            options=self._history_options,
        )

    def _try_connect(self) -> ConnectResult:
        """Try to connect and check auth."""
        self._fritzbox_phonebook = FritzBoxPhonebook(
            host=self._host,
            username=self._username,
            password=self._password,
        )

        try:
            self._fritzbox_phonebook.init_phonebook()
            self._phonebook_ids = self._fritzbox_phonebook.get_phonebook_ids()

            fritz_connection = FritzConnection(
                address=self._host, user=self._username, password=self._password
            )
            info = fritz_connection.updatecheck
        except FritzSecurityError:
            return ConnectResult.INSUFFICIENT_PERMISSIONS
        except FritzConnectionException:
            return ConnectResult.INVALID_AUTH
        except RequestsConnectionError:
            # e.g. host unreachable / connection refused (TR-064 port closed).
            return ConnectResult.NO_DEVIES_FOUND
        except Exception:  # noqa: BLE001 - deliberately broad: never let an
            # unexpected exception (timeout, HTTP error, malformed XML
            # response, ...) surface to the user as an unhelpful "Unknown
            # error occurred" without at least a traceback in the log.
            _LOGGER.exception(
                "Unerwarteter Fehler beim Verbindungsaufbau zur FRITZ!Box unter %s",
                self._host,
            )
            return ConnectResult.UNKNOWN

        self._serial_number = info[FRITZ_ATTR_SERIAL_NUMBER]
        return ConnectResult.SUCCESS

    async def _get_name_of_phonebook(self, phonebook_id: int) -> str:
        """Return name of phonebook for given phonebook_id."""
        phonebook_info = await self.hass.async_add_executor_job(
            self._fritzbox_phonebook.fph.phonebook_info, phonebook_id
        )
        return cast(str, phonebook_info[FRITZ_ATTR_NAME])

    async def _get_list_of_phonebook_names(self) -> list[str]:
        """Return list of names for all available phonebooks."""
        return [
            await self._get_name_of_phonebook(phonebook_id)
            for phonebook_id in self._phonebook_ids
        ]

    @staticmethod
    @callback
    @override
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> FritzBoxCallMonitorOptionsFlowHandler:
        """Get the options flow for this handler."""
        return FritzBoxCallMonitorOptionsFlowHandler()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA_USER, errors={}
            )

        self._host = user_input[CONF_HOST]
        self._port = user_input[CONF_PORT]
        self._password = user_input[CONF_PASSWORD]
        self._username = user_input[CONF_USERNAME]

        result = await self.hass.async_add_executor_job(self._try_connect)

        if result in (ConnectResult.INVALID_AUTH, ConnectResult.UNKNOWN):
            # Recoverable: re-show the form instead of aborting the whole
            # flow, so the user can just correct the input and retry.
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA_USER,
                errors={"base": result},
            )

        if result != ConnectResult.SUCCESS:
            return self.async_abort(reason=result)

        if len(self._phonebook_ids) > 1:
            return await self.async_step_phonebook()

        self._phonebook_id = DEFAULT_PHONEBOOK
        self._phonebook_name = await self._get_name_of_phonebook(self._phonebook_id)

        await self.async_set_unique_id(f"{self._serial_number}-{self._phonebook_id}")
        self._abort_if_unique_id_configured()

        return await self.async_step_history()

    async def async_step_phonebook(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow to chose one of multiple available phonebooks."""

        if self._phonebook_names is None:
            self._phonebook_names = await self._get_list_of_phonebook_names()

        if user_input is None:
            return self.async_show_form(
                step_id="phonebook",
                data_schema=vol.Schema(
                    {vol.Required(CONF_PHONEBOOK): vol.In(self._phonebook_names)}
                ),
                errors={},
            )

        self._phonebook_name = user_input[CONF_PHONEBOOK]
        self._phonebook_id = self._phonebook_names.index(self._phonebook_name)

        await self.async_set_unique_id(f"{self._serial_number}-{self._phonebook_id}")
        self._abort_if_unique_id_configured()

        return await self.async_step_history()

    async def async_step_history(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask, per call-list sensor, how much call history to keep.

        Shown once during initial setup (in addition to being changeable
        later via the options flow) so the retention depth for
        fritzbox_anrufe_eingehend/ausgehend/verpasst can be picked from the
        start instead of only defaulting to 10 calls each.
        """
        if user_input is None:
            return self.async_show_form(
                step_id="history",
                data_schema=vol.Schema(_history_schema_dict({})),
                errors={},
            )

        self._history_options = _parse_history_input(user_input)
        return self._get_config_entry()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle flow upon an API authentication error."""
        self._entry = self._get_reauth_entry()
        self._host = entry_data[CONF_HOST]
        self._port = entry_data[CONF_PORT]
        self._username = entry_data[CONF_USERNAME]
        self._password = entry_data[CONF_PASSWORD]
        self._phonebook_id = entry_data[CONF_PHONEBOOK]

        return await self.async_step_reauth_confirm()

    def _show_setup_form_reauth_confirm(
        self, user_input: dict[str, Any], errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Show the reauth form to the user."""
        default_username = user_input.get(CONF_USERNAME)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=default_username): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            description_placeholders={"host": self._host},
            errors=errors or {},
        )

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self._show_setup_form_reauth_confirm(
                user_input={CONF_USERNAME: self._username}
            )

        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]

        if (
            error := await self.hass.async_add_executor_job(self._try_connect)
        ) is not ConnectResult.SUCCESS:
            return self._show_setup_form_reauth_confirm(
                user_input=user_input, errors={"base": error}
            )

        self.hass.config_entries.async_update_entry(
            self._entry,
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_PHONEBOOK: self._phonebook_id,
                SERIAL_NUMBER: self._serial_number,
            },
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)
        return self.async_abort(reason="reauth_successful")


class FritzBoxCallMonitorOptionsFlowHandler(OptionsFlowWithReload):
    """Handle a fritzbox_anrufe options flow.

    Seit v1.1.1 kein einzelner flacher Formular-Schritt mehr, sondern ein
    Menü mit zwei Zielen: die bisherigen Grundeinstellungen (Präfixe,
    Verlaufstiefe, auto_mark_read, Spam-Nummern - siehe
    async_step_general_settings) UND die neue Anrufbeantworter-Verwaltung
    (async_step_manage_tams), die den vormals binären second_tam_enabled-
    Schalter durch wiederholt anklickbare "Weiteren Anrufbeantworter
    hinzufügen"/"entfernen"-Schaltflächen ersetzt (bis zu MAX_TAM_COUNT=5,
    siehe const.py). Beide Zielschritte speichern unabhängig voneinander
    und mergen dabei stets über die JEWEILS AKTUELLEN self.config_entry.
    options, damit ein Speichern in einem Zweig die Einstellungen des
    anderen nicht überschreibt (die Options-Flow-API ersetzt den gesamten
    options-dict pro async_create_entry-Aufruf, kein automatisches Merge).
    """

    def __init__(self) -> None:
        """Initialize per-flow working state for the TAM-Verwaltung-Menü.

        ``_pending_tam_count`` hält den Zwischenstand über mehrere Schritte
        des "Anrufbeantworter verwalten"-Untermenüs hinweg (siehe
        async_step_manage_tams) - erst async_step_tams_done übernimmt ihn
        tatsächlich in die gespeicherten Optionen. ``None`` bis zum ersten
        Betreten dieses Untermenüs.
        """
        self._pending_tam_count: int | None = None

    @classmethod
    def _are_prefixes_valid(cls, prefixes: str | None) -> bool:
        """Check if prefixes are valid."""
        return bool(prefixes.strip()) if prefixes else prefixes is None

    @classmethod
    def _get_list_of_prefixes(cls, prefixes: str | None) -> list[str] | None:
        """Get list of prefixes."""
        if prefixes is None:
            return None
        return [prefix.strip() for prefix in prefixes.split(",")]

    def _get_option_schema(self) -> vol.Schema:
        """Get the option schema for prefixes and each sensor's history depth.

        Each of the three call-list sensors (fritzbox_anrufe_eingehend/
        ausgehend/verpasst) has its own, independently configurable
        Anzahl-oder-Tage setting - see :func:`_history_schema_dict`.
        """
        options = self.config_entry.options
        schema: dict[Any, Any] = {
            vol.Optional(
                CONF_PREFIXES,
                description={"suggested_value": options.get(CONF_PREFIXES)},
            ): vol.Any(str, None),
        }
        schema.update(_history_schema_dict(options))
        # Anrufbeantworter: nach Wiedergabe automatisch als gelesen markieren
        # (seit v1.0.5b4, EXPERIMENTELL, Standard AUS) - siehe tam.py/
        # voicemail.py:maybe_auto_mark_read. Bewusst auf Integrations-
        # (Options-Flow-) statt Karten-Ebene, da dies tatsächlichen, von
        # allen Dashboards/Apps geteilten Zustand auf der FRITZ!Box selbst
        # ändert, nicht nur diese eine Kartenansicht.
        schema[
            vol.Optional(
                CONF_AUTO_MARK_READ,
                default=options.get(CONF_AUTO_MARK_READ, DEFAULT_AUTO_MARK_READ),
            )
        ] = selector.BooleanSelector()
        # Spam-Erkennung (seit v1.0.6b1) - Freitextliste von Nummern/
        # Vorwahlen, Präfix-Abgleich, siehe spam.py. Mirrors exakt das
        # bestehende CONF_PREFIXES-Muster oben (keine eigene DEFAULT-
        # Konstante, options.get() liefert None/leer).
        #
        # Bugfix (seit v1.1.1): der Validator war bislang das nackte
        # ``str``-Voluptuous-Schema, das NUR echte Strings akzeptiert. Ein
        # leer gelassenes optionales Textfeld schickt das Home-Assistant-
        # Frontend aber als ``null`` mit (nicht etwa als leerer String, und
        # der Schlüssel fehlt auch nicht einfach im user_input-Dict) -
        # dagegen schlug die Validierung mit "expected str" fehl, obwohl
        # das Feld laut ``vol.Optional`` gar nicht ausgefüllt werden muss.
        # ``vol.Any(str, None)`` lässt beide Fälle zu; die nachgelagerte
        # Verarbeitung (``_get_list_of_prefixes``) behandelt ``None``
        # bereits korrekt. Betraf denselben Schema-Aufbau auch bei
        # CONF_PREFIXES oben, dort nur nicht aufgefallen, weil dieses Feld
        # bei den meisten Installationen bereits befüllt ist.
        schema[
            vol.Optional(
                CONF_SPAM_NUMBERS,
                description={"suggested_value": options.get(CONF_SPAM_NUMBERS)},
            )
        ] = vol.Any(str, None)
        return vol.Schema(schema)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the top-level menu: Grundeinstellungen vs. Anrufbeantworter verwalten."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["general_settings", "manage_tams"],
        )

    async def async_step_general_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Die bisherigen Grundeinstellungen - inhaltlich unverändert seit v1.1.0,

        nur aus dem vormaligen "init"-Schritt hierher verschoben (siehe
        Klassendocstring). Schließt den gesamten Options-Flow ab, sobald
        gespeichert wird - identisch zum bisherigen Verhalten.
        """
        option_schema = self._get_option_schema()

        if user_input is None:
            return self.async_show_form(
                step_id="general_settings",
                data_schema=option_schema,
                errors={},
            )

        prefixes: str | None = user_input.get(CONF_PREFIXES)

        if not self._are_prefixes_valid(prefixes):
            return self.async_show_form(
                step_id="general_settings",
                data_schema=option_schema,
                errors={"base": ConnectResult.MALFORMED_PREFIXES},
            )

        spam_numbers_input: str | None = user_input.get(CONF_SPAM_NUMBERS)

        return self.async_create_entry(
            title="",
            data={
                # Bestehende Optionen (insbesondere CONF_TAM_COUNT, siehe
                # async_step_tams_done unten) bleiben erhalten - dieser
                # Zweig überschreibt nur die hier tatsächlich gezeigten
                # Felder, nicht den gesamten Optionen-Datensatz.
                **self.config_entry.options,
                CONF_PREFIXES: self._get_list_of_prefixes(prefixes),
                CONF_AUTO_MARK_READ: user_input.get(CONF_AUTO_MARK_READ, DEFAULT_AUTO_MARK_READ),
                CONF_SPAM_NUMBERS: self._get_list_of_prefixes(spam_numbers_input) or [],
                **_parse_history_input(user_input),
            },
        )

    async def async_step_manage_tams(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Menü: 'Weiteren Anrufbeantworter hinzufügen'/'entfernen' per Klick.

        Seit v1.1.1 - ersetzt den bisherigen einzelnen second_tam_enabled-
        Schalter durch eine Anzahl (1-5, const.py:MAX_TAM_COUNT/
        MIN_TAM_COUNT), gesteuert über wiederholt anklickbare
        Schaltflächen statt eines einzelnen An/Aus-Reglers oder Zahlenfelds.
        ``self._pending_tam_count`` hält den Zwischenstand, bis
        async_step_tams_done ihn tatsächlich speichert - so lässt sich
        mehrfach hintereinander hinzufügen/entfernen, bevor überhaupt ein
        Config-Entry-Reload (OptionsFlowWithReload) ausgelöst wird.
        """
        if self._pending_tam_count is None:
            self._pending_tam_count = migrated_tam_count(self.config_entry.options)

        count = self._pending_tam_count
        menu_options: list[str] = []
        if count < MAX_TAM_COUNT:
            menu_options.append("add_tam")
        if count > MIN_TAM_COUNT:
            menu_options.append("remove_tam")
        menu_options.append("tams_done")

        return self.async_show_menu(
            step_id="manage_tams",
            menu_options=menu_options,
            description_placeholders={"count": str(count)},
        )

    async def async_step_add_tam(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schaltfläche 'Weiteren Anrufbeantworter hinzufügen' - erhöht den Zwischenstand."""
        assert self._pending_tam_count is not None
        self._pending_tam_count = min(MAX_TAM_COUNT, self._pending_tam_count + 1)
        return await self.async_step_manage_tams()

    async def async_step_remove_tam(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schaltfläche 'Anrufbeantworter entfernen' - verringert den Zwischenstand.

        Entfernt immer den zuletzt hinzugefügten Slot (höchste Nummer) -
        dieselbe "Slot 1 lässt sich nie deaktivieren"-Regel, die schon das
        vormalige second_tam_enabled hatte. Ein bereits eingerichteter
        Sensor/Schalter für den entfernten Slot wird dadurch NICHT sofort
        aus der Entity-Registry gelöscht - er erscheint nach dem folgenden
        Reload (OptionsFlowWithReload) einfach als "nicht verfügbar",
        exakt das Verhalten, das second_tam_enabled=False vorher schon
        hatte.
        """
        assert self._pending_tam_count is not None
        self._pending_tam_count = max(MIN_TAM_COUNT, self._pending_tam_count - 1)
        return await self.async_step_manage_tams()

    async def async_step_tams_done(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schaltfläche 'Fertig' - übernimmt den Zwischenstand in die Optionen."""
        assert self._pending_tam_count is not None
        return self.async_create_entry(
            title="",
            data={
                # Bestehende Optionen (Präfixe, Verlaufstiefe, auto_mark_read,
                # Spam-Nummern) bleiben erhalten - siehe
                # async_step_general_settings für das Gegenstück.
                **self.config_entry.options,
                CONF_TAM_COUNT: self._pending_tam_count,
            },
        )
