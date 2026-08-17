# FRITZ!Box Anrufe

Home-Assistant-Integration für den Anrufmonitor und die Anruflisten (eingehend,
ausgehend, verpasst) einer AVM FRITZ!Box. Basiert auf der in Home Assistant
integrierten "FRITZ!Box Call Monitor"-Komponente, erweitert um historische
Anruflisten-Sensoren, konfigurierbare Verlaufstiefe je Sensor und eine
mitgelieferte Dashboard-Karte.

## Inhalt

- [Funktionsumfang](#funktionsumfang)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Einrichtung](#einrichtung)
- [Sensoren](#sensoren)
- [Spam-Erkennung](#spam-erkennung-seit-version-110-optional)
- [Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111)
- [Anrufbeantworter Ein/Aus-Schalter](#anrufbeantworter-einaus-schalter-seit-version-110-experimentell)
- [Einstellungen (Optionen)](#einstellungen-optionen)
- [Dashboard-Karte](#dashboard-karte)
- [Icon](#icon)
- [Bekannte Einschränkungen](#bekannte-einschränkungen)
- [Versionshistorie](#versionshistorie)
- [Datei-Integrität (Hash-Kommentare)](#datei-integrität-hash-kommentare)
- [Fehlerbehebung](#fehlerbehebung)

## Funktionsumfang

- Live-Anrufmonitor (klingelt/wählt/spricht/inaktiv) in Echtzeit über den
  FRITZ!Box-Callmonitor (TCP-Port 1012), wie bei der Kernintegration.
- Drei zusätzliche Sensoren für die Anruflisten: eingehend, ausgehend,
  verpasst - inklusive Anrufer-/Angerufener-Name (aus dem Telefonbuch),
  Nummer, Zeitpunkt, Dauer und Gerät je Anruf.
- Verlaufstiefe je Sensor unabhängig einstellbar (Anzahl der Anrufe ODER
  Anzahl Tage), bereits bei der Erst-Einrichtung und jederzeit später über
  die Integrations-Optionen änderbar.
- Mitgelieferte, interaktive Dashboard-Karte (`fritzbox-anrufe-card`) mit
  Icon-Filterleiste, Live-Banner und responsivem Layout - keine manuelle
  Lovelace-Ressource nötig.
- Optionale Filter-/Sortierleiste direkt auf der Karte (seit Version
  1.0.4, `show_filter_bar`): nach eigener Rufnummer filtern und nach
  Datum/Dauer/Name sortieren, ohne den Editor zu öffnen - siehe
  [Filter-/Sortierleiste](#filter-sortierleiste-seit-version-104-optional).
- Grafischer Karten-Editor (Home-Assistant-Standardformular): Sensoren,
  Zeilenanzahl, einzeln zuschaltbare Kategorien (Alle/Gesamt, Angenommen,
  Ausgehend, Verpasst, Anrufbeantworter) und einzeln zuschaltbare Spalten
  (Name, Nummer, eigene Rufnummer, Gerät, Dauer, Datum, VIP) lassen sich
  ohne YAML einstellen.
- **Experimentell:** Anrufbeantworter-Sensor mit Nachrichtenliste (an echter
  Hardware bestätigt funktionsfähig) und abspielbaren Sprachnachrichten
  direkt im Dashboard (siehe [Bekannte Einschränkungen](#bekannte-einschränkungen)),
  als 5. Symbol/Tab in der Kartenkopfzeile - nicht als Bereich unterhalb der
  Anrufliste.
- Neues Event `fritzbox_anrufe_new_voicemail_message` (seit Version
  1.1.0), gefeuert sobald eine bislang unbekannte
  Anrufbeantworter-Nachricht eintrifft - direkt als Automations-Auslöser
  nutzbar, ohne die `messages`-Attributliste selbst per Vorlage auf neue
  Einträge vergleichen zu müssen, siehe
  [Event bei neuer Anrufbeantworter-Nachricht](#event-bei-neuer-anrufbeantworter-nachricht-seit-version-110).
- **Spam-Erkennung** (seit Version 1.1.0, optional): Anrufe und
  Anrufbeantworter-Nachrichten werden als Spam markiert, wenn die FRITZ!Box
  sie bereits selbst blockiert hat UND/ODER die Nummer mit einer selbst
  gepflegten Liste übereinstimmt - die FRITZ!Box hat dafür keine eigene,
  automatische Erkennung, siehe
  [Spam-Erkennung](#spam-erkennung-seit-version-110-optional). Spam-Einträge
  lassen sich auf der Dashboard-Karte optional ausblenden (`hide_spam`).
- **Mehrere Anrufbeantworter** (bis zu 5, seit Version 1.1.1, optional):
  Sind auf der FRITZ!Box mehrere Anrufbeantworter eingerichtet, lässt sich
  deren Anzahl per Schaltfläche in den Integrations-Einstellungen erhöhen -
  jeder wird als eigener Sensor (plus Ein/Aus-Schalter) abgerufen, siehe
  [Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111).
  Die Dashboard-Karte zeigt den zweiten Anrufbeantworter optional direkt mit
  an (`entity_voicemail_2`, gemischt oder in getrennten Abschnitten);
  Anrufbeantworter 3 bis 5 lassen sich über zusätzliche Karteninstanzen
  einbinden.
- **Experimentell, neu seit Version 1.1.0: Anrufbeantworter Ein/Aus-Schalter**:
  ein neuer Schalter (`switch`-Entität, TR-064-Aktion `SetEnable`) pro
  konfiguriertem Anrufbeantworter (auch für den zweiten, falls aktiviert)
  schaltet diesen ein bzw. aus, siehe
  [Anrufbeantworter Ein/Aus-Schalter](#anrufbeantworter-einaus-schalter-seit-version-110-experimentell).
  Auf der Dashboard-Karte optional anzeigbar (`show_tam_switch`, Editor-
  Bereich "Darstellung"), direkt vor der Nachrichten-Auflistung im
  Anrufbeantworter-Tab.
- Alternative: einfache YAML-Tabellenkarte auf Basis von `flex-table-card`
  (siehe [`examples/dashboard_flex_table.yaml`](examples/dashboard_flex_table.yaml)).

## Voraussetzungen

**Wichtig:** Die folgenden zwei Schritte müssen **direkt in der
FRITZ!Box-Oberfläche** (`http://fritz.box` oder die IP der Box) erledigt
werden, **bevor** die Integration in Home Assistant installiert/eingerichtet
wird - ohne sie schlägt entweder die Einrichtung fehl oder einzelne Sensoren
bleiben dauerhaft `unavailable`.

### 1. Callmonitor aktivieren

Der Live-Anrufmonitor-Sensor (`fritzbox_anrufe_live`) hört auf einem eigenen
Port (1012) mit, der auf der FRITZ!Box standardmäßig **deaktiviert** ist:

1. Ein an der FRITZ!Box angeschlossenes Telefon (Fest- oder IP-Telefon)
   nehmen und die Ziffernfolge `#96*5*` wählen. Kurz klingeln lassen bzw.
   auflegen reicht - der Anruf muss nicht angenommen werden.
2. Zum Deaktivieren (z. B. zum Testen) analog `#96*4*` wählen.

Zusätzlich muss der **TR-064-Zugriff** aktiviert sein - darüber laufen die
Anruflisten-, Anrufbeantworter- und Options-Abfragen:

3. FRITZ!Box-Oberfläche → **Heimnetz → Netzwerk → Netzwerkeinstellungen**
   (Reiter) → Häkchen bei **"Zugriff für Anwendungen zulassen"** setzen und
   speichern.

Ohne Schritt 1 bleibt ausschließlich der Live-Sensor `unavailable` (der Rest
funktioniert unabhängig davon); ohne Schritt 3 funktioniert die gesamte
Integration nicht, da sie ohne TR-064 keine Verbindung aufbauen kann.

### 2. FRITZ!Box-Benutzerkonto einrichten

Die Integration meldet sich mit einem regulären FRITZ!Box-Benutzerkonto an
(nicht mit einem separaten API-Schlüssel) - dieses Konto muss vorher
angelegt bzw. mit den richtigen Berechtigungen versehen werden:

1. FRITZ!Box-Oberfläche → **System → FRITZ!Box-Benutzer** →
   "Benutzer hinzufügen" (oder ein bestehendes Konto bearbeiten).
2. Benutzername und Kennwort vergeben - diese Zugangsdaten werden später bei
   der Einrichtung der Integration in Home Assistant abgefragt.
3. Unter **"Berechtigungen für diesen Benutzer"** mindestens ankreuzen:
   - **"FRITZ!Box-Einstellungen"** (Grundvoraussetzung für jeglichen
     TR-064-Zugriff).
   - **"Sprachnachrichten, Faxnachrichten, FRITZ!App Fon und Anrufliste"**
     (wird für die drei Verlaufs-Sensoren UND den
     Anrufbeantworter-Sensor benötigt). Fehlt diese Berechtigung, bleiben
     genau diese vier Sensoren `unavailable` - der Live-Sensor ist davon
     unabhängig, da er nicht über TR-064, sondern über den separaten
     Callmonitor-Port läuft.
4. Speichern.

Erst wenn beide Schritte erledigt sind, mit [Installation](#installation)
fortfahren.

### Home Assistant

Aktuelle Version empfohlen (getestet mit Python 3.14+, wie von aktuellen
Home-Assistant-Releases vorausgesetzt).

## Installation

### Über HACS (empfohlen)

1. HACS → Integrationen → drei Punkte oben rechts → "Benutzerdefinierte
   Repositories" → URL `https://github.com/Meine-smarte-Welt/fritzbox_anrufe`,
   Kategorie "Integration" hinzufügen (falls das Repository nicht bereits
   als Standard-Repository gelistet ist).
2. "FRITZ!Box Anrufe" suchen und herunterladen.
3. Home Assistant **vollständig neu starten** (nicht nur neu laden).

### Manuell

1. Den Ordner `custom_components/fritzbox_anrufe` aus diesem Repository nach
   `<Home-Assistant-Konfigurationsverzeichnis>/custom_components/fritzbox_anrufe`
   kopieren.
2. Home Assistant vollständig neu starten.

## Einrichtung

1. Einstellungen → Geräte & Dienste → "+ Integration hinzufügen" →
   "FRITZ!Box Anrufe" suchen.
2. Zugangsdaten eingeben: Host/IP, Port (Standard 1012 für den Callmonitor),
   Benutzername, Passwort des oben genannten FRITZ!Box-Kontos.
3. Falls mehrere Telefonbücher vorhanden sind: gewünschtes Telefonbuch
   auswählen.
4. **Verlaufstiefe festlegen**: Für jeden der drei Anruflisten-Sensoren
   (eingehend/ausgehend/verpasst) getrennt auswählen, ob er nach *Anzahl*
   oder nach *Tagen* begrenzt werden soll, und den jeweiligen Wert per
   Dropdown wählen. Standardwert, falls nichts geändert wird: **10 Anrufe**
   je Sensor. Diese Einstellung lässt sich später jederzeit unter
   "Konfigurieren" wieder ändern (siehe [Einstellungen](#einstellungen-optionen)).

## Sensoren

Pro konfiguriertem Telefonbuch/FRITZ!Box-Konto werden fünf Sensoren angelegt:

| Sensor (Übersetzungsschlüssel) | Beschreibung | Zustand | Attribut |
| --- | --- | --- | --- |
| `fritzbox_anrufe_live` | Live-Anrufmonitor | `idle` / `ringing` / `dialing` / `talking` | - (siehe Live-Attribute unten) |
| `fritzbox_anrufe_eingehend` | Angenommene Anrufe | Anzahl gespeicherter Anrufe | `calls`: Liste angenommener Anrufe |
| `fritzbox_anrufe_ausgehend` | Ausgehende Anrufe | Anzahl gespeicherter Anrufe | `calls`: Liste ausgehender Anrufe |
| `fritzbox_anrufe_verpasst` | Verpasste Anrufe | Anzahl gespeicherter Anrufe | `calls`: Liste verpasster Anrufe |
| `fritzbox_anrufe_anrufbeantworter` **(experimentell)** | Anrufbeantworter-Nachrichten | Anzahl gespeicherter Nachrichten | `messages`: Liste der Sprachnachrichten |

Zusätzlich legt die Integration seit Version 1.1.0 pro konfiguriertem
Anrufbeantworter eine `switch`-Entität an (Übersetzungsschlüssel
`fritzbox_anrufe_anrufbeantworter_schalter`, für Anrufbeantworter 2 bis 5
entsprechend `fritzbox_anrufe_anrufbeantworter_2_schalter` bis `_5_schalter`,
seit Version 1.1.1 bis zu fünf statt bisher höchstens zwei) - siehe
[Anrufbeantworter Ein/Aus-Schalter](#anrufbeantworter-einaus-schalter-seit-version-110-experimentell).

Die Verlaufs- und der Anrufbeantworter-Sensor werden **nicht** über den
Callmonitor befüllt, sondern alle 5 Minuten per TR-064 von der FRITZ!Box
abgerufen (`X_AVM-DE_OnTel`/`GetCallList` bzw. `X_AVM-DE_TAM1`/
`GetMessageList`) - der Callmonitor liefert nur Live-Ereignisse, keine
Historie. Seit Version 1.0.3 löst der Live-Sensor zusätzlich eine gezielte
Aktualisierung beider Sensoren aus, sobald sein Zustand nach einem
Klingeln/Wählen/Gespräch wieder auf `idle` wechselt (mit 5 Sekunden
Verzögerung, damit die FRITZ!Box den neuen Anrufliste-Eintrag bzw. eine
ggf. aufgezeichnete Nachricht verarbeiten kann) - das deckt auch verpasste
Anrufe ab, nicht nur tatsächlich geführte Gespräche, und sorgt dafür, dass
ein Anruf in der Regel binnen weniger Sekunden statt erst nach bis zu 5
Minuten in den Sensoren erscheint. Die reguläre 5-Minuten-Aktualisierung
bleibt zusätzlich als Rückfallebene bestehen.

Jeder Eintrag in `calls` enthält: `type`, `date` (ISO-Zeitstempel), `name`
(aus dem Telefonbuch oder vom FRITZ!Box-Anruflisteneintrag), `number`,
`own_number`, `device`, `duration`, `vip` (Telefonbuch-Kategorie "wichtig"),
sowie seit Version 1.0.3 zusätzlich `outcome` und `media_url`:

- `outcome` beschreibt, wie der Anruf konkret ausgegangen ist (feiner als
  `type`): `beantwortet` (eingehend, von einer Person angenommen),
  `anrufbeantworter` (an den Anrufbeantworter weitergeleitet, Nachricht
  aufgezeichnet - zählt seit 1.0.3 zu `verpasst`, siehe unten),
  `keine_nachricht` (an den Anrufbeantworter weitergeleitet, aber keine
  Nachricht aufgezeichnet - neu seit 1.0.3, vorher Teil von `nicht_erreicht`),
  `nicht_erreicht` (verpasst, ohne dass die Integration eine Weiterleitung an
  den Anrufbeantworter feststellen konnte - z. B. aufgelegt, bevor der
  Anrufbeantworter ansprang, oder kein Anrufbeantworter aktiv/konfiguriert),
  `verbunden` (ausgehend, Gespräch zustande gekommen) sowie `nicht_verbunden`
  (ausgehend, keine Verbindung - fasst "besetzt" und "niemand nimmt ab"
  zusammen, siehe [Bekannte Einschränkungen](#bekannte-einschränkungen)).
  Wird von der Dashboard-Karte für die optionale
  "Weiterverarbeitung"-Zeile ausgewertet (siehe
  [Dashboard-Karte](#dashboard-karte)).

  Ein ausgehender Anruf ohne zustande gekommene Verbindung (`nicht_verbunden`)
  erscheint bei `fritzbox_anrufe_ausgehend` **nicht** über die reguläre
  TR-064-Abfrage - die FRITZ!Box trägt einen solchen Versuch dort
  überhaupt nicht ein, selbst nicht mit Dauer 0 (Bestätigung an echter
  Hardware). Stattdessen erkennt die Integration einen erfolglosen
  ausgehenden Anruf direkt über den Live-Callmonitor (Zustand wechselt von
  "Wählen" zurück auf "Idle", ohne zwischenzeitlich "Gespräch läuft" zu
  erreichen) und trägt ihn selbst in die Liste ein. Das funktioniert nur
  für Anrufe, die auftreten, während diese Integration läuft - Versuche
  vor dem letzten Neustart von Home Assistant bzw. vor der Installation
  dieser Version sind nicht rückwirkend rekonstruierbar.

  Ob ein eingehender Anruf an den Anrufbeantworter weitergeleitet wurde,
  erkennt die Integration am von der FRITZ!Box selbst gemeldeten
  "Gerät"-Wert (`device: "Anrufbeantworter"`); ob dabei tatsächlich eine
  Nachricht aufgezeichnet wurde, wird zusätzlich per Datum/Uhrzeit- (und,
  falls vorhanden, Rufnummer-)Abgleich mit den echten
  Anrufbeantworter-Nachrichten bestätigt (nicht mehr nur anhand des
  call-list-eigenen `Path`-Felds, das dafür nicht immer gesetzt ist).
- `media_url` ist gesetzt, sobald zu diesem Anruf eine Anrufbeantworter-
  Aufnahme vorliegt (`outcome: anrufbeantworter`) - eine Home-Assistant-
  interne, authentifizierte URL, über die die Aufnahme direkt im Browser
  abgespielt werden kann, analog zu `media_url` bei `messages` (siehe
  unten). Wurde die zugehörige Anrufbeantworter-Nachricht per Datum/
  Uhrzeit-Abgleich eindeutig gefunden, zeigt `media_url` direkt auf
  denselben, bereits an echter Hardware bestätigten Proxy wie beim
  Anrufbeantworter-Sensor selbst.

**Verhaltensänderung ab Version 1.0.3:** Ein eingehender Anruf, der an den
Anrufbeantworter weitergeleitet wurde (unabhängig davon, ob dabei eine
Nachricht aufgezeichnet wurde), zählt jetzt zu `fritzbox_anrufe_verpasst`
statt zu `fritzbox_anrufe_eingehend` - `eingehend` enthält damit nur noch
tatsächlich von einer Person angenommene Anrufe. Das entspricht der
Kategorisierung, die auch die FRITZ!Box-Weboberfläche selbst verwendet.
Zusätzlich werden seit 1.0.3 auch von der FRITZ!Box selbst abgewiesene
Anrufe (z. B. per Rufnummernblockierung) korrekt als `verpasst` erfasst -
zuvor erschienen solche Anrufe in keinem der drei Verlaufs-Sensoren.

Der Live-Sensor liefert je nach Zustand u. a. `from`/`to`/`with`,
`from_name`/`to_name`/`with_name`, `device`, `duration`, `vip`.

Jeder Eintrag in `messages` (Anrufbeantworter, experimentell) enthält:
`name`, `number`, `date` (ISO-Zeitstempel), `duration`, `new` (bool, ob die
Nachricht noch nicht abgehört wurde), `vip`, sowie `media_url` - eine
Home-Assistant-interne, authentifizierte URL, über die die Aufnahme direkt
im Browser abgespielt werden kann (siehe [Dashboard-Karte](#dashboard-karte)).

### Entity-IDs

Die Sensoren heißen intern `fritzbox_anrufe_live`/`_eingehend`/`_ausgehend`/
`_verpasst`/`_anrufbeantworter` (Übersetzungsschlüssel, steuert den je nach
Home-Assistant-Spracheinstellung übersetzten Anzeigenamen sowie das Icon).
Seit Version 1.0.3 heißt `_eingehend` in der Oberfläche "Angenommene Anrufe"
bzw. auf der Dashboard-Karte "Angenommen" - der interne Schlüssel
`eingehend` sowie alle entity_ids, unique_ids und Konfigurationsschlüssel
bleiben davon unberührt, um bestehende Installationen nicht zu brechen.

Ab Version 1.0.1 wird zusätzlich die **technische entity_id** bei der
Ersteinrichtung fest auf genau diese Werte reserviert, z. B.
`sensor.fritzbox_anrufe_eingehend` (unabhängig von der Sprache, da
entity_ids in Home Assistant grundsätzlich sprachneutral bleiben sollen).
Das gilt für neu angelegte Entities; bereits vorhandene Entities aus einer
älteren Installation behalten ihre bisherige entity_id (Home Assistant
ändert bestehende entity_ids nie automatisch, um Automatisierungen nicht zu
brechen). Wer bei einem Bestandssystem auf die neuen, festen IDs wechseln
möchte: die fünf betroffenen Entities unter Einstellungen → Geräte &
Dienste → Entitäten einmalig löschen und die Integration danach neu laden
lassen - sie werden dann mit der festen entity_id neu angelegt. Bei mehr
als einem FRITZ!Box-Konto bekommt das zweite/dritte Konto automatisch die
Endungen `_2`/`_3` (normales Home-Assistant-Verhalten bei ID-Kollisionen).

### Event bei neuer Anrufbeantworter-Nachricht (seit Version 1.1.0)

Sobald der Anrufbeantworter-Sensor beim regulären Abruf der
Nachrichtenliste (alle 5 Minuten, oder mit kurzer Verzögerung direkt nach
einem Anruf, siehe oben) eine Nachricht entdeckt, die beim vorherigen
Abruf noch nicht bekannt war, feuert die Integration zusätzlich zur
aktualisierten `messages`-Attributliste ein eigenes Home-Assistant-Event
`fritzbox_anrufe_new_voicemail_message` - direkt als Automations-Auslöser
nutzbar, ohne selbst per Vorlage (Template) die alte gegen die neue
`messages`-Liste auf neu hinzugekommene Einträge vergleichen zu müssen.

Beim allerersten Abruf nach einem (Neu-)Start von Home Assistant wird
bewusst **kein** Event gefeuert - sonst gäbe es bei jedem Neustart Events
für längst bekannte, nur noch nicht abgehörte Nachrichten. Ab dem zweiten
erfolgreichen Abruf danach gilt eine Nachricht als "neu", sobald ihre ID
beim vorherigen Abruf noch nicht bekannt war - unabhängig vom "Neu"-Status
der Nachricht selbst (der könnte theoretisch schon wieder gelöscht sein,
z. B. weil sie zwischenzeitlich direkt an der FRITZ!Box abgehört wurde).

Das Event-Datenobjekt (`event_data`) enthält:

| Feld | Bedeutung |
| --- | --- |
| `entry_id` | ID des Integrations-Eintrags (bei mehreren FRITZ!Box-Konten zur Unterscheidung) |
| `message_id` | Rohe FRITZ!Box-Nachrichten-ID (entspricht `messages[].id`) |
| `number` | Rufnummer des Anrufers, falls von der FRITZ!Box übermittelt |
| `name` | Name des Anrufers, falls von der FRITZ!Box übermittelt - **kein** Abgleich mit dem Home-Assistant-Telefonbuch dieser Integration, anders als das `name`-Feld in `messages` |
| `date` | Zeitpunkt der Nachricht (ISO-Zeitstempel) |
| `duration` | Länge der Aufnahme |
| `media_url` | Home-Assistant-interne, authentifizierte URL zum Abspielen (wie bei `messages[].media_url`), `null` falls die FRITZ!Box keinen Aufnahmepfad übermittelt hat |

Beispiel-Automation (Push-Benachrichtigung mit Anrufername/-nummer):

```yaml
trigger:
  - trigger: event
    event_type: fritzbox_anrufe_new_voicemail_message
action:
  - action: notify.mobile_app_dein_handy
    data:
      title: "Neue Anrufbeantworter-Nachricht"
      message: "{{ trigger.event.data.name or trigger.event.data.number or 'Unbekannt' }}"
```

### Spam-Erkennung (seit Version 1.1.0, optional)

**Wichtig:** Die FRITZ!Box selbst hat über die TR-064-Schnittstelle keine
eigene, automatische Spam-/KI-Erkennung - anders als der Name "Spam-
Erkennung" vermuten lassen könnte, liefert `GetCallList` kein natives
Feld dafür. Diese Integration kombiniert stattdessen zwei Signale zu
einem Gesamturteil "ist das Spam":

1. **Die FRITZ!Box hat den Anruf bereits selbst blockiert** (z. B. über
   eine eigene Telefonbuch-/Rufsperre-Regel, die auch von Drittanbieter-
   Tools wie PhoneBlock oder SpamBlockUp befüllt worden sein kann).
2. **Die Nummer stimmt mit einer selbst gepflegten Liste** von
   Spam-Nummern/-Vorwahlen überein (Options-Flow, `spam_numbers`,
   kommagetrennt) - Präfix-Abgleich, es reicht also z. B. eine Vorwahl wie
   `0900` für alle Nummern, die damit beginnen.

Ein Anruf oder eine Anrufbeantworter-Nachricht gilt als Spam, sobald
**mindestens eines** der beiden Signale zutrifft. Ohne konfigurierte Liste
(`spam_numbers` leer) wirkt ausschließlich das erste Signal. Das Ergebnis
steht als `spam`-Feld (`true`/`false`) in den `calls`- und
`messages`-Attributlisten der jeweiligen Sensoren sowie im Event-Payload
von `fritzbox_anrufe_new_voicemail_message` zur Verfügung - nutzbar für
eigene Automatisierungen (z. B. Spam-Anrufe von Push-Benachrichtigungen
ausschließen) und für die mitgelieferte Dashboard-Karte, die Spam-Einträge
optional mit einem Badge markiert oder ganz ausblendet (`hide_spam`, siehe
[Dashboard-Karte](#dashboard-karte)).

### Mehrere Anrufbeantworter (bis zu 5, seit Version 1.1.1)

Manche FRITZ!Box-Modelle/-Konfigurationen erlauben mehr als einen
Anrufbeantworter. Seit Version 1.1.1 lässt sich die Anzahl der von dieser
Integration abgefragten Anrufbeantworter über Einstellungen → Geräte &
Dienste → FRITZ!Box Anrufe → "Konfigurieren" → **Anrufbeantworter
verwalten** per Schaltfläche schrittweise von 1 auf bis zu 5 erhöhen (bzw.
wieder verringern) - jeder Klick auf "Weiteren Anrufbeantworter
hinzufügen"/"Anrufbeantworter entfernen" ändert die konfigurierte Anzahl um
genau 1, "Fertig" übernimmt den zuletzt angezeigten Stand. Für jeden so
konfigurierten Anrufbeantworter legt die Integration einen eigenen Sensor
(`fritzbox_anrufe_anrufbeantworter_2` bis `_5`) mit denselben Fähigkeiten
wie der erste an (Wiedergabe, Löschen, automatisch als gelesen markieren,
Event bei neuer Nachricht mit zusätzlichem `tam`-Feld im Payload, z. B.
`"tam": "3"`), sowie einen zugehörigen Ein/Aus-Schalter (siehe
[Anrufbeantworter Ein/Aus-Schalter](#anrufbeantworter-einaus-schalter-seit-version-110-experimentell)).

**Bestehende Installationen (Migration von `second_tam_enabled`):** Wer
bereits vor Version 1.1.1 die (jetzt entfallene) Option "Zweiten
Anrufbeantworter aktivieren" eingeschaltet hatte, muss nichts weiter tun -
die Integration übernimmt beim ersten Start nach dem Update automatisch
"aktiviert" → Anzahl 2 bzw. "deaktiviert" → Anzahl 1 in die neue Einstellung
und schreibt das genau einmal in die Konfiguration zurück. Die bisherige
entity_id `sensor.fritzbox_anrufe_anrufbeantworter_2` bleibt dabei
unverändert erhalten.

Hat die eigene FRITZ!Box gar nicht so viele Anrufbeantworter wie
konfiguriert, bleiben die überzähligen Sensoren einfach dauerhaft "nicht
verfügbar" - das blockiert die übrige Integration zu keinem Zeitpunkt,
genau wie beim ersten Anrufbeantworter bei fehlender Berechtigung oder
unbestätigter TR-064-API-Form (siehe
[Bekannte Einschränkungen](#bekannte-einschränkungen)).

**Wichtig - EXPERIMENTELL für Anrufbeantworter 2 bis 5:** Nur der erste
Anrufbeantworter (Index 0) ist an echter Hardware bestätigt. Für die
Anrufbeantworter 2 bis 5 nimmt die Integration lediglich an, dass die
FRITZ!Box deren TR-064-Indizes fortlaufend (1, 2, 3, 4) vergibt - das ist
NICHT unabhängig bestätigt (siehe den Modul-Docstring in `tam.py`). Bei
Auffälligkeiten (z. B. eine falsche Nachrichtenliste hinter Anrufbeantworter
3) bitte ein GitHub-Issue mit Angabe der tatsächlichen Anzahl und
Reihenfolge der Anrufbeantworter am eigenen Gerät eröffnen.

**Auf der Dashboard-Karte anzeigen:** Seit Version 1.2.0 unterstützt die
mitgelieferte Karte alle bis zu fünf Anrufbeantworter DIREKT in derselben
Karte - dafür im Editor (oder per YAML) unter "Sensoren" zusätzlich zu
`entity_voicemail_2` auch `entity_voicemail_3`/`_4`/`_5` auf die
entsprechenden Sensoren setzen (`sensor.fritzbox_anrufe_anrufbeantworter_3`
bis `_5`). `voicemail_2_mode` bestimmt dann, WIE die konfigurierten Listen
dargestellt werden:

- **`merged`** (Standard, nur bei GENAU zwei konfigurierten
  Anrufbeantwortern wählbar): eine gemeinsame, chronologisch gemischte
  Liste - jede Nachricht bekommt ein kleines "AB 1"/"AB 2"-Badge, damit
  erkennbar bleibt, von welchem Anrufbeantworter sie stammt.
- **`separate`** (ebenfalls nur bei genau zwei): eigene, überschriebene
  Abschnitte ("Anrufbeantworter 1"/"Anrufbeantworter 2") untereinander,
  jeweils unvermischt - ohne Badge, da die Überschriften bereits eindeutig
  trennen.
- **`accordion`** (neu in Version 1.2.0): je Anrufbeantworter ein
  unabhängig auf-/zuklappbarer Abschnitt. Ein Abschnitt mit mindestens
  einer neuen ("Neu"-Status) Nachricht öffnet sich beim ersten Anzeigen der
  Karte automatisch, alle anderen starten eingeklappt; danach entscheidet
  ausschließlich ein Klick auf den jeweiligen Abschnitt, ob er offen ist
  (auch mehrere gleichzeitig möglich). Sobald mehr als zwei
  Anrufbeantworter konfiguriert sind, verwendet die Karte automatisch
  "accordion", unabhängig vom hier eingestellten Wert - "merged"/"separate"
  sind nur für genau zwei Listen sinnvoll definiert.

**Welcher Anrufbeantworter angezeigt wird, ist zweistufig wählbar (seit
Version 1.2.0):** Die Editor-Schalter `show_voicemail_1` bis `_5`
("Kategorien", Standard AN für alle) legen den dauerhaft gespeicherten
Grundzustand fest, welche konfigurierten Anrufbeantworter grundsätzlich
einbezogen werden. Sobald zwei oder mehr Anrufbeantworter konfiguriert
sind, erscheint zusätzlich direkt auf der Karte selbst eine Reihe kleiner
Kontrollkästchen ("AB 1", "AB 2", …) - damit lässt sich beim Betrachten des
Dashboards schnell ein einzelner Anrufbeantworter isolieren oder wieder
einblenden, ohne die Karte zu bearbeiten. Diese Auswahl ist reiner
Anzeige-Laufzeitstatus (geht beim Neuladen der Karte wieder auf den
Editor-Grundzustand zurück, genau wie die bestehende Filter-/Sortierleiste)
und wirkt auf alle drei obigen Darstellungen gleichermaßen. Werden alle
Anrufbeantworter abgewählt, erscheint statt der Nachrichten-Auflistung ein
Hinweistext - die Kontrollkästchen selbst bleiben sichtbar, um mindestens
einen wieder einzublenden.

Hat man nur zwei Anrufbeantworter konfiguriert, funktioniert weiterhin auch
das bisherige Muster (seit Version 1.0.6b1) einer zusätzlichen, eigenen
Karteninstanz pro Anrufbeantworter als Alternative zur gemeinsamen Karte
(`entity_voicemail: sensor.fritzbox_anrufe_anrufbeantworter_3` in einer
zweiten Karte, nicht benötigte Kategorien über deren eigene
Kategorien-Einstellungen ausgeblendet) - seit Version 1.2.0 aber nicht mehr
nötig, sofern alle Anrufbeantworter in einer einzigen Karte erscheinen
sollen.

Löschen (`show_delete_button`) und Spam-Ausblenden (`hide_spam`)
funktionieren in allen drei Darstellungen unverändert für jeden
Anrufbeantworter, auch wenn deren Nachrichten-IDs sich überschneiden (die
FRITZ!Box zählt bei jedem Anrufbeantworter unabhängig ab 0) - die Karte
unterscheidet intern anhand des jeweiligen Sensors. Ohne gesetztes
`entity_voicemail_2` (und `_3`/`_4`/`_5`) verhält sich die Karte wie vor
Version 1.1.0 (eine einzelne Liste, kein Badge).

## Einstellungen (Optionen)

Über Einstellungen → Geräte & Dienste → FRITZ!Box Anrufe → "Konfigurieren"
öffnet sich seit Version 1.1.1 zunächst ein Auswahlmenü mit zwei Zielen:

- **Grundeinstellungen**: alle bisherigen Optionen (Präfixe, Verlaufstiefe,
  automatisch als gelesen markieren, Spam-Nummern) - siehe Liste unten.
- **Anrufbeantworter verwalten**: die neue, schaltflächenbasierte Auswahl
  der Anzahl abgefragter Anrufbeantworter (1 bis 5) - siehe
  [Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111).

Unter "Grundeinstellungen" lassen sich jederzeit ändern:

- **Präfixe** (kommagetrennte Liste), zur Rufnummernauflösung z. B. bei
  abweichenden Landes-/Ortsvorwahlen im Telefonbuch.
- **Verlaufstiefe je Sensor** (eingehend/ausgehend/verpasst getrennt):
  - *Modus*: "Anzahl Anrufe" oder "Anzahl Tage".
  - *Anzahl*: Dropdown mit festen Werten 5 / 10 / 20 / 50 / 100 / 200
    (nur wirksam im Modus "Anzahl Anrufe").
  - *Tage*: Zahl zwischen 1 und 90 (nur wirksam im Modus "Anzahl Tage").
- **Nach Wiedergabe automatisch als gelesen markieren** (seit Version
  1.0.5, `auto_mark_read`, standardmäßig aus): sobald eine
  Anrufbeantworter-Nachricht über diese Integration abgespielt wurde,
  entfernt die FRITZ!Box selbst das "Neu"-Kennzeichen - genau wie beim
  Abhören direkt an einem FRITZ!Box-Gerät oder in FRITZ!App Fon (TR-064-
  Aktion `MarkMessage`, siehe
  [Automatisch als gelesen markieren](#automatisch-als-gelesen-markieren-seit-version-105-optional)).
  Bewusst auf dieser Integrations-Ebene statt als Karten-Option angesiedelt,
  da dabei tatsächlicher, von allen Apps/Dashboards gemeinsam genutzter
  Zustand auf der FRITZ!Box geändert wird (u. a. auch die Anzahl ungelesener
  Nachrichten in FRITZ!App Fon) - nicht nur die Darstellung dieser einen
  Karte.
- **Spam-Nummern/-Vorwahlen** (seit Version 1.1.0, `spam_numbers`,
  kommagetrennte Liste, standardmäßig leer): siehe
  [Spam-Erkennung](#spam-erkennung-seit-version-110-optional).

Die frühere Option "Zweiten Anrufbeantworter aktivieren"
(`second_tam_enabled`) ist mit Version 1.1.1 entfallen und wurde durch die
Anzahl-Auswahl unter "Anrufbeantworter verwalten" ersetzt (bestehende
Installationen werden automatisch migriert, siehe
[Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111)).

## Dashboard-Karte

### Variante 1: mitgelieferte Custom Card (empfohlen)

Ab Version 1.0.1 wird die Karte `fritzbox-anrufe-card` automatisch mit der
Integration ausgeliefert und registriert sich selbst als Lovelace-Ressource
(keine manuelle Einrichtung nötig - nur einmal Home Assistant neu starten,
nachdem die Integration installiert/aktualisiert wurde). Es gibt bewusst nur
diesen einen Kartentyp - Anrufliste und Anrufbeantworter teilen sich eine
Karte, jede Kategorie darin lässt sich aber einzeln ein-/ausblenden (siehe
unten).

Funktionen:

- Icon-Leiste oben zum Filtern per Klick - fünf mögliche Symbole: Alle/
  Gesamt, Angenommen, Ausgehend, Verpasst und (als 5. Symbol)
  **Anrufbeantworter**. Welche davon überhaupt erscheinen, ist einzeln
  konfigurierbar (siehe **Kategorien** unten). Ist nach dem Ausblenden nur
  noch eine Kategorie übrig, entfällt die Leiste ganz.
- Kategorie "Alle"/"Gesamt" zeigt die neuesten Anrufe aller aktivierten
  Anruftypen gemischt (sortiert nach Datum), begrenzt auf `max_rows` Zeilen
  (Standard: 10). Anrufbeantworter-Nachrichten zählen NICHT zu "Alle" - sie
  erscheinen ausschließlich im eigenen Anrufbeantworter-Tab.
- Findet gerade ein Gespräch statt (Live-Sensor ≠ "idle"), erscheint
  oberhalb der Icon-Leiste automatisch ein hervorgehobenes Live-Banner.
- **Experimentell:** Klick auf das Anrufbeantworter-Symbol (nur sichtbar,
  wenn ein Anrufbeantworter-Sensor eingetragen ist) wechselt den
  Karteninhalt komplett zur Nachrichtenliste
  (Name/Nummer/Zeitpunkt/Dauer, neue Nachrichten farblich markiert) samt
  "Abspielen"-Button pro Nachricht - genau wie bei den Anruf-Tabs ersetzt
  das die Anrufliste, es erscheint kein zusätzlicher Bereich darunter.
  Siehe [Wiedergabe der Anrufbeantworter-Nachrichten](#wiedergabe-der-anrufbeantworter-nachrichten)
  unten für Details, wie das Abspielen technisch funktioniert.
- Responsives Layout: auf schmalen Bildschirmen (Smartphone) werden
  Tab-Beschriftungen und die Geräte-Spalte ausgeblendet, Name/Nummer/Zeit
  bleiben immer sichtbar. Seit Version 1.0.4 reagiert die Tab-Leiste
  zusätzlich auf die tatsächliche **Kartenbreite** (nicht nur die
  Fensterbreite): ist die Karte selbst schmal - z. B. in einer engen
  Dashboard-Spalte am Desktop -, blendet sie die Tab-Beschriftungen
  ebenfalls aus, statt einen horizontalen Scrollbalken zu zeigen (siehe
  [Bekannte Einschränkungen](#bekannte-einschränkungen) zur
  Browser-Voraussetzung dafür).
- Seit Version 1.0.4 lassen sich die Farben der wichtigsten Icons/Symbole
  über den Editor-Bereich **Farben** anpassen (aktiver Tab, Weiterver-
  arbeitungs-Icons, VIP-Markierung, Anruf-Symbole in der Liste,
  Live-Banner-Hintergrund) - siehe **Farben** unten.

Beispielkonfiguration: [`examples/dashboard_custom_card.yaml`](examples/dashboard_custom_card.yaml).

```yaml
type: custom:fritzbox-anrufe-card
title: FRITZ!Box Anrufe
entity_live: sensor.fritz_box_7590_call_monitor
entity_eingehend: sensor.fritz_box_7590_eingehende_anrufe
entity_ausgehend: sensor.fritz_box_7590_ausgehende_anrufe
entity_verpasst: sensor.fritz_box_7590_verpasste_anrufe
entity_voicemail: sensor.fritz_box_7590_anrufbeantworter  # optional, experimentell
entity_voicemail_2: sensor.fritz_box_7590_anrufbeantworter_2  # optional, seit Version 1.1.0
entity_voicemail_3: sensor.fritz_box_7590_anrufbeantworter_3  # optional, seit Version 1.2.0
entity_voicemail_4: sensor.fritz_box_7590_anrufbeantworter_4  # optional, seit Version 1.2.0
entity_voicemail_5: sensor.fritz_box_7590_anrufbeantworter_5  # optional, seit Version 1.2.0
entity_tam_switch: switch.fritz_box_7590_anrufbeantworter_ein_aus  # optional, seit Version 1.1.0, experimentell
entity_tam_switch_2: switch.fritz_box_7590_anrufbeantworter_2_ein_aus  # optional, seit Version 1.1.0
entity_tam_switch_3: switch.fritz_box_7590_anrufbeantworter_3_ein_aus  # optional, seit Version 1.2.0
entity_tam_switch_4: switch.fritz_box_7590_anrufbeantworter_4_ein_aus  # optional, seit Version 1.2.0
entity_tam_switch_5: switch.fritz_box_7590_anrufbeantworter_5_ein_aus  # optional, seit Version 1.2.0
max_rows: 10
show_alle: true
show_eingehend: true
show_ausgehend: true
show_verpasst: true
show_anrufbeantworter: true
# Grundzustand je Anrufbeantworter-Slot (seit Version 1.2.0, Standard AN für
# alle) - nur mit dem jeweils zugehörigen entity_voicemail_N gesetzt von
# Bedeutung. Ab zwei konfigurierten Anrufbeantwortern lässt sich das
# zusätzlich direkt auf der Karte per Kontrollkästchen temporär anpassen,
# ohne die Karte zu bearbeiten.
show_voicemail_1: true
show_voicemail_2: true
show_voicemail_3: true
show_voicemail_4: true
show_voicemail_5: true
show_name: true
show_number: true
show_own_number: false
show_device: true
show_duration: true
show_date: true
show_vip: true
show_processing_alle: false
show_processing_eingehend: false
show_processing_ausgehend: false
show_processing_verpasst: false
# Filter-/Sortierleiste (seit Version 1.0.4, optional) - standardmäßig
# aus, damit bestehende Dashboards nach einem Update optisch unverändert
# bleiben.
show_filter_bar: false
# Papierkorb-Button für Anrufbeantworter-Nachrichten (seit Version 1.0.5,
# optional) - standardmäßig aus: Löschen ist unwiderruflich.
show_delete_button: false
# Als Spam erkannte Anrufe/Nachrichten ausblenden (seit Version 1.1.0,
# optional) - standardmäßig aus. Was als Spam gilt, wird über die
# Integrations-Optionen definiert, siehe
# https://github.com/Meine-smarte-Welt/fritzbox_anrufe#spam-erkennung-seit-version-110-optional
hide_spam: false
# Darstellung bei mehreren Anrufbeantwortern (seit Version 1.1.0, optional,
# nur mit mindestens entity_voicemail_2 gesetzt) - "merged" mischt die
# Nachrichtenlisten chronologisch mit einem "AB 1"/"AB 2"-Badge pro
# Nachricht, "separate" zeigt stattdessen eigene, überschriebene Abschnitte
# untereinander (beide nur bei GENAU zwei konfigurierten
# Anrufbeantwortern wählbar), "accordion" (seit Version 1.2.0) zeigt
# unabhängig auf-/zuklappbare Abschnitte je Anrufbeantworter und ist ab drei
# konfigurierten Anrufbeantwortern die einzige, automatisch erzwungene
# Darstellung.
voicemail_2_mode: merged
# Anrufbeantworter Ein/Aus-Schalter (seit Version 1.1.0, optional,
# experimentell) - standardmäßig aus, benötigt zusätzlich einen gesetzten
# entity_tam_switch (bzw. entity_tam_switch_2).
show_tam_switch: false
# Farben (seit Version 1.0.4, optional) - CSS-Farbwert (Hex, rgb()/rgba(),
# hsl(), oder eine Theme-Variable wie var(--accent-color)); leer/weggelassen
# = bisherige Standardfarbe.
color_tab_active: ""
color_success: ""
color_error: ""
color_playback: ""
color_vip: ""
color_row_icon: ""
color_live_banner: ""
color_icon_alle: ""
color_icon_eingehend: ""
color_icon_ausgehend: ""
color_icon_verpasst: ""
color_icon_anrufbeantworter: ""
```

**Grafischer Editor:** Statt die Karte per YAML zu konfigurieren, kann sie
über die normale Lovelace-Karten-Auswahl bearbeitet werden ("Karte
bearbeiten" → es öffnet sich automatisch ein Home-Assistant-Standardformular
statt des YAML-Editors). Dort lassen sich Titel, alle Sensoren (inkl. des
optionalen zweiten Anrufbeantworters) sowie - seit Version 1.1.0 - der/die
optionale(n) Anrufbeantworter-Ein/Aus-Schalter per Entity-Picker setzen,
zusätzlich die Zeilenanzahl per Eingabefeld. Die tatsächlichen Entity-IDs
findest du unter Einstellungen → Geräte & Dienste → Entitäten (Suche nach
"Anrufe"/"Call monitor"/"Anrufbeantworter"). Seit Version 1.0.4
ist der Editor in aufklappbare Abschnitte gruppiert (Sensoren, Kategorien,
Darstellung, Weiterverarbeitung, Farben) - bei einer inzwischen recht langen
Feldliste auf Wunsch von Thorsten eingeführt, um den Überblick zu behalten.
Das ist eine rein optische Gruppierung; gespeichert wird weiterhin dieselbe
flache YAML-Struktur wie zuvor. Die ersten vier Abschnitte (Sensoren,
Kategorien, Darstellung, Weiterverarbeitung) setzen dafür ein halbwegs
aktuelles Home-Assistant-Frontend voraus (dieses Gruppierungsfeature war zum
Zeitpunkt dieser Änderung noch nicht an echter Hardware bestätigt) - erscheint
einer dieser vier Abschnitte stattdessen als eine lange, ungruppierte Liste
oder mit einem seltsam benannten Zusatzfeld, bitte als GitHub-Issue mit der
Home-Assistant-Version melden. Der fünfte Abschnitt, "Farben", ist davon
**nicht** betroffen: er wird seit Version 1.0.4 nicht mehr über dieses
Home-Assistant-Formularfeature gerendert, sondern mit einfachem,
browser-eigenem HTML (siehe [Farben](#farben-seit-version-104-optional)
unten) - unabhängig von der Home-Assistant-Frontend-Version.

**Kategorien:** Fünf Schalter (`show_alle`, `show_eingehend`,
`show_ausgehend`, `show_verpasst`, `show_anrufbeantworter`) blenden ganze
Kategorien/Tabs ein oder aus. Bei den vier Anruf-Kategorien reicht dafür der
Schalter allein; der Anrufbeantworter-Tab braucht zusätzlich einen
konfigurierten `entity_voicemail` - ohne Sensor bleibt er auch bei
`show_anrufbeantworter: true` ausgeblendet, da es nichts anzuzeigen gäbe.
Eine deaktivierte Anruf-Kategorie verschwindet aus der Icon-Leiste und wird
auch aus der "Alle"/"Gesamt"-Sammelansicht herausgerechnet.

**Spalten:** Sieben weitere Schalter (`show_name`, `show_number`,
`show_own_number`, `show_device`, `show_duration`, `show_date`, `show_vip`)
blenden einzelne Spalten der Anrufliste ein oder aus.

### Filter-/Sortierleiste (seit Version 1.0.4, optional)

Über `show_filter_bar` (Standard: `false`, damit bestehende Dashboards nach
einem Update optisch unverändert bleiben) lässt sich eine kleine Leiste
oberhalb der Anrufliste einblenden:

- **Eigene Rufnummer:** Dropdown mit "Alle" plus einem Eintrag je Rufnummer,
  die in den aktuell geladenen Anrufen tatsächlich als `own_number`
  vorkommt (bei mehreren an der FRITZ!Box eingerichteten Rufnummern/MSNs,
  z. B. um nur die Anrufe einer bestimmten Nummer zu sehen). Gilt nur für
  die Anrufliste (Alle/Angenommen/Ausgehend/Verpasst) - **nicht** für den
  Anrufbeantworter-Tab: die FRITZ!Box liefert für Anrufbeantworter-
  Nachrichten keine eigene Rufnummer (fritzconnection-/TR-064-seitige
  Einschränkung, siehe [Bekannte Einschränkungen](#bekannte-einschränkungen)),
  das Dropdown erscheint dort deshalb gar nicht erst.
- **Sortierung:** Dropdown mit Datum (neueste/älteste zuerst), Dauer
  (längste/kürzeste zuerst) und Name (A-Z/Z-A) - gilt auf jedem Tab,
  einschließlich Anrufbeantworter.

Beide Auswahlen sind reiner Anzeigezustand der laufenden Karte (nicht Teil
der gespeicherten Kartenkonfiguration) - sie setzen sich beim Neuladen der
Seite oder nach einer Konfigurationsänderung wieder auf "Alle"/"Datum,
neueste zuerst" zurück, genau wie der aktuell ausgewählte Tab.

### Farben (seit Version 1.0.4, optional)

Zwölf Farbfelder passen die Icons/Symbole der Karte an - standardmäßig leer,
was die bisherige, feste Theme-Farbe unverändert lässt:

| Config-Schlüssel | Betrifft | Standardfarbe |
| --- | --- | --- |
| `color_tab_active` | Aktiver Tab (Text + Unterstrich) | `--primary-color` |
| `color_success` | Weiterverarbeitung "Angenommen"/"Verbunden" | `--success-color` |
| `color_error` | Weiterverarbeitung "Nicht verbunden"/"Nicht erreicht"/"Keine Anrufbeantworter-Nachricht vorhanden" | `--error-color` |
| `color_playback` | Abspielen-Button, "Neu"-Markierung, Weiterverarbeitung "Anrufbeantworter-Nachricht abspielen" | `--primary-color` |
| `color_vip` | VIP-Stern | `--warning-color` |
| `color_row_icon` | Anruf-Symbol in jeder Zeile - EINE Farbe für ALLE Zeilen, überschreibt bei Bedarf die Kategorie-Icon-Farben unten | `--secondary-text-color` |
| `color_live_banner` | Hintergrund des Live-Banners | `--state-icon-active-color` |
| `color_icon_alle` (seit 1.0.4) | Symbol des Tabs "Alle" | folgt der Tab-Farbe (aktiv/inaktiv) |
| `color_icon_eingehend` (seit 1.0.4) | Symbol des Tabs "Angenommen" | folgt der Tab-Farbe (aktiv/inaktiv) |
| `color_icon_ausgehend` (seit 1.0.4) | Symbol des Tabs "Ausgehend" | folgt der Tab-Farbe (aktiv/inaktiv) |
| `color_icon_verpasst` (seit 1.0.4) | Symbol des Tabs "Verpasst" | folgt der Tab-Farbe (aktiv/inaktiv) |
| `color_icon_anrufbeantworter` (seit 1.0.4) | Symbol des Tabs "Anrufbeantworter" | folgt der Tab-Farbe (aktiv/inaktiv) |

Jeder Wert akzeptiert einen beliebigen CSS-Farbwert - Hex (`#4caf50`),
`rgb()`/`rgba()`, `hsl()`/`hsla()`, einen benannten CSS-Farbnamen, oder eine
Theme-Variable wie `var(--accent-color)`. Ungültige bzw. nicht eindeutig als
Farbwert erkennbare Eingaben werden verworfen (Warnung in der
Browser-Konsole) und fallen auf die Standardfarbe zurück, statt die Karte zu
beschädigen.

Die 5 Kategorie-Icon-Farben (`color_icon_*`) sind unabhängig vom Tab-Status:
einmal gesetzt, behält das Symbol diese Farbe sowohl im aktiven als auch im
inaktiven Zustand des Tabs - anders als `color_tab_active`, das nur den
aktiven Tab betrifft.

**Kategorie-Farbe wirkt jetzt auch in der Anrufliste (seit Version 1.0.4):**
Wird die Icon-Farbe einer Kategorie geändert (z. B. `color_icon_ausgehend`),
färbt sich damit nicht mehr nur das Symbol im Tab, sondern auch das
Zeilen-Icon jedes Anrufs dieser Kategorie in der Liste - auf der
"Alle"/"Gesamt"-Sammelansicht entsprechend gemischt, jede Zeile in der Farbe
ihrer eigenen Kategorie. **Einzige Ausnahme:** Ist `color_row_icon` gesetzt
(eine Farbe für ALLE Zeilen-Icons, siehe Tabelle oben), gewinnt diese
einheitliche Einstellung - Kategorie-Icon-Farben wirken dann ausschließlich
noch auf die Tab-Symbole selbst, nicht mehr auf die Zeilen darunter.

**Grafische Farbauswahl (seit Version 1.0.4):** Im grafischen Editor
("Karte bearbeiten" → Abschnitt "Farben") steht neben jedem Textfeld
zusätzlich ein Farbfeld (`<input type="color">`) - ein Klick darauf öffnet
die native Farbauswahl des Betriebssystems/Browsers. Eine dort gewählte
Farbe wird automatisch als Hex-Wert in das danebenliegende Textfeld
übernommen; umgekehrt lässt sich das Textfeld weiterhin frei mit jedem
CSS-Farbwert befüllen (also auch mit Werten, die die grafische Auswahl nicht
abbilden kann, z. B. `var(--accent-color)` oder `rgb(...)`) - das Farbfeld
zeigt in diesem Fall ersatzweise die Standardfarbe an, das Textfeld bleibt
maßgeblich. Unter jedem Feld steht außerdem, welche Farbe aktuell wirksam
ist ("Aktuell verwendet: …" bzw. bei leerem Feld "Aktuell verwendet
(Standard): …") - so ist auch ohne Blick in die YAML-Konfiguration
ersichtlich, welche Farbe eine Karte gerade tatsächlich verwendet. Diese
Sektion ist bewusst nicht über das Home-Assistant-Formularfeature
(`<ha-form>`) umgesetzt, sondern mit einfachem, browser-eigenem HTML -
sowohl weil `<ha-form>` keinen Feldtyp anbietet, der gleichzeitig beliebige
CSS-Werte, eine grafische Auswahl und die aktuell wirksame Farbe anzeigen
kann, als auch damit diese Sektion unabhängig von der
Home-Assistant-Frontend-Version zuverlässig funktioniert.

**Zurücksetzen (seit Version 1.0.4):** Der Button "Alle Farben
zurücksetzen" oben im Abschnitt leert alle zwölf Farbfelder auf einen Schlag
(zurück zur jeweiligen Standardfarbe) - praktischer als jedes Feld einzeln zu
leeren.

**Bleiben die Farben nach einem Neustart erhalten?** Ja. Farbwerte sind ganz
normale Einstellungen der Lovelace-Kartenkonfiguration und werden von Home
Assistants eigener Dashboard-Speicherung verwaltet - genau wie Titel,
Sensor-Zuordnung oder die `show_*`-Schalter dieser Karte. Diese Integration
hat darauf keinen eigenen Einfluss und keinen Grund, sie jemals
zurückzusetzen; sie überstehen einen Neustart von Home Assistant oder ein
Update der Integration ebenso zuverlässig wie jede andere Karteneinstellung.

### Weiterverarbeitung (seit Version 1.0.3, optional)

Vier weitere Schalter (`show_processing_eingehend`, `show_processing_ausgehend`,
`show_processing_verpasst`, `show_processing_alle`) blenden - standardmäßig
deaktiviert, damit bestehende Dashboards nach einem Update optisch
unverändert bleiben - pro Kategorie eine zusätzliche Zeile unter jedem
Anruf ein, die zeigt, wie der Anruf konkret ausgegangen ist (Pfeil-Symbol +
Icon + Beschriftung, ausgewertet aus dem neuen `outcome`-Feld, siehe
[Sensoren](#sensoren)). `show_processing_alle` steuert diese Zeile
unabhängig von den drei Einzelschaltern auf dem gemeinsamen "Alle"/"Gesamt"-
Tab.

| `outcome` | Icon | Bedeutung | Klick |
| --- | --- | --- | --- |
| `beantwortet` | grüner Telefonhörer (`mdi:phone-check`) | Eingehender Anruf wurde angenommen | wechselt zum Tab "Angenommen" |
| `verbunden` | grüner Telefonhörer (`mdi:phone-check`) | Ausgehender Anruf kam zustande | wechselt zum Tab "Ausgehend" |
| `nicht_verbunden` | durchgestrichener Hörer (`mdi:phone-remove`) | Ausgehender Anruf kam nicht zustande (besetzt oder niemand nimmt ab - nicht unterscheidbar, siehe [Bekannte Einschränkungen](#bekannte-einschränkungen)) | wechselt zum Tab "Ausgehend" |
| `keine_nachricht` | roter, durchgestrichener Hörer (`mdi:phone-missed`) | An den Anrufbeantworter weitergeleitet, aber keine Nachricht hinterlassen | wechselt zum Tab "Verpasst" |
| `nicht_erreicht` | roter, durchgestrichener Hörer (`mdi:phone-missed`) | Verpasster Anruf, ohne dass eine Weiterleitung an den Anrufbeantworter festgestellt werden konnte | wechselt zum Tab "Verpasst" |
| `anrufbeantworter` | Play-Symbol (`mdi:play-circle-outline`) | Anrufbeantworter hat eine Nachricht aufgezeichnet | spielt die Aufnahme **direkt inline** ab (kein Tab-Wechsel) - technisch identisch zum "Abspielen"-Button im Anrufbeantworter-Tab, siehe unten |

**Zur Wiedergabe-Technik:** Konnte die zugehörige Anrufbeantworter-Nachricht
eindeutig per Datum/Uhrzeit-Abgleich gefunden werden (siehe
[Sensoren](#sensoren)), nutzt die Direktwiedergabe denselben, bereits an
echter Hardware bestätigten Proxy wie der Anrufbeantworter-Tab selbst. Nur
falls kein eindeutiger Treffer gefunden wurde (`call.Path` ist gesetzt, aber
z. B. der Anrufbeantworter-Sensor hat noch nicht aktualisiert), greift ein
neuer, eigener Codepfad (`FritzBoxCallMediaView`), der zwar denselben
Downloadmechanismus verwendet, aber als solcher noch **nicht** separat an
echter Hardware verifiziert wurde. Funktioniert die Wiedergabe im
Anrufbeantworter-Tab, aber nicht über diese Weiterverarbeitungs-Zeile, bitte
mit dem HTTP-Statuscode aus dem Home-Assistant-Log als GitHub-Issue melden
(siehe [Fehlerbehebung](#fehlerbehebung)).

### Wiedergabe der Anrufbeantworter-Nachrichten

Ein `<audio src="...">` kann in Home Assistant grundsätzlich keine
Zugangsdaten mitschicken - der Browser hängt an eine reine Medien-URL keinen
Authorization-Header an. Deshalb setzt die Karte die Aufnahme-URL nicht
direkt als `src`, sondern zeigt pro Nachricht zunächst einen
"Abspielen"-Button. Erst ein Klick darauf lädt die Aufnahme über die
authentifizierte Fetch-Funktion, die Home Assistant Karten dafür zur
Verfügung stellt (`hass.fetchWithAuth`), und übergibt sie danach als
abspielbaren Audio-Player. Ohne diesen Umweg schlägt die Wiedergabe fehl und
im Home-Assistant-Log erscheint eine Meldung wie *"Login attempt or request
with invalid authentication ... /api/fritzbox_anrufe/tam_media/..."* vom
`http.ban`-Modul - das war das Verhalten vor diesem Fix.

### Anrufbeantworter-Nachrichten löschen (seit Version 1.0.5, optional)

Ein neuer, standardmäßig ausgeblendeter Papierkorb-Button (`show_delete_button`)
löscht eine Anrufbeantworter-Nachricht unwiderruflich von der FRITZ!Box (TR-064-
Aktion `DeleteMessage`) - die FRITZ!Box selbst hat dafür keinen Papierkorb, ein
Löschvorgang kann also nicht rückgängig gemacht werden. Ein Klick auf den
Button löscht deshalb NICHT sofort, sondern zeigt zunächst inline "Wirklich
löschen?" mit Bestätigen-/Abbrechen-Symbolen; erst ein Klick auf Bestätigen
löst die Löschung tatsächlich aus. Die Zeile verschwindet dabei optimistisch
sofort - schlägt der Löschvorgang fehl (z. B. ein TR-064-Fehler), erscheint
sie wieder.

Intern über einen neuen Home-Assistant-Entity-Service
(`fritzbox_anrufe.delete_voicemail_message`, Parameter `message_id`)
umgesetzt, den auch eigene Automatisierungen nutzen können - die dafür
nötige, zuvor nur intern verwendete Nachrichten-ID steht jetzt als `id`-Feld
im `messages`-Attribut des Anrufbeantworter-Sensors.

**Bestätigt:** Von Thorsten an eigener Hardware erfolgreich getestet -
`DeleteMessage` funktioniert wie erwartet. Da der Löschvorgang trotzdem
unwiderruflich bleibt, empfiehlt sich bei Unsicherheit weiterhin ein erster
Test mit einer unwichtigen Nachricht.

### Automatisch als gelesen markieren (seit Version 1.0.5, optional)

Über die Einstellungen der Integration (siehe
[Einstellungen (Optionen)](#einstellungen-optionen)) lässt sich `auto_mark_read`
aktivieren, standardmäßig aus. Ist die Option an, entfernt die Integration
nach jeder erfolgreichen Wiedergabe einer Anrufbeantworter-Nachricht - egal
ob über den Abhören-Button im Anrufbeantworter-Tab oder über eine verknüpfte
Aufnahme in der Anrufliste (Weiterverarbeitung) - automatisch das
"Neu"-Kennzeichen dieser Nachricht auf der FRITZ!Box selbst (TR-064-Aktion
`MarkMessage`), genau wie es beim Abhören an einem FRITZ!Box-eigenen Gerät
oder in FRITZ!App Fon geschieht. War die Nachricht bereits gelesen, passiert
nichts (kein unnötiger TR-064-Aufruf). Schlägt die Markierung fehl (z. B.
TR-064-Fehler), wird das nur ins Home-Assistant-Log geschrieben - eine
fehlgeschlagene Markierung lässt eine ansonsten erfolgreiche Wiedergabe
niemals fehlschlagen.

Damit eine laufende Wiedergabe durch die anschließende Kartenaktualisierung
nicht unterbrochen wird, erkennt die Karte aktive/gerade gestartete
Wiedergaben und verschiebt eine fällige Neudarstellung, bis die Wiedergabe
endet - unabhängig davon, ob `auto_mark_read` aktiviert ist oder nicht.

**Bestätigt:** Von Thorsten an eigener Hardware erfolgreich getestet -
`MarkMessage` funktioniert wie erwartet, das "Neu"-Kennzeichen verschwindet
nach der Wiedergabe.

### Spam ausblenden (seit Version 1.1.0, optional)

Anrufe und Anrufbeantworter-Nachrichten, die als Spam erkannt wurden (siehe
[Spam-Erkennung](#spam-erkennung-seit-version-110-optional)), bekommen auf
der Karte standardmäßig ein kleines rotes "Spam"-Badge neben dem
Namen/der Nummer - genau wie das bestehende "neu"-Badge bei
Anrufbeantworter-Nachrichten, nur in der Fehlerfarbe statt der
Wiedergabefarbe. Der Schalter `hide_spam` (standardmäßig aus) blendet
solche Einträge stattdessen komplett aus der Anrufliste bzw. der
Nachrichtenliste aus, sowohl auf dem "Alle"/"Gesamt"-Tab als auch auf den
Einzelkategorien.

### Mehrere Anrufbeantworter anzeigen (seit Version 1.1.0, erweitert in Version 1.2.0, optional)

Mit gesetztem `entity_voicemail_2` (und optional `_3`/`_4`/`_5`, seit
Version 1.2.0 - siehe
[Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111))
zeigt der Anrufbeantworter-Tab alle konfigurierten Nachrichtenlisten
zusammen. `voicemail_2_mode` wählt zwischen `merged` (Standard, nur bei
genau zwei konfigurierten Anrufbeantwortern: eine gemeinsame chronologische
Liste mit "AB 1"/"AB 2"-Badge je Nachricht), `separate` (ebenfalls nur bei
genau zwei: eigene, überschriebene Abschnitte untereinander, unvermischt)
und `accordion` (seit Version 1.2.0: unabhängig auf-/zuklappbare Abschnitte
je Anrufbeantworter, ab drei konfigurierten automatisch erzwungen - siehe
[Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111)
für die genaue Beschreibung des Auf-/Zuklapp-Verhaltens). Zusätzlich lässt
sich seit Version 1.2.0 über die Editor-Schalter `show_voicemail_1` bis `_5`
(dauerhaft) sowie über Kontrollkästchen direkt auf der Karte (temporär,
sobald zwei oder mehr Anrufbeantworter konfiguriert sind) auswählen, welche
Anrufbeantworter überhaupt einbezogen werden. Papierkorb-Button und
Spam-Ausblenden funktionieren dabei für jeden Anrufbeantworter wie gewohnt.
Ohne `entity_voicemail_2` ändert sich am bisherigen Verhalten nichts.

### Anrufbeantworter Ein/Aus-Schalter (seit Version 1.1.0, experimentell)

**Wichtig, experimentell:** Die verwendete TR-064-Aktion `SetEnable` (Dienst
`X_AVM-DE_TAM1`, derselbe Dienst wie `GetMessageList`/`DeleteMessage`/
`MarkMessage`) konnte NICHT unabhängig gegen AVMs offizielle Dokumentation
oder eine Community-Referenz bestätigt werden - sie wurde ausschließlich
durch die starke, innerhalb desselben Diensts bereits mehrfach bestätigte
Namenskonvention hergeleitet (`NewIndex` plus ein einzelnes
`New<Konzept>`-Argument, hier `NewEnable`). Aus demselben Grund ruft diese
Integration bewusst weiterhin **nicht** die Aktion `GetInfo` auf (siehe
[Bekannte Einschränkungen](#bekannte-einschränkungen)), mit der sich der
tatsächliche Ein/Aus-Zustand zuverlässig auslesen ließe. Der Schalter zeigt
deshalb keinen bestätigten, von der FRITZ!Box zurückgelesenen Zustand,
sondern ausschließlich den zuletzt über Home Assistant selbst gesetzten
(`assumed_state`) - übersteht einen Neustart von Home Assistant (der letzte
bekannte Zustand wird wiederhergestellt), aber nicht zwingend eine
Änderung, die direkt an der FRITZ!Box oder in FRITZ!App Fon vorgenommen
wurde. Bitte mit dem Ergebnis eines eigenen Tests (schaltet der
Anrufbeantworter an der FRITZ!Box tatsächlich um?) als GitHub-Issue melden.

Pro konfiguriertem Anrufbeantworter legt die Integration automatisch eine
eigene `switch`-Entität an (siehe [Sensoren](#sensoren)) - ein Klick
schaltet den jeweiligen Anrufbeantworter über TR-064 ein bzw. aus, mit
sofortiger optischer Rückmeldung und automatischem Zurücksetzen, falls der
TR-064-Aufruf fehlschlägt (derselbe optimistische Ansatz wie beim Löschen
von Nachrichten, siehe
[Anrufbeantworter-Nachrichten löschen](#anrufbeantworter-nachrichten-löschen-seit-version-105-optional)).
Sind weitere Anrufbeantworter konfiguriert (bis zu 5, siehe
[Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111)),
legt die Integration für jeden davon eine eigene, unabhängige
Schalter-Entität an.

**Auf der Dashboard-Karte anzeigen:** Standardmäßig blendet die Karte
keinen Schalter ein (`show_tam_switch: false`, wie jeder rein optische
Regler dieser Karte, damit bestehende Dashboards nach einem Update optisch
unverändert bleiben). Zum Aktivieren im grafischen Editor unter
"Sensoren" die Felder **Schalter: Anrufbeantworter Ein/Aus** und (bei
konfiguriertem zweitem Anrufbeantworter) **Schalter: Zweiter
Anrufbeantworter Ein/Aus** auf die jeweilige `switch.…`-Entität setzen und
zusätzlich unter "Darstellung" den Regler **Anrufbeantworter-Ein/Aus-
Schalter auf der Karte anzeigen** (`show_tam_switch`) einschalten. Der
Schalter erscheint dann im Anrufbeantworter-Tab direkt **vor** der
Nachrichten-Auflistung, unabhängig davon, ob ein zweiter Anrufbeantworter
konfiguriert ist und ob `voicemail_2_mode` auf `merged` oder `separate`
steht. Diese beiden Entity-Felder sind bewusst eigenständige Picker (nicht
aus `entity_voicemail`/`entity_voicemail_2` abgeleitet) - Home Assistant
bietet für sprachabhängig benannte Entitäten keinen zuverlässigen
Mechanismus, um die zugehörige `switch`-entity_id automatisch zu
bestimmen; die tatsächlichen Entity-IDs finden sich wie gewohnt unter
Einstellungen → Geräte & Dienste → Entitäten (Suche nach "Anrufbeantworter").

### Variante 2: flex-table-card (YAML, spaltenweise ein-/ausblendbar)

Für eine klassische, tabellarische Darstellung mit frei konfigurierbaren
Spalten: [`examples/dashboard_flex_table.yaml`](examples/dashboard_flex_table.yaml).
Benötigt die separat über HACS installierbare Community-Karte
["flex-table-card"](https://github.com/custom-cards/flex-table-card).

## Icon

Home Assistant unterstützt seit Version 2026.3 eigene Marken-Icons für
Custom Integrations über einen `brand/`-Unterordner (`icon.png`,
`logo.png`, optional `@2x`- und `dark_`-Varianten) - ganz ohne Eintrag in
der offiziellen `home-assistant/brands`-Sammlung (die für Custom
Integrations inzwischen keine Icons mehr annimmt). Dieses Repository
liefert ab Version 1.0.1 ein FRITZ!-Icon (`brand/icon.png`,
`brand/logo.png`) mit aus - es wird ohne weitere Konfiguration automatisch
in der Integrationsliste sowie als Geräte-Icon verwendet. Die Quelldatei
war ein kleines JPEG (165×153 px), das auf ein quadratisches 256×256-PNG
aufbereitet wurde; wer eine höher aufgelöste offizielle Vektor-/Bilddatei
hat, kann `brand/icon.png`/`brand/logo.png` jederzeit durch eine bessere
Version ersetzen (z. B. von
[home-assistant.io/integrations/fritzbox_callmonitor](https://www.home-assistant.io/integrations/fritzbox_callmonitor/)).

Die Entitäten selbst haben bereits passende Icons (`mdi:phone`,
`mdi:phone-incoming`, `mdi:phone-outgoing`, `mdi:phone-missed`,
`mdi:voicemail`, siehe `icons.json`).

**Icon erscheint nicht auf der HACS-Downloads-Seite:** Das ist ein
bekannter, aktuell offener Fehler in HACS selbst, nicht in dieser
Integration. HACS' eigene Downloads-Übersicht lädt Icons weiterhin über
die alte öffentliche CDN (`data-v2.hacs.xyz`/`brands.home-assistant.io`),
kennt den seit Home Assistant 2026.3 unterstützten Weg für inline
mitgelieferte Icons (`brand/`-Ordner, wie oben beschrieben) aber noch nicht
- siehe [hacs/integration#5223](https://github.com/hacs/integration/issues/5223)
und [hacs/integration#5171](https://github.com/hacs/integration/issues/5171).
Für Custom Integrations akzeptiert `home-assistant/brands` inzwischen
bewusst keine Icons mehr, ein Workaround auf Integrationsseite existiert
also nicht. Wichtig: Das Icon wird davon unabhängig überall sonst in Home
Assistant korrekt angezeigt (Einstellungen → Geräte & Dienste, Geräteseite
usw.) - betroffen ist ausschließlich die HACS-eigene Downloads-Liste, bis
die dortigen Maintainer den Fehler beheben.

## Bekannte Einschränkungen

- Die FRITZ!Box/`fritzconnection`-API erlaubt nur EINEN gemeinsamen
  Anzahl-*oder*-Tage-Parameter für den kombinierten Anrufabruf (alle Typen
  gemischt), keinen getrennten Parameter je Anruftyp. Um trotzdem
  unabhängige Grenzwerte je Sensor anzubieten, lädt die Integration je
  Aktualisierungszyklus einmal die letzten 90 Tage (alle Typen kombiniert)
  und wendet die eigene Einstellung jedes Sensors anschließend clientseitig
  an. Praktische Folge: ein auf "Tage" eingestellter Sensor kann nie weiter
  als 90 Tage zurückblicken; ein auf "Anzahl" eingestellter Sensor zeigt
  weniger als den konfigurierten Wert, falls es innerhalb dieser 90 Tage
  schlicht nicht genug Anrufe dieses Typs gab.
- Die feste entity_id (siehe [Entity-IDs](#entity-ids) oben) gilt nur für
  neu angelegte Entities; bei Bestandssystemen bleibt die bisherige
  entity_id erhalten, bis die Entity manuell gelöscht und neu angelegt wird
  - das ist bewusstes Home-Assistant-Verhalten, keine Einschränkung dieser
  Integration.
- **Anrufbeantworter-Sensor und -Wiedergabe sind experimentell**, aber
  inzwischen an echter Hardware bestätigt funktionsfähig (u. a. unter
  FRITZ!OS 8.24) - sowohl die Nachrichtenliste (Sensor
  `fritzbox_anrufe_anrufbeantworter`, TR-064-Aktion
  `X_AVM-DE_TAM1`/`GetMessageList`) als auch die Wiedergabe. Der
  Audio-Download läuft über
  `/cgi-bin/luacgi_notimeout?sid=...&script=/lua/photo.lua&myabfile=...`
  gegen den normalen Web-UI-Port (80/443) der FRITZ!Box - **nicht** über
  `download.lua`, wie es die in der Nachrichtenliste enthaltene `Path`-
  Angabe nahelegt, und **nicht** über den TR-064-Port (i. d. R. 49000).
  Da unterschiedliche FRITZ!OS-Versionen sich in Testberichten uneinig
  waren, woher die dafür nötige Sitzung (`sid`) stammen muss, probiert die
  Integration bei Bedarf automatisch zwei Varianten durch: zuerst die in
  der `GetMessageList`-Antwort enthaltene sid (ohne zusätzliche Anmeldung),
  bei Fehlschlag eine vollständige FRITZ!Box-Weboberflächen-Anmeldung als
  Rückfalloption. Falls die Wiedergabe auf einer bestimmten FRITZ!OS-
  Version dennoch fehlschlägt, bitte mit dem vollständigen Log-Auszug
  (`custom_components.fritzbox_anrufe.*`, insbesondere dem/den
  HTTP-Statuscode(s)) als GitHub-Issue melden. Bewusst **nicht**
  unterstützt: Faxnachrichten.
- Die Anrufbeantworter-Wiedergabe läuft über einen serverseitigen,
  Home-Assistant-authentifizierten Proxy (die FRITZ!Box-Anmeldedaten
  verlassen dabei nie den Home-Assistant-Server); pro Wiedergabe wird die
  Audiodatei einmal komplett von der FRITZ!Box geladen, es gibt aktuell kein
  Streaming/Caching. Aus demselben Grund ist bewusst ein "Abspielen"-Button
  statt eines direkt befüllten `<audio src="...">` verbaut - siehe
  [Wiedergabe der Anrufbeantworter-Nachrichten](#wiedergabe-der-anrufbeantworter-nachrichten).
- **Ausgehende Anrufe - kein "besetzt"-Signal, und TR-064 kennt erfolglose
  Versuche gar nicht**: Die FRITZ!Box-Anrufliste (TR-064/`GetCallList`)
  liefert für ausgehende Anrufe keine eigene, von "niemand nimmt ab"
  unterscheidbare Kennung für "besetzt" - `outcome` fasst beide deshalb
  bewusst zu einem gemeinsamen `nicht_verbunden` zusammen (siehe
  [Sensoren](#sensoren)); mehrere unabhängige Quellen (u. a. AVMs eigene
  Dokumentation sowie die FHEM-Callmonitor-Implementierung) bestätigen, dass
  ein solches Feld dort schlicht nicht existiert. Stärker noch: ein
  erfolgloser ausgehender Anruf (besetzt, niemand nimmt ab, vor Annahme
  aufgelegt) erscheint über TR-064 überhaupt **nicht** in der Anrufliste -
  nicht einmal mit Verbindungsdauer 0 - sondern ausschließlich, sobald
  tatsächlich eine Verbindung zustande kam (an echter Hardware bestätigt).
  Seit Version 1.0.3 füllt die Integration diese Lücke selbst: der
  Live-Callmonitor erkennt einen erfolglosen Anruf am Zustandswechsel
  "Wählen" → "Idle" (ohne "Gespräch läuft" dazwischen) und trägt ihn direkt
  in den Sensor `fritzbox_anrufe_ausgehend` ein - solche Einträge existieren
  aber ausschließlich im Arbeitsspeicher von Home Assistant und gehen bei
  einem Neustart verloren; nur Versuche, die während des laufenden Betriebs
  dieser Integration auftreten, werden erfasst. Bei zwei praktisch
  gleichzeitigen ausgehenden Anrufen werden diese anhand der vom Callmonitor
  gemeldeten ConnectionID sauber auseinandergehalten.
- **Verpasste Anrufe - Detailunterscheidung**: Ob ein Anruf überhaupt an den
  Anrufbeantworter weitergeleitet wurde, erkennt die Integration seit
  Version 1.0.3 direkt am von der FRITZ!Box gemeldeten "Gerät"-Wert
  (`Device: "Anrufbeantworter"`) - an echter Hardware bestätigt und
  zuverlässiger als frühere Heuristiken. Ob dabei tatsächlich eine Nachricht
  aufgezeichnet wurde, wird zusätzlich per Datum/Uhrzeit- (und, falls
  vorhanden, Rufnummer-)Abgleich mit den echten Anrufbeantworter-Nachrichten
  bestätigt. Damit ist jetzt klar unterscheidbar, ob ein verpasster Anruf den
  Anrufbeantworter nie erreicht hat (`outcome: nicht_erreicht` - z. B.
  aufgelegt, bevor er ansprang, abgewiesen, oder kein Anrufbeantworter
  aktiv), ob er ihn erreicht hat, aber keine Nachricht hinterlassen wurde
  (`outcome: keine_nachricht`), oder ob eine Nachricht aufgezeichnet wurde
  (`outcome: anrufbeantworter`). Offen bleibt lediglich eine sehr feine
  Unterscheidung *innerhalb* von `keine_nachricht`, nämlich ob der Anrufer
  schon während der Ansage oder erst nach dem Signalton stumm aufgelegt hat -
  dafür existiert schlicht kein von der FRITZ!Box gemeldetes Feld. Bei
  aktiviertem Debug-Logging (`custom_components.fritzbox_anrufe`, siehe
  [Fehlerbehebung](#fehlerbehebung)) protokolliert die Integration weiterhin
  die Rohdaten jedes Anrufs (inkl. `Device` und einer ggf. gefundenen
  zugehörigen Nachricht) mitsamt berechnetem `outcome`.
- **Kartengrenzwerte in modernen Browser-Features**: Zwei Funktionen der
  Dashboard-Karte seit Version 1.0.4 nutzen vergleichsweise moderne
  Web-Plattform-Features und wurden noch nicht an einer breiten Auswahl
  echter Home-Assistant-Frontend-Versionen/Browser bestätigt: die
  breitenabhängige Tab-Leiste (CSS Container Queries - in allen gängigen,
  aktuellen Browsern seit 2022/2023 unterstützt) und die aufklappbaren
  Editor-Abschnitte für Sensoren/Kategorien/Darstellung/Weiterverarbeitung
  (`ha-form`s "expandable"-Schema-Typ mit `flatten: true` - Verfügbarkeit
  hängt von der Home-Assistant-Frontend-Version ab). Beide degradieren im
  Zweifel unauffällig (Tab-Leiste: Beschriftungen können statt komplett
  auszublenden gekürzt werden, aber es entsteht kein Scrollbalken mehr;
  Editor: Felder erscheinen ggf. als eine lange, ungruppierte statt
  gruppierte Liste) - bitte mit Home-Assistant-Version und Browser als
  GitHub-Issue melden, falls sich das anders verhält. Der fünfte
  Editor-Abschnitt, "Farben", ist von dieser Einschränkung seit Version
  1.0.4 **nicht** mehr betroffen: er verwendet statt `ha-form` einfaches,
  browser-eigenes HTML (`<details>`, `<input type="color">`), das seit
  Langem in praktisch jedem Browser gleich funktioniert. Dessen
  Icon-Größe/Schriftgröße wurde in Version 1.0.4 noch einmal geprüft und an
  die von `ha-form` für die anderen vier Abschnitte verwendeten
  Standardwerte (24px Icon-Größe, 16px Schriftgröße, `--primary-text-color`)
  angeglichen - verifiziert per automatisiertem Test gegen die tatsächlich
  gerenderte DOM (`getComputedStyle()`), mangels Zugriff auf eine echte
  Home-Assistant-Installation in dieser Entwicklungsumgebung aber ebenfalls
  noch nicht an echter Hardware/Companion App gegengeprüft - bitte mit
  Screenshot melden, falls die fünf Abschnittsüberschriften optisch
  weiterhin unterschiedlich groß wirken.
- **Filter-/Sortierleiste - keine "Eigene Rufnummer" bei Anrufbeantworter-
  Nachrichten** (seit Version 1.0.4): Die FRITZ!Box-TAM-Nachrichtenliste
  (TR-064-Aktion `GetMessageList`, `fritzconnection`-Modell `TamMessage`)
  liefert für jede Nachricht nur Anrufer, Datum, Dauer und Name - **keine**
  eigene Rufnummer/MSN, im Gegensatz zur normalen Anrufliste
  (`GetCallList`). Das Dropdown "Eigene Rufnummer" der Filter-/Sortierleiste
  kann diese Information deshalb für den Anrufbeantworter-Tab grundsätzlich
  nicht anbieten - eine FRITZ!Box/fritzconnection-seitige Einschränkung,
  nicht etwas, das diese Integration umgehen könnte. Die Sortierung
  (Datum/Dauer/Name) ist davon nicht betroffen und funktioniert auf jedem
  Tab, einschließlich Anrufbeantworter.
- **Anrufbeantworter-Nachrichten löschen - unwiderruflich**
  (seit Version 1.0.5): Die TR-064-Aktion `DeleteMessage` löscht sofort und
  endgültig - die FRITZ!Box selbst hat dafür keinen Papierkorb. Der Button
  ist deshalb standardmäßig ausgeblendet (`show_delete_button: false`) und
  zeigt vor dem eigentlichen Löschen eine Bestätigung.
- **Event bei neuer Anrufbeantworter-Nachricht - noch nicht an eigener
  Hardware bestätigt** (seit Version 1.1.0): Die Erkennung vergleicht bei
  jedem Abruf der Nachrichtenliste die aktuellen Nachrichten-IDs mit denen
  des vorherigen Abrufs - technisch unabhängig von den bereits an echter
  Hardware bestätigten TR-064-Aktionen (`GetMessageList` selbst wird
  unverändert genutzt), aber als komplett neue Logik dieser Version wie
  üblich zunächst unbestätigt. `name`/`number` im Event-Payload stammen
  direkt von der FRITZ!Box, ohne Abgleich mit dem Home-Assistant-Telefonbuch
  dieser Integration - bei einem unbekannten Anrufer bleiben beide Felder
  ggf. leer.
- **Spam-Erkennung - kein natives FRITZ!Box-Signal** (seit Version 1.1.0):
  Wie unter [Spam-Erkennung](#spam-erkennung-seit-version-110-optional)
  beschrieben, gibt es keine automatische, KI-/datenbankbasierte
  Spam-Erkennung der FRITZ!Box selbst. Ohne konfigurierte `spam_numbers`
  erkennt diese Integration nur Anrufe, die die FRITZ!Box bereits selbst
  blockiert hat - alles andere erfordert eine selbst gepflegte Liste.
- **Anrufbeantworter 2 bis 5 - TAM-Indizes unbestätigt, kein eigener
  Karten-Tab** (seit Version 1.1.0, erweitert auf bis zu 5 in Version
  1.1.1): Die Existenz eines zweiten, über den TAM-Index "1" ansprechbaren
  Anrufbeantworters stützt sich auf Hinweise in der TR-064-Dokumentation
  sowie den bereits bestehenden Code-Kommentar in `tam.py`. Für
  Anrufbeantworter 3 bis 5 (TAM-Indizes "2"/"3"/"4") nimmt die Integration
  seit Version 1.1.1 zusätzlich eine rein fortlaufende Nummerierung an -
  das ist eine reine Vermutung, noch weniger abgesichert als bei Index "1".
  Keine dieser Annahmen wurde (mangels passender Testhardware in dieser
  Entwicklungsumgebung) an echter Hardware mit tatsächlich konfigurierten
  weiteren Anrufbeantwortern verifiziert - bei fehlender
  Hardware-Unterstützung bleibt der jeweilige Sensor einfach dauerhaft
  "nicht verfügbar", ohne die übrige Integration zu beeinträchtigen. Es
  gibt weiterhin keinen eigenen Tab/Icon in der Kartenkopfzeile dafür - seit
  Version 1.1.0 lässt sich der zweite Anrufbeantworter, seit Version 1.2.0
  auch der dritte bis fünfte, direkt im bestehenden Anrufbeantworter-Tab mit
  anzeigen (`entity_voicemail_2`/`_3`/`_4`/`_5`), siehe
  [Mehrere Anrufbeantworter anzeigen](#mehrere-anrufbeantworter-anzeigen-seit-version-110-erweitert-in-version-120-optional).
- **Migration von `second_tam_enabled`** (seit Version 1.1.1): Die
  automatische Übernahme des alten Boolean-Werts in die neue Anzahl (siehe
  [Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111))
  wurde nur gegen synthetische Testdaten geprüft, nicht an einem
  tatsächlichen Bestandssystem mit echter FRITZ!Box. Sollte nach einem
  Update auf 1.1.1 die Anzahl der Anrufbeantworter in den
  Integrations-Einstellungen nicht dem erwarteten Wert entsprechen, bitte
  als GitHub-Issue melden - die vorherige entity_id
  `sensor.fritzbox_anrufe_anrufbeantworter_2` bleibt in jedem Fall
  unverändert erhalten.
- **Anrufbeantworter Ein/Aus-Schalter - `SetEnable` unbestätigt, kein
  Zustands-Rücklesen** (seit Version 1.1.0): Die TR-064-Aktion `SetEnable`
  wurde ausschließlich durch Namenskonvention innerhalb des bereits
  bestätigten Diensts `X_AVM-DE_TAM1` hergeleitet, nicht durch AVMs
  offizielle Dokumentation oder eine Community-Referenz. Aus demselben
  Grund, aus dem `GetInfo` in dieser Integration grundsätzlich nicht
  verwendet wird (dessen genaue Rückgabewerte konnten trotz mehrerer
  Versuche nicht bestätigt werden), liest der Schalter den tatsächlichen
  Zustand nicht von der FRITZ!Box zurück, sondern zeigt ausschließlich den
  zuletzt über Home Assistant selbst gesetzten (`assumed_state`) - siehe
  [Anrufbeantworter Ein/Aus-Schalter](#anrufbeantworter-einaus-schalter-seit-version-110-experimentell).
  Bitte mit dem Ergebnis eines eigenen Tests als GitHub-Issue melden.

## Versionshistorie

- **1.2.0**: **Bis zu fünf Anrufbeantworter direkt in einer Karte:** die
  mitgelieferte Dashboard-Karte unterstützt jetzt alle bis zu fünf
  Anrufbeantworter direkt in derselben Karte (neue Felder
  `entity_voicemail_3`/`_4`/`_5`, analog zu `entity_voicemail_2`) - bislang
  war dafür ab dem dritten stets eine eigene, zusätzliche Karteninstanz
  nötig. Neuer Darstellungsmodus **`accordion`** (`voicemail_2_mode`): je
  Anrufbeantworter ein unabhängig auf-/zuklappbarer Abschnitt, ab drei
  konfigurierten Anrufbeantwortern automatisch verwendet, da "merged"/
  "separate" nur für genau zwei Listen sinnvoll definiert sind - ein
  Abschnitt mit ungehörten Nachrichten öffnet sich beim ersten Anzeigen
  automatisch. Zusätzlich neu: eine Auswahl, WELCHE Anrufbeantworter
  überhaupt angezeigt werden - dauerhaft über neue Editor-Schalter
  `show_voicemail_1` bis `_5`, und (sobald zwei oder mehr Anrufbeantworter
  konfiguriert sind) zusätzlich direkt auf der Karte über Kontrollkästchen,
  ohne die Karte bearbeiten zu müssen. Siehe
  [Mehrere Anrufbeantworter anzeigen](#mehrere-anrufbeantworter-anzeigen-seit-version-110-erweitert-in-version-120-optional)
  für Details. Keine Änderungen an der Integration selbst (reine
  Karten-/Dashboard-Erweiterung) - bestehende Konfigurationen mit nur einem
  oder zwei Anrufbeantwortern bleiben optisch unverändert (Standard
  weiterhin `merged`, alle `show_voicemail_N` standardmäßig an).
- **1.1.2**: **Bugfix (Grundeinstellungen):** Der in 1.1.1 als behoben
  gemeldete Fehler "not a valid value" beim Speichern eines leer
  gelassenen Felds **Präfixe** oder **Spam-Nummern/-Vorwahlen** trat in
  einem konkreten Fall weiterhin auf: wurde das Feld nie befüllt und
  direkt gespeichert, übermittelte Home Assistant dafür offenbar eine
  leere Liste statt des erwarteten `null` - ein Fall, den der bisherige
  automatisierte Test fälschlich als "muss abgelehnt werden" eingestuft
  hatte. Die interne Validierung akzeptiert diesen (und weitere
  gleichwertige "kein Wert"-Formen) jetzt zusätzlich, ohne die Darstellung
  des Formularfelds zu verändern. Beide Felder lassen sich damit jetzt
  tatsächlich in jedem Fall leer lassen.
- **1.1.1**: **Mehrere Anrufbeantworter** (bis zu 5, statt bisher fest 1
  oder 2): die Options-Flow-Einstellung `second_tam_enabled` entfällt
  zugunsten einer neuen, schaltflächenbasierten Auswahl unter
  "Anrufbeantworter verwalten" (Einstellungen → Geräte & Dienste →
  FRITZ!Box Anrufe → "Konfigurieren"), mit der sich die Anzahl abgefragter
  Anrufbeantworter schrittweise zwischen 1 und 5 einstellen lässt - siehe
  [Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111).
  Bestehende Installationen mit aktiviertem `second_tam_enabled` werden
  beim ersten Start nach dem Update automatisch und ohne weiteres Zutun auf
  die neue Einstellung migriert (aktiviert → 2, deaktiviert → 1). Für jeden
  konfigurierten Anrufbeantworter ab dem dritten (Anrufbeantworter 3 bis 5)
  gilt dieselbe experimentelle Einschränkung wie bereits seit Version 1.1.0
  für den zweiten: der verwendete TR-064-Index ist nicht unabhängig
  bestätigt, sondern aus einer fortlaufenden Nummerierung abgeleitet. Die
  mitgelieferte Dashboard-Karte selbst wurde nicht erweitert - sie
  unterstützt weiterhin nur einen zweiten Anrufbeantworter direkt in
  derselben Karte (`entity_voicemail_2`); Anrufbeantworter 3 bis 5 lassen
  sich über zusätzliche Karteninstanzen einbinden.

  **Bugfix (Grundeinstellungen):** Ein leer gelassenes Textfeld bei
  **Präfixe** oder **Spam-Nummern/-Vorwahlen** führte zuvor zu einer
  Fehlermeldung ("expected str") beim Speichern, obwohl beide Felder
  optional sind - Home Assistant übermittelt ein leeres Textfeld intern als
  `null`, was die bisherige Validierung nicht zuließ. Behoben, beide Felder
  lassen sich jetzt problemlos leer lassen. (Zwei Korrekturversuche
  brachten dabei jeweils kurzzeitig einen neuen, eigenen Fehler mit sich -
  zunächst ein leerer, nur mit "Fehler" betitelter Dialog beim Öffnen der
  "Grundeinstellungen", danach eine Meldung "not a valid value" beim
  Speichern; beide sind mit der jetzt ausgelieferten, auf einem
  vollwertigen Text-Selector statt einem einfachen Typ basierenden Fassung
  behoben.)
- **1.1.0**: **Anrufbeantworter Ein/Aus-Schalter** (neu, experimentell):
  ein neuer Schalter pro konfiguriertem Anrufbeantworter schaltet diesen
  über TR-064 (`SetEnable`) ein bzw. aus - siehe
  [Anrufbeantworter Ein/Aus-Schalter](#anrufbeantworter-einaus-schalter-seit-version-110-experimentell).
  Ist ein zweiter Anrufbeantworter konfiguriert, steht derselbe Schalter
  auch für ihn zur Verfügung. Auf der Dashboard-Karte erscheint der
  Schalter, sofern aktiviert (`show_tam_switch`, standardmäßig aus, im
  Editor unter "Darstellung"), direkt unter der Kategorie Anrufbeantworter
  vor der Nachrichten-Auflistung.

  Außerdem in dieser Version zusammengeführt: **Event bei neuer
  Anrufbeantworter-Nachricht** (`fritzbox_anrufe_new_voicemail_message`,
  gefeuert sobald beim Abruf der Nachrichtenliste eine gegenüber dem
  vorherigen Abruf neue Nachrichten-ID entdeckt wird - direkt als
  Automations-Auslöser nutzbar, ohne die `messages`-Attributliste selbst
  per Vorlage auf neu hinzugekommene Einträge vergleichen zu müssen, siehe
  [Event bei neuer Anrufbeantworter-Nachricht](#event-bei-neuer-anrufbeantworter-nachricht-seit-version-110));
  **Spam-Erkennung** (Anrufe und Anrufbeantworter-Nachrichten werden als
  Spam markiert - `spam`-Feld in `calls`/`messages` sowie im Event-Payload -
  wenn die FRITZ!Box den Anruf bereits selbst blockiert hat und/oder die
  Nummer mit einer selbst gepflegten Options-Flow-Liste (`spam_numbers`)
  übereinstimmt, siehe
  [Spam-Erkennung](#spam-erkennung-seit-version-110-optional); Karte kann
  Spam-Einträge markieren oder ausblenden, `hide_spam`, siehe
  [Spam ausblenden](#spam-ausblenden-seit-version-110-optional));
  **Zweiter Anrufbeantworter** (Options-Flow-Einstellung
  `second_tam_enabled`, standardmäßig aus, richtet bei Bedarf einen
  zweiten Anrufbeantworter-Sensor `fritzbox_anrufe_anrufbeantworter_2` mit
  denselben Fähigkeiten wie der erste ein, siehe
  [Mehrere Anrufbeantworter](#mehrere-anrufbeantworter-bis-zu-5-seit-version-111))
  samt direkter Anzeige in derselben Dashboard-Karte (`entity_voicemail_2`,
  `voicemail_2_mode`: `merged` oder `separate`, siehe
  [Mehrere Anrufbeantworter anzeigen](#mehrere-anrufbeantworter-anzeigen-seit-version-110-erweitert-in-version-120-optional)).
  Beim allerersten Event-Abruf nach einem Neustart wird bewusst kein Event
  gefeuert, um keine Benachrichtigungen für längst bekannte, nur noch nicht
  abgehörte Nachrichten auszulösen.
- **1.0.5**: Anrufbeantworter-Nachrichten lassen sich jetzt direkt über die
  Dashboard-Karte löschen (neuer Papierkorb-Button, `show_delete_button`,
  standardmäßig aus - siehe
  [Anrufbeantworter-Nachrichten löschen](#anrufbeantworter-nachrichten-löschen-seit-version-105-optional)),
  unwiderruflich über die TR-064-Aktion `DeleteMessage`, mit Bestätigung vor
  dem eigentlichen Löschen und einem neuen
  `fritzbox_anrufe.delete_voicemail_message`-Entity-Service für eigene
  Automatisierungen. Zusätzlich eine neue Options-Flow-Einstellung
  `auto_mark_read` (standardmäßig aus): markiert eine
  Anrufbeantworter-Nachricht nach erfolgreicher Wiedergabe über diese
  Integration automatisch auf der FRITZ!Box selbst als gelesen, genau wie
  beim Abhören an einem FRITZ!Box-eigenen Gerät (TR-064-Aktion
  `MarkMessage` - siehe
  [Automatisch als gelesen markieren](#automatisch-als-gelesen-markieren-seit-version-105-optional)).
  Anders als die rein optischen `show_*`-Kartenoptionen sitzt dieser
  Schalter bewusst auf Integrations- statt Kartenebene, weil er
  tatsächlichen, von allen Apps/Dashboards geteilten Zustand auf der Box
  ändert. Beide Fähigkeiten wurden bewusst nacheinander entwickelt und
  jede für sich mit Thorsten getestet, bevor die nächste dazukam - die
  automatische Markierung als gelesen löst nach der Wiedergabe eine
  Kartenaktualisierung aus, die eine noch laufende Audiowiedergabe nicht
  unterbrechen darf; die entsprechende Schutzlogik wurde von Anfang an
  gemeinsam mit dieser Funktion gebaut und getestet, nicht erst als
  Korrektur nachgereicht. Beide Fähigkeiten wurden von Thorsten an eigener
  Hardware erfolgreich getestet und bestätigt.
- **1.0.4**: Individuelle farbliche Gestaltung der Dashboard-Karte über den
  grafischen Editor (neuer Bereich "Farben", zwölf `color_*`-Schlüssel für
  Tab-Farbe, VIP-Stern, Zeilen-Icons, Live-Banner, Weiterverarbeitungs-Icons
  sowie je eine eigene Farbe pro Kategorie-Tab-Icon - siehe
  [Farben](#farben-seit-version-104-optional)) mit grafischer Farbauswahl
  (`<input type="color">`), Anzeige des aktuell wirksamen Werts je Feld und
  einem "Alle Farben zurücksetzen"-Button. **Eine an einer Kategorie
  eingestellte Icon-Farbe färbt jetzt auch die Zeilen-Icons dieser Kategorie
  in der Anrufliste ein**, nicht mehr nur das Tab-Symbol - einzige Ausnahme:
  ist `color_row_icon` (eine Farbe für ALLE Zeilen-Icons) gesetzt, gewinnt
  diese einheitliche Einstellung. Grafischer Karten-Editor jetzt in fünf
  aufklappbare Abschnitte gruppiert (Sensoren/Kategorien/Darstellung/
  Weiterverarbeitung/Farben); alle fünf Akkordeon-Köpfe verwenden dieselbe
  Icon-Größe (24px) und Schriftgröße (16px), nachdem der zuletzt eigens
  gebaute "Farben"-Abschnitt anfangs kleiner wirkte als die anderen vier -
  siehe [Bekannte Einschränkungen](#bekannte-einschränkungen) zur
  verbleibenden Unsicherheit ohne echte Hardware/Companion-App-Bestätigung.
  Optionale Filter-/Sortierleiste direkt auf der Karte (`show_filter_bar`,
  standardmäßig aus): nach eigener Rufnummer filtern (nur Anrufliste, nicht
  Anrufbeantworter) und nach Datum/Dauer/Name sortieren - siehe
  [Filter-/Sortierleiste](#filter-sortierleiste-seit-version-104-optional).
  Fix für einen horizontalen Scrollbalken in der Tab-Leiste, der auf einer
  schmalen Desktop-Dashboard-Spalte auftreten konnte, seit "Eingehend" in
  Version 1.0.3 zum längeren "Angenommen" wurde - die Tab-Leiste reagiert
  jetzt auf die tatsächliche Kartenbreite statt nur auf die Fensterbreite.
  Fix für eine unbehandelte Ausnahme im Fallback-Login-Pfad der
  Anrufbeantworter-Wiedergabe, die auf manchen FRITZ!Box-Kontokonfigurationen
  zu einem rohen HTTP 500 statt einer sauberen, protokollierten 502-Antwort
  führte - siehe [Fehlerbehebung](#fehlerbehebung). Einige Features dieser
  Version (die breitenabhängige Tab-Leiste, die aufklappbaren
  Sensoren/Kategorien/Darstellung/Weiterverarbeitung-Editor-Abschnitte)
  beruhen auf vergleichsweise moderner Web-Plattform-Technik und sind noch
  nicht an einer breiten Auswahl echter Home-Assistant-Frontend-Versionen
  bestätigt - siehe [Bekannte Einschränkungen](#bekannte-einschränkungen).
  Über mehrere Vorabversionen hinweg schrittweise mit Thorsten anhand
  seiner eigenen Praxistests entwickelt und verfeinert.
- **1.0.3**: Größere Überarbeitung der Anrufklassifizierung, gemeinsam mit
  Thorsten anhand von Beobachtungen an seiner eigenen FRITZ!Box entwickelt.
  Eingehende Anrufe, die an den Anrufbeantworter weitergeleitet wurden
  (erkannt am von der FRITZ!Box gemeldeten Gerät `"Anrufbeantworter"`),
  zählen jetzt zu "Verpasste Anrufe" statt zu "Eingehende Anrufe" - diese
  Kategorie heißt in der UI deshalb jetzt **"Angenommen"** statt
  "Eingehend" (Sensor-Anzeigename, Karten-Tab, Editor-Beschriftungen; die
  technische entity_id/der interne Schlüssel bleiben zur Abwärtskompatibilität
  unverändert `eingehend`), da sie nur noch tatsächlich von einer Person
  angenommene Anrufe enthält. Von der FRITZ!Box selbst abgewiesene Anrufe
  erscheinen jetzt korrekt als "Verpasst" statt in keinem Sensor. Jeder
  Anruf-Eintrag hat jetzt zusätzlich ein `outcome`-Feld (feinere
  Klassifizierung: `beantwortet`/`anrufbeantworter`/`keine_nachricht`/
  `nicht_erreicht`/`verbunden`/`nicht_verbunden`, siehe [Sensoren](#sensoren))
  sowie bei Anrufbeantworter-Nachrichten ein `media_url`-Feld - ob eine
  Nachricht aufgezeichnet wurde, wird per Datum/Uhrzeit- (und ggf.
  Rufnummer-)Abgleich mit den echten Anrufbeantworter-Nachrichten bestätigt,
  nicht nur vermutet. Neue, optionale "Weiterverarbeitung"-Zeile auf der
  Dashboard-Karte (vier neue `show_processing_*`-Schalter, standardmäßig
  aus) zeigt den Ausgang jedes Anrufs mit Icon und verlinkt zum passenden
  Tab bzw. spielt bei einer aufgezeichneten Nachricht die Aufnahme direkt
  inline ab - siehe
  [Weiterverarbeitung](#weiterverarbeitung-seit-version-103-optional).
  Ausgehende Anrufe ohne zustande gekommene Verbindung, die die FRITZ!Box
  über TR-064 gar nicht erst in ihre Anrufliste einträgt, werden jetzt über
  den Live-Callmonitor selbst erfasst und ergänzt (siehe
  [Bekannte Einschränkungen](#bekannte-einschränkungen) für die
  In-Memory-Einschränkung dabei). Der Live-Sensor löst außerdem eine
  gezielte Aktualisierung der Verlaufs-/Anrufbeantworter-Sensoren aus,
  sobald er nach einem Anruf wieder auf `idle` wechselt - ein Anruf
  erscheint dadurch meist binnen Sekunden statt erst nach bis zu 5 Minuten.
  Bekannte, dokumentierte Einschränkungen (kein "besetzt"-Signal bei
  ausgehenden Anrufen; innerhalb von `keine_nachricht` keine feinere
  Unterscheidung zwischen "vor dem Anrufbeantworter aufgelegt" und
  "Anrufbeantworter erreicht, aber nichts gesagt"; die neue
  Direktwiedergabe-Funktion aus der Anrufliste heraus ist nur als Fallback
  aktiv und selbst nicht separat an Hardware verifiziert) - siehe jeweils
  [Bekannte Einschränkungen](#bekannte-einschränkungen). Temporäres
  Debug-Logging hilft, Rohdaten für die offene Detailfrage zu sammeln
  (siehe [Fehlerbehebung](#fehlerbehebung)).
- **1.0.2**: Fix für "Dashboard-Karte wird nicht gefunden" bzw.
  "Konfigurationsfehler: Custom-Element ist im Frontend unbekannt" trotz
  fehlerfrei geladener Integration und vorhandener Kartendatei - betraf
  einen Teil der Installationen. Ursache (durch Tests eines Nutzers,
  marcedale, an echter Hardware bestätigt): die Karte wurde auf zwei
  Wegen gleichzeitig registriert, direkt eingebettet über
  `add_extra_js_url()` **und** als Ressourcen-Eintrag unter
  Einstellungen → Dashboards → Ressourcen. Ein Browser führt eine
  Modul-URL aber nur genau einmal aus - schlug der eingebettete Weg fehl
  (z. B. wegen einer bereits zwischengespeicherten Startseite in Browser
  oder Companion-App), galt die URL als "abgearbeitet", und der
  Ressourcen-Eintrag konnte sie danach nicht mehr laden, selbst wenn er
  korrekt angelegt war. Fix: Die Karte wird jetzt ausschließlich noch als
  Ressourcen-Eintrag geladen (`add_extra_js_url()` entfernt), inklusive
  Versionsparameter an der URL (`?v=<Version>`) zur zuverlässigen
  Cache-Invalidierung nach Updates. Details siehe
  [Fehlerbehebung](#fehlerbehebung). Zusätzlich robuster gegen eine falsch
  konfigurierte `entity_live`: Das Live-Banner erscheint jetzt nur noch bei
  den drei bekannten Anruf-Zuständen (Klingelt/Wählen/Gespräch läuft) statt
  bei "allem außer ein paar bekannten Ruhezuständen" - zeigt ein falsch
  zugeordneter Sensor (z. B. der Anrufbeantworter-Sensor mit seiner
  Nachrichtenanzahl als Zustand) also z. B. den Wert `10`, bleibt das
  Banner jetzt korrekt ausgeblendet statt die Zahl dauerhaft anzuzeigen.
- **1.0.1**: Fünf separate Sensoren (`_live`/`_eingehend`/`_ausgehend`/
  `_verpasst`/`_anrufbeantworter`) mit sprachabhängigem Anzeigenamen
  (Deutsch/Englisch) und fest reservierter, sprachneutraler entity_id für
  neu angelegte Entities; je Verlaufs-Sensor unabhängig einstellbare
  Verlaufstiefe (Anzahl-Dropdown mit festen Presets oder Tage), bereits bei
  der Erst-Einrichtung wählbar; mitgelieferte interaktive Dashboard-Karte
  `fritzbox-anrufe-card` (Icon-Filterleiste, Live-Banner, responsives
  Layout, grafischer Karten-Editor mit Sensor-/Zeilen-/Spaltenauswahl,
  Zeilenanzahl per Schieberegler 1-15) mit **experimentellem**
  Anrufbeantworter-Sensor (Nachrichtenliste und Wiedergabe an echter
  Hardware bestätigt funktionsfähig, u. a. unter FRITZ!OS 8.24) samt im
  Dashboard direkt abspielbaren Sprachnachrichten über einen
  authentifizierten Server-Proxy und "Abspielen"-Button
  (`hass.fetchWithAuth`; Download-Details siehe
  [Bekannte Einschränkungen](#bekannte-einschränkungen)); alle Kategorien
  (Alle/Gesamt, Eingehend, Ausgehend, Verpasst, Anrufbeantworter) einzeln
  ein-/ausblendbar auf derselben Karte; FRITZ!-Marken-Icon (`brand/`);
  Übersetzungsdateien (`translations/`) ergänzt, die für
  Home-Assistant-Custom-Integrations zwingend nötig sind, damit übersetzte
  Entitätsnamen überhaupt greifen.
- **1.0.0**: Umbenennung von `fritzbox_callmonitor` auf `fritzbox_anrufe`;
  drei neue Verlaufs-Sensoren für eingehende/ausgehende/verpasste Anrufe
  (TR-064-basiert) mit gemeinsam konfigurierbarer Verlaufstiefe
  (Anzahl oder Tage); `flex-table-card`-Beispielkarte.

## Datei-Integrität (Hash-Kommentare)

Seit Version 1.0.5 trägt jede Python-/JavaScript-/YAML-Datei dieser
Integration als allererste Zeile einen Kommentar mit dem SHA256-Hash
ihres restlichen Inhalts, z. B.:

```
# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 85bb4d0d...
```

Der Hash deckt bewusst nicht die Kommentarzeile selbst ab (das wäre
technisch unmöglich - eine Datei kann keinen Hash über sich selbst
*inklusive* dieses Hashwerts enthalten), sondern alles AB Zeile 2, also
exakt den ursprünglichen Dateiinhalt vor dem Einfügen dieser Zeile. Zum
Nachrechnen z. B. unter Linux/macOS:

```
tail -n +2 tam.py | sha256sum
```

Stimmt das Ergebnis mit dem in Zeile 1 eingetragenen Wert überein, ist die
Datei unverändert gegenüber dieser Auslieferung. JSON-Dateien
(`manifest.json`, `strings.json`, `translations/*.json`, `icons.json`)
unterstützen technisch keine Kommentare und bleiben deshalb unverändert -
ihre Hashes stehen stattdessen in der Tabelle unten (dort ganz normal über
die komplette Datei, z. B. `sha256sum manifest.json`).

| Datei | SHA256 (Version 1.2.0) |
| --- | --- |
| `__init__.py` | `85eaddff90e92ebc314aa5e7474f97707e9e2fdfa02525cc7ff0f359cd962f6c` |
| `base.py` | `8b263a8dd288006c4461a00b5d120548f1b1f7add1e3b7c9faa5f9fc1cd45986` |
| `call_log.py` | `c7115af494200e8a19dae9efaed855680b4ac8186b81788aeacb6c5aae8721f9` |
| `config_flow.py` | `10ad669abc160bc54dd79087757cff21306105c72f9864820e574f01f790cf99` |
| `const.py` | `69cadf3c875e12376cc945e1b072393f2459c6dc5763d484261b2afe031be0a6` |
| `http.py` | `a5823e4d0838b8783484179dbdbe17290bd484017ccc38001a29e57463d999cf` |
| `sensor.py` | `4116f337557a8eea43d8a85f47293928e20651c04d7b6516e5bf8b1e6a5a1b90` |
| `spam.py` | `2e300431c40ce61953fc92a4e92e661caa7c825b26683a3ce6d70c6ebc04872b` |
| `switch.py` | `7cdbb0e5d3c5d1c8fa3cc5cad1cba6fa1f666b6c7eb1e034fbed40861b0e73c2` |
| `tam.py` | `b569e1109b1dbc84a552dd36835fb912aa3ae5b47a29a516c523783e799e09c6` |
| `voicemail.py` | `b03e665eba0cb346c8877988da845a957a6737f9a8a6de8811fe2199a0e4e9b7` |
| `services.yaml` | `9745c630a06b64f58563bf7abca6dbd5607d6b2c8c16b0d47490edf393b4372b` |
| `www/fritzbox-anrufe-card.js` | `341fc1a75747fad57a140258f25f69f3f985931a3947269f91aa54369a056dce` |
| `manifest.json` | `bed4ea016b419a405bc4fa759fc6291cf2d62e9d804b22b512c840a1cece4510` |
| `strings.json` | `7141f53bb34bf7ee725238b0406ce0e1f9875c3e7cf4076032e43008f752a93b` |
| `translations/de.json` | `b50b22d3cd943bea2b835fc5e73039ccdb3704bd95655fff86e0430cec0bd4fd` |
| `translations/en.json` | `7141f53bb34bf7ee725238b0406ce0e1f9875c3e7cf4076032e43008f752a93b` |
| `icons.json` | `b1ebf716e78af310f50d29096270ab340a0d82d8f6183347c79d08ee7fdd495c` |

## Fehlerbehebung

- **Verlaufs-Sensoren zeigen `unavailable`**: Kontoberechtigung
  "Sprachnachrichten, Faxnachrichten, FRITZ!App Fon und Anrufliste" prüfen
  (siehe [Voraussetzungen](#voraussetzungen)); Fehlermeldung dazu erscheint
  im Home-Assistant-Log.
- **Integration erscheint nach Update nicht mehr in "Geräte & Dienste"**:
  Meist ein unvollständiger Download/Cache-Rest. Ordner
  `custom_components/fritzbox_anrufe` komplett löschen, in HACS erneut
  herunterladen, Home Assistant vollständig neu starten.
- **Sensoren zeigen nur den Gerätenamen statt "Angenommene Anrufe" etc.**:
  Home Assistant vollständig neu starten (Übersetzungen werden beim Start
  geladen); falls das nicht reicht, die betroffenen Entitäten einmal löschen
  und die Integration neu laden lassen.
- **Dashboard-Karte "fritzbox-anrufe-card" wird nicht gefunden /
  "Konfigurationsfehler: Custom-Element ist im Frontend unbekannt"**,
  obwohl die Integration fehlerfrei lädt und die Datei
  `custom_components/fritzbox_anrufe/www/fritzbox-anrufe-card.js`
  nachweislich vorhanden ist: Seit Version 1.0.2 wird die Karte
  ausschließlich noch als echter, dauerhafter Ressourcen-Eintrag unter
  Einstellungen → Dashboards → Ressourcen registriert - das ist der einzige
  Ladeweg. (In einer früheren Zwischenversion registrierte die Karte
  zusätzlich über `add_extra_js_url()` direkt in der Startseite; das führte
  auf manchen Installationen dazu, dass die Karte nach einem Neustart der
  Companion-App dauerhaft verschwand, weil ein Browser eine Modul-URL nur
  einmal ausführt - schlug der eingebettete Weg fehl, blieb auch der
  Ressourcen-Eintrag wirkungslos. Das ist seit 1.0.2 behoben, es gibt nur
  noch den einen, zuverlässigen Weg.) Prüfen: erscheint unter
  Einstellungen → Dashboards → Ressourcen ein
  Eintrag für `/fritzbox_anrufe_files/fritzbox-anrufe-card.js` (mit einem
  `?v=...`-Versionsparameter)? Fehlt er, läuft das Dashboard vermutlich im
  YAML-Modus - dort verwaltet Home Assistant Ressourcen ausschließlich über
  `configuration.yaml`, ein automatischer Eintrag ist dann technisch nicht
  möglich; die Zeile muss einmalig manuell in die `lovelace:`-Konfiguration
  eingetragen werden (`resources: - url:
  /fritzbox_anrufe_files/fritzbox-anrufe-card.js`, `type: module` - ohne
  Versionsparameter, da hier keine automatische Aktualisierung stattfindet).
  Ist der Eintrag vorhanden, aber die Karte lädt trotzdem nicht: einmal den
  Service Worker der Website löschen (Browser-DevTools → Anwendung/
  Application → Service Worker → "Unregister") bzw. bei der Companion-App
  den App-Cache leeren, danach normal neu laden.
- **Anrufbeantworter-Sensor zeigt immer 0 Nachrichten / Warnung im Log zu
  `GetMessageList`**: experimentelle Funktion, siehe
  [Bekannte Einschränkungen](#bekannte-einschränkungen) - bitte mit dem
  Log-Auszug als GitHub-Issue melden.
- **Log-Meldung "Login attempt or request with invalid authentication ...
  /api/fritzbox_anrufe/tam_media/..." (Quelle `components/http/ban.py`)**:
  war vor der ersten Anrufbeantworter-Korrektur das erwartete Verhalten,
  wenn eine Sprachnachricht abgespielt wurde - behoben, siehe
  [Wiedergabe der Anrufbeantworter-Nachrichten](#wiedergabe-der-anrufbeantworter-nachrichten).
  Tritt es weiterhin auf: Integration auf die neueste Version aktualisiert
  und Home Assistant vollständig neu gestartet (nicht nur neu geladen), damit
  die aktualisierte Karten-Datei vom Browser geladen wird? Zusätzlich
  Browser-Cache leeren (Strg+Shift+R).
- **Sprachnachricht lässt sich in der Karte nicht abspielen** (Button zeigt
  "Fehler – erneut versuchen"): prüfen, ob die Kontoberechtigung
  "Sprachnachrichten, Faxnachrichten, FRITZ!App Fon und Anrufliste" gesetzt
  ist; ansonsten Home-Assistant-Log nach Warnungen von `fritzbox_anrufe` zur
  betroffenen Nachrichten-ID durchsuchen, sowie die Browser-Konsole (F12) auf
  Fehler beim Laden von `/api/fritzbox_anrufe/tam_media/...` prüfen.
- **Log-Meldung `custom_components.fritzbox_anrufe.http`: "Fehler beim
  Abrufen der Anrufbeantworter-Nachricht ...: Anrufbeantworter-Download
  fehlgeschlagen (HTTP 404) nach N Versuch(en) mit unterschiedlichen
  Sitzungen"**: Die Anrufbeantworter-Wiedergabe funktioniert an echter
  Hardware bestätigt (u. a. FRITZ!OS 8.24) - tritt der Fehler dennoch auf,
  zunächst prüfen, ob wirklich die neueste Version installiert ist
  (Einstellungen → Geräte & Dienste → FRITZ!Box Anrufe → Version; nach dem
  Ersetzen der Dateien Home Assistant **vollständig neu starten**, nicht
  nur neu laden). Die Integration probiert bereits automatisch mehrere
  `sid`-Quellen gegen den Web-UI-Port durch (siehe
  [Bekannte Einschränkungen](#bekannte-einschränkungen)) und meldet erst
  einen Fehler, wenn alle davon fehlschlagen - "N Versuch(en)" in der
  Meldung zeigt, wie viele das waren. Tritt der Fehler auf der aktuellen
  Version weiterhin auf, bitte mit dem vollständigen Log-Auszug **und dem
  darin enthaltenen HTTP-Statuscode sowie der FRITZ!OS-Version** als
  GitHub-Issue melden (kann z. B. auch an ein durch die FRITZ!Box-
  Blockzeit nach mehreren Fehlversuchen gesperrtes Konto liegen - in dem
  Fall kurz warten und erneut versuchen).
- **Sprachnachricht-Wiedergabe schlägt mit HTTP 500 statt einer
  aussagekräftigen Fehlermeldung fehl** (Browser-Konsole zeigt
  `status: 500` beim Abruf von `/api/fritzbox_anrufe/tam_media/...` bzw.
  `/api/fritzbox_anrufe/call_media/...`): Seit Version 1.0.4 behoben - eine
  bislang ungeschützte Stelle im Fallback-Login (der zweite von zwei Wegen,
  eine für den Datei-Download nötige Sitzungs-ID zu ermitteln, siehe
  [Wiedergabe der Anrufbeantworter-Nachrichten](#wiedergabe-der-anrufbeantworter-nachrichten))
  konnte dort auftretende Fehler nicht abfangen und ließ sie unbehandelt bis
  zum Browser durchreichen, statt sie - wie an allen anderen Stellen dieser
  Methode - in eine saubere 502-Antwort mit WARNING-Log-Zeile umzuwandeln.
  Auf der aktuellen Version erscheint stattdessen eine Log-Zeile
  "Anrufbeantworter-Download: Sitzungs-ID konnte nicht ermittelt werden
  (...)" mit dem konkreten Python-Fehlertyp und -text. Tritt der Fehler
  weiterhin auf: Diese Log-Zeile zusammen mit der FRITZ!Box-Kontoberechtigung
  des verwendeten Benutzerkontos (insbesondere, ob es Zugriff auf die
  normale FRITZ!Box-Weboberfläche hat, nicht nur auf einzelne TR-064-
  Funktionen) als GitHub-Issue melden - ein eingeschränktes, "nur für Apps"
  freigegebenes Benutzerkonto ist ein plausibler Kandidat für einen
  fehlschlagenden Fallback-Login.
- **Grafischer Karten-Editor: "Max. Zeilen" lässt sich nicht auf einen
  neuen Wert ändern / springt zurück**: dafür ist ein Schieberegler statt
  eines Texteingabefelds verbaut - Home Assistant nach dem Update
  vollständig neu starten und Browser-Cache leeren (Strg+Shift+R). Bis auf
  15 Zeilen per Schieberegler einstellbar; höhere Werte weiterhin über den
  YAML-Editor der Karte möglich.
- **Debug-Logging aktivieren** (z. B. um Rohdaten für die offene
  "nicht_erreicht"-Detailfrage zu sammeln, siehe
  [Bekannte Einschränkungen](#bekannte-einschränkungen)): entweder unter
  Einstellungen → Geräte & Dienste → FRITZ!Box Anrufe → Drei-Punkte-Menü (⋮)
  → "Debug-Protokollierung aktivieren", oder dauerhaft per
  `configuration.yaml`:
  ```yaml
  logger:
    logs:
      custom_components.fritzbox_anrufe: debug
  ```
  Jeder Anruf erscheint danach im Home-Assistant-Log mit seinen Rohdaten
  (`Id`, `Type`, `Path`, `Duration`, `Date`) sowie dem daraus berechneten
  `bucket`/`outcome` - beim Melden eines Falls bitte diese Zeile(n)
  zusammen mit einer kurzen Beschreibung des tatsächlichen Anrufverlaufs
  (z. B. "vor dem Anrufbeantworter aufgelegt" vs. "Ansage gehört, aber
  nichts gesagt") als GitHub-Issue mitschicken.
- **Weiterverarbeitungs-Zeile spielt Aufnahme nicht ab** (Symbol zeigt
  Fehler, obwohl die Wiedergabe im Anrufbeantworter-Tab funktioniert): Diese
  neue Direktwiedergabe aus der Anrufliste heraus wurde noch nicht separat
  an echter Hardware bestätigt (siehe
  [Weiterverarbeitung](#weiterverarbeitung-seit-version-103-optional)).
  Bitte den HTTP-Statuscode aus dem Home-Assistant-Log
  (`custom_components.fritzbox_anrufe.http`, Meldung "Fehler beim Abrufen
  der Anruf-Aufnahme ...") als GitHub-Issue melden.
- **Anrufbeantworter Ein/Aus-Schalter erscheint nicht auf der Karte**:
  prüfen, ob sowohl `show_tam_switch: true` (Editor-Bereich "Darstellung")
  als auch die passende `entity_tam_switch`/`entity_tam_switch_2`-Entität
  (Editor-Bereich "Sensoren") gesetzt sind - beides zusammen ist nötig,
  siehe [Anrufbeantworter Ein/Aus-Schalter](#anrufbeantworter-einaus-schalter-seit-version-110-experimentell).
- **Anrufbeantworter Ein/Aus-Schalter schaltet den Anrufbeantworter an der
  FRITZ!Box nicht tatsächlich um**: Die zugrunde liegende TR-064-Aktion
  `SetEnable` ist experimentell und nicht unabhängig bestätigt (siehe
  [Bekannte Einschränkungen](#bekannte-einschränkungen)). Bitte mit der
  FRITZ!OS-Version und dem Modell als GitHub-Issue melden.
