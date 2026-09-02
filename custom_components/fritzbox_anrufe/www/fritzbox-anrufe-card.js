// SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 4af8179c2e6b8dc6eddb88d79d9b18eb0b96af827d5dae2002170e6132b97e80
/**
 * fritzbox-anrufe-card
 * ---------------------
 * Custom Lovelace card for the fritzbox_anrufe Home Assistant integration.
 *
 * Shows a filterable list of incoming/outgoing/missed FRITZ!Box calls plus
 * Anrufbeantworter (answering machine) messages, switched via a 5-icon
 * header bar (Alle / Angenommen / Ausgehend / Verpasst / Anrufbeantworter -
 * Anrufbeantworter is a tab like the others, not a separate section below
 * the call list), with a live-call banner above the icons whenever a call
 * is currently ringing/dialing/ongoing. Responsive: the layout stays
 * legible on both a phone-width and a desktop-width dashboard.
 *
 * The "eingehend"/incoming filter/config key (internal identifier, unique_id
 * and entity_id all stay "eingehend" for backwards compatibility - see
 * const.py:CALL_TYPE_INCOMING) is labeled "Angenommen" in the UI since
 * v1.0.3: after that version's reclassification (calls routed to the
 * answering machine now count as "verpasst"), this tab only ever contains
 * calls a person actually answered, so "Eingehend" read as misleading -
 * per Thorsten.
 *
 * Every category - Alle/Gesamt, Angenommen, Ausgehend, Verpasst and
 * Anrufbeantworter - can be individually shown or hidden via the graphical
 * config editor (or the matching show_* YAML key); the Anrufbeantworter tab
 * additionally only appears once entity_voicemail is configured. There is
 * deliberately only ONE card type: a dedicated, separate Anrufbeantworter
 * card was considered but dropped in favor of these per-category toggles on
 * this single card.
 *
 * Includes a graphical config editor (via getConfigElement) to pick the
 * entities, which categories are shown, the row count, and which call
 * attributes/columns are shown - no YAML editing required, though YAML
 * configuration still works. Since v1.0.4, the editor groups its many
 * settings into collapsible sections (Sensoren/Kategorien/Darstellung/
 * Weiterverarbeitung/Farben) via <ha-form>'s "expandable" schema type with
 * `flatten: true` - the resulting config stays a flat object (identical
 * YAML keys as before), the grouping is purely visual. Since v1.2.2 the
 * "Sensoren" section additionally nests the answering-machine entity pickers
 * (entity_voicemail/entity_voicemail_2..5 plus the entity_tam_switch/
 * entity_tam_switch_2..5 on/off switches) inside their own collapsible
 * "Anrufbeantworter" sub-expandable (again `flatten: true`, so the stored
 * config is unchanged - purely an editor grouping), collapsed by default to
 * keep the four call sensors readable above it. This relies on a
 * reasonably recent Home Assistant frontend; NOT confirmed against real
 * hardware/every HA version - please open a GitHub issue if the editor
 * renders oddly (e.g. ungrouped, or with a stray top-level key) on your
 * instance.
 *
 * Since v1.0.4, most icon/symbol colors are also configurable (editor
 * group "Farben", `color_*` config keys below) - each accepts a CSS color
 * value (hex, rgb()/rgba(), hsl(), or a CSS variable reference) and falls
 * back to the previous hard-coded theme-color default when left empty, so
 * existing dashboards render unchanged unless a color is explicitly set.
 * Since v1.0.4b1 the 5 category-tab icons (Alle/Angenommen/Ausgehend/
 * Verpasst/Anrufbeantworter) can also be colored individually and
 * independently of the tab's active/inactive state (`color_icon_*` keys) -
 * see CATEGORY_ICON_COLOR_KEYS/_renderTabs() below. Also since v1.0.4b1,
 * the "Farben" editor group is no longer rendered via <ha-form> like the
 * other groups; it's built from plain, always-supported HTML instead
 * (native <input type="color"> swatch plus a text field per color, see
 * FritzboxAnrufeCardEditor._buildColorSection()) so every field gets a
 * graphical color picker AND shows the color currently in effect
 * (explicit value or resolved default) - something <ha-form>'s generic
 * text selector couldn't offer. This also means the color section no
 * longer carries the same "unconfirmed against every HA frontend version"
 * caveat as the other 4 accordion groups (native <details>/<input>, not an
 * HA-specific component).
 *
 * v1.0.4b2: two small follow-ups from Thorsten's first real-hardware test of
 * the above. (1) The native <summary> disclosure marker rendered
 * inconsistently/invisibly in the Companion App, unlike the chevron-down
 * <ha-form> shows for its own 4 accordion groups - the "Farben" section now
 * renders its own explicit chevron icon (rotates on open/close via CSS) so
 * it looks the same as the other 4 groups regardless of browser/WebView
 * default marker behavior. (2) An "Alle Farben zurücksetzen" button clears
 * all 12 color_* keys back to "" (= the previous fixed theme colors) in one
 * step - see FritzboxAnrufeCardEditor._resetAllColors(). Note on
 * persistence: color values are ordinary Lovelace card config, stored by
 * Home Assistant's own dashboard storage exactly like every other setting
 * on this card (title, entities, show_* toggles, ...) - nothing in this
 * integration/card can reset them on its own, including across a Home
 * Assistant restart.
 *
 * v1.0.4b3: two further additions from Thorsten. (1) The "Farben" editor
 * section's summary icon/chevron used a smaller --mdc-icon-size (20px) than
 * <ha-form>'s own expandable groups render for their leading icon/chevron
 * (24px, the standard ha-icon/MDC default) - now matched to 24px so all 5
 * accordion headers in the editor look the same size, not just "similar".
 * (2) An optional filter/sort bar (`show_filter_bar`, off by default so
 * existing dashboards stay visually unchanged - same reasoning as
 * show_processing_*) can now be shown above the call list: a "Eigene
 * Rufnummer"/own-number dropdown (populated from the distinct own_number
 * values actually present across the enabled call categories; not shown on
 * the Anrufbeantworter tab, since TAM messages carry no own-number field at
 * all - a FRITZ!Box/fritzconnection limitation, not something this card can
 * work around) plus a sort dropdown (Datum/Dauer/Name, each
 * auf-/absteigend) that applies to every tab including Anrufbeantworter.
 * Both selections are pure client-side UI state (not persisted to the card
 * config) - they reset on reload/on any config change, same as the active
 * tab already did. When `show_filter_bar` is off (the default), calls
 * render in exactly the same order as before this version - the new sort
 * logic in `_visibleCalls()`/`_renderVoicemailRows()` is only reached at all
 * once the bar is enabled, so there is no behavior change for anyone who
 * doesn't opt in.
 *
 * v1.0.4 (final): a configured category-tab icon color (`color_icon_*`)
 * now also colors that category's row icons in the call list, not just the
 * tab itself - per Thorsten: "Wird die Farbe des Symbols in der Kategorie
 * geändert, soll sich auch das Symbol in der Liste in dieser Farbe ändern."
 * See `FritzboxAnrufeCard._rowIconColor()`. The single exception is
 * `color_row_icon` (one uniform color for every row icon, in the "Farben"
 * editor section) - if set, it wins over any per-category color, exactly
 * as Thorsten specified. Also: the "Farben" editor section's chevron/font
 * size was re-verified once more for consistency with the other 4
 * accordion groups (see the v1.0.4b3 paragraph above for the original fix).
 *
 * v1.0.5b3: deleting an Anrufbeantworter message (EXPERIMENTAL, `X_AVM-DE_
 * TAM1`'s `DeleteMessage` TR-064 action, see tam.py), permanent and with no
 * undo on the FRITZ!Box itself. `show_delete_button` (off by default) shows
 * a trash icon per message; clicking it does NOT delete immediately but
 * switches inline to a "Wirklich löschen?" confirm/cancel pair (deliberately
 * not a native `confirm()` dialog, since those are known to misbehave in the
 * Companion App WebView) - only confirming calls the new
 * `fritzbox_anrufe.delete_voicemail_message` entity service. The row hides
 * optimistically the instant deletion is confirmed and reappears if the
 * service call fails (see `FritzboxAnrufeCard._deleteVoicemailMessage()`).
 *
 * This is a deliberately narrow, single-feature rebuild on top of v1.0.4:
 * an earlier v1.0.5 line (b0 through b2) additionally bundled an
 * "auto_mark_read" option (auto-clearing the "Neu" status after playback)
 * in the very same release as this delete feature - which, combined with
 * the delete button's own layout change below, triggered a genuine,
 * deterministic CSS regression (the Anrufbeantworter-tab's playback bar
 * silently collapsing to zero width, see the fix applied to
 * `.voicemail-player-slot` below) that took multiple rounds to properly
 * isolate and diagnose, none of which had shipped publicly. Restarting
 * cleanly from v1.0.4 and shipping ONE new capability at a time (delete
 * first, auto_mark_read as a later, separate step) - per Thorsten - makes
 * each change easier to verify in isolation before the next one lands on
 * top of it.
 *
 * v1.0.5b4: the "auto_mark_read" step promised above, now that Thorsten
 * confirmed the delete feature works well in practice. A new Options-Flow
 * switch (integration level, NOT a card config key - see const.py's
 * `CONF_AUTO_MARK_READ` docstring for why) clears a message's "Neu" status
 * directly on the FRITZ!Box itself (`MarkMessage` TR-064 action, see
 * tam.py) right after it has been played back through this integration -
 * matching what happens when a message is played back on a real FRITZ!Box
 * device/app, which is what Thorsten asked for. Off by default. This
 * reintroduces the exact re-render race the abandoned v1.0.5b0-b2 line's b1
 * paragraph above describes (a coordinator refresh fired by
 * `maybe_auto_mark_read()` during active playback tearing down the in-
 * progress `<audio>` element) - so `FritzboxAnrufeCard._hasActiveMediaPlayback()`
 * / `_catchUpRender()` and the `onEnded` callback wiring on
 * `playVoicemail()`/`playCallRecording()` (all below) are ported back in
 * alongside it, this time verified together with `auto_mark_read` from the
 * start rather than discovered as a follow-up bug.
 *
 * Playback: the FRITZ!Box audio recording is served by this integration's
 * own authenticated proxy endpoint (see http.py), which requires a valid
 * Home Assistant session - a plain <audio src="..."> cannot supply that
 * (browsers never attach Home Assistant's auth header to a bare media
 * src). The card therefore renders an "Abspielen" button per message that,
 * on click, downloads the audio via `hass.fetchWithAuth()` (the documented
 * custom-card API for authenticated fetches), turns the response into a
 * blob object URL, and only then hands it to a real <audio> element.
 *
 * Bundled with and auto-registered by the fritzbox_anrufe custom
 * integration (see custom_components/fritzbox_anrufe/__init__.py) - no
 * manual Lovelace resource registration needed.
 *
 * "Weiterverarbeitung" (since v1.0.3, optional, off by default): an extra
 * status row per call, shown beneath its normal row when the matching
 * show_processing_* toggle is on. Shows how the call was resolved
 * (call.outcome, computed server-side - see call_log.py:_classify_call)
 * as an arrow + icon. For eingehend/ausgehend/verpasst it links to that
 * outcome's most relevant tab (e.g. a "verpasst" entry with a recorded
 * message links to "Anrufbeantworter"); for a recorded message it instead
 * plays the recording directly, inline, the same way the Anrufbeantworter
 * tab's own "Abspielen" button does. show_processing_alle controls the
 * same row on the combined "Alle" tab independently of the three
 * per-category toggles. See PROCESSING_META below for the exact
 * icon/label/target mapping, and the README's Fehlerbehebung section for
 * known limitations (the FRITZ!Box call list cannot reliably distinguish
 * "besetzt" from "niemand nimmt ab", nor "vor dem Anrufbeantworter
 * aufgelegt" from "Anrufbeantworter erreicht, aber keine Nachricht
 * hinterlassen" - both pairs collapse into one shared outcome each for
 * now).
 *
 * v1.0.6b2: zweiter Anrufbeantworter DIREKT in derselben Karte (statt nur
 * über eine zweite Karteninstanz, siehe v1.0.6b1). Neues, optionales Feld
 * `entity_voicemail_2` - sobald gesetzt, holt die Karte zusätzlich dessen
 * `messages`-Attribut (rein clientseitig, keine Änderung an der Integration
 * nötig, da `sensor.fritzbox_anrufe_anrufbeantworter_2` bereits seit 1.0.6b1
 * existiert) und zeigt beide Nachrichtenlisten weiterhin unter derselben
 * "Anrufbeantworter"-Kategorie (kein zusätzlicher Tab). `voicemail_2_mode`
 * bestimmt WIE: `merged` (Standard) mischt beide Listen chronologisch in
 * eine gemeinsame Liste, jede Nachricht bekommt ein kleines "AB 1"/"AB
 * 2"-Badge (analog zum Spam-Badge, siehe TAM_BADGE_STYLES); `separate`
 * zeigt stattdessen zwei klar überschriebene Abschnitte untereinander,
 * jeweils unvermischt. Beides bleibt bei leerem `entity_voicemail_2` exakt
 * beim bisherigen 1.0.6b1-Verhalten - siehe CONFIG_DEFAULTS.
 *
 * Da die Nachrichten-`id` (FRITZ!Box-eigener TamMessage.Index) je
 * Anrufbeantworter unabhängig bei 0 zählt, können beide Listen kollidierende
 * IDs enthalten - für Lösch-/Bestätigungs-UI-Status verwendet die Karte
 * daher intern einen zusammengesetzten Schlüssel `"<tam>:<id>"`
 * (FritzboxAnrufeCard._voicemailsFor()); an den `delete_voicemail_message`-
 * Service geht weiterhin die rohe, unveränderte `id` zusammen mit der
 * jeweils korrekten `entity_id`. Als kleiner Nebeneffekt behebt der neue,
 * garantiert nicht-leere Schlüssel eine vorher bestehende Lücke: eine
 * Nachricht mit Index 0 (erste Nachricht überhaupt) bekam wegen einer
 * Wahrheitswert-Prüfung auf die (dann falsy) rohe `id` bislang nie einen
 * Papierkorb-Button angezeigt.
 *
 * v1.1.0: Anrufbeantworter Ein/Aus-Schalter, EXPERIMENTELL (neue
 * `switch`-Plattform der Integration, siehe switch.py/tam.py:
 * ACTION_SET_ENABLE - das zugrunde liegende TR-064-Argument ist NICHT
 * unabhängig bestätigt). `show_tam_switch` (Standard AUS, editierbar unter
 * "Darstellung") blendet vor der Nachrichten-Auflistung im
 * Anrufbeantworter-Tab bis zu zwei Zeilen ein - eine je konfiguriertem
 * `entity_tam_switch`/`entity_tam_switch_2` (eigene Entity-Picker unter
 * "Sensoren", switch-Domäne; `entity_tam_switch_2` wirkt nur zusätzlich zu
 * einem gesetzten `entity_voicemail_2`). Die Zeile zeigt den zuletzt von
 * dieser Integration selbst gesetzten (optimistischen) Zustand, KEINE
 * bestätigte Rücklesung vom FRITZ!Box-Gerät - siehe _renderTamSwitches().
 * Ein Klick ruft den Standard-Home-Assistant-Dienst `switch.turn_on`/
 * `switch.turn_off` auf; kein eigener, kartenseitig optimistischer Zustand
 * nötig, da switch.py selbst bereits optimistisch mit Rückgängigmachen bei
 * Fehler arbeitet (siehe dortiger Modul-Docstring) und der neue Zustand über
 * die reguläre hass-Aktualisierung zurück in die Karte fließt (siehe
 * _computeSignature()).
 *
 * v1.2.0: bis zu fünf Anrufbeantworter DIREKT in derselben Karte (statt wie
 * bislang nur zwei, siehe v1.0.6b2 oben) - neue, optionale Felder
 * `entity_voicemail_3`/`_4`/`_5` (analog zu `entity_voicemail_2`, dieselbe
 * Verallgemeinerung wie bereits backendseitig seit v1.1.1 bei den
 * Integrations-Sensoren selbst, siehe const.py:CALL_TYPES_VOICEMAIL). Bisher
 * war für Anrufbeantworter 3-5 stets eine eigene, zusätzliche Karteninstanz
 * nötig (siehe README "Bekannte Einschränkungen" vor 1.2.0). Neuer
 * `voicemail_2_mode`-Wert `"accordion"`: zeigt je Anrufbeantworter einen
 * unabhängig auf-/zuklappbaren Abschnitt (natives `<details>`, siehe
 * FritzboxAnrufeCard._renderVoicemailAccordion()) - ein Abschnitt mit
 * mindestens einer neuen ("Neu"-Status) Nachricht startet aufgeklappt, alle
 * anderen eingeklappt; danach bestimmt ausschließlich der Nutzer per Klick,
 * welche Abschnitte offen sind (mehrere gleichzeitig möglich), auch über
 * spätere Re-Renders hinweg (siehe FritzboxAnrufeCard._tamAccordionOpen).
 * "merged"/"separate" bleiben für GENAU zwei konfigurierte Anrufbeantworter
 * unverändert wählbar (Standard weiterhin "merged", exakt das bisherige
 * Verhalten bestehender Dashboards) - sobald mehr als zwei Anrufbeantworter
 * konfiguriert sind, erzwingt die Karte "accordion" unabhängig vom
 * gespeicherten `voicemail_2_mode`-Wert, da "merged"/"separate" nur für
 * genau zwei Listen sinnvoll definiert sind (siehe
 * FritzboxAnrufeCard._voicemailDisplayMode()). `entity_tam_switch_3`/`_4`/
 * `_5` (EXPERIMENTELL, wie `entity_tam_switch_2` seit v1.1.0) ergänzen die
 * Ein/Aus-Schalter-Zeilen entsprechend, siehe _renderTamSwitches().
 *
 * Ebenfalls neu in v1.2.0: ein Live-Regler direkt auf der Karte (Checkboxen
 * "AB 1".."AB 5", siehe FritzboxAnrufeCard._renderTamPicker()), sobald zwei
 * oder mehr Anrufbeantworter konfiguriert sind - erlaubt, einzelne
 * Anrufbeantworter beim Betrachten des Dashboards temporär aus der Ansicht
 * zu nehmen (z. B. nur einen bestimmten AB sehen wollen), OHNE die
 * Kartenkonfiguration zu bearbeiten. Der dabei gewählte Zustand ist reiner
 * UI-Laufzeitstatus (this._tamPickerVisible) und geht bei jedem Neuladen der
 * Karte bzw. jeder Konfigurationsänderung wieder auf den DAUERHAFT
 * gespeicherten Grundzustand zurück - dafür neue, optionale Editor-Schalter
 * `show_voicemail_1` bis `_5` (Standard AN für alle, Abschnitt
 * "Kategorien"), analog zu den bestehenden show_alle/show_eingehend-
 * Schaltern. Wirkt auf alle drei Mehrfach-Darstellungen (merged/separate/
 * accordion) gleichermaßen: die jeweils SICHTBARE Teilmenge der
 * konfigurierten Anrufbeantworter bestimmt sowohl, ob überhaupt noch
 * "merged"/"separate" (nur bei genau zwei sichtbaren) oder "accordion" (drei
 * oder mehr sichtbare) gilt, als auch, WELCHE zwei Slots im "merged"-/
 * "separate"-Fall gezeigt werden - nicht mehr zwingend Slot 1+2, siehe
 * _renderVoicemailRows(). Werden alle Anrufbeantworter abgewählt, erscheint
 * statt der (dann leeren) Nachrichten-Auflistung ein eigener Hinweistext;
 * der Regler selbst bleibt weiterhin sichtbar, um mindestens einen wieder
 * einzublenden.
 *
 * Example card configuration (YAML):
 *
 *   type: custom:fritzbox-anrufe-card
 *   title: FRITZ!Box Anrufe
 *   entity_live: sensor.fritz_box_7590_call_monitor
 *   entity_eingehend: sensor.fritz_box_7590_eingehende_anrufe
 *   entity_ausgehend: sensor.fritz_box_7590_ausgehende_anrufe
 *   entity_verpasst: sensor.fritz_box_7590_verpasste_anrufe
 *   entity_voicemail: sensor.fritz_box_7590_anrufbeantworter
 *   entity_voicemail_2: sensor.fritz_box_7590_anrufbeantworter_2  # optional, seit 1.0.6b2
 *   entity_voicemail_3: sensor.fritz_box_7590_anrufbeantworter_3  # optional, seit 1.2.0
 *   entity_voicemail_4: sensor.fritz_box_7590_anrufbeantworter_4  # optional, seit 1.2.0
 *   entity_voicemail_5: sensor.fritz_box_7590_anrufbeantworter_5  # optional, seit 1.2.0
 *   voicemail_2_mode: merged  # "merged"/"separate" (nur bei genau 2 ABs) oder "accordion" (seit 1.2.0, ab 3 ABs erzwungen)
 *   entity_tam_switch: switch.fritz_box_7590_anrufbeantworter_ein_aus  # optional, seit 1.1.0, EXPERIMENTELL
 *   entity_tam_switch_2: switch.fritz_box_7590_anrufbeantworter_2_ein_aus  # optional, seit 1.1.0
 *   entity_tam_switch_3: switch.fritz_box_7590_anrufbeantworter_3_ein_aus  # optional, seit 1.2.0
 *   entity_tam_switch_4: switch.fritz_box_7590_anrufbeantworter_4_ein_aus  # optional, seit 1.2.0
 *   entity_tam_switch_5: switch.fritz_box_7590_anrufbeantworter_5_ein_aus  # optional, seit 1.2.0
 *   show_tam_switch: false
 *   max_rows: 10
 *   show_alle: true
 *   show_eingehend: true
 *   show_ausgehend: true
 *   show_verpasst: true
 *   show_anrufbeantworter: true
 *   show_voicemail_1: true  # seit 1.2.0, Grundzustand für den Live-Regler auf der Karte
 *   show_voicemail_2: true
 *   show_voicemail_3: true
 *   show_voicemail_4: true
 *   show_voicemail_5: true
 *   show_name: true
 *   show_number: true
 *   show_own_number: false
 *   show_device: true
 *   show_duration: true
 *   show_date: true
 *   show_vip: true
 *   show_processing_alle: false
 *   show_processing_eingehend: false
 *   show_processing_ausgehend: false
 *   show_processing_verpasst: false
 *   show_filter_bar: false
 *   color_tab_active: ""
 *   color_success: ""
 *   color_error: ""
 *   color_playback: ""
 *   color_vip: ""
 *   color_row_icon: ""
 *   color_live_banner: ""
 *   color_icon_alle: ""
 *   color_icon_eingehend: ""
 *   color_icon_ausgehend: ""
 *   color_icon_verpasst: ""
 *   color_icon_anrufbeantworter: ""
 */

const FILTER_ALL = "alle";
const FILTER_VOICEMAIL = "anrufbeantworter";
// Einstellungen-Tab (Zahnrad, seit v1.3.0b0, EXPERIMENTELL) - kein Anruf-
// Filter, sondern eine eigene Ansicht (Telefoniegeräte-Tabelle, seit
// v1.3.0b2), siehe _renderSettings(). Standardmäßig aus (show_einstellungen);
// sichtbar, sobald die Kategorie aktiviert ist - der Sensor wird automatisch
// gefunden (siehe _settingsEntityId()/_visibleFilterTypes()).
const FILTER_SETTINGS = "einstellungen";
// "anrufbeantworter" is a tab like any other (5th icon in the header row),
// not a section rendered underneath the call list - see _renderMainContent().
const FILTER_ORDER = ["alle", "eingehend", "ausgehend", "verpasst", FILTER_VOICEMAIL, FILTER_SETTINGS];

const FILTER_META = {
  alle: { icon: "mdi:phone-log", label: "Alle" },
  // Label "Angenommen" since v1.0.3 (was "Eingehend") - see the module
  // docstring above. The filter/config key itself stays "eingehend".
  eingehend: { icon: "mdi:phone-incoming", label: "Angenommen" },
  ausgehend: { icon: "mdi:phone-outgoing", label: "Ausgehend" },
  verpasst: { icon: "mdi:phone-missed", label: "Verpasst" },
  anrufbeantworter: { icon: "mdi:voicemail", label: "Anrufbeantworter" },
  einstellungen: { icon: "mdi:cog", label: "Einstellungen" },
};

// Maximale Anzahl direkt in dieser Karte anzeigbarer Anrufbeantworter (seit
// v1.2.0) - identisch zu const.py:MAX_TAM_COUNT in der Integration (die dort
// je konfiguriertem Slot ohnehin nie mehr als 5 Sensoren anlegt). Siehe
// FritzboxAnrufeCard._activeTamSlots()/_tamEntityKey()/_tamSwitchKey().
const MAX_TAM_SLOTS = 5;

// --- Filter-/Sortierleiste (seit v1.0.4b3, optional über show_filter_bar) --
//
// "Eigene Rufnummer" filtert die Anrufliste (nicht Anrufbeantworter, siehe
// unten) auf einen bestimmten own_number-Wert; die Optionen dafür werden
// dynamisch aus den tatsächlich geladenen Anrufen ermittelt (siehe
// FritzboxAnrufeCard._availableOwnNumbers()), nicht hier fest hinterlegt.
const DEFAULT_SORT = "date_desc";

const SORT_OPTIONS = [
  { value: "date_desc", label: "Datum (neueste zuerst)" },
  { value: "date_asc", label: "Datum (älteste zuerst)" },
  { value: "duration_desc", label: "Dauer (längste zuerst)" },
  { value: "duration_asc", label: "Dauer (kürzeste zuerst)" },
  { value: "name_asc", label: "Name (A-Z)" },
  { value: "name_desc", label: "Name (Z-A)" },
];

// Wandelt die vom Backend als str(timedelta) gelieferte Dauer ("H:MM:SS",
// bei sehr langen Aufnahmen ggf. mit "X days, "-Präfix) in Sekunden um, für
// die Dauer-Sortierung. Ein leerer/unparsbarer Wert wird als 0 behandelt
// (landet beim Sortieren nach Dauer am Anfang bzw. Ende, statt einen Fehler
// zu werfen).
function parseDurationToSeconds(value) {
  if (!value) return 0;
  const str = String(value).trim();
  const dayMatch = str.match(/^(\d+)\s+days?,\s*(.*)$/);
  let days = 0;
  let rest = str;
  if (dayMatch) {
    days = parseInt(dayMatch[1], 10) || 0;
    rest = dayMatch[2];
  }
  const parts = rest.split(":").map((p) => parseFloat(p));
  let seconds = 0;
  if (parts.length === 3 && parts.every((p) => !Number.isNaN(p))) {
    seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
  } else if (parts.length === 2 && parts.every((p) => !Number.isNaN(p))) {
    seconds = parts[0] * 60 + parts[1];
  } else if (parts.length === 1 && !Number.isNaN(parts[0])) {
    seconds = parts[0];
  }
  return days * 86400 + seconds;
}

// Gemeinsamer Vergleicher für Anrufe UND Anrufbeantworter-Nachrichten (beide
// haben passende date/duration/name-Felder, siehe sensor.py:_call_to_dict/
// _message_to_dict) - eine Instanz reicht für beide Listen.
function compareEntriesBySort(a, b, sortBy) {
  switch (sortBy) {
    case "date_asc":
      return String(a.date || "").localeCompare(String(b.date || ""));
    case "duration_desc":
      return parseDurationToSeconds(b.duration) - parseDurationToSeconds(a.duration);
    case "duration_asc":
      return parseDurationToSeconds(a.duration) - parseDurationToSeconds(b.duration);
    case "name_asc":
      return String(a.name || a.number || "").localeCompare(String(b.name || b.number || ""), "de");
    case "name_desc":
      return String(b.name || b.number || "").localeCompare(String(a.name || a.number || ""), "de");
    case "date_desc":
    default:
      return String(b.date || "").localeCompare(String(a.date || ""));
  }
}

const LIVE_STATE_LABELS = {
  ringing: "Klingelt",
  dialing: "Wählen",
  talking: "Gespräch läuft",
};

// Allowlist, not a denylist: the banner must only ever appear for the three
// known "call in progress" states. A denylist of merely "known-inactive"
// values (idle/unavailable/unknown/"") looked equivalent at first glance,
// but silently broke down whenever entity_live pointed at the wrong entity
// (e.g. a *count* sensor such as the Anrufbeantworter-Sensor, whose native
// state is an integer like "10") - any value not on that denylist was
// treated as an active call and rendered verbatim as the banner text. With
// an allowlist, a misconfigured or unexpected state simply hides the
// banner instead of displaying garbage.
const LIVE_ACTIVE_STATES = new Set(Object.keys(LIVE_STATE_LABELS));

// "Weiterverarbeitung"-Zeile (seit v1.0.3, siehe Moduldoku oben): Zuordnung
// call.outcome (server-seitig berechnet, siehe call_log.py:_classify_call)
// -> Icon/Beschriftung/Farb-Kategorie/Ziel-Tab. "playable" statt "tab":
// Klick spielt die verlinkte Aufnahme direkt ab, statt nur den Tab zu
// wechseln - siehe _renderProcessingRow()/playCallRecording().
//
// "colorKind" (seit v1.0.4, statt einer festen Farbe direkt hier): verweist
// auf eine der drei benutzerdefinierbaren Farbgruppen aus PROCESSING_COLOR_VARS
// unten (success/error/playback) - siehe dort für die tatsächliche CSS-
// Custom-Property samt Standardwert, und den Editor-Bereich "Farben" für
// die Konfigurationsoberfläche.
const PROCESSING_META = {
  beantwortet: {
    icon: "mdi:phone-check",
    label: "Angenommen",
    colorKind: "success",
    tab: "eingehend",
  },
  verbunden: {
    icon: "mdi:phone-check",
    label: "Verbunden",
    colorKind: "success",
    tab: "ausgehend",
  },
  nicht_verbunden: {
    icon: "mdi:phone-remove",
    label: "Nicht verbunden",
    colorKind: "error",
    tab: "ausgehend",
  },
  nicht_erreicht: {
    icon: "mdi:phone-missed",
    label: "Nicht erreicht",
    colorKind: "error",
    tab: "verpasst",
  },
  // Ging zum Anrufbeantworter, aber es wurde keine Nachricht hinterlassen -
  // seit v1.0.3 getrennt von "nicht_erreicht" (siehe const.py:
  // CALL_OUTCOME_NO_VOICEMAIL), da der Anruf den Anrufbeantworter ja
  // tatsächlich erreicht hat, nur eben ohne Sprachnachricht - per Thorsten
  // war "Nicht erreicht" dafür irreführend.
  keine_nachricht: {
    icon: "mdi:phone-missed",
    label: "Keine Anrufbeantworter-Nachricht vorhanden",
    colorKind: "error",
    tab: "verpasst",
  },
  anrufbeantworter: {
    icon: "mdi:play-circle-outline",
    label: "Anrufbeantworter-Nachricht abspielen",
    colorKind: "playback",
    tab: "anrufbeantworter",
    playable: true,
  },
};

// --- Konfigurierbare Farben (seit v1.0.4) -----------------------------
//
// Jede Farbgruppe entspricht einer CSS-Custom-Property, die _colorVars()
// pro Karteninstanz auf Basis der Konfiguration (config-Schlüssel gleichen
// Namens) setzt - leer/nicht gesetzt lässt den bisherigen, festen
// Theme-Farbwert unverändert (siehe DEFAULT dort). PROCESSING_COLOR_VARS
// bildet den obigen "colorKind" auf die jeweilige CSS-Variable ab.
const COLOR_CONFIG_KEYS = {
  tab_active: { cssVar: "--fba-color-tab-active", fallback: "var(--primary-color, #03a9f4)" },
  success: { cssVar: "--fba-color-success", fallback: "var(--success-color, #4caf50)" },
  error: { cssVar: "--fba-color-error", fallback: "var(--error-color, #db4437)" },
  playback: { cssVar: "--fba-color-playback", fallback: "var(--primary-color, #03a9f4)" },
  vip: { cssVar: "--fba-color-vip", fallback: "var(--warning-color, #ff9800)" },
  row_icon: { cssVar: "--fba-color-row-icon", fallback: "var(--secondary-text-color, #727272)" },
  live_banner: {
    cssVar: "--fba-color-live-banner",
    fallback: "var(--state-icon-active-color, #03a9f4)",
  },
};

const PROCESSING_COLOR_VARS = {
  success: "var(--fba-color-success)",
  error: "var(--fba-color-error)",
  playback: "var(--fba-color-playback)",
};

// Kategorie-Tab-Icon-Farben (seit v1.0.4b1) - eine Farbe je Kategorie
// (Alle/Angenommen/Ausgehend/Verpasst/Anrufbeantworter), unabhängig vom
// Tab-Status. Anders als COLOR_CONFIG_KEYS oben (eine gemeinsame CSS-
// Custom-Property über :host für die ganze Karte) braucht jede Kategorie
// hier einen eigenen, unabhängigen Wert - die Farbe wird deshalb direkt als
// Inline-Style auf das jeweilige <ha-icon> geschrieben (siehe _renderTabs())
// statt über eine gemeinsame Property. Leer/ungesetzt = kein Inline-Style,
// d.h. das Icon folgt weiterhin wie bisher der Tab-Farbe (color_tab_active
// bei aktivem Tab, sonst die sekundäre Textfarbe).
//
// Seit v1.0.4 (final) gilt dieselbe Farbe auch für das Zeilen-Icon jedes
// Anrufs der jeweiligen Kategorie in der Liste (siehe
// FritzboxAnrufeCard._rowIconColor()/_renderRows()) - ändert man z. B. die
// Icon-Farbe von "Ausgehend", färben sich sowohl das Tab-Icon als auch alle
// Zeilen-Icons ausgehender Anrufe. Einzige Ausnahme: ist `color_row_icon`
// gesetzt (EINE Farbe für ALLE Zeilen-Icons, siehe COLOR_CONFIG_KEYS oben),
// gewinnt diese einheitliche Einstellung - per Thorstens Vorgabe.
const CATEGORY_ICON_COLOR_KEYS = {
  alle: "color_icon_alle",
  eingehend: "color_icon_eingehend",
  ausgehend: "color_icon_ausgehend",
  verpasst: "color_icon_verpasst",
  anrufbeantworter: "color_icon_anrufbeantworter",
};

// Defensive allowlist for user-supplied color values before they land
// inside a <style> block (via innerHTML, see _render()): permits hex
// codes, rgb()/rgba()/hsl()/hsla(), CSS variable references
// (var(--name, fallback)) and plain color-word characters, but rejects
// anything containing characters that could break out of the custom
// property declaration or the <style> tag itself (";", "{", "}", "<",
// ">", quotes, ...). An invalid value is treated the same as "not set"
// (falls back to the theme default) rather than raising an error, since
// this runs on every render.
const SAFE_COLOR_RE = /^[a-zA-Z0-9#(),.%\-\s]+$/;

function sanitizeColor(value) {
  const trimmed = String(value || "").trim();
  if (!trimmed) return "";
  if (!SAFE_COLOR_RE.test(trimmed)) {
    // eslint-disable-next-line no-console
    console.warn(
      "fritzbox_anrufe: ungültiger Farbwert ignoriert (nur Hex/rgb()/hsl()/var()/CSS-Farbnamen" +
        " erlaubt):",
      value
    );
    return "";
  }
  return trimmed;
}

const CONFIG_DEFAULTS = {
  title: "FRITZ!Box Anrufe",
  // Überschrift der Karte (ha-card-Header) anzeigen (seit v1.3.0b0). Standard
  // AN = bisheriges Verhalten. Bei false wird kein Header gerendert - hilfreich
  // z. B. in einem Bubble-Card-Popup, das ohnehin schon einen Titel hat.
  show_title: true,
  // Einstellungen-Kategorie/-Tab (Zahnrad, seit v1.3.0b0, EXPERIMENTELL) -
  // Standard AUS, zeigt seit v1.3.0b2 die Telefoniegeräte-Tabelle (Name/
  // Anschluss/ausgehende/ankommende/interne Nummer je Gerät, Detail-Popup,
  // Anrufbeantworter-Schalter), siehe _renderSettings()/_visibleFilterTypes().
  show_einstellungen: false,
  // Rückwärtskompatibel: ein explizit gesetzter Einstellungen-Sensor wird
  // weiterhin bevorzugt (siehe _settingsEntityId()); ein Editor-Picker dafür
  // existiert seit v1.3.0b2 aber nicht mehr - der Sensor wird automatisch
  // gefunden.
  entity_settings: "",
  max_rows: 10,
  // Kategorien/Tabs (Alle/Gesamt, Angenommen, Ausgehend, Verpasst,
  // Anrufbeantworter) einzeln ein-/ausblendbar. show_anrufbeantworter
  // wirkt zusätzlich zur Voraussetzung, dass entity_voicemail gesetzt ist -
  // siehe _visibleFilterTypes().
  show_alle: true,
  show_eingehend: true,
  show_ausgehend: true,
  show_verpasst: true,
  show_anrufbeantworter: true,
  // Spalten der Anrufliste einzeln ein-/ausblendbar.
  show_name: true,
  show_number: true,
  show_own_number: false,
  show_device: true,
  show_duration: true,
  show_date: true,
  show_vip: true,
  // "Weiterverarbeitung"-Zeile je Kategorie einzeln ein-/ausblendbar -
  // standardmäßig aus, damit bestehende Dashboards nach einem Update
  // optisch unverändert bleiben (siehe Moduldoku oben).
  show_processing_alle: false,
  show_processing_eingehend: false,
  show_processing_ausgehend: false,
  show_processing_verpasst: false,
  // Filter-/Sortierleiste (seit v1.0.4b3) - standardmäßig aus, aus demselben
  // Grund wie show_processing_*: bestehende Dashboards sollen nach einem
  // Update optisch unverändert bleiben. Bewusst nur der SICHTBARE Regler;
  // solange dieser aus ist, bleibt auch die Reihenfolge/Filterung exakt wie
  // zuvor (siehe FritzboxAnrufeCard._visibleCalls()).
  show_filter_bar: false,
  // Papierkorb-Button je Anrufbeantworter-Nachricht (seit v1.0.5b3,
  // EXPERIMENTELL, siehe Moduldoku oben) - standardmäßig aus: Löschen ist
  // unwiderruflich (die FRITZ!Box selbst hat keinen Papierkorb dafür), das
  // soll niemand versehentlich freigeschaltet bekommen.
  show_delete_button: false,
  // Spam-Anrufe/-Nachrichten ausblenden (seit v1.0.6b1) - siehe spam.py in
  // der Integration für die Definition von "Spam" (Kombination aus FRITZ!Box-
  // eigener Sperrliste und einer vom Nutzer gepflegten Nummernliste).
  // Standardmäßig aus, damit bestehende Dashboards nach einem Update
  // optisch unverändert bleiben, exakt wie die anderen show_*-Schalter.
  hide_spam: false,
  // Zweiter Anrufbeantworter in derselben Karte (seit v1.0.6b1 gibt es
  // dafür bereits einen eigenen Sensor, seit v1.0.6b2 kann diese Karte ihn
  // direkt mit anzeigen statt nur über eine zweite Karteninstanz) - siehe
  // Moduldoku oben. Leer = kein zweiter Anrufbeantworter, exakt das
  // bisherige Verhalten.
  entity_voicemail_2: "",
  // Dritter bis fünfter Anrufbeantworter (seit v1.2.0) - analog zu
  // entity_voicemail_2 oben, dieselbe TAM_SLOTS-Behandlung (siehe
  // FritzboxAnrufeCard._activeTamSlots()). Die Integration selbst legt seit
  // v1.1.1 für jeden konfigurierten Anrufbeantworter (bis zu 5, siehe
  // const.py:MAX_TAM_COUNT) einen eigenen Sensor an - diese Karte konnte
  // davon bislang aber nur die ersten beiden direkt anzeigen, für Slot 3-5
  // war bis v1.1.1 stets eine eigene, zusätzliche Karteninstanz nötig (siehe
  // README "Bekannte Einschränkungen"). Leer = dieser Slot bleibt
  // unberücksichtigt, exakt wie bei entity_voicemail_2.
  entity_voicemail_3: "",
  entity_voicemail_4: "",
  entity_voicemail_5: "",
  // "merged" (Standard, nur bei GENAU zwei konfigurierten Anrufbeantwortern
  // wählbar) mischt beide Nachrichtenlisten chronologisch mit "AB 1"/"AB
  // 2"-Badge, "separate" zeigt getrennte Abschnitte untereinander,
  // "accordion" (seit v1.2.0) zeigt stattdessen je Anrufbeantworter einen
  // auf-/zuklappbaren Abschnitt - siehe Moduldoku oben und
  // FritzboxAnrufeCard._voicemailDisplayMode(). Sobald mehr als zwei
  // Anrufbeantworter konfiguriert sind, erzwingt die Karte "accordion"
  // unabhängig vom hier gespeicherten Wert, da "merged"/"separate" nur für
  // exakt zwei Listen definiert sind. Ohne mindestens entity_voicemail_2
  // ohne jede Wirkung.
  voicemail_2_mode: "merged",
  // Anrufbeantworter Ein/Aus-Schalter (seit v1.1.0, EXPERIMENTELL - siehe
  // switch.py in der Integration). entity_tam_switch/entity_tam_switch_2/
  // _3/_4/_5 sind eigene Entity-Picker (switch-Domäne) - bewusst NICHT aus
  // entity_voicemail/entity_voicemail_2/_3/_4/_5 abgeleitet, da Home
  // Assistant für sprachabhängig benannte Entitäten keinen zuverlässigen
  // Mechanismus bietet, den zugehörigen Schalter-entity_id algorithmisch zu
  // bestimmen. entity_tam_switch_N (N>1) wirkt jeweils nur zusätzlich zu
  // einem gesetzten entity_voicemail_N (siehe _renderTamSwitches()).
  // show_tam_switch ist der sichtbare Regler dafür (Standard AUS, exakt wie
  // show_filter_bar/show_delete_button/hide_spam oben, damit bestehende
  // Dashboards nach einem Update optisch unverändert bleiben).
  entity_tam_switch: "",
  entity_tam_switch_2: "",
  entity_tam_switch_3: "",
  entity_tam_switch_4: "",
  entity_tam_switch_5: "",
  show_tam_switch: false,
  // Welche konfigurierten Anrufbeantworter standardmäßig einbezogen werden
  // (seit v1.2.0) - Standard AN für alle 5, damit bestehende Dashboards nach
  // einem Update unverändert bleiben (jeder konfigurierte entity_voicemail_N
  // erscheint weiterhin wie bisher). Wirkt nur zusätzlich zu einem
  // tatsächlich gesetzten entity_voicemail_N - Slots ohne konfigurierten
  // Sensor bleiben ohnehin unberücksichtigt (siehe _activeTamSlots()). Ab
  // zwei konfigurierten Anrufbeantwortern kann diese Auswahl zusätzlich
  // direkt auf der Karte über Checkboxen temporär angepasst werden (reiner
  // UI-Laufzeitstatus, siehe FritzboxAnrufeCard._tamPickerVisible/
  // _renderTamPicker()) - dieser Wert hier ist nur der beim Laden der Karte
  // wiederhergestellte, dauerhaft gespeicherte Grundzustand dafür.
  show_voicemail_1: true,
  show_voicemail_2: true,
  show_voicemail_3: true,
  show_voicemail_4: true,
  show_voicemail_5: true,
  // Farben (seit v1.0.4) - leer = bisheriger, fester Theme-Farbwert (siehe
  // COLOR_CONFIG_KEYS oben für die jeweiligen Standardwerte).
  color_tab_active: "",
  color_success: "",
  color_error: "",
  color_playback: "",
  color_vip: "",
  color_row_icon: "",
  color_live_banner: "",
  // Kategorie-Tab-Icon-Farben (seit v1.0.4b1) - siehe CATEGORY_ICON_COLOR_KEYS
  // oben. Leer = Icon folgt weiterhin der Tab-Farbe (aktiv/inaktiv).
  color_icon_alle: "",
  color_icon_eingehend: "",
  color_icon_ausgehend: "",
  color_icon_verpasst: "",
  color_icon_anrufbeantworter: "",
};

function withDefaults(config) {
  return { ...CONFIG_DEFAULTS, ...(config || {}) };
}

function escapeHtml(value) {
  return String(value === undefined || value === null ? "" : value).replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[c])
  );
}

function formatDateTime(iso) {
  if (!iso) return "";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// --- Anrufbeantworter row markup / styles -----------------------------------

function renderVoicemailRows(messages, opts) {
  const options = {
    showNumber: true,
    showDate: true,
    showDuration: true,
    maxRows: Infinity,
    // Papierkorb-Button (seit v1.0.5b3, EXPERIMENTELL) - siehe Moduldoku
    // oben. showDeleteButton gated durch die Kartenkonfiguration
    // (show_delete_button); confirmDeleteId ist reiner UI-Laufzeitstatus
    // (welche Nachricht gerade die "Wirklich löschen?"-Bestätigung zeigt) -
    // siehe FritzboxAnrufeCard._confirmDeleteMessageId.
    showDeleteButton: false,
    confirmDeleteId: null,
    // Zweiter Anrufbeantworter, "merged"-Modus (seit v1.0.6b2, siehe
    // Moduldoku oben) - zeigt bei gesetztem msg._tam ein kleines "AB
    // 1"/"AB 2"-Badge. Ungenutzt (und ohne jede Auswirkung), solange
    // entity_voicemail_2 nicht konfiguriert ist.
    showTamLabel: false,
    ...(opts || {}),
  };
  const list = (messages || []).slice(0, options.maxRows);

  if (!list.length) {
    return `<div class="empty">Keine Nachrichten vorhanden.</div>`;
  }

  return `
    <div class="voicemail-rows">
      ${list
        .map((msg) => {
          // Zusammengesetzter Schlüssel (seit v1.0.6b2, siehe
          // FritzboxAnrufeCard._voicemailsFor()) statt der rohen `id` -
          // eindeutig auch bei kollidierenden IDs zwischen zwei
          // Anrufbeantwortern, und (Nebeneffekt) garantiert nicht-leer, auch
          // bei Index 0 (siehe Moduldoku oben).
          const key = msg._key !== undefined ? msg._key : msg.id;
          const confirming = options.showDeleteButton && key !== undefined && key !== null && options.confirmDeleteId === key;
          return `
        <div class="voicemail-row ${msg.new ? "unread" : ""}">
          <div class="voicemail-main">
            <div class="voicemail-primary">
              <span class="voicemail-name">${escapeHtml(msg.name || msg.number || "Unbekannt")}</span>
              ${options.showTamLabel && msg._tam ? `<span class="voicemail-badge tam-badge">AB ${escapeHtml(msg._tam)}</span>` : ""}
              ${msg.new ? '<span class="voicemail-badge">neu</span>' : ""}
              ${msg.spam ? '<span class="voicemail-badge spam-badge">Spam</span>' : ""}
            </div>
            <div class="voicemail-secondary">
              ${options.showNumber ? `<span>${escapeHtml(msg.number || "")}</span>` : ""}
              ${options.showDate ? `<span>${formatDateTime(msg.date)}</span>` : ""}
              ${options.showDuration && msg.duration ? `<span>${escapeHtml(msg.duration)}</span>` : ""}
            </div>
          </div>
          <div class="voicemail-actions">
            ${
              msg.media_url
                ? `<div class="voicemail-player-slot" data-media-url="${escapeHtml(msg.media_url)}">
                     <button class="voicemail-play-btn" type="button">
                       <ha-icon icon="mdi:play-circle-outline"></ha-icon>
                       <span>Abspielen</span>
                     </button>
                   </div>`
                : `<span class="voicemail-no-audio">Kein Wiedergabelink</span>`
            }
            ${
              options.showDeleteButton && key !== undefined && key !== null
                ? confirming
                  ? `<div class="voicemail-delete-confirm" data-key="${escapeHtml(key)}" data-message-id="${escapeHtml(msg.id)}" data-entity-id="${escapeHtml(msg._entityId || "")}">
                       <span>Wirklich löschen?</span>
                       <button class="voicemail-delete-confirm-yes" type="button" title="Löschen bestätigen">
                         <ha-icon icon="mdi:check"></ha-icon>
                       </button>
                       <button class="voicemail-delete-confirm-no" type="button" title="Abbrechen">
                         <ha-icon icon="mdi:close"></ha-icon>
                       </button>
                     </div>`
                  : `<button class="voicemail-delete-btn" type="button" data-key="${escapeHtml(key)}" title="Nachricht löschen">
                       <ha-icon icon="mdi:trash-can-outline"></ha-icon>
                     </button>`
                : ""
            }
          </div>
        </div>
      `;
        })
        .join("")}
    </div>
  `;
}

const BASE_CARD_STYLES = `
  ha-card { overflow: hidden; }
  /* container-type/-name (seit v1.0.4): lässt die Tab-Leiste unten auf die
     tatsächliche Breite DIESER KARTE reagieren statt auf die Browser-
     Fensterbreite (siehe TABS_CONTAINER_QUERY_STYLES unten für den Grund -
     das bestehende @media-Breakpoint für Smartphones griff auf einer
     schmalen Desktop-Dashboard-Spalte nie, weil der Browser selbst breit
     genug war). Modernes CSS-Feature (Container Queries) - falls der
     Browser es nicht unterstützt, greift ersatzweise nur die
     min-width/ellipsis-Absicherung direkt an .tab/.tab span, die
     Kategorie-Leiste läuft dann nie in einen Scrollbalken, kann aber
     Beschriftungen abschneiden statt komplett auf Icons umzuschalten. */
  .card-content { padding: 8px 16px 16px; container-type: inline-size; container-name: fba; }
  .empty {
    padding: 24px 0;
    text-align: center;
    color: var(--secondary-text-color, #727272);
  }
  /* Einstellungen-Ansicht (Zahnrad-Tab, seit v1.3.0b0) */
  .settings-view { display: flex; flex-direction: column; gap: 14px; }
  .settings-experimental {
    font-size: 0.8em;
    color: var(--secondary-text-color, #727272);
    font-style: italic;
  }
  .settings-section-title {
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--primary-text-color, #212121);
  }
  .settings-list { display: flex; flex-direction: column; }
  .settings-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
  }
  .settings-row:last-child { border-bottom: none; }
  .settings-row-icon { color: var(--state-icon-color, var(--secondary-text-color, #727272)); }
  .settings-row-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .settings-row-meta { color: var(--secondary-text-color, #727272); font-size: 0.9em; }
  .settings-more { padding: 6px 0; color: var(--secondary-text-color, #727272); font-size: 0.9em; }
  .settings-note {
    margin-top: 8px;
    font-size: 0.82em;
    color: var(--secondary-text-color, #727272);
  }
  /* Telefoniegeräte-Tabelle (seit v1.3.0b2) */
  .settings-table { display: flex; flex-direction: column; overflow-x: auto; }
  .settings-table-head,
  .settings-table-row {
    display: grid;
    grid-template-columns: minmax(120px, 1.6fr) minmax(72px, 0.9fr) minmax(70px, 1fr) minmax(70px, 1fr) minmax(74px, 1fr);
    gap: 8px;
    align-items: center;
    padding: 7px 4px;
    min-width: 460px;
  }
  .settings-table-head {
    font-size: 0.78em;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    color: var(--secondary-text-color, #727272);
    border-bottom: 2px solid var(--divider-color, #e0e0e0);
  }
  .settings-table-row { border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .settings-table-row:last-child { border-bottom: none; }
  .settings-table-row.clickable { cursor: pointer; }
  .settings-table-row.clickable:hover { background: var(--secondary-background-color, rgba(0,0,0,0.04)); }
  .settings-table .col-name { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .settings-table .settings-device-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .settings-table .col-num { font-variant-numeric: tabular-nums; font-size: 0.92em; }
  .settings-table .col-intern { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
  .device-tam-toggle {
    display: inline-flex;
    align-items: center;
    border: none;
    background: transparent;
    cursor: pointer;
    padding: 0;
    color: var(--secondary-text-color, #727272);
    --mdc-icon-size: 22px;
  }
  .device-tam-toggle.on { color: var(--fba-color-answered, var(--success-color, #43a047)); }
  .device-tam-toggle[disabled] { opacity: 0.4; cursor: default; }
  /* Detail-Popup (seit v1.3.0b2) */
  .settings-popup-backdrop {
    position: fixed;
    inset: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    background: rgba(0, 0, 0, 0.45);
  }
  .settings-popup {
    background: var(--card-background-color, var(--ha-card-background, #fff));
    color: var(--primary-text-color, #212121);
    border-radius: var(--ha-card-border-radius, 12px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    width: min(360px, 100%);
    max-height: 80vh;
    overflow-y: auto;
  }
  .settings-popup-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 14px;
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
  }
  .settings-popup-title { flex: 1; font-weight: 600; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
  .settings-popup-close {
    border: none;
    background: transparent;
    cursor: pointer;
    color: var(--secondary-text-color, #727272);
    padding: 2px;
    display: inline-flex;
  }
  .settings-popup-body { padding: 6px 14px 14px; }
  .settings-popup-line {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
  }
  .settings-popup-line:last-child { border-bottom: none; }
  .settings-popup-label { color: var(--secondary-text-color, #727272); }
  .settings-popup-value { font-weight: 500; text-align: right; word-break: break-word; }
`;

// Schwelle empirisch ermittelt (siehe PR-Beschreibung/Commit): bei den fünf
// Tabs "Alle"/"Angenommen"/"Ausgehend"/"Verpasst"/"Anrufbeantworter" passt
// der volle Text ab ca. 488px Innenbreite der Karte ohne jede Kürzung -
// darunter wird auf reine Icons umgeschaltet (mit Tooltip via title="...",
// siehe _renderTabs()), statt Labels hässlich mitten im Wort abzuschneiden.
const TABS_CONTAINER_QUERY_STYLES = `
  @container fba (max-width: 480px) {
    .tab span { display: none; }
    .tab ha-icon { --mdc-icon-size: 22px; }
  }
`;

const VOICEMAIL_ROWS_STYLES = `
  .voicemail-rows { display: flex; flex-direction: column; gap: 10px; }
  .voicemail-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px;
    border-radius: 8px;
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
  }
  .voicemail-row.unread { border-left: 3px solid var(--fba-color-playback); }
  .voicemail-main { display: flex; flex-direction: column; gap: 2px; }
  .voicemail-primary { display: flex; align-items: center; gap: 6px; }
  .voicemail-name { font-weight: 500; }
  .voicemail-badge {
    font-size: 0.7em;
    text-transform: uppercase;
    background: var(--fba-color-playback);
    color: var(--text-primary-color, #fff);
    border-radius: 4px;
    padding: 1px 6px;
  }
  /* Spam-Badge (seit v1.0.6b1) - eigene Farbe (Fehler-/Warnfarbe), damit sie
     sich von der "neu"-Markierung (.voicemail-badge, Playback-Farbe) und dem
     entsprechenden Anruf-Badge unten (.spam-badge) unterscheidet. */
  .voicemail-badge.spam-badge,
  .row-badge.spam-badge {
    background: var(--fba-color-error);
  }
  /* "AB 1"/"AB 2"-Badge (seit v1.0.6b2, nur im "merged"-Modus des zweiten
     Anrufbeantworters) - bewusst neutral/unauffällig (Sekundärfarben statt
     einer der bestehenden Akzentfarben), da es sich um reine
     Herkunftsinformation handelt, nicht um einen Status wie "neu"/"Spam". */
  .voicemail-badge.tam-badge {
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.12));
    color: var(--primary-text-color, #212121);
  }
  /* Getrennte Abschnitte (seit v1.0.6b2, "separate"-Modus des zweiten
     Anrufbeantworters) - siehe FritzboxAnrufeCard._renderVoicemailRows(). */
  .voicemail-section:not(:last-child) { margin-bottom: 18px; }
  .voicemail-section-title {
    font-weight: 600;
    font-size: 0.8em;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    color: var(--secondary-text-color, #727272);
    margin-bottom: 8px;
  }
  /* Akkordeon-Darstellung mehrerer Anrufbeantworter (seit v1.2.0, "accordion"-
     Modus, ab drei Anrufbeantwortern erzwungen) - siehe Moduldoku oben und
     FritzboxAnrufeCard._renderVoicemailAccordion(). Bewusst derselbe
     natives-<details>-plus-eigener-Chevron-Aufbau wie die Farben-Abschnitte
     im Karten-EDITOR (.fba-color-editor, siehe dort für die ausführliche
     Begründung je Detail) - hier als eigener Klassensatz, da diese Regeln in
     der eigentlichen KARTE (nicht im Editor) gelten und unabhängig von
     dessen Aufbau bestehen bleiben sollen. */
  .voicemail-accordion-section:not(:last-child) { margin-bottom: 8px; }
  .voicemail-accordion-section {
    border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    border-radius: 8px;
    padding: 0 12px;
  }
  .voicemail-accordion-summary {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 0;
    cursor: pointer;
    font-weight: 500;
    color: var(--primary-text-color, #212121);
    list-style: none;
  }
  .voicemail-accordion-summary::-webkit-details-marker { display: none; }
  .voicemail-accordion-summary::marker { display: none; }
  .voicemail-accordion-title { flex: 1 1 auto; }
  .voicemail-accordion-count {
    font-size: 0.8em;
    color: var(--secondary-text-color, #727272);
  }
  .voicemail-accordion-chevron {
    --mdc-icon-size: 20px;
    color: var(--secondary-text-color, #727272);
    transition: transform 0.2s ease;
  }
  .voicemail-accordion-section[open] > .voicemail-accordion-summary .voicemail-accordion-chevron {
    transform: rotate(180deg);
  }
  .voicemail-accordion-body { padding: 0 0 12px; }
  .row-badge {
    font-size: 0.7em;
    text-transform: uppercase;
    color: var(--text-primary-color, #fff);
    border-radius: 4px;
    padding: 1px 6px;
  }
  .voicemail-secondary {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 0.8em;
    color: var(--secondary-text-color, #727272);
  }
  /* .voicemail-player-slot sitzt (wegen des Papierkorb-Buttons daneben,
     siehe .voicemail-actions unten) in einem Flex-Container. Ohne eigene
     Breitenangabe würde ein Flex-Item nur eine "auto"-Breite basierend auf
     seinem Inhalt bekommen - und ein prozentual breites Ersatzelement (das
     audio-Element mit width:100% unten, sobald Wiedergabe startet) trägt zu
     dieser Inhaltsgröße NICHT bei (Prozentwerte zählen dafür als 0). Ohne
     flex: 1 1 auto; min-width: 0; würden sowohl der Slot als auch das
     audio-Element auf Breite 0 kollabieren - technisch vorhanden und
     (dank autoplay) hörbar spielend, aber unsichtbar. Deshalb von Anfang an
     hier festgelegt, nicht erst nachträglich als Bugfix.
     .row-processing-player (Weiterverarbeitungs-Zeile) hat bewusst keine
     eigene width:100%-Regel und ist von diesem Effekt nicht betroffen. */
  .voicemail-player-slot { flex: 1 1 auto; min-width: 0; }
  .voicemail-player { width: 100%; height: 32px; }
  /* Live-AB-Regler (seit v1.2.0, ab 2 konfigurierten Anrufbeantwortern) -
     steht nach den Ein/Aus-Schaltern (falls aktiv) und vor der eigentlichen
     Nachrichten-Auflistung, siehe _renderTamPicker(). */
  .voicemail-tam-picker {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 12px;
  }
  .voicemail-tam-picker-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    border-radius: 999px;
    padding: 3px 10px 3px 8px;
    font-size: 0.85em;
    color: var(--secondary-text-color, #727272);
    cursor: pointer;
    user-select: none;
  }
  .voicemail-tam-picker-chip.checked {
    border-color: var(--fba-color-playback);
    color: var(--primary-text-color, #212121);
  }
  .voicemail-tam-picker-chip input[type="checkbox"] {
    margin: 0;
    accent-color: var(--fba-color-playback);
  }
  /* Anrufbeantworter Ein/Aus-Schalter (seit v1.1.0, EXPERIMENTELL, nur bei
     show_tam_switch) - steht vor der Nachrichten-Auflistung, siehe
     _renderTamSwitches(). */
  .tam-switch-block {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
  }
  .tam-switch-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .tam-switch-icon { color: var(--fba-color-row-icon); }
  .tam-switch-label { flex: 1 1 auto; }
  .tam-switch-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.08));
    color: var(--primary-text-color, #212121);
    font: inherit;
    font-size: 0.85em;
    cursor: pointer;
  }
  .tam-switch-toggle.on {
    background: var(--fba-color-success);
    color: var(--text-primary-color, #fff);
  }
  .tam-switch-toggle:disabled { opacity: 0.6; cursor: default; }
  .tam-switch-toggle ha-icon { --mdc-icon-size: 18px; }
  .voicemail-play-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    background: var(--fba-color-playback);
    color: var(--text-primary-color, #fff);
    font: inherit;
    font-size: 0.85em;
    cursor: pointer;
  }
  .voicemail-play-btn:disabled { opacity: 0.6; cursor: default; }
  .voicemail-play-btn ha-icon { --mdc-icon-size: 18px; }
  .voicemail-no-audio {
    font-size: 0.8em;
    color: var(--secondary-text-color, #727272);
    font-style: italic;
  }
  /* Papierkorb-Button + Inline-Bestätigung (seit v1.0.5b3, EXPERIMENTELL,
     nur bei show_delete_button) - bewusst KEIN natives confirm(), da sich
     solche Dialoge in der Companion-App-WebView erfahrungsgemäß nicht immer
     zuverlässig verhalten. */
  .voicemail-actions { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
  .voicemail-delete-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: none;
    color: var(--fba-color-error);
    cursor: pointer;
    padding: 4px;
    border-radius: 6px;
  }
  .voicemail-delete-btn:hover { background: var(--secondary-background-color, rgba(0, 0, 0, 0.08)); }
  .voicemail-delete-btn ha-icon { --mdc-icon-size: 18px; }
  .voicemail-delete-confirm {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8em;
    color: var(--secondary-text-color, #727272);
  }
  .voicemail-delete-confirm-yes,
  .voicemail-delete-confirm-no {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: 6px;
    padding: 3px;
    cursor: pointer;
  }
  .voicemail-delete-confirm-yes { background: var(--fba-color-error); color: var(--text-primary-color, #fff); }
  .voicemail-delete-confirm-no {
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.1));
    color: var(--primary-text-color, #212121);
  }
  .voicemail-delete-confirm-yes ha-icon,
  .voicemail-delete-confirm-no ha-icon { --mdc-icon-size: 16px; }
`;

// --- "Weiterverarbeitung"-Zeile (seit v1.0.3) --------------------------
const PROCESSING_ROW_STYLES = `
  .row-processing {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 2px 0 6px 30px;
    padding: 2px 8px;
    font-size: 0.8em;
    color: var(--secondary-text-color, #727272);
  }
  .row-processing.clickable {
    cursor: pointer;
    border-radius: 6px;
  }
  .row-processing.clickable:hover {
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
  }
  .row-processing-arrow { opacity: 0.6; }
  .row-processing ha-icon { --mdc-icon-size: 18px; }
  .row-processing-player { height: 28px; }
`;

/**
 * Download one message's audio via the authenticated fetch API exposed to
 * custom cards (hass.fetchWithAuth), turn it into a blob object URL, and
 * swap the "Abspielen" button for a real, playable <audio> element.
 *
 * `onEnded` (seit dem auto_mark_read-Re-Render-Bugfix, siehe
 * FritzboxAnrufeCard._hasActiveMediaPlayback()/_catchUpRender()): wird beim
 * natürlichen Ende der Wiedergabe aufgerufen, damit die Karte einen
 * inzwischen fälligen, aber wegen der laufenden Wiedergabe zurückgehaltenen
 * Re-Render jetzt nachholen kann (z. B. um den "Neu"-Status zu aktualisieren).
 */
async function playVoicemail(hass, button, onObjectUrlCreated, onEnded) {
  const slot = button.closest(".voicemail-player-slot");
  const mediaUrl = slot && slot.dataset.mediaUrl;
  if (!mediaUrl || !hass || !hass.fetchWithAuth) return;

  button.disabled = true;
  button.innerHTML = `<ha-icon icon="mdi:loading"></ha-icon><span>Lädt …</span>`;

  try {
    const response = await hass.fetchWithAuth(mediaUrl);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    if (onObjectUrlCreated) onObjectUrlCreated(objectUrl);

    const audio = document.createElement("audio");
    audio.controls = true;
    audio.autoplay = true;
    audio.className = "voicemail-player";
    audio.src = objectUrl;
    if (onEnded) audio.addEventListener("ended", () => onEnded());
    slot.replaceChildren(audio);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("fritzbox_anrufe: Anrufbeantworter-Wiedergabe fehlgeschlagen", err);
    button.disabled = false;
    button.innerHTML = `<ha-icon icon="mdi:alert-circle-outline"></ha-icon><span>Fehler – erneut versuchen</span>`;
    if (onEnded) onEnded();
  }
}

/**
 * Same idea as playVoicemail() above, but for a "Weiterverarbeitung" row
 * (see PROCESSING_META) linked from a call-list entry rather than the
 * Anrufbeantworter tab's own message list - reuses the identical
 * hass.fetchWithAuth()-to-blob-object-URL approach, just swapping the
 * *whole* row's content (arrow+icon+label) for the <audio> element instead
 * of a dedicated player slot next to a button. `onEnded`: siehe
 * playVoicemail() oben.
 */
async function playCallRecording(hass, rowEl, onObjectUrlCreated, onEnded) {
  const mediaUrl = rowEl.dataset.mediaUrl;
  if (!mediaUrl || !hass || !hass.fetchWithAuth) return;

  rowEl.classList.remove("clickable");
  rowEl.innerHTML = `<ha-icon icon="mdi:loading"></ha-icon><span>Lädt …</span>`;

  try {
    const response = await hass.fetchWithAuth(mediaUrl);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    if (onObjectUrlCreated) onObjectUrlCreated(objectUrl);

    const audio = document.createElement("audio");
    audio.controls = true;
    audio.autoplay = true;
    audio.className = "row-processing-player";
    audio.src = objectUrl;
    if (onEnded) audio.addEventListener("ended", () => onEnded());
    rowEl.replaceChildren(audio);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("fritzbox_anrufe: Wiedergabe über die Weiterverarbeitungs-Zeile fehlgeschlagen", err);
    rowEl.classList.add("clickable");
    rowEl.innerHTML = `<ha-icon icon="mdi:alert-circle-outline"></ha-icon><span>Fehler – erneut versuchen</span>`;
    if (onEnded) onEnded();
  }
}

// -----------------------------------------------------------------------
// fritzbox-anrufe-card
// -----------------------------------------------------------------------

class FritzboxAnrufeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._activeFilter = FILTER_ALL;
    // Filter-/Sortierleiste (seit v1.0.4b3, siehe Moduldoku oben) - reines
    // UI-Laufzeitstatus, nicht Teil der Kartenkonfiguration, genau wie
    // _activeFilter oben: geht bei jedem Neuladen bzw. jeder Config-Änderung
    // verloren (siehe setConfig()).
    this._filterOwnNumber = "";
    this._sortBy = DEFAULT_SORT;
    // Papierkorb-Bestätigung (seit v1.0.5b3, EXPERIMENTELL) - reiner
    // UI-Laufzeitstatus, genau wie _activeFilter/_filterOwnNumber/_sortBy:
    // welche Nachrichten-ID gerade die "Wirklich löschen?"-Bestätigung
    // zeigt, und welche IDs optimistisch (vor der Coordinator-Bestätigung)
    // bereits ausgeblendet sind - siehe _deleteVoicemailMessage().
    this._confirmDeleteMessageId = null;
    this._pendingDeletedMessageIds = new Set();
    // Akkordeon-Auf-/Zuklapp-Status je Anrufbeantworter-Slot (seit v1.2.0,
    // siehe _renderVoicemailAccordion()) - reiner UI-Laufzeitstatus, genau
    // wie die übrigen Felder hier: geht bei jedem Neuladen bzw. jeder
    // Config-Änderung verloren (siehe setConfig()). Objekt bleibt leer, bis
    // ein Slot zum ersten Mal gerendert wird - erst dann wird der
    // Startzustand einmalig festgelegt (siehe dortiger Kommentar).
    this._tamAccordionOpen = {};
    // Live-AB-Regler (seit v1.2.0, siehe _renderTamPicker()) - ebenfalls
    // reiner UI-Laufzeitstatus, wird in setConfig() aus dem dauerhaft
    // gespeicherten Grundzustand (show_voicemail_1-5) neu befüllt.
    this._tamPickerVisible = {};
    // Welche Telefoniegeräte-Zeile gerade ihr Detail-Popup zeigt (Einstellungen-
    // Tab, seit v1.3.0b2) - reiner UI-Laufzeitstatus, null = kein Popup offen.
    this._settingsPopupIndex = null;
    this._hass = null;
    this._config = null;
    this._objectUrls = [];
    this._lastSignature = null;
  }

  setConfig(config) {
    if (!config) {
      throw new Error("fritzbox-anrufe-card: Konfiguration fehlt.");
    }
    if (!config.entity_eingehend || !config.entity_ausgehend || !config.entity_verpasst) {
      throw new Error(
        "fritzbox-anrufe-card: entity_eingehend, entity_ausgehend und entity_verpasst sind erforderlich."
      );
    }
    this._config = withDefaults(config);
    this._activeFilter = this._defaultFilter();
    this._filterOwnNumber = "";
    this._sortBy = DEFAULT_SORT;
    this._confirmDeleteMessageId = null;
    this._pendingDeletedMessageIds = new Set();
    this._tamAccordionOpen = {};
    // Grundzustand für den Live-Regler aus der dauerhaft gespeicherten
    // Konfiguration übernehmen (siehe CONFIG_DEFAULTS/_renderTamPicker()) -
    // JEDE Config-Änderung (auch nur ein einzelnes anderes Feld) setzt einen
    // zuvor per Klick temporär geänderten Regler-Zustand wieder auf diesen
    // Grundzustand zurück, exakt wie bei den übrigen UI-Laufzeitstatus-
    // Feldern hier.
    this._tamPickerVisible = {};
    for (let n = 1; n <= MAX_TAM_SLOTS; n += 1) {
      this._tamPickerVisible[n] = this._config[`show_voicemail_${n}`] !== false;
    }
    this._settingsPopupIndex = null;
    this._lastSignature = null;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    // Lovelace pushes a new `hass` object on *every* state change anywhere
    // in Home Assistant, not just for this card's own entities. Rebuilding
    // the whole DOM on each of those would kill any Anrufbeantworter
    // playback in progress, so only actually re-render when something this
    // card cares about (its own entities, or the active tab) changed.
    const signature = this._computeSignature();
    if (signature === this._lastSignature && this.shadowRoot.firstChild) {
      return;
    }
    // Bugfix (seit v1.0.5b4, `auto_mark_read`): der Options-Flow-Schalter
    // löst NACH JEDER Wiedergabe absichtlich eine Coordinator-Aktualisierung
    // aus, um den "Neu"-Status zeitnah zu löschen (siehe voicemail.py:
    // maybe_auto_mark_read()). Genau das ändert aber `entity_voicemail`s
    // `last_updated` - also die Signatur oben - und würde damit ohne diesen
    // Schutz exakt den einen Playback-Vorgang zerstören, den es gerade selbst
    // ausgelöst hat: ein vollständiger Re-Render tauscht die gesamte
    // Kartenoberfläche aus (siehe _render()/_revokeObjectUrls()), das
    // laufende <audio>-Element wird dabei aus dem sichtbaren DOM entfernt
    // (spielt technisch weiter, aber ohne jede sichtbare Bedienleiste) bzw.
    // - falls der Refresh noch VOR dem Laden der Aufnahme eintrifft - der
    // "Lädt …"-Button wird zurückgesetzt, während der ursprüngliche Klick-
    // Handler noch auf das inzwischen losgelöste alte DOM-Element zeigt,
    // sodass die fertige Aufnahme dort landet, wo sie niemand mehr sieht.
    // Reproduzierbar bei JEDER Wiedergabe im Anrufbeantworter-Tab, sobald
    // `auto_mark_read` aktiv ist (dort ist `message.Index` immer bekannt,
    // der Refresh also garantiert) - über die Weiterverarbeitungs-Zeile nur,
    // wenn der Anruf zusätzlich eindeutig einer Anrufbeantworter-Nachricht
    // zugeordnet werden konnte. Fix: einen laufenden oder gerade erst
    // gestarteten Wiedergabevorgang erkennen und den Re-Render in diesem
    // Fall verschieben, statt die Karte trotzdem neu aufzubauen - bewusst
    // OHNE `_lastSignature` zu aktualisieren, damit der nächste reguläre
    // hass-Push (der ohnehin bald eintrifft) die inzwischen verpasste
    // Aktualisierung (z. B. den verschwundenen "Neu"-Status) sauber
    // nachholt, sobald die Wiedergabe nicht mehr aktiv ist.
    if (this._hasActiveMediaPlayback()) {
      return;
    }
    this._lastSignature = signature;
    this._render();
  }

  // Erkennt eine laufende ODER gerade erst angestoßene (noch ladende)
  // Wiedergabe, sowohl im Anrufbeantworter-Tab (.voicemail-player-slot) als
  // auch in der Weiterverarbeitungs-Zeile (.row-processing) - siehe
  // set hass() oben für den Grund. `.row-processing:not(.clickable)` deckt
  // dort sowohl den "Lädt …"-Zwischenzustand als auch die fertige
  // <audio>-Wiedergabe ab, da playCallRecording() die "clickable"-Klasse
  // beim Laden entfernt und nie wieder hinzufügt. Ein bereits ZU ENDE
  // gespieltes <audio>-Element (`.ended === true`) zählt bewusst NICHT mehr
  // als aktiv - sonst würde _catchUpRender() nach dem natürlichen Ende der
  // Wiedergabe für immer blockiert bleiben, da das <audio>-Element (mit
  // sichtbarer Bedienleiste zum Nachhören) im DOM bestehen bleibt.
  _hasActiveMediaPlayback() {
    if (!this.shadowRoot) return false;
    if (this.shadowRoot.querySelector(".voicemail-play-btn[disabled]")) return true;
    if (this.shadowRoot.querySelector(".row-processing[data-media-url]:not(.clickable)")) {
      const rowAudio = this.shadowRoot.querySelector(".row-processing-player");
      if (!rowAudio || !rowAudio.ended) return true;
    }
    const voicemailAudio = this.shadowRoot.querySelector(".voicemail-player-slot audio");
    if (voicemailAudio && !voicemailAudio.ended) return true;
    return false;
  }

  // Wird aufgerufen, sobald eine Wiedergabe natürlich endet (audio "ended",
  // siehe playVoicemail()/playCallRecording()) oder fehlschlägt - holt einen
  // währenddessen zurückgehaltenen Re-Render jetzt nach, falls sich die
  // Signatur inzwischen geändert hat (z. B. der "Neu"-Status durch
  // auto_mark_read). Kein Effekt, falls sich nichts geändert hat oder
  // inzwischen eine ANDERE Wiedergabe läuft (dann bleibt es weiterhin
  // zurückgehalten, bis auch die vorbei ist).
  _catchUpRender() {
    if (!this._hass || !this._config) return;
    if (this._hasActiveMediaPlayback()) return;
    const signature = this._computeSignature();
    if (signature !== this._lastSignature) {
      this._lastSignature = signature;
      this._render();
    }
  }

  get hass() {
    return this._hass;
  }

  getCardSize() {
    return 5;
  }

  static getConfigElement() {
    return document.createElement("fritzbox-anrufe-card-editor");
  }

  static getStubConfig(hass, entities) {
    const guess = (suffix) =>
      (entities || []).find((e) => e.startsWith("sensor.") && e.includes(suffix)) || "";
    // Eigene Guess-Funktion für die switch-Domäne (seit v1.1.0) - die
    // Suffixe "anrufbeantworter_schalter"/"anrufbeantworter_2_schalter"
    // matchen absichtlich nicht gegenseitig (siehe
    // __init__.py:SWITCH_TRANSLATION_KEY_VOICEMAIL/_2 für die zugrunde
    // liegende suggested_object_id).
    const guessSwitch = (suffix) =>
      (entities || []).find((e) => e.startsWith("switch.") && e.includes(suffix)) || "";
    return {
      ...CONFIG_DEFAULTS,
      entity_live: guess("call_monitor") || guess("live"),
      entity_eingehend: guess("eingehend"),
      entity_ausgehend: guess("ausgehend"),
      entity_verpasst: guess("verpasst"),
      entity_voicemail: guess("anrufbeantworter") || guess("voicemail"),
      entity_voicemail_2: guess("anrufbeantworter_2") || guess("voicemail_2"),
      // Slot 3-5 (seit v1.2.0) - dieselben Suffixe wie die Integration seit
      // v1.1.1 selbst für diese Sensoren vergibt (const.py:CALL_TYPES_VOICEMAIL).
      entity_voicemail_3: guess("anrufbeantworter_3") || guess("voicemail_3"),
      entity_voicemail_4: guess("anrufbeantworter_4") || guess("voicemail_4"),
      entity_voicemail_5: guess("anrufbeantworter_5") || guess("voicemail_5"),
      entity_tam_switch: guessSwitch("anrufbeantworter_schalter"),
      entity_tam_switch_2: guessSwitch("anrufbeantworter_2_schalter"),
      entity_tam_switch_3: guessSwitch("anrufbeantworter_3_schalter"),
      entity_tam_switch_4: guessSwitch("anrufbeantworter_4_schalter"),
      entity_tam_switch_5: guessSwitch("anrufbeantworter_5_schalter"),
      // Kein entity_settings mehr: der von der Integration angelegte
      // sensor.fritzbox_anrufe_einstellungen wird seit v1.3.0b2 immer
      // automatisch gefunden (siehe _settingsEntityId()); ein eigener Picker
      // (und damit ein Stub-Vorschlag) entfällt.
    };
  }

  _entityState(entityId) {
    if (!entityId || !this._hass) return undefined;
    return this._hass.states[entityId];
  }

  // Kategorien (Tabs), die laut Konfiguration angezeigt werden sollen. Für
  // Anruf-Kategorien reicht der show_*-Schalter allein; die
  // Anrufbeantworter-Kategorie braucht zusätzlich einen konfigurierten
  // entity_voicemail - ohne Sensor gibt es dort nichts zu zeigen.
  _visibleFilterTypes() {
    return FILTER_ORDER.filter((type) => {
      if (this._config[`show_${type}`] === false) return false;
      if (type === FILTER_VOICEMAIL && !this._config.entity_voicemail) return false;
      // Einstellungen-Tab: seit v1.3.0b1 sichtbar, sobald die Kategorie
      // aktiviert ist (show_einstellungen). Der zugehörige Sensor wird - falls
      // nicht explizit gesetzt - automatisch gefunden (_settingsEntityId());
      // fehlt er ganz, zeigt _renderSettings() einen Hinweis, statt den Tab
      // stillschweigend zu verstecken (das war die Verwirrung in b0).
      return true;
    });
  }

  // Ermittelt den Einstellungen-Sensor: bevorzugt die explizite Konfiguration,
  // sonst der von der Integration angelegte sensor.fritzbox_anrufe_einstellungen
  // (Auto-Fallback seit v1.3.0b1, damit das Einschalten der Kategorie allein
  // genügt). Leerer String, wenn nichts gefunden wird.
  _settingsEntityId() {
    if (this._config && this._config.entity_settings) return this._config.entity_settings;
    if (!this._hass || !this._hass.states) return "";
    const ids = Object.keys(this._hass.states);
    return (
      ids.find(
        (id) =>
          id.startsWith("sensor.") &&
          id.includes("einstellungen") &&
          (id.includes("fritzbox") || id.includes("anrufe"))
      ) ||
      ids.find((id) => id.startsWith("sensor.") && id.endsWith("_einstellungen")) ||
      ""
    );
  }

  // Anruf-Typen (ohne "alle"), die in der "Alle"-Sammelansicht enthalten
  // sein sollen.
  _enabledCallTypes() {
    return ["eingehend", "ausgehend", "verpasst"].filter(
      (type) => this._config[`show_${type}`] !== false
    );
  }

  _defaultFilter() {
    const visible = this._visibleFilterTypes();
    if (visible.includes(FILTER_ALL)) return FILTER_ALL;
    return visible[0] || FILTER_ALL;
  }

  _computeSignature() {
    const ids = [
      this._config.entity_live,
      this._config.entity_eingehend,
      this._config.entity_ausgehend,
      this._config.entity_verpasst,
      this._config.entity_voicemail,
      this._config.entity_voicemail_2,
      // Slot 3-5 (seit v1.2.0) - siehe _activeTamSlots().
      this._config.entity_voicemail_3,
      this._config.entity_voicemail_4,
      this._config.entity_voicemail_5,
      // Seit v1.1.0 - siehe _renderTamSwitches(): ohne dies würde ein
      // Schalter-Klick zwar den Service-Call auslösen, aber der Karte erst
      // beim nächsten ohnehin fälligen Re-Render (z. B. Tab-Wechsel)
      // auffallen, statt sofort nach der hass-Aktualisierung.
      this._config.entity_tam_switch,
      this._config.entity_tam_switch_2,
      this._config.entity_tam_switch_3,
      this._config.entity_tam_switch_4,
      this._config.entity_tam_switch_5,
      // Einstellungen-Sensor (seit v1.3.0b0; b1: inkl. Auto-Fallback) - damit
      // der Zahnrad-Tab neu rendert, sobald seine Geräte-/Telefonbuchdaten
      // eintreffen.
      this._settingsEntityId(),
    ].filter(Boolean);
    const statePart = ids
      .map((id) => {
        const s = this._entityState(id);
        return s ? `${id}:${s.state}:${s.last_updated}` : `${id}:_`;
      })
      .join("|");
    return `${statePart}|filter:${this._activeFilter}|own:${this._filterOwnNumber}|sort:${this._sortBy}`;
  }

  _callsFor(callType) {
    const key = `entity_${callType}`;
    const stateObj = this._entityState(this._config[key]);
    if (!stateObj) return [];
    const calls = stateObj.attributes ? stateObj.attributes.calls : undefined;
    return Array.isArray(calls) ? calls : [];
  }

  // Distinkte own_number-Werte über alle aktuell aktivierten Anruf-
  // Kategorien hinweg (nicht nur die des gerade aktiven Tabs) - so bleibt
  // die Dropdown-Liste stabil, unabhängig davon, welcher Tab gerade
  // angezeigt wird. Nicht für Anrufbeantworter-Nachrichten: TamMessage
  // (fritzconnection) hat kein own-number-Feld, siehe Moduldoku oben.
  _availableOwnNumbers() {
    const set = new Set();
    this._enabledCallTypes().forEach((type) => {
      this._callsFor(type).forEach((call) => {
        if (call.own_number) set.add(call.own_number);
      });
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b, "de"));
  }

  _applyOwnNumberFilter(calls) {
    if (!this._filterOwnNumber) return calls;
    return calls.filter((call) => call.own_number === this._filterOwnNumber);
  }

  _sortEntries(entries) {
    return entries.slice().sort((a, b) => compareEntriesBySort(a, b, this._sortBy));
  }

  _visibleCalls() {
    const maxRows = Number(this._config.max_rows) || 10;
    let calls;
    if (this._activeFilter === FILTER_ALL) {
      calls = this._enabledCallTypes().flatMap((type) => this._callsFor(type));
      calls.sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));
    } else {
      calls = this._callsFor(this._activeFilter).slice();
    }
    // show_filter_bar aus (Standard): Reihenfolge/Filterung bleibt exakt wie
    // vor v1.0.4b3 - die Sortier-/Eigene-Nummer-Logik unten wird dann gar
    // nicht erst erreicht, siehe Moduldoku oben.
    if (this._config.show_filter_bar) {
      calls = this._applyOwnNumberFilter(calls);
      calls = this._sortEntries(calls);
    }
    // Spam ausblenden (seit v1.0.6b1) - siehe hide_spam in CONFIG_DEFAULTS.
    // Bewusst NACH der max_rows-unabhängigen Sortierung/Own-Number-Filterung
    // oben, aber VOR dem finalen slice(), damit ausgeblendete Spam-Einträge
    // nicht die Zeilenzahl auffüllen, sondern durch die nächsten regulären
    // Einträge ersetzt werden.
    if (this._config.hide_spam) {
      calls = calls.filter((call) => !call.spam);
    }
    return calls.slice(0, maxRows);
  }

  // Nachrichten eines Anrufbeantworter-Sensors, getaggt mit `_tam`
  // ("1"/"2"), `_entityId` (für den delete_voicemail_message-Service-Call)
  // und `_key` (zusammengesetzter, garantiert nicht-leerer UI-Status-
  // Schlüssel "<tam>:<id>" - siehe Moduldoku oben zum v1.0.6b2-Nebeneffekt
  // bei Index 0). Rein clientseitig, keine Änderung an den Sensor-Attributen
  // selbst nötig.
  _voicemailsFor(entityId, tamLabel) {
    const stateObj = this._entityState(entityId);
    if (!stateObj) return [];
    const messages = stateObj.attributes ? stateObj.attributes.messages : undefined;
    if (!Array.isArray(messages)) return [];
    return messages.map((msg) => ({
      ...msg,
      _tam: tamLabel,
      _entityId: entityId,
      _key: `${tamLabel}:${msg.id}`,
    }));
  }

  _voicemails() {
    return this._voicemailsFor(this._config.entity_voicemail, "1");
  }

  // Zweiter Anrufbeantworter (seit v1.0.6b2, siehe Moduldoku oben) - leeres
  // Array ohne konfiguriertes entity_voicemail_2, exakt wie bei jedem
  // anderen optionalen Sensor dieser Karte.
  _voicemails2() {
    if (!this._config.entity_voicemail_2) return [];
    return this._voicemailsFor(this._config.entity_voicemail_2, "2");
  }

  // Konfigurationsschlüssel für Anrufbeantworter-Slot `n` (1-5, seit
  // v1.2.0) - Slot 1 nutzt bewusst die schon immer unsuffixierten
  // Feldnamen (entity_voicemail/entity_tam_switch), damit bestehende
  // Konfigurationen unverändert gültig bleiben; Slot 2-5 folgen dem seit
  // v1.0.6b2 etablierten "_N"-Muster.
  _tamEntityKey(n) {
    return n === 1 ? "entity_voicemail" : `entity_voicemail_${n}`;
  }

  _tamSwitchKey(n) {
    return n === 1 ? "entity_tam_switch" : `entity_tam_switch_${n}`;
  }

  // Nachrichten für einen beliebigen Slot 1-5 (seit v1.2.0) - Verallgemeinerung
  // von _voicemails()/_voicemails2() oben (die beide unverändert bestehen
  // bleiben, um an ihren bestehenden Aufrufstellen keine unnötige Diff-Last
  // zu erzeugen) für Slot 3-5 sowie für den neuen Akkordeon-Renderpfad.
  _voicemailsForSlot(n) {
    const entityId = this._config[this._tamEntityKey(n)];
    if (!entityId) return [];
    return this._voicemailsFor(entityId, String(n));
  }

  // Alle tatsächlich konfigurierten Anrufbeantworter-Slots (1-5, seit
  // v1.2.0), in Reihenfolge. Ein Slot gilt als "aktiv", sobald sein
  // entity_voicemail_N gesetzt ist - unabhängig davon, ob die vorherigen
  // Slots ebenfalls gesetzt sind (auch wenn dieser Fall in der Praxis kaum
  // vorkommen dürfte, siehe MAX_TAM_COUNT/migrated_tam_count in der
  // Integration selbst, die Slots stets lückenlos von 1 an vergibt).
  _activeTamSlots() {
    const slots = [];
    for (let n = 1; n <= MAX_TAM_SLOTS; n += 1) {
      const entityId = this._config[this._tamEntityKey(n)];
      if (!entityId) continue;
      slots.push({ n, entityId, switchEntityId: this._config[this._tamSwitchKey(n)] });
    }
    return slots;
  }

  // Bestimmt, WIE mehrere Anrufbeantworter dargestellt werden (seit v1.2.0)
  // - siehe Moduldoku oben und CONFIG_DEFAULTS:voicemail_2_mode. "merged"/
  // "separate" sind nur für GENAU zwei Listen definiert (siehe deren
  // Renderlogik unten) - ab drei Slots gibt es dafür keine sinnvolle
  // Fortsetzung (ein "AB 1"/"AB 2"/"AB 3"/...-Badge-Gemisch wäre kaum noch
  // lesbar), daher erzwingt diese Methode "accordion" ab dem dritten Slot,
  // unabhängig vom gespeicherten Konfigurationswert.
  _voicemailDisplayMode(slotCount) {
    if (slotCount <= 2) {
      return this._config.voicemail_2_mode === "accordion" ||
        this._config.voicemail_2_mode === "separate"
        ? this._config.voicemail_2_mode
        : "merged";
    }
    return "accordion";
  }

  _liveStateObj() {
    return this._entityState(this._config.entity_live);
  }

  _isLiveActive() {
    const stateObj = this._liveStateObj();
    return !!stateObj && LIVE_ACTIVE_STATES.has(stateObj.state);
  }

  _typeIcon(type) {
    return (FILTER_META[type] && FILTER_META[type].icon) || "mdi:phone";
  }

  // Farbe des Zeilen-Icons (seit v1.0.4) - seit v1.0.4 (final) folgt es der
  // pro-Kategorie konfigurierten Tab-Icon-Farbe (color_icon_eingehend/
  // _ausgehend/_verpasst - dieselben Schlüssel wie das jeweilige Tab-Icon in
  // _renderTabs()), damit eine an einer Kategorie geänderte Symbolfarbe
  // sichtbar auch bei den zugehörigen Zeilen in der Liste ankommt - genau
  // wie beim Tab selbst ist das unabhängig vom Tab-Status (aktiv/inaktiv).
  // EINZIGE AUSNAHME (per Thorsten): ist `color_row_icon` gesetzt - die
  // Einstellung, die EINE Farbe für ALLE Zeilen-Icons zuweist -, gewinnt
  // diese einheitliche Farbe. Sie wird hier bewusst NICHT zurückgegeben
  // (leerer String = kein Inline-Style), weil sie bereits als CSS-Variable
  // (--fba-color-row-icon, siehe _colorVars()/.row-icon) für JEDES
  // Zeilen-Icon gilt - ein Inline-Style hier wäre nur eine Dopplung.
  _rowIconColor(callType) {
    const cfg = this._config || {};
    if (sanitizeColor(cfg.color_row_icon)) return "";
    const iconColorKey = CATEGORY_ICON_COLOR_KEYS[callType];
    return iconColorKey ? sanitizeColor(cfg[iconColorKey]) : "";
  }

  // Ob die "Weiterverarbeitung"-Zeile für einen Anruf des gegebenen
  // Anruflisten-Typs gezeigt werden soll. Auf der "Alle"-Sammelansicht
  // entscheidet ausschließlich show_processing_alle (Punkt 6) - unabhängig
  // vom eigentlichen Typ des jeweiligen Anrufs; auf einer einzelnen
  // Kategorie-Ansicht (eingehend/ausgehend/verpasst) der jeweils passende
  // show_processing_<typ>-Schalter (Punkte 3-5).
  _processingEnabledFor(callType) {
    if (this._activeFilter === FILTER_ALL) {
      return !!this._config.show_processing_alle;
    }
    return !!this._config[`show_processing_${callType}`];
  }

  _renderProcessingRow(call) {
    if (!this._processingEnabledFor(call.type)) return "";
    const meta = PROCESSING_META[call.outcome];
    // Kein bekannter/gemappter outcome (z. B. noch nicht aktualisierter
    // Sensor-Zustand vor einem Neustart nach dem Update) - Zeile einfach
    // weglassen statt ein kaputtes Icon zu zeigen.
    if (!meta) return "";

    const canPlay = !!(meta.playable && call.media_url);
    const attrs = [
      canPlay ? `data-media-url="${escapeHtml(call.media_url)}"` : "",
      meta.tab ? `data-target-tab="${escapeHtml(meta.tab)}"` : "",
    ]
      .filter(Boolean)
      .join(" ");
    const clickable = canPlay || !!meta.tab;

    const color = PROCESSING_COLOR_VARS[meta.colorKind] || "inherit";
    return `
      <div class="row-processing ${clickable ? "clickable" : ""}" ${attrs} title="${escapeHtml(meta.label)}">
        <span class="row-processing-arrow" aria-hidden="true">↳</span>
        <ha-icon icon="${meta.icon}" style="color: ${color};"></ha-icon>
        <span class="row-processing-label">${escapeHtml(meta.label)}</span>
      </div>
    `;
  }

  _renderLiveBanner() {
    if (!this._isLiveActive()) return "";
    const stateObj = this._liveStateObj();
    const attrs = stateObj.attributes || {};
    const label = LIVE_STATE_LABELS[stateObj.state] || stateObj.state;
    const name = attrs.from_name || attrs.to_name || attrs.with_name || "";
    const number = attrs.from || attrs.to || attrs.with || "";
    const separator = name && number ? " · " : "";
    return `
      <div class="live-banner">
        <ha-icon icon="mdi:phone-in-talk"></ha-icon>
        <div class="live-banner-text">
          <span class="live-state">${escapeHtml(label)}</span>
          <span class="live-detail">${escapeHtml(name)}${separator}${escapeHtml(number)}</span>
        </div>
      </div>
    `;
  }

  _renderTabs() {
    const visible = this._visibleFilterTypes();
    if (visible.length <= 1) return "";
    const cfg = this._config || {};
    return `
      <div class="tabs" role="tablist">
        ${visible
          .map((type) => {
            const meta = FILTER_META[type];
            const active = type === this._activeFilter ? "active" : "";
            // Optionale, pro Kategorie feste Icon-Farbe (seit v1.0.4b1) -
            // per Inline-Style, damit sie (falls gesetzt) die geerbte
            // Tab-Farbe (aktiv/inaktiv) überschreibt; ungesetzt/ungültig
            // bleibt das Icon wie bisher beim geerbten Wert.
            const iconColorKey = CATEGORY_ICON_COLOR_KEYS[type];
            const iconColor = iconColorKey ? sanitizeColor(cfg[iconColorKey]) : "";
            const iconStyle = iconColor ? ` style="color: ${iconColor};"` : "";
            return `
              <button
                class="tab ${active}"
                role="tab"
                aria-selected="${type === this._activeFilter}"
                data-filter="${type}"
                title="${escapeHtml(meta.label)}"
              >
                <ha-icon icon="${meta.icon}"${iconStyle}></ha-icon>
                <span>${escapeHtml(meta.label)}</span>
              </button>
            `;
          })
          .join("")}
      </div>
    `;
  }

  // Anrufbeantworter ist ein Tab wie jeder andere (5. Symbol in der
  // Kopfzeile, siehe FILTER_ORDER) - kein Abschnitt unterhalb der
  // Anrufliste. Je nach aktivem Tab zeigt der Kartenkörper entweder die
  // Anrufliste oder die Anrufbeantworter-Nachrichten, nie beides.
  _renderMainContent() {
    if (this._activeFilter === FILTER_VOICEMAIL) {
      return this._renderVoicemailRows();
    }
    if (this._activeFilter === FILTER_SETTINGS) {
      return this._renderSettings();
    }
    return this._renderRows();
  }

  // Einstellungen-Ansicht (Zahnrad-Tab, seit v1.3.0b0, EXPERIMENTELL) - liest
  // die Attribute des Einstellungen-Sensors (siehe settings_data.py/sensor.py):
  // die Telefoniegeräte-Tabelle (Name/Anschluss/ausgehende/ankommende/interne
  // Nummer je Gerät, seit v1.3.0b2 aus data.lua) sowie die Rufnummern als
  // Fallback. Je Gerät ein Detail-Popup; hinter jedem Anrufbeantworter ein
  // Ein/Aus-Schalter (siehe _renderTamSwitchRow/_toggleTamSwitch). Das
  // Telefonbuch wird seit v1.3.0b2 bewusst NICHT mehr angezeigt.
  _renderSettings() {
    const entityId = this._settingsEntityId();
    if (!entityId) {
      return `
        <div class="settings-view">
          <div class="settings-experimental">Experimentell – siehe README.</div>
          <div class="empty">
            Kein Einstellungen-Sensor gefunden.<br />
            Er wird von der Integration angelegt
            (<code>sensor.fritzbox_anrufe_einstellungen</code>) und automatisch
            verwendet, sobald die Kategorie „Einstellungen" aktiviert ist.
          </div>
        </div>
      `;
    }
    const stateObj = this._hass ? this._hass.states[entityId] : null;
    if (!stateObj) {
      return `
        <div class="settings-view">
          <div class="settings-experimental">Experimentell – siehe README.</div>
          <div class="empty">
            Einstellungen-Sensor <code>${escapeHtml(entityId)}</code> ist nicht
            verfügbar (lädt evtl. noch oder das FRITZ!Box-Konto/FRITZ!OS liefert
            die Daten nicht). Siehe README.
          </div>
        </div>
      `;
    }
    const attrs = stateObj.attributes || {};
    const devices = Array.isArray(attrs.devices) ? attrs.devices : [];
    const numbers = Array.isArray(attrs.numbers) ? attrs.numbers : [];
    const fallback = attrs.devices_fallback === true;

    const section = (title, bodyHtml) => `
      <div class="settings-section">
        <div class="settings-section-title">${escapeHtml(title)}</div>
        ${bodyHtml}
      </div>
    `;

    // --- Telefoniegeräte-Tabelle -------------------------------------------
    let deviceHtml;
    if (devices.length) {
      const rows = devices
        .map((dev, idx) => this._renderDeviceRow(dev, idx))
        .join("");
      // Trägt IRGENDEIN Gerät eine ausgehende/ankommende/interne Nummer? Wenn
      // nicht (die FRITZ!Box liefert die Zuordnung auf dieser FRITZ!OS-Version
      // nicht mit), das ehrlich vermerken statt nur „–" ohne Erklärung.
      const anyNumbers = devices.some(
        (d) => (d.outgoing || "") || (d.incoming || "") || (d.intern || "")
      );
      deviceHtml = `
        <div class="settings-table" role="table">
          <div class="settings-table-head" role="row">
            <span class="col-name">Name</span>
            <span class="col-anschluss">Anschluss</span>
            <span class="col-num">Ausgehend</span>
            <span class="col-num">Ankommend</span>
            <span class="col-num">Intern</span>
          </div>
          ${rows}
        </div>
        ${
          fallback
            ? `<div class="settings-note">Hinweis: Die ausgehende/ankommende/interne
                 Rufnummern-Zuordnung konnte nicht gelesen werden (data.lua nicht
                 verfügbar); es werden nur die per TR-064 gemeldeten Geräte gezeigt.</div>`
            : !anyNumbers
              ? `<div class="settings-note">Hinweis: Diese FRITZ!Box/FRITZ!OS liefert die
                   ausgehende/ankommende/interne Rufnummern-Zuordnung nicht mit – daher „–".
                   Die Geräteliste ist auf echte Telefoniegeräte gefiltert (ohne Heimnetz-/
                   Netzwerkgeräte). Siehe README.</div>`
              : ""
        }`;
    } else {
      const numberHtml = numbers.length
        ? `<div class="settings-list">${numbers
            .map(
              (n) => `
            <div class="settings-row">
              <ha-icon class="settings-row-icon" icon="mdi:phone"></ha-icon>
              <span class="settings-row-name">${escapeHtml(n.name || n.number || "")}</span>
              <span class="settings-row-meta">${escapeHtml(n.number || "")}</span>
            </div>`
            )
            .join("")}</div>`
        : "";
      deviceHtml = `
        <div class="empty">
          Keine Telefoniegeräte gelesen. Das FRITZ!Box-Konto/FRITZ!OS liefert die
          Telefoniegeräte-Tabelle (data.lua) hier nicht. Siehe README.
        </div>
        ${numbers.length ? section("Rufnummern", numberHtml) : ""}`;
    }

    return `
      <div class="settings-view">
        <div class="settings-experimental">Experimentell – Anzeige, siehe README.</div>
        ${section("Telefoniegeräte", deviceHtml)}
        ${this._renderDevicePopup(devices)}
      </div>
    `;
  }

  // Eine Zeile der Telefoniegeräte-Tabelle. Anklickbar (öffnet das Detail-
  // Popup, siehe _renderDevicePopup); hinter einem Anrufbeantworter zusätzlich
  // ein Ein/Aus-Schalter (nur, wenn ein passender Schalter konfiguriert ist).
  _renderDeviceRow(dev, idx) {
    const name = dev.name || "";
    const anschluss = dev.anschluss || dev.type || "";
    const outgoing = dev.outgoing || "";
    const incoming = dev.incoming || "";
    const intern = dev.intern || "";
    const icon = this._deviceIcon(dev);
    const tamToggle = dev.is_tam ? this._deviceTamToggle(dev) : "";
    return `
      <div class="settings-table-row clickable" role="row" data-device-index="${idx}" title="Details anzeigen">
        <span class="col-name" role="cell">
          <ha-icon class="settings-row-icon" icon="${icon}"></ha-icon>
          <span class="settings-device-name">${escapeHtml(name)}</span>
        </span>
        <span class="col-anschluss" role="cell">${escapeHtml(anschluss)}</span>
        <span class="col-num" role="cell">${escapeHtml(outgoing) || "–"}</span>
        <span class="col-num" role="cell">${escapeHtml(incoming) || "–"}</span>
        <span class="col-num col-intern" role="cell">
          <span>${escapeHtml(intern) || "–"}</span>
          ${tamToggle}
        </span>
      </div>
    `;
  }

  // mdi-Symbol je Gerätetyp (best effort, rein optisch).
  _deviceIcon(dev) {
    if (dev.is_tam) return "mdi:answering-machine";
    const token = `${dev.type || ""} ${dev.anschluss || ""} ${dev.name || ""}`.toLowerCase();
    if (token.includes("dect") || token.includes("mobilteil")) return "mdi:phone-classic";
    if (token.includes("app")) return "mdi:cellphone";
    if (token.includes("fon") || token.includes("telefon")) return "mdi:phone";
    return "mdi:phone";
  }

  // Ordnet einer Anrufbeantworter-Zeile den passenden konfigurierten Ein/Aus-
  // Schalter zu (tam_index 1 -> entity_tam_switch, 2 -> _2 …) und liefert die
  // bestehende Schalter-Schaltfläche (Klasse .tam-switch-toggle, derselbe
  // Klick-Handler wie im Anrufbeantworter-Tab, siehe _toggleTamSwitch). Ohne
  // passenden konfigurierten Schalter erscheint nichts.
  _deviceTamSwitchEntity(dev) {
    const n = Number(dev.tam_index) || 1;
    const key = this._tamSwitchKey(n);
    return (this._config && this._config[key]) || "";
  }

  _deviceTamToggle(dev) {
    const entityId = this._deviceTamSwitchEntity(dev);
    if (!entityId) return "";
    const stateObj = this._entityState(entityId);
    const state = stateObj ? stateObj.state : undefined;
    const isOn = state === "on";
    const unavailable = !stateObj || state === "unavailable";
    return `
      <button
        class="tam-switch-toggle device-tam-toggle${isOn ? " on" : ""}"
        data-entity="${escapeHtml(entityId)}"
        data-state="${escapeHtml(state || "")}"
        title="Anrufbeantworter ${isOn ? "ausschalten" : "einschalten"}"
        ${unavailable ? "disabled" : ""}
      >
        <ha-icon icon="${isOn ? "mdi:toggle-switch" : "mdi:toggle-switch-off-outline"}"></ha-icon>
      </button>
    `;
  }

  // Detail-Popup zu einer Gerätezeile (seit v1.3.0b2) - bewusst KEIN natives
  // dialog()/confirm() (siehe Moduldoku: die misslingen im Companion-App-
  // WebView), sondern ein eigenes Overlay im Shadow-Root. Offen, wenn
  // this._settingsPopupIndex auf eine gültige Zeile zeigt.
  _renderDevicePopup(devices) {
    const idx = this._settingsPopupIndex;
    if (idx === null || idx === undefined) return "";
    const dev = devices[idx];
    if (!dev) return "";
    const line = (label, value) => `
      <div class="settings-popup-line">
        <span class="settings-popup-label">${escapeHtml(label)}</span>
        <span class="settings-popup-value">${escapeHtml(value) || "–"}</span>
      </div>`;
    const tamToggle = dev.is_tam ? this._deviceTamToggle(dev) : "";
    return `
      <div class="settings-popup-backdrop">
        <div class="settings-popup" role="dialog" aria-modal="true">
          <div class="settings-popup-head">
            <ha-icon icon="${this._deviceIcon(dev)}"></ha-icon>
            <span class="settings-popup-title">${escapeHtml(dev.name || "")}</span>
            <button class="settings-popup-close" title="Schließen" aria-label="Schließen">
              <ha-icon icon="mdi:close"></ha-icon>
            </button>
          </div>
          <div class="settings-popup-body">
            ${line("Anschluss", dev.anschluss || dev.type || "")}
            ${line("Rufnummer ausgehend", dev.outgoing || "")}
            ${line("Rufnummer ankommend", dev.incoming || "")}
            ${line("Intern", dev.intern || "")}
            ${
              tamToggle
                ? `<div class="settings-popup-line">
                     <span class="settings-popup-label">Anrufbeantworter</span>
                     <span class="settings-popup-value">${tamToggle}</span>
                   </div>`
                : ""
            }
          </div>
        </div>
      </div>
    `;
  }

  _renderRows() {
    const calls = this._visibleCalls();
    const cfg = this._config;
    if (!calls.length) {
      return `<div class="empty">Keine Anrufe vorhanden.</div>`;
    }
    return `
      <div class="rows">
        ${calls
          .map((call) => {
            const rowIconColor = this._rowIconColor(call.type);
            const rowIconStyle = rowIconColor ? ` style="color: ${rowIconColor};"` : "";
            return `
          <div class="row">
            <ha-icon class="row-icon" icon="${this._typeIcon(call.type)}"${rowIconStyle}></ha-icon>
            <div class="row-main">
              <div class="row-primary">
                ${cfg.show_name ? `<span class="row-name">${escapeHtml(call.name || call.number || "Unbekannt")}</span>` : ""}
                ${cfg.show_vip && call.vip ? '<ha-icon class="vip" icon="mdi:star"></ha-icon>' : ""}
                ${call.spam ? '<span class="row-badge spam-badge">Spam</span>' : ""}
              </div>
              <div class="row-secondary">
                ${cfg.show_number ? `<span class="row-number">${escapeHtml(call.number || "")}</span>` : ""}
                ${cfg.show_own_number && call.own_number ? `<span class="row-own-number">${escapeHtml(call.own_number)}</span>` : ""}
                ${cfg.show_date ? `<span class="row-date">${formatDateTime(call.date)}</span>` : ""}
              </div>
            </div>
            <div class="row-extra">
              ${cfg.show_duration && call.duration ? `<span class="row-duration">${escapeHtml(call.duration)}</span>` : ""}
              ${cfg.show_device && call.device ? `<span class="row-device">${escapeHtml(call.device)}</span>` : ""}
            </div>
          </div>
          ${this._renderProcessingRow(call)}
        `;
          })
          .join("")}
      </div>
    `;
  }

  // Gemeinsame Aufbereitung (Sortierung/optimistisches Ausblenden gelöschter
  // Nachrichten/Spam-Filter) für eine einzelne Nachrichtenliste - identisch
  // zum bisherigen (Vor-1.0.6b2-)Verhalten, wenn `sort` true bleibt.
  // `sort: false` (seit v1.0.6b2, "merged"-Modus) überlässt die Sortierung
  // stattdessen dem Aufrufer, der beide Listen erst zusammenführt und dann
  // EINMAL gemeinsam sortiert - kein own_number-Filter hier (siehe
  // _availableOwnNumbers()), nur die Sortierung gilt auch für
  // Anrufbeantworter-Nachrichten.
  _prepareVoicemails(messages, { sort = true } = {}) {
    let list = messages;
    if (sort && this._config.show_filter_bar) {
      list = this._sortEntries(list);
    }
    // Optimistisch ausgeblendete, gerade erst gelöschte Nachrichten (seit
    // v1.0.5b3) - siehe _deleteVoicemailMessage(). Verschwinden endgültig,
    // sobald der Coordinator-Refresh sie tatsächlich aus den Sensordaten
    // entfernt hat; bei einem fehlgeschlagenen Löschversuch werden sie
    // wieder eingeblendet. Seit v1.0.6b2 über den zusammengesetzten `_key`
    // (siehe _voicemailsFor()), nicht mehr die rohe `id`.
    if (this._pendingDeletedMessageIds && this._pendingDeletedMessageIds.size) {
      list = list.filter((msg) => !this._pendingDeletedMessageIds.has(msg._key));
    }
    // Spam ausblenden (seit v1.0.6b1) - siehe hide_spam in CONFIG_DEFAULTS
    // und die analoge Filterung in _visibleCalls().
    if (this._config.hide_spam) {
      list = list.filter((msg) => !msg.spam);
    }
    return list;
  }

  // Anrufbeantworter Ein/Aus-Schalter (seit v1.1.0, EXPERIMENTELL - siehe
  // switch.py in der Integration) - rein optisch über show_tam_switch
  // steuerbar (Standard AUS, siehe CONFIG_DEFAULTS). Erscheint, wenn
  // aktiviert, VOR der Nachrichten-Auflistung im Anrufbeantworter-Tab
  // (siehe _renderVoicemailRows() unten) - für beide voicemail_2_mode-
  // Varianten identisch platziert, da die Aufgabenstellung "vor der
  // Auflistung" nicht zwischen "gemischt"/"getrennt" unterscheidet.
  _renderTamSwitches() {
    if (!this._config.show_tam_switch) return "";
    const rows = [];
    if (this._config.entity_tam_switch) {
      rows.push(this._renderTamSwitchRow(this._config.entity_tam_switch, "Anrufbeantworter"));
    }
    // Slot 2-5 (seit v1.2.0 verallgemeinert von zuvor nur Slot 2): der
    // Schalter eines Slots wirkt nur zusammen mit einem gesetzten
    // entity_voicemail_N - ohne diesen Anrufbeantworter gibt es hier nichts
    // zu schalten, exakt wie bei der übrigen Slot-Logik dieser Karte.
    for (let n = 2; n <= MAX_TAM_SLOTS; n += 1) {
      const entityId = this._config[this._tamEntityKey(n)];
      const switchEntityId = this._config[this._tamSwitchKey(n)];
      if (entityId && switchEntityId) {
        rows.push(this._renderTamSwitchRow(switchEntityId, `Anrufbeantworter ${n}`));
      }
    }
    if (!rows.length) return "";
    return `<div class="tam-switch-block">${rows.join("")}</div>`;
  }

  // Eine einzelne Schalter-Zeile. `state` ist der rohe Home-Assistant-
  // Zustand ("on"/"off"/"unavailable"/"unknown") - EXPERIMENTELL, siehe
  // switch.py: assumed_state bedeutet, dieser Zustand ist die zuletzt von
  // dieser Integration selbst gesetzte (optimistische) Annahme, keine
  // bestätigte Rücklesung vom FRITZ!Box-Gerät.
  _renderTamSwitchRow(entityId, label) {
    const stateObj = this._entityState(entityId);
    const state = stateObj ? stateObj.state : undefined;
    const isOn = state === "on";
    const unavailable = !stateObj || state === "unavailable";
    const stateLabel = unavailable ? "Nicht verfügbar" : isOn ? "An" : "Aus";
    return `
      <div class="tam-switch-row">
        <ha-icon class="tam-switch-icon" icon="mdi:answering-machine"></ha-icon>
        <span class="tam-switch-label">${escapeHtml(label)}</span>
        <button
          class="tam-switch-toggle${isOn ? " on" : ""}"
          data-entity="${escapeHtml(entityId)}"
          data-state="${escapeHtml(state || "")}"
          ${unavailable ? "disabled" : ""}
        >
          <ha-icon icon="${isOn ? "mdi:toggle-switch" : "mdi:toggle-switch-off-outline"}"></ha-icon>
          <span>${stateLabel}</span>
        </button>
      </div>
    `;
  }

  // Klick-Handler für .tam-switch-toggle (siehe _render() unten) - ruft den
  // Standard-Home-Assistant-Service switch.turn_on/turn_off auf (kein
  // eigener Dienst nötig, anders als beim Löschen von Nachrichten). Kein
  // eigenes optimistisches UI-Update hier: switch.py selbst arbeitet bereits
  // optimistisch (siehe dortiger Modul-Docstring) und der neue Zustand
  // erreicht diese Karte über die reguläre hass-Aktualisierung (siehe
  // _computeSignature() - entity_tam_switch/entity_tam_switch_2 sind dort
  // seit v1.1.0 Teil der Signatur).
  async _toggleTamSwitch(entityId, currentState) {
    if (!entityId || !this._hass) return;
    const turnOn = currentState !== "on";
    try {
      await this._hass.callService("switch", turnOn ? "turn_on" : "turn_off", {
        entity_id: entityId,
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(
        "fritzbox_anrufe: Anrufbeantworter-Schalter konnte nicht umgeschaltet werden",
        err
      );
    }
  }

  // Live-AB-Regler (seit v1.2.0) - Checkboxen zum temporären Ein-/Ausblenden
  // einzelner konfigurierter Anrufbeantworter direkt auf der Karte, ohne
  // deren Konfiguration zu bearbeiten (analog zur bestehenden Filter-/
  // Sortierleiste, show_filter_bar). Zeigt IMMER alle konfigurierten Slots
  // an (auch gerade ausgeblendete, damit sie wieder einblendbar bleiben) -
  // der Startzustand kommt aus show_voicemail_1-5 (siehe CONFIG_DEFAULTS/
  // setConfig()), jede weitere Änderung hier ist reiner UI-Laufzeitstatus
  // (this._tamPickerVisible). Nur sichtbar ab zwei konfigurierten
  // Anrufbeantwortern - mit nur einem gibt es nichts auszuwählen.
  _renderTamPicker(configuredSlots) {
    if (configuredSlots.length < 2) return "";
    const chips = configuredSlots
      .map(({ n }) => {
        const checked = this._tamPickerVisible[n] !== false;
        return `
          <label class="voicemail-tam-picker-chip${checked ? " checked" : ""}">
            <input
              type="checkbox"
              class="voicemail-tam-picker-checkbox"
              data-tam="${n}"
              ${checked ? "checked" : ""}
            />
            <span>AB ${n}</span>
          </label>
        `;
      })
      .join("");
    return `<div class="voicemail-tam-picker">${chips}</div>`;
  }

  // Anrufbeantworter-Tab-Inhalt. Mit höchstens einem konfigurierten
  // Anrufbeantworter exakt das bisherige (Vor-1.0.6b2-)Verhalten: eine
  // einzelne Liste. Mit zwei (aktuell sichtbaren, siehe Live-AB-Regler oben)
  // Anrufbeantwortern je nach voicemail_2_mode entweder chronologisch
  // gemischt mit "AB X"/"AB Y"-Badge ("merged", Standard - wie die
  // "Alle"-Sammelansicht bei den Anrufen, siehe _visibleCalls()), als
  // getrennte, überschriebene Abschnitte untereinander ("separate"), oder
  // als auf-/zuklappbare Abschnitte ("accordion", seit v1.2.0). Ab drei
  // sichtbaren Anrufbeantwortern ist "accordion" die einzige Darstellung -
  // siehe Moduldoku oben und _voicemailDisplayMode(). Seit v1.1.0 steht ggf.
  // _renderTamSwitches() VOR jeder dieser Varianten (siehe dort), seit
  // v1.2.0 direkt danach ggf. _renderTamPicker().
  _renderVoicemailRows() {
    const maxRows = Number(this._config.max_rows) || 10;
    const switches = this._renderTamSwitches();
    const configuredSlots = this._activeTamSlots();

    if (configuredSlots.length <= 1) {
      const messages = this._prepareVoicemails(this._voicemails());
      return (
        switches +
        renderVoicemailRows(messages, {
          maxRows,
          showDeleteButton: !!this._config.show_delete_button,
          confirmDeleteId: this._confirmDeleteMessageId,
        })
      );
    }

    const picker = this._renderTamPicker(configuredSlots);
    const visibleSlots = configuredSlots.filter((slot) => this._tamPickerVisible[slot.n] !== false);
    const rowOpts = {
      maxRows,
      showDeleteButton: !!this._config.show_delete_button,
      confirmDeleteId: this._confirmDeleteMessageId,
    };

    if (!visibleSlots.length) {
      return `${switches}${picker}<div class="empty">Kein Anrufbeantworter ausgewählt.</div>`;
    }

    if (visibleSlots.length === 1) {
      const messages = this._prepareVoicemails(this._voicemailsForSlot(visibleSlots[0].n));
      return switches + picker + renderVoicemailRows(messages, rowOpts);
    }

    const mode = this._voicemailDisplayMode(visibleSlots.length);

    if (mode === "accordion") {
      return switches + picker + this._renderVoicemailAccordion(visibleSlots, maxRows);
    }

    if (mode === "separate") {
      const sections = visibleSlots.map(({ n }) => {
        const messages = this._prepareVoicemails(this._voicemailsForSlot(n));
        return `
          <div class="voicemail-section">
            <div class="voicemail-section-title">Anrufbeantworter ${n}</div>
            ${renderVoicemailRows(messages, rowOpts)}
          </div>
        `;
      });
      return switches + picker + sections.join("");
    }

    // "merged" (Standard, nur mit genau 2 sichtbaren Slots erreichbar -
    // siehe _voicemailDisplayMode()): Sortierung erst NACH dem
    // Zusammenführen, sonst wären beide Quellen nur hintereinandergehängt
    // statt tatsächlich chronologisch gemischt - dieselbe Reihenfolge wie
    // bei der "Alle"-Sammelansicht der Anrufe (_visibleCalls()): immer nach
    // Datum sortiert als Grundordnung, bei aktiver Filter-/Sortierleiste
    // stattdessen die dort gewählte Sortierung. Verallgemeinert seit v1.2.0
    // auf ein BELIEBIGES Slot-Paar (nicht mehr zwingend Slot 1+2), da der
    // Live-AB-Regler z. B. auch nur Slot 1+3 sichtbar lassen kann.
    const [slotA, slotB] = visibleSlots;
    const primary = this._prepareVoicemails(this._voicemailsForSlot(slotA.n), { sort: false });
    const secondary = this._prepareVoicemails(this._voicemailsForSlot(slotB.n), { sort: false });
    let merged = [...primary, ...secondary];
    merged.sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));
    if (this._config.show_filter_bar) {
      merged = this._sortEntries(merged);
    }
    return (
      switches +
      picker +
      renderVoicemailRows(merged, {
        ...rowOpts,
        showTamLabel: true,
      })
    );
  }

  // Akkordeon-Darstellung mehrerer Anrufbeantworter (seit v1.2.0, siehe
  // Moduldoku oben) - je Slot ein unabhängig auf-/zuklappbarer <details>-
  // Abschnitt (nativ, kein eigener JS-Zustandsautomat für das Auf-/Zuklappen
  // selbst nötig - siehe _render() weiter unten für das "toggle"-Event, das
  // lediglich den geöffneten Zustand in this._tamAccordionOpen spiegelt,
  // damit er einen nachfolgenden Re-Render übersteht). Mehrere Abschnitte
  // können gleichzeitig offen sein, unabhängig voneinander - kein
  // "nur-einer-offen"-Verhalten.
  //
  // Startzustand (einmalig, siehe Kommentar unten bei this._tamAccordionOpen):
  // ein Slot mit mindestens einer neuen ("Neu"-Status) Nachricht startet
  // aufgeklappt, alle anderen eingeklappt. Danach bestimmt ausschließlich der
  // Nutzer per Klick auf den jeweiligen Abschnitt, ob dieser offen ist - ein
  // späterer Re-Render (z. B. weil eine ANDERE Nachricht eintrifft) ändert
  // eine bereits getroffene Nutzerentscheidung nicht mehr, selbst wenn sich
  // der "hat neue Nachrichten"-Status dieses Slots inzwischen geändert hat.
  _renderVoicemailAccordion(slots, maxRows) {
    const rowOpts = {
      maxRows,
      showDeleteButton: !!this._config.show_delete_button,
      confirmDeleteId: this._confirmDeleteMessageId,
    };
    const sections = slots.map(({ n }) => {
      const messages = this._prepareVoicemails(this._voicemailsForSlot(n));
      const hasNew = messages.some((msg) => msg.new);
      if (!(n in this._tamAccordionOpen)) {
        this._tamAccordionOpen[n] = hasNew;
      }
      const open = !!this._tamAccordionOpen[n];
      return `
        <details class="voicemail-accordion-section" data-tam="${n}" ${open ? "open" : ""}>
          <summary class="voicemail-accordion-summary">
            <ha-icon class="voicemail-accordion-chevron" icon="mdi:chevron-down"></ha-icon>
            <span class="voicemail-accordion-title">Anrufbeantworter ${n}</span>
            ${hasNew ? '<span class="voicemail-badge">neu</span>' : ""}
            <span class="voicemail-accordion-count">${messages.length}</span>
          </summary>
          <div class="voicemail-accordion-body">
            ${renderVoicemailRows(messages, rowOpts)}
          </div>
        </details>
      `;
    });
    return `<div class="voicemail-accordion">${sections.join("")}</div>`;
  }

  // Filter-/Sortierleiste (seit v1.0.4b3) - siehe Moduldoku oben. Eigene
  // Rufnummer nur für die Anrufliste (nicht Anrufbeantworter, siehe
  // _availableOwnNumbers()); Sortierung gilt auf jedem Tab.
  _renderFilterBar() {
    if (!this._config.show_filter_bar) return "";
    const isVoicemail = this._activeFilter === FILTER_VOICEMAIL;
    const ownNumbers = isVoicemail ? [] : this._availableOwnNumbers();
    return `
      <div class="filter-bar">
        ${
          isVoicemail
            ? ""
            : `<label class="filter-bar-field">
                 <span class="filter-bar-label">Eigene Rufnummer</span>
                 <select class="filter-own-number">
                   <option value="" ${this._filterOwnNumber ? "" : "selected"}>Alle</option>
                   ${ownNumbers
                     .map(
                       (num) => `
                     <option value="${escapeHtml(num)}" ${this._filterOwnNumber === num ? "selected" : ""}>
                       ${escapeHtml(num)}
                     </option>
                   `
                     )
                     .join("")}
                 </select>
               </label>`
        }
        <label class="filter-bar-field">
          <span class="filter-bar-label">Sortierung</span>
          <select class="filter-sort-by">
            ${SORT_OPTIONS.map(
              (opt) => `
              <option value="${opt.value}" ${this._sortBy === opt.value ? "selected" : ""}>
                ${escapeHtml(opt.label)}
              </option>
            `
            ).join("")}
          </select>
        </label>
      </div>
    `;
  }

  _revokeObjectUrls() {
    (this._objectUrls || []).forEach((u) => URL.revokeObjectURL(u));
    this._objectUrls = [];
  }

  // Papierkorb-Button (seit v1.0.5b3, EXPERIMENTELL) - siehe Moduldoku oben.
  // Blendet die Zeile optimistisch sofort aus, ruft den neuen
  // delete_voicemail_message-Entity-Service auf (siehe sensor.py), und
  // blendet die Zeile bei einem fehlgeschlagenen Service-Call (z. B. TR-064-
  // Fehler auf der FRITZ!Box) wieder ein - das Löschen selbst ist
  // unwiderruflich, das optimistische Ausblenden hier ist es bewusst nicht.
  //
  // `key` (seit v1.0.6b2, der zusammengesetzte "<tam>:<id>"-Schlüssel aus
  // _voicemailsFor()) für den optimistischen UI-Status, `messageId`/
  // `entityId` unverändert die rohen Werte für den eigentlichen
  // Service-Call - bei nur einem Anrufbeantworter entspricht `entityId`
  // weiterhin exakt `this._config.entity_voicemail`.
  async _deleteVoicemailMessage(key, messageId, entityId) {
    if (!entityId || !this._hass) return;
    this._pendingDeletedMessageIds.add(key);
    this._render();
    try {
      await this._hass.callService("fritzbox_anrufe", "delete_voicemail_message", {
        message_id: messageId,
        entity_id: entityId,
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("fritzbox_anrufe: Löschen der Anrufbeantworter-Nachricht fehlgeschlagen", err);
      this._pendingDeletedMessageIds.delete(key);
      this._render();
    }
  }

  _render() {
    if (!this._config || !this._hass) return;

    // A full re-render tears down and rebuilds every node below, including
    // any <audio> currently playing a downloaded recording - release the
    // blob URLs backing those before they become unreachable.
    this._revokeObjectUrls();

    // The active tab might no longer be visible (e.g. its category was just
    // switched off in the editor) - fall back before painting.
    if (!this._visibleFilterTypes().includes(this._activeFilter)) {
      this._activeFilter = this._defaultFilter();
    }

    // Persistente Wurzelknoten (seit v1.3.0b0, Hint „Theme geht beim
    // Tab-Wechsel verloren"): NICHT mehr den kompletten shadowRoot.innerHTML
    // ersetzen. Ein voller innerHTML-Reset entfernt auch von AUSSEN in den
    // Shadow-Root injizierte <style>-Elemente (z. B. von card_mod bzw. einem
    // globalen UIX-Theme). Die wurden zwar beim ersten Öffnen angewandt, gingen
    // aber bei jedem Re-Render (Tab-/Filterwechsel) wieder verloren, weil sie
    // mit weggeräumt wurden. Stattdessen: ein eigener, dauerhafter <style> plus
    // ein Inhalts-Container, deren Inhalt hier nur AKTUALISIERT wird - fremde
    // Geschwisterknoten im Shadow-Root (die externen Styles) bleiben erhalten.
    if (
      !this._styleEl ||
      !this._contentEl ||
      this._styleEl.parentNode !== this.shadowRoot ||
      this._contentEl.parentNode !== this.shadowRoot
    ) {
      this.shadowRoot.textContent = "";
      this._styleEl = document.createElement("style");
      this._contentEl = document.createElement("div");
      this._contentEl.className = "fba-root";
      this.shadowRoot.appendChild(this._styleEl);
      this.shadowRoot.appendChild(this._contentEl);
    }
    this._styleEl.textContent = this._styles();

    // Überschrift optional (seit v1.3.0b0, show_title). Ohne header-Attribut
    // rendert ha-card keine Kopfzeile.
    const headerAttr =
      this._config.show_title === false
        ? ""
        : ` header="${escapeHtml(this._config.title)}"`;
    this._contentEl.innerHTML = `
      <ha-card${headerAttr}>
        <div class="card-content">
          ${this._renderLiveBanner()}
          ${this._renderTabs()}
          ${this._renderFilterBar()}
          ${this._renderMainContent()}
        </div>
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll(".tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        this._activeFilter = btn.dataset.filter;
        this._lastSignature = this._computeSignature();
        this._render();
      });
    });

    const ownNumberSelect = this.shadowRoot.querySelector(".filter-own-number");
    if (ownNumberSelect) {
      ownNumberSelect.addEventListener("change", () => {
        this._filterOwnNumber = ownNumberSelect.value;
        this._lastSignature = this._computeSignature();
        this._render();
      });
    }

    const sortSelect = this.shadowRoot.querySelector(".filter-sort-by");
    if (sortSelect) {
      sortSelect.addEventListener("change", () => {
        this._sortBy = sortSelect.value;
        this._lastSignature = this._computeSignature();
        this._render();
      });
    }

    // Anrufbeantworter Ein/Aus-Schalter (seit v1.1.0, nur bei aktivem
    // show_tam_switch gerendert, siehe _renderTamSwitches()).
    this.shadowRoot.querySelectorAll(".tam-switch-toggle").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        // In der Telefoniegeräte-Tabelle steckt der Schalter in einer
        // anklickbaren Zeile (öffnet sonst das Detail-Popup) - der Klick auf
        // den Schalter darf das Popup NICHT mitöffnen.
        event.stopPropagation();
        this._toggleTamSwitch(btn.dataset.entity, btn.dataset.state);
      });
    });

    // Telefoniegeräte-Tabelle (Einstellungen-Tab, seit v1.3.0b2): Klick auf
    // eine Zeile öffnet das Detail-Popup; Klick auf das Overlay/den
    // Schließen-Button schließt es wieder. Reiner UI-Laufzeitstatus
    // (this._settingsPopupIndex), daher ein einfacher Re-Render.
    this.shadowRoot.querySelectorAll(".settings-table-row.clickable").forEach((row) => {
      row.addEventListener("click", (event) => {
        if (event.target.closest(".tam-switch-toggle")) return;
        const idx = Number(row.dataset.deviceIndex);
        this._settingsPopupIndex = Number.isInteger(idx) ? idx : null;
        this._render();
      });
    });
    const popupBackdrop = this.shadowRoot.querySelector(".settings-popup-backdrop");
    if (popupBackdrop) {
      popupBackdrop.addEventListener("click", (event) => {
        // Nur ein Klick auf den Hintergrund (nicht auf das Popup selbst) schließt.
        if (event.target === popupBackdrop) {
          this._settingsPopupIndex = null;
          this._render();
        }
      });
    }
    const popupClose = this.shadowRoot.querySelector(".settings-popup-close");
    if (popupClose) {
      popupClose.addEventListener("click", () => {
        this._settingsPopupIndex = null;
        this._render();
      });
    }

    // Akkordeon-Abschnitte (seit v1.2.0, siehe _renderVoicemailAccordion()) -
    // bewusst KEIN _render() hier: das native <details>-Element klappt sich
    // bereits selbst auf/zu, ein voller Re-Render würde nur unnötig das DOM
    // austauschen (und, falls in einem ANDEREN Abschnitt gerade eine
    // Anrufbeantworter-Nachricht abgespielt wird, dessen <audio>-Element
    // zerstören - siehe _hasActiveMediaPlayback()/Moduldoku oben). Der
    // "toggle"-Event-Listener spiegelt den neuen Zustand nur in
    // this._tamAccordionOpen, damit er einen späteren, aus anderem Grund
    // ausgelösten Re-Render übersteht.
    this.shadowRoot.querySelectorAll(".voicemail-accordion-section").forEach((details) => {
      details.addEventListener("toggle", () => {
        const n = Number(details.dataset.tam);
        if (Number.isInteger(n)) {
          this._tamAccordionOpen[n] = details.open;
        }
      });
    });

    // Live-AB-Regler (seit v1.2.0, siehe _renderTamPicker()) - anders als
    // der Akkordeon-Toggle oben MUSS dies einen echten Re-Render auslösen,
    // da sich dadurch ändert, WELCHE Anrufbeantworter überhaupt angezeigt
    // werden (nicht nur ein Auf-/Zuklapp-Zustand innerhalb der bestehenden
    // Darstellung) - ein reiner CSS-/DOM-Attributwechsel würde hier nicht
    // ausreichen.
    this.shadowRoot.querySelectorAll(".voicemail-tam-picker-checkbox").forEach((cb) => {
      cb.addEventListener("change", () => {
        const n = Number(cb.dataset.tam);
        if (Number.isInteger(n)) {
          this._tamPickerVisible[n] = cb.checked;
          this._render();
        }
      });
    });

    this.shadowRoot.querySelectorAll(".voicemail-play-btn").forEach((btn) => {
      btn.addEventListener("click", () =>
        playVoicemail(
          this._hass,
          btn,
          (url) => this._objectUrls.push(url),
          () => this._catchUpRender()
        )
      );
    });

    // Papierkorb-Button + Inline-Bestätigung (seit v1.0.5b3, EXPERIMENTELL) -
    // siehe Moduldoku oben. Zwei getrennte Klicks statt eines nativen
    // confirm(): erster Klick zeigt "Wirklich löschen?" nur für DIESE
    // Nachricht (ein erneuter Re-Render tauscht die anderen Zeilen nicht an).
    this.shadowRoot.querySelectorAll(".voicemail-delete-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this._confirmDeleteMessageId = btn.dataset.key;
        this._render();
      });
    });
    this.shadowRoot.querySelectorAll(".voicemail-delete-confirm-no").forEach((btn) => {
      btn.addEventListener("click", () => {
        this._confirmDeleteMessageId = null;
        this._render();
      });
    });
    this.shadowRoot.querySelectorAll(".voicemail-delete-confirm-yes").forEach((btn) => {
      btn.addEventListener("click", () => {
        const wrap = btn.closest(".voicemail-delete-confirm");
        const key = wrap && wrap.dataset.key;
        const messageId = wrap && wrap.dataset.messageId;
        const entityId = wrap && wrap.dataset.entityId;
        this._confirmDeleteMessageId = null;
        if (key && messageId && entityId) {
          this._deleteVoicemailMessage(key, messageId, entityId);
        } else {
          this._render();
        }
      });
    });

    this.shadowRoot.querySelectorAll(".row-processing.clickable").forEach((row) => {
      row.addEventListener("click", () => {
        // Once playback has started the row holds a native <audio> element -
        // let its own controls handle further clicks instead of re-triggering.
        if (row.querySelector("audio")) return;
        if (row.dataset.mediaUrl) {
          playCallRecording(
            this._hass,
            row,
            (url) => this._objectUrls.push(url),
            () => this._catchUpRender()
          );
          return;
        }
        if (row.dataset.targetTab) {
          this._activeFilter = row.dataset.targetTab;
          this._lastSignature = this._computeSignature();
          this._render();
        }
      });
    });
  }

  // CSS-Custom-Property-Deklarationen für alle konfigurierbaren Farben
  // (seit v1.0.4) - ein leerer/nicht gesetzter config-Wert fällt auf den
  // bisherigen, festen Theme-Farbwert zurück (COLOR_CONFIG_KEYS), ein
  // ungültiger Wert wird von sanitizeColor() verworfen (ebenfalls Fallback).
  _colorVars() {
    const cfg = this._config || {};
    return Object.entries(COLOR_CONFIG_KEYS)
      .map(([key, { cssVar, fallback }]) => {
        const value = sanitizeColor(cfg[`color_${key}`]) || fallback;
        return `${cssVar}: ${value};`;
      })
      .join("\n        ");
  }

  _styles() {
    return `
      :host {
        ${this._colorVars()}
      }

      ${BASE_CARD_STYLES}

      .live-banner {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        margin-bottom: 12px;
        border-radius: 8px;
        background: var(--fba-color-live-banner);
        color: var(--text-primary-color, #fff);
      }
      .live-banner ha-icon { --mdc-icon-size: 28px; flex-shrink: 0; }
      .live-banner-text { display: flex; flex-direction: column; min-width: 0; }
      .live-state { font-weight: 600; }
      .live-detail {
        font-size: 0.9em;
        opacity: 0.9;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .tabs {
        display: flex;
        gap: 4px;
        margin-bottom: 8px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        overflow-x: auto;
      }
      .tab {
        display: flex;
        align-items: center;
        gap: 6px;
        flex: 1 1 auto;
        /* min-width: 0 overrides the flexbox default of "min-width: auto"
           (= the label's un-wrapped content width), which is what let a
           tab's own label force the whole .tabs row wider than the card
           and trigger its horizontal scrollbar - most noticeably once
           "Eingehend" (v1.0.3) became the longer "Angenommen". With this,
           a tab can now shrink below its label's natural width; the label
           itself truncates with an ellipsis (see ".tab span" below)
           instead of forcing an overflow. */
        min-width: 0;
        justify-content: center;
        background: none;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 8px 6px;
        cursor: pointer;
        color: var(--secondary-text-color, #727272);
        font: inherit;
        white-space: nowrap;
      }
      .tab ha-icon { --mdc-icon-size: 20px; flex-shrink: 0; }
      .tab.active {
        color: var(--fba-color-tab-active);
        border-bottom-color: var(--fba-color-tab-active);
        font-weight: 600;
      }
      .tab span {
        font-size: 0.8em;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      /* Filter-/Sortierleiste (seit v1.0.4b3, nur bei show_filter_bar) */
      .filter-bar {
        display: flex;
        flex-wrap: wrap;
        column-gap: 16px;
        row-gap: 6px;
        align-items: center;
        padding: 4px 0 10px;
        margin-bottom: 4px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }
      .filter-bar-field {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.8em;
        color: var(--secondary-text-color, #727272);
      }
      .filter-bar-field select {
        font: inherit;
        font-size: 1em;
        color: var(--primary-text-color, #212121);
        background: var(--card-background-color, #fff);
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 6px;
        padding: 4px 6px;
        max-width: 160px;
      }

      .rows { display: flex; flex-direction: column; }
      .row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }
      .row:last-child { border-bottom: none; }
      .row-icon {
        flex-shrink: 0;
        color: var(--fba-color-row-icon);
        --mdc-icon-size: 20px;
      }
      .row-main { flex: 1 1 auto; min-width: 0; }
      .row-primary { display: flex; align-items: center; gap: 4px; }
      .row-name {
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .vip { --mdc-icon-size: 14px; color: var(--fba-color-vip); }
      .row-secondary {
        display: flex;
        gap: 8px;
        font-size: 0.85em;
        color: var(--secondary-text-color, #727272);
        overflow: hidden;
      }
      .row-number,
      .row-own-number { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .row-date { flex-shrink: 0; }
      .row-extra {
        flex-shrink: 0;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 2px;
        font-size: 0.8em;
        color: var(--secondary-text-color, #727272);
        text-align: right;
      }

      ${VOICEMAIL_ROWS_STYLES}
      ${PROCESSING_ROW_STYLES}
      ${TABS_CONTAINER_QUERY_STYLES}

      /* --- Responsive: schmale Ansicht (Smartphone) --- */
      @media (max-width: 500px) {
        .card-content { padding: 4px 10px 10px; }
        .tab span { display: none; }
        .tab ha-icon { --mdc-icon-size: 24px; }
        .row-extra .row-device { display: none; }
      }
    `;
  }
}

/**
 * fritzbox-anrufe-card-editor
 * -----------------------------
 * Graphical config editor shown by the Lovelace card picker/edit dialog.
 * Built on Home Assistant's own <ha-form> so it automatically matches the
 * standard HA look (entity pickers, toggles, number field) instead of a
 * hand-rolled UI.
 */

const EDITOR_LABELS = {
  title: "Titel",
  show_title: "Überschrift (Titel) anzeigen",
  show_einstellungen: "Kategorie 'Einstellungen' anzeigen (experimentell)",
  entity_live: "Sensor: Live-Anrufmonitor (optional)",
  entity_eingehend: "Sensor: Angenommene Anrufe",
  entity_ausgehend: "Sensor: Ausgehende Anrufe",
  entity_verpasst: "Sensor: Verpasste Anrufe",
  entity_voicemail: "Sensor: Anrufbeantworter (optional)",
  entity_voicemail_2: "Sensor: Zweiter Anrufbeantworter (optional)",
  entity_voicemail_3: "Sensor: Dritter Anrufbeantworter (optional)",
  entity_voicemail_4: "Sensor: Vierter Anrufbeantworter (optional)",
  entity_voicemail_5: "Sensor: Fünfter Anrufbeantworter (optional)",
  voicemail_2_mode: "Darstellung bei mehreren Anrufbeantwortern",
  entity_tam_switch: "Schalter: Anrufbeantworter Ein/Aus (optional)",
  entity_tam_switch_2: "Schalter: Zweiter Anrufbeantworter Ein/Aus (optional)",
  entity_tam_switch_3: "Schalter: Dritter Anrufbeantworter Ein/Aus (optional)",
  entity_tam_switch_4: "Schalter: Vierter Anrufbeantworter Ein/Aus (optional)",
  entity_tam_switch_5: "Schalter: Fünfter Anrufbeantworter Ein/Aus (optional)",
  show_tam_switch: "Anrufbeantworter-Ein/Aus-Schalter auf der Karte anzeigen",
  max_rows: "Max. Zeilen",
  show_alle: "Kategorie 'Gesamt' (Alle) anzeigen",
  show_eingehend: "Kategorie 'Angenommen' anzeigen",
  show_ausgehend: "Kategorie 'Ausgehend' anzeigen",
  show_verpasst: "Kategorie 'Verpasst' anzeigen",
  show_anrufbeantworter: "Kategorie 'Anrufbeantworter' anzeigen",
  show_voicemail_1: "Anrufbeantworter 1 einbeziehen",
  show_voicemail_2: "Anrufbeantworter 2 einbeziehen",
  show_voicemail_3: "Anrufbeantworter 3 einbeziehen",
  show_voicemail_4: "Anrufbeantworter 4 einbeziehen",
  show_voicemail_5: "Anrufbeantworter 5 einbeziehen",
  show_name: "Name anzeigen",
  show_number: "Nummer anzeigen",
  show_own_number: "Eigene Rufnummer anzeigen",
  show_device: "Gerät anzeigen",
  show_duration: "Dauer anzeigen",
  show_date: "Datum/Uhrzeit anzeigen",
  show_vip: "VIP-Markierung anzeigen",
  show_processing_alle: "Weiterverarbeitung auf 'Gesamt' anzeigen",
  show_processing_eingehend: "Weiterverarbeitung bei 'Angenommen' anzeigen",
  show_processing_ausgehend: "Weiterverarbeitung bei 'Ausgehend' anzeigen",
  show_processing_verpasst: "Weiterverarbeitung bei 'Verpasst' anzeigen",
  show_filter_bar: "Filter-/Sortierleiste auf der Karte anzeigen",
  show_delete_button: "Papierkorb-Button zum Löschen von Anrufbeantworter-Nachrichten anzeigen",
  hide_spam: "Als Spam erkannte Anrufe/Nachrichten ausblenden",
  // Farben (seit v1.0.4, seit v1.0.4b1 nicht mehr über <ha-form> gerendert)
  // sind hier absichtlich NICHT mehr gelistet - siehe COLOR_EDITOR_FIELDS
  // und FritzboxAnrufeCardEditor._buildColorSection() weiter unten.
};

// EDITOR_HELPERS/computeEditorHelper: kurzer Hilfetext unter einzelnen
// Feldern, falls die laufende <ha-form>-Version computeHelper unterstützt
// (siehe _renderConfig()) - andernfalls folgenlos ignoriert.
const EDITOR_HELPERS = {
  show_filter_bar:
    "Zeigt auf der Karte eine Leiste zum Filtern nach eigener Rufnummer (nur Anrufliste, nicht Anrufbeantworter) und zum Sortieren (Datum/Dauer/Name).",
  show_delete_button:
    "EXPERIMENTELL: Löschen ist unwiderruflich - die FRITZ!Box selbst hat keinen Papierkorb dafür. Vor dem endgültigen Löschen erscheint eine Bestätigung.",
  hide_spam:
    "Spam wird über die Integrationseinstellungen definiert (FRITZ!Box-eigene Sperrliste und/oder eine von dir gepflegte Nummernliste) - siehe Einstellungen -> Geräte & Dienste -> FRITZ!Box Anrufe -> Konfigurieren.",
  voicemail_2_mode:
    "Nur mit mindestens 'Sensor: Zweiter Anrufbeantworter' gesetzt. 'Gemischt' und 'Getrennt' funktionieren ausschließlich mit GENAU zwei Anrufbeantwortern. 'Akkordeon' zeigt je Anrufbeantworter einen einzeln auf-/zuklappbaren Abschnitt (ein Abschnitt mit ungehörten Nachrichten öffnet sich beim ersten Anzeigen automatisch) und ist die einzige Darstellung, sobald drei oder mehr Anrufbeantworter konfiguriert sind - die Einstellung wird dann unabhängig vom hier gewählten Wert erzwungen.",
  show_voicemail_1:
    "Legt den Grundzustand fest, ob dieser Anrufbeantworter standardmäßig einbezogen wird. Ab zwei konfigurierten Anrufbeantwortern lässt sich das zusätzlich direkt auf der Karte per Checkbox temporär ändern, ohne die Karte zu bearbeiten.",
  show_voicemail_2:
    "Legt den Grundzustand fest, ob dieser Anrufbeantworter standardmäßig einbezogen wird. Ab zwei konfigurierten Anrufbeantwortern lässt sich das zusätzlich direkt auf der Karte per Checkbox temporär ändern, ohne die Karte zu bearbeiten.",
  show_voicemail_3:
    "Legt den Grundzustand fest, ob dieser Anrufbeantworter standardmäßig einbezogen wird. Ab zwei konfigurierten Anrufbeantwortern lässt sich das zusätzlich direkt auf der Karte per Checkbox temporär ändern, ohne die Karte zu bearbeiten.",
  show_voicemail_4:
    "Legt den Grundzustand fest, ob dieser Anrufbeantworter standardmäßig einbezogen wird. Ab zwei konfigurierten Anrufbeantwortern lässt sich das zusätzlich direkt auf der Karte per Checkbox temporär ändern, ohne die Karte zu bearbeiten.",
  show_voicemail_5:
    "Legt den Grundzustand fest, ob dieser Anrufbeantworter standardmäßig einbezogen wird. Ab zwei konfigurierten Anrufbeantwortern lässt sich das zusätzlich direkt auf der Karte per Checkbox temporär ändern, ohne die Karte zu bearbeiten.",
  show_tam_switch:
    "EXPERIMENTELL: Zeigt vor der Nachrichten-Auflistung im Anrufbeantworter-Tab einen Ein/Aus-Schalter (benötigt einen unter 'Sensoren' gesetzten Schalter). Der angezeigte Zustand ist keine bestätigte Rücklesung vom FRITZ!Box-Gerät, siehe README.",
};

function computeEditorLabel(schemaItem) {
  return EDITOR_LABELS[schemaItem.name] || schemaItem.name;
}

function computeEditorHelper(schemaItem) {
  return EDITOR_HELPERS[schemaItem.name] || "";
}

// Seit v1.0.4 in Abschnitte gruppiert (Home Assistant seit einiger Zeit als
// <ha-form>-Schema-Typ "expandable" verfügbar), damit der mittlerweile recht
// lange Editor übersichtlich bleibt - per Nutzerwunsch, nachdem die Liste
// der Einzelfelder unhandlich geworden war. "flatten: true" sorgt dafür,
// dass die Werte trotz der visuellen Gruppierung weiterhin als flaches
// Konfigurationsobjekt gespeichert werden (identische YAML-Schlüssel wie
// zuvor) - siehe Moduldoku oben für den Hinweis zur Versionsabhängigkeit.
const EDITOR_SCHEMA = [
  { name: "title", selector: { text: {} } },
  {
    name: "",
    type: "expandable",
    title: "Sensoren",
    icon: "mdi:radar",
    flatten: true,
    expanded: true,
    schema: [
      { name: "entity_live", selector: { entity: { domain: "sensor" } } },
      { name: "entity_eingehend", selector: { entity: { domain: "sensor" } } },
      { name: "entity_ausgehend", selector: { entity: { domain: "sensor" } } },
      { name: "entity_verpasst", selector: { entity: { domain: "sensor" } } },
      // Anrufbeantworter-Sensoren + -Schalter als eigenes, zuklappbares
      // Unter-Akkordeon innerhalb von "Sensoren" (seit v1.2.2). Umgesetzt als
      // verschachteltes ha-form-"expandable" mit flatten:true, sodass die
      // Feldnamen weiterhin direkt auf die Top-Level-Config-Schlüssel
      // abbilden (entity_voicemail, entity_voicemail_2..5,
      // entity_tam_switch, entity_tam_switch_2..5) - es ändert sich rein die
      // Editor-Gruppierung, nicht die gespeicherte Konfiguration. Bewusst
      // standardmäßig eingeklappt (expanded:false), um die "Sensoren"-Sektion
      // aufzuräumen: bis zu 10 AB-bezogene Picker liegen sonst lang zwischen
      // den vier Anruf-Sensoren. Die reinen Sichtbarkeits-/Anzeige-Regler der
      // Anrufbeantworter (show_voicemail_1..5, show_tam_switch,
      // voicemail_2_mode) bleiben bewusst in "Kategorien"/"Darstellung" -
      // hier stehen nur die Entity-Picker selbst.
      {
        name: "",
        type: "expandable",
        title: "Anrufbeantworter",
        icon: "mdi:voicemail",
        flatten: true,
        expanded: false,
        schema: [
          { name: "entity_voicemail", selector: { entity: { domain: "sensor" } } },
          { name: "entity_voicemail_2", selector: { entity: { domain: "sensor" } } },
          // Slot 3-5 (seit v1.2.0) - siehe CONFIG_DEFAULTS/_activeTamSlots().
          { name: "entity_voicemail_3", selector: { entity: { domain: "sensor" } } },
          { name: "entity_voicemail_4", selector: { entity: { domain: "sensor" } } },
          { name: "entity_voicemail_5", selector: { entity: { domain: "sensor" } } },
          // Seit v1.1.0, EXPERIMENTELL - eigene switch-Domäne, siehe
          // CONFIG_DEFAULTS für den Grund, warum dies kein von
          // entity_voicemail abgeleitetes Feld ist, sondern ein eigener Picker.
          { name: "entity_tam_switch", selector: { entity: { domain: "switch" } } },
          { name: "entity_tam_switch_2", selector: { entity: { domain: "switch" } } },
          { name: "entity_tam_switch_3", selector: { entity: { domain: "switch" } } },
          { name: "entity_tam_switch_4", selector: { entity: { domain: "switch" } } },
          { name: "entity_tam_switch_5", selector: { entity: { domain: "switch" } } },
        ],
      },
      // Der Einstellungen-Sensor (sensor.fritzbox_anrufe_einstellungen) wird
      // seit v1.3.0b2 IMMER automatisch gefunden (siehe _settingsEntityId());
      // ein eigener Sensor-Picker entfällt daher (Nutzerwunsch).
    ],
  },
  {
    name: "",
    type: "expandable",
    title: "Kategorien",
    icon: "mdi:filter-variant",
    flatten: true,
    expanded: false,
    schema: [
      { name: "show_alle", selector: { boolean: {} } },
      { name: "show_eingehend", selector: { boolean: {} } },
      { name: "show_ausgehend", selector: { boolean: {} } },
      { name: "show_verpasst", selector: { boolean: {} } },
      // Einstellungen-Kategorie (seit v1.3.0b0, Zahnrad-Tab) - Standard AUS,
      // siehe CONFIG_DEFAULTS/_visibleFilterTypes(). EXPERIMENTELL.
      { name: "show_einstellungen", selector: { boolean: {} } },
      // Die Anrufbeantworter-Kategorie-Schalter (seit v1.3.0b0) als eigenes,
      // zuklappbares Unter-Akkordeon innerhalb von "Kategorien" (analog zu
      // "Sensoren" seit v1.2.2) - `flatten: true`, also rein visuelle
      // Gruppierung, die Feldnamen/Config bleiben unverändert. Enthält den
      // Kategorie-Hauptschalter `show_anrufbeantworter` sowie den Grundzustand
      // je Slot (`show_voicemail_1..5`, seit v1.2.0 - nur mit gesetztem
      // entity_voicemail_N von Bedeutung, siehe _renderTamPicker()).
      {
        name: "",
        type: "expandable",
        title: "Anrufbeantworter",
        icon: "mdi:voicemail",
        flatten: true,
        expanded: false,
        schema: [
          { name: "show_anrufbeantworter", selector: { boolean: {} } },
          { name: "show_voicemail_1", selector: { boolean: {} } },
          { name: "show_voicemail_2", selector: { boolean: {} } },
          { name: "show_voicemail_3", selector: { boolean: {} } },
          { name: "show_voicemail_4", selector: { boolean: {} } },
          { name: "show_voicemail_5", selector: { boolean: {} } },
        ],
      },
    ],
  },
  {
    name: "",
    type: "expandable",
    title: "Darstellung",
    icon: "mdi:table-column",
    flatten: true,
    expanded: false,
    schema: [
      // Überschrift der Karte ein-/ausblenden (seit v1.3.0b0).
      { name: "show_title", selector: { boolean: {} } },
      // "slider" statt "box": das Zahlenfeld ("box") ließ sich bei manchen
      // Nutzern nicht zuverlässig per Tastatur bearbeiten (Eingaben wurden
      // teils zurückgesetzt) - ein Schieberegler kommt komplett ohne
      // Texteingabe aus und umgeht das Problem. Wer mehr als 15 Zeilen
      // braucht, kann max_rows weiterhin über den YAML-Editor der Karte auf
      // einen beliebigen Wert setzen.
      { name: "max_rows", selector: { number: { min: 1, max: 15, step: 1, mode: "slider" } } },
      { name: "show_name", selector: { boolean: {} } },
      { name: "show_number", selector: { boolean: {} } },
      { name: "show_own_number", selector: { boolean: {} } },
      { name: "show_device", selector: { boolean: {} } },
      { name: "show_duration", selector: { boolean: {} } },
      { name: "show_date", selector: { boolean: {} } },
      { name: "show_vip", selector: { boolean: {} } },
      { name: "show_filter_bar", selector: { boolean: {} } },
      { name: "show_delete_button", selector: { boolean: {} } },
      { name: "hide_spam", selector: { boolean: {} } },
      // Seit v1.1.0, EXPERIMENTELL - siehe CONFIG_DEFAULTS/_renderTamSwitches().
      // Bewusst hier in "Darstellung" (nicht "Sensoren"), da dies der rein
      // optische Sichtbarkeits-Regler ist - die zugehörigen Entity-Picker
      // (entity_tam_switch/entity_tam_switch_2) stehen wie gewohnt oben unter
      // "Sensoren".
      { name: "show_tam_switch", selector: { boolean: {} } },
      {
        name: "voicemail_2_mode",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "merged", label: "Gemischt (eine Liste, mit AB-1/AB-2-Badge, nur bei genau 2 ABs)" },
              { value: "separate", label: "Getrennt (Abschnitte untereinander, nur bei genau 2 ABs)" },
              { value: "accordion", label: "Akkordeon (auf-/zuklappbare Abschnitte, ab 3 ABs erzwungen)" },
            ],
          },
        },
      },
    ],
  },
  {
    name: "",
    type: "expandable",
    title: "Weiterverarbeitung",
    icon: "mdi:arrow-decision-outline",
    flatten: true,
    expanded: false,
    schema: [
      { name: "show_processing_alle", selector: { boolean: {} } },
      { name: "show_processing_eingehend", selector: { boolean: {} } },
      { name: "show_processing_ausgehend", selector: { boolean: {} } },
      { name: "show_processing_verpasst", selector: { boolean: {} } },
    ],
  },
  // Keine "Farben"-Gruppe mehr hier (siehe Moduldoku oben) - die Sektion
  // wird seit v1.0.4b1 separat, nativ und mit grafischer Farbauswahl von
  // FritzboxAnrufeCardEditor._buildColorSection() gerendert.
];

// --- Farben-Editor (seit v1.0.4b1) ------------------------------------
//
// Ein Eintrag je konfigurierbarer Farbe: config-Schlüssel, Beschriftung,
// ein Hex-Näherungswert für das grafische <input type="color">-Swatch bzw.
// den "aktuell verwendet"-Hilfetext, und optional eine zusätzliche Notiz
// (bei den 5 Kategorie-Icon-Farben, deren tatsächlicher Standard vom
// Tab-Status abhängt statt eines einzelnen festen Werts). fallbackHex ist
// bewusst NUR eine Näherung fürs Editor-UI - der tatsächliche CSS-Fallback
// (inkl. Theme-Variable, z. B. "var(--success-color, #4caf50)") bleibt
// COLOR_CONFIG_KEYS/PROCESSING_COLOR_VARS vorbehalten und wird weiterhin
// dort verwendet, wenn die Karte selbst rendert.
const CATEGORY_ICON_COLOR_NOTE =
  "Standard: folgt der Tab-Farbe (aktiv/inaktiv) - hier unabhängig vom Tab-Status fest einstellbar.";

const COLOR_EDITOR_FIELDS = [
  { key: "color_tab_active", label: "Aktiver Tab", fallbackHex: "#03a9f4" },
  { key: "color_success", label: "Erfolgreich (angenommen/verbunden)", fallbackHex: "#4caf50" },
  {
    key: "color_error",
    label: "Nicht erfolgreich (nicht erreicht/nicht verbunden)",
    fallbackHex: "#db4437",
  },
  {
    key: "color_playback",
    label: "Wiedergabe (Abspielen-Button, Anrufbeantworter-Symbol, 'Neu'-Markierung)",
    fallbackHex: "#03a9f4",
  },
  { key: "color_vip", label: "VIP-Markierung", fallbackHex: "#ff9800" },
  { key: "color_row_icon", label: "Anruf-Symbole in der Liste", fallbackHex: "#727272" },
  { key: "color_live_banner", label: "Live-Banner-Hintergrund", fallbackHex: "#03a9f4" },
  {
    key: "color_icon_alle",
    label: "Symbol Kategorie 'Alle'",
    fallbackHex: "#727272",
    note: CATEGORY_ICON_COLOR_NOTE,
  },
  {
    key: "color_icon_eingehend",
    label: "Symbol Kategorie 'Angenommen'",
    fallbackHex: "#727272",
    note: CATEGORY_ICON_COLOR_NOTE,
  },
  {
    key: "color_icon_ausgehend",
    label: "Symbol Kategorie 'Ausgehend'",
    fallbackHex: "#727272",
    note: CATEGORY_ICON_COLOR_NOTE,
  },
  {
    key: "color_icon_verpasst",
    label: "Symbol Kategorie 'Verpasst'",
    fallbackHex: "#727272",
    note: CATEGORY_ICON_COLOR_NOTE,
  },
  {
    key: "color_icon_anrufbeantworter",
    label: "Symbol Kategorie 'Anrufbeantworter'",
    fallbackHex: "#727272",
    note: CATEGORY_ICON_COLOR_NOTE,
  },
];

// <input type="color"> verlangt zwingend die 6-stellige #rrggbb-Form -
// weder 3-stellige Kurzschreibweise (#4c5) noch rgb()/hsl()/var()/
// Farbnamen werden akzeptiert. Wird zum Anzeigen eines evtl. 3-stelligen
// Hex-Fallbacks im Swatch gebraucht; für alles andere (rgb()/var()/...)
// bleibt das Swatch beim fallbackHex stehen, siehe _updateColorSection().
function normalizeHex(hex) {
  const h = String(hex || "").replace("#", "");
  if (h.length === 3) {
    return "#" + h.split("").map((c) => c + c).join("");
  }
  return "#" + h;
}

const HEX_COLOR_RE = /^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$/;

const COLOR_EDITOR_STYLES = `
  .fba-color-editor {
    margin-top: 12px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 8px;
    padding: 0 12px;
  }
  .fba-color-editor summary {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 0;
    cursor: pointer;
    /* Explicit 16px/500 instead of just inheriting the ambient font-size -
       matches <ha-expansion-panel>'s own header text (used by the other 4
       accordion groups) regardless of whatever smaller base font-size the
       surrounding HA editor dialog cascades in. Left implicit, this summary
       rendered visibly smaller than the other 4 headers - see v1.0.4b3 in
       the module docstring. */
    font-size: 16px;
    font-weight: 500;
    color: var(--primary-text-color, #212121);
    /* Hide the browser's own <summary> disclosure marker - we render our own
       chevron icon instead (see .fba-color-editor-chevron below), so it can
       be positioned/rotated identically across browsers/WebViews. Without
       this, some engines show no marker at all (observed in the Companion
       App), others show one on the left in a different style than the
       chevron-down icon <ha-form>'s own expandable groups use on the right -
       either way it looked inconsistent/missing next to the other 4
       accordion sections. */
    list-style: none;
  }
  .fba-color-editor summary::-webkit-details-marker { display: none; }
  .fba-color-editor summary::marker { display: none; }
  /* 24px, not 20px: the standard ha-icon/MDC default size, matching the
     leading icon and chevron <ha-form> renders for the other 4 accordion
     groups - see v1.0.4b3 in the module docstring for why this changed. */
  .fba-color-editor summary > ha-icon:first-child {
    --mdc-icon-size: 24px;
    color: var(--secondary-text-color, #727272);
  }
  .fba-color-editor-chevron {
    margin-left: auto;
    --mdc-icon-size: 24px;
    color: var(--secondary-text-color, #727272);
    transition: transform 0.2s ease;
  }
  .fba-color-editor[open] > summary .fba-color-editor-chevron {
    transform: rotate(180deg);
  }
  .fba-color-editor-body {
    padding: 4px 0 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .fba-color-reset-row { display: flex; justify-content: flex-end; }
  .fba-color-reset-button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 6px;
    padding: 6px 10px;
    background: none;
    color: var(--primary-text-color, #212121);
    font: inherit;
    font-size: 0.85em;
    cursor: pointer;
  }
  .fba-color-reset-button:hover { background: var(--secondary-background-color, rgba(0, 0, 0, 0.04)); }
  .fba-color-reset-button ha-icon { --mdc-icon-size: 16px; }
  .fba-color-row { display: flex; flex-direction: column; gap: 4px; }
  .fba-color-row-label { font-size: 0.9em; color: var(--primary-text-color, #212121); }
  .fba-color-row-controls { display: flex; align-items: center; gap: 8px; }
  .fba-color-row-controls input[type="color"] {
    width: 36px;
    height: 36px;
    padding: 0;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 6px;
    cursor: pointer;
    background: none;
  }
  .fba-color-row-controls input[type="text"] {
    flex: 1 1 auto;
    min-width: 0;
    padding: 8px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 6px;
    font: inherit;
    color: var(--primary-text-color, #212121);
    background: var(--card-background-color, #fff);
    box-sizing: border-box;
  }
  .fba-color-row-helper { font-size: 0.75em; color: var(--secondary-text-color, #727272); }
`;

class FritzboxAnrufeCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = withDefaults(config);
    this._renderConfig();
  }

  set hass(hass) {
    this._hass = hass;
    // IMPORTANT: only refresh the form's `hass` reference here (needed so
    // e.g. entity pickers see current entity state/translations) - do NOT
    // also reset `.data` on every hass tick. Home Assistant pushes a new
    // hass object to every card/editor on ANY entity state change system-
    // wide, completely unrelated to this form; re-assigning `.data` each
    // time reset the underlying <ha-form> number/text inputs mid-edit,
    // which made it look like a value (e.g. typing "5" over "10") could
    // never "stick" - every keystroke got wiped by the next hass update
    // before the user could finish. `.data` is now only set from
    // setConfig()/_renderConfig() - i.e. on genuine external config
    // changes, not on unrelated background hass churn.
    if (this._form) {
      this._form.hass = hass;
    } else {
      this._renderConfig();
    }
  }

  _valueChanged(ev) {
    ev.stopPropagation();
    this._config = ev.detail.value;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }

  _renderConfig() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => this._valueChanged(ev));
      this._form.schema = EDITOR_SCHEMA;
      this._form.computeLabel = computeEditorLabel;
      // computeHelper is a newer <ha-form> hook (short description text
      // under a field); if the running frontend version doesn't support it,
      // it's simply never called - safe to always set.
      this._form.computeHelper = computeEditorHelper;
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;

    // Farben-Sektion (seit v1.0.4b1) - siehe Moduldoku und
    // _buildColorSection() unten. Wie beim <ha-form> oben nur bei einer
    // ECHTEN externen Config-Änderung neu befüllen (setConfig()/erster
    // hass-Aufruf), NICHT bei jedem hass-Tick - siehe die ausführliche
    // Begründung im hass-Setter oben, dasselbe Problem (Eingaben würden bei
    // jedem unabhängigen hass-Update überschrieben) gilt hier genauso.
    if (!this._colorSection) {
      this._colorSection = this._buildColorSection();
      this.appendChild(this._colorSection);
    }
    this._updateColorSection();
  }

  // Baut die "Farben"-Sektion einmalig als natives <details>-Akkordeon mit
  // einer Zeile je COLOR_EDITOR_FIELDS-Eintrag: ein grafisches
  // <input type="color">-Swatch (Klick öffnet den Farbwähler des
  // Betriebssystems/Browsers) plus ein Textfeld für den vollen CSS-Wert
  // (var()/rgb()/hsl()/Farbnamen - alles, was das Swatch selbst nicht
  // abbilden kann). Bewusst NICHT über <ha-form> gelöst (siehe Moduldoku
  // oben): <ha-form> hat keinen eingebauten Selector-Typ, der gleichzeitig
  // beliebige CSS-Werte UND eine grafische Farbauswahl UND den aktuell
  // wirksamen Wert anzeigen kann - natives HTML ist hier zugleich
  // funktional passender und unabhängig von der HA-Frontend-Version.
  _buildColorSection() {
    const details = document.createElement("details");
    details.className = "fba-color-editor";

    const style = document.createElement("style");
    style.textContent = COLOR_EDITOR_STYLES;
    details.appendChild(style);

    const summary = document.createElement("summary");
    summary.innerHTML =
      `<ha-icon icon="mdi:palette-outline"></ha-icon><span>Farben</span>` +
      `<ha-icon class="fba-color-editor-chevron" icon="mdi:chevron-down"></ha-icon>`;
    details.appendChild(summary);

    const body = document.createElement("div");
    body.className = "fba-color-editor-body";
    details.appendChild(body);

    const resetRow = document.createElement("div");
    resetRow.className = "fba-color-reset-row";
    resetRow.innerHTML =
      `<button type="button" class="fba-color-reset-button">` +
      `<ha-icon icon="mdi:restore"></ha-icon><span>Alle Farben zurücksetzen</span>` +
      `</button>`;
    resetRow.querySelector(".fba-color-reset-button").addEventListener("click", () =>
      this._resetAllColors()
    );
    body.appendChild(resetRow);

    this._colorInputs = {};
    this._focusedColorKey = null;

    COLOR_EDITOR_FIELDS.forEach((field) => {
      const row = document.createElement("div");
      row.className = "fba-color-row";
      row.innerHTML = `
        <div class="fba-color-row-label">${escapeHtml(field.label)}</div>
        <div class="fba-color-row-controls">
          <input type="color" class="fba-color-swatch" aria-label="${escapeHtml(field.label)} (grafische Auswahl)" />
          <input type="text" class="fba-color-text" placeholder="${escapeHtml(field.fallbackHex)}" />
        </div>
        <div class="fba-color-row-helper"></div>
      `;
      const swatch = row.querySelector(".fba-color-swatch");
      const text = row.querySelector(".fba-color-text");

      // Swatch -> Textfeld: <input type="color"> liefert immer ein gültiges
      // #rrggbb, das direkt als CSS-Wert übernommen werden kann.
      swatch.addEventListener("input", () => {
        text.value = swatch.value;
        this._onColorFieldChange(field.key, swatch.value);
      });

      // Textfeld -> config: erst bei "change" (Verlassen des Felds/Enter),
      // nicht bei jedem Tastenanschlag - vermeidet unnötig viele
      // config-changed-Events während des Tippens.
      text.addEventListener("change", () => {
        this._onColorFieldChange(field.key, text.value);
      });
      // _updateColorSection() darf ein Feld, das der Nutzer gerade
      // bearbeitet, nicht überschreiben (gleiches Prinzip wie beim
      // hass-Setter oben) - eigene Fokus-Verfolgung statt
      // document.activeElement, da Letzteres über Shadow-DOM-Grenzen
      // hinweg (z. B. innerhalb eines HA-Dialogs) nicht zuverlässig auf
      // dieses konkrete <input> zeigt.
      text.addEventListener("focus", () => {
        this._focusedColorKey = field.key;
      });
      text.addEventListener("blur", () => {
        if (this._focusedColorKey === field.key) this._focusedColorKey = null;
      });

      body.appendChild(row);
      this._colorInputs[field.key] = { row, swatch, text };
    });

    return details;
  }

  _onColorFieldChange(key, rawValue) {
    this._config = { ...this._config, [key]: rawValue };
    this._updateColorSection();
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }

  // "Alle Farben zurücksetzen" (seit v1.0.4b2) - leert alle 12 color_*-
  // Schlüssel in einem Zug (= zurück zum bisherigen, festen
  // Theme-Farbverhalten), statt jedes der 12 Felder einzeln leeren zu
  // müssen. Löscht bewusst den Fokus-Schutz für diese eine Aktion (siehe
  // _updateColorSection()) - ein expliziter Zurücksetzen-Klick soll IMMER
  // greifen, auch falls der Nutzer gerade in einem der Textfelder tippt.
  // Ein einziges config-changed-Event mit allen 12 geänderten Werten, nicht
  // 12 einzelne.
  _resetAllColors() {
    const cleared = {};
    COLOR_EDITOR_FIELDS.forEach((field) => {
      cleared[field.key] = "";
    });
    this._config = { ...this._config, ...cleared };
    this._focusedColorKey = null;
    this._updateColorSection();
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }

  // Aktualisiert Swatch/Textfeld/Hilfetext je Farbfeld anhand von
  // this._config - insbesondere den "aktuell verwendet"-Hinweis (expliziter
  // Wert, sonst der Standardwert), siehe Moduldoku/Farben-Editor-Kommentar
  // oben.
  _updateColorSection() {
    if (!this._colorInputs) return;
    const cfg = this._config || {};
    COLOR_EDITOR_FIELDS.forEach((field) => {
      const inputs = this._colorInputs[field.key];
      if (!inputs) return;
      const raw = String(cfg[field.key] || "").trim();

      inputs.swatch.value = HEX_COLOR_RE.test(raw) ? normalizeHex(raw) : field.fallbackHex;

      if (this._focusedColorKey !== field.key) {
        inputs.text.value = raw;
      }

      const helperParts = [
        raw ? `Aktuell verwendet: ${raw}` : `Aktuell verwendet (Standard): ${field.fallbackHex}`,
      ];
      if (field.note) helperParts.push(field.note);
      inputs.row.querySelector(".fba-color-row-helper").textContent = helperParts.join(" – ");
    });
  }
}

customElements.define("fritzbox-anrufe-card", FritzboxAnrufeCard);
customElements.define("fritzbox-anrufe-card-editor", FritzboxAnrufeCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "fritzbox-anrufe-card",
  name: "FRITZ!Box Anrufe",
  description:
    "Zeigt eingehende, ausgehende und verpasste FRITZ!Box-Anrufe als filterbare Liste inkl. Live-Anzeige und Anrufbeantworter - jede Kategorie einzeln ein-/ausblendbar.",
});
