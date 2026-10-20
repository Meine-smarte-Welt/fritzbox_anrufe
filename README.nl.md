[🇩🇪 Deutsch](README.md) · [🇬🇧 English](README.en.md) · 🇳🇱 Nederlands

# FRITZ!Box Gesprekken

Home Assistant-integratie voor de gesprekkenmonitor en gesprekslijsten
(inkomend, uitgaand, gemist) van een AVM FRITZ!Box, met berichten van het
antwoordapparaat, een dashboardkaart en – nieuw in 1.6.0 – telefoonnummers,
wekker, doorschakeling en gespreksstatistiek.

> **Let op:** De Duitse [README.md](README.md) is de volledige referentie
> (alle opties, kaartsleutels, spamherkenning, meerdere antwoordapparaten,
> versiegeschiedenis). Deze pagina behandelt installatie, instelling en alles
> wat nieuw is in 1.6.1 en 1.6.0.

## Functies

- Live gesprekkenmonitor (overgaan / kiezen / bellen / inactief) via de FRITZ!Box-callmonitor (TCP-poort 1012).
- Sensoren voor inkomende, uitgaande en gemiste gesprekken en antwoordapparaat-berichten (tot 5 apparaten, optionele aan/uit-schakelaar).
- Meegeleverde dashboardkaart `fritzbox-anrufe-card` met grafische editor; elke categorie kan afzonderlijk aan of uit.
- Spammarkering, afspelen van berichten, events voor nieuwe berichten en gemiste gesprekken.
- **Nieuw in 1.6.1 (pre-release):** optionele Notification Center-koppeling (gemiste oproep, nieuw bericht op het antwoordapparaat, verbinding verloren, update beschikbaar), schakelbaar in de kaart en de opties.
- **Nieuw in 1.6.0:** externe en interne telefoonnummers, wekker, doorschakeling (tonen / schakelen / verwijderen / aanmaken, experimenteel), gespreksstatistiek, versieweergave met updatemelding, kaartteksten in Duits, Engels en Nederlands.

## Vereisten

- Home Assistant 2025.6 of nieuwer, een AVM FRITZ!Box.
- Callmonitor ingeschakeld op de box (`#96*5*` op een aangesloten telefoon).
- Een FRITZ!Box-gebruiker met rechten voor telefonie, TR-064 en smarthome / FRITZ!Box-instellingen. Schrijfacties (wekker, doorschakeling) werken alleen voor Home Assistant-beheerders.

## Installatie

**HACS:** HACS → Aangepaste repositories → `https://github.com/Meine-smarte-Welt/fritzbox_anrufe` → categorie *Integratie* → downloaden → Home Assistant herstarten → browser geforceerd verversen (Ctrl+F5).

**Handmatig:** kopieer `custom_components/fritzbox_anrufe` naar je configuratiemap en herstart Home Assistant.

## Instellen

*Instellingen → Apparaten & diensten → Integratie toevoegen → "FRITZ!Box Anrufe"*; vul host, gebruiker, wachtwoord en telefoonboek in. Opties (geschiedenisdiepte, spam, antwoordapparaten) vind je onder *Configureren*. De kaart wordt automatisch geregistreerd; in YAML-modus voeg je de resource handmatig toe.

## Nieuw in 1.6.1

**Pre-release.** Versie 1.6.1 is op GitHub als *pre-release* gemarkeerd. HACS toont haar alleen als je voor deze integratie "Bètaversies tonen" inschakelt.

**Teststatus, eerlijk:** de koppeling is getest tegen een *gesimuleerde* event-bus (23 automatische tests) en de kaart is met testdata in een gesimuleerde browser gecontroleerd. **Niet getest tegen een echt Notification Center en niet op echte FRITZ!Box-hardware.** Feedback is welkom.

### Notification Center (optioneel)

De integratie kan haar meldingen naar het **Notification Center** sturen, een aparte optionele integratie die meldingen van meerdere integraties verzamelt, op urgentie sorteert en aflevert. Deze integratie *meldt* alleen en werkt volledig zonder het Notification Center door (geen fout, geen logspam). Het transport is de Home Assistant-event-bus (geen MQTT, interface "schema 1"). De bestaande events (`fritzbox_anrufe_missed_call`, `fritzbox_anrufe_new_voicemail_message`) blijven ongewijzigd.

| Meldingstype | Urgentie | Wanneer |
| --- | --- | --- |
| `connection_lost` | Waarschuwing | Oproeplijst **en** instellingen niet op te halen; sluit zich bij herstel |
| `missed_call` | Info | Gemiste oproep (live-oproepmonitor), eenmalig |
| `new_voicemail` | Info | Nieuw bericht op het antwoordapparaat, eenmalig |
| `update_available` | Info | Nieuwere versie van deze integratie op GitHub; sluit zich na de update |

Telefoonnummers en namen staan alleen als plaatshouders in de meldingen en worden nooit gelogd. Bij het starten worden bestaande toestanden alleen als beginstand gemeld (geen push). De teksten bestaan in Duits, Engels, Nederlands, Frans en Spaans; het Notification Center kiest de taal.

**Schakelaars:** kaart → tandwiel → "Notification Center" (hoofdschakelaar en een schakelaar per meldingstype, op urgentie gesorteerd) of *Instellingen → Apparaten & diensten → FRITZ!Box Anrufe → Configureren → Notification Center*. Uitgeschakelde meldingstypen worden niet verstuurd. Met `read_only: true` in de kaartconfiguratie verbergt de kaart de schakelaars van dit onderdeel en toont alleen de stand.

| Service | Doel |
| --- | --- |
| `fritzbox_anrufe.set_notification_center` | Hoofdschakelaar (`enabled`) |
| `fritzbox_anrufe.set_notification_type` | Meldingstype schakelen (`nc_type`, `enabled`) |

Beide alleen voor beheerders; geef bij meerdere FRITZ!Boxen `entry_id` mee.

Verder: de versiecontrole kent nu bèta-/RC-aanduidingen (`1.0.0b1`, `1.0.0rc1`) en houdt bij een geïnstalleerde bèta/RC ook rekening met pre-releases.

## Nieuw in 1.6.0

**Teststatus, eerlijk:** alles hieronder is getest tegen een *gesimuleerde* FRITZ!Box (23 automatische tests) en de kaart is in een browser met testdata gecontroleerd. **Het is niet getest op echte FRITZ!Box-hardware.**

| Functie | Wat het doet |
| --- | --- |
| Telefoonnummers | Tik op een telefoonapparaat op het tabblad Instellingen voor een pop-up met aansluiting, uitgaand, inkomend en intern nummer ("alle" = gaat over op alle nummers). Tabblad Instellingen → "Nummers": externe nummers (TR-064 `GetNumbers`) en interne nummers per apparaat. IP-telefoons/apps komen via TR-064; analoge/DECT-nummers komen nog uit de webinterface van de box en zijn gemarkeerd als "niet geverifieerd". Ontbrekende waarden tonen "–". Of FHEM interne nummers toont kon ik niet bevestigen; de implementatie volgt de AVM-documentatie. |
| Wekker | Toont tijd, weekdagen, naam en status. **Aan/uit zetten** gebruikt de gedocumenteerde TR-064-aanroep. AVM heeft **geen** TR-064-aanroep voor tijd/weekdagen, dus een wekker *wijzigen* (de box heeft vaste plaatsen, meestal 3) is **experimenteel** via de webinterface; het resultaat wordt teruggelezen en een afwijking wordt als fout gemeld. |
| Doorschakeling | Toont bestaande regels, schakelt ze aan/uit, **verwijdert** en **maakt** ze **aan** (knop "Nieuwe doorschakeling"; bevestiging met twee klikken, alleen beheerder). **Experimenteel:** AVM heeft hiervoor geen TR-064-aanroep; de integratie gebruikt dezelfde formuliervelden als de webinterface van de box (`callRedi` / `rul_edit`, opgeslagen via `data.lua`). Veldnamen en waarden zijn uit de paginascripts van een FRITZ!Box 5690 Pro gelezen; **opslaan is niet op echte hardware getest.** Beveiligingen: waarden worden met de lijsten van de box vergeleken, na het opslaan wordt teruggelezen (geen treffer = fout), een tweefactorvraag wordt niet omzeild. Bestaande regels kunnen niet worden bewerkt (verwijderen en opnieuw aanmaken). |
| Gespreksstatistiek | `sensor.fritzbox_anrufe_anrufstatistik` (totaal, nieuw, vandaag, laatste 7/30 dagen, laatste gesprek, laatste 14 dagen, per uur, lijst) en `sensor.fritzbox_anrufe_letzter_ab_anruf` (tijdstempel). Telt wat de box nu op het antwoordapparaat bewaart – niet alle gesprekken. Kaarttabblad "Statistiek" (`show_statistik`, standaard uit). |
| Versie en updatemelding | Op drie plekken: kaart → tandwiel → "App-versie", bovenaan de kaarteditor, optiesdialoog. De integratie controleert de GitHub-releases bij het starten en elke 12 uur; een nieuwere versie is oranje gemarkeerd. Is GitHub niet bereikbaar, dan werkt alles gewoon door. |

### Services (alleen beheerders)

| Service | Doel |
| --- | --- |
| `fritzbox_anrufe.set_alarm_clock_enabled` | Wekker aan/uit (`index`, `enabled`) |
| `fritzbox_anrufe.set_alarm_clock` | Tijd / weekdagen / naam / status instellen (experimenteel) |
| `fritzbox_anrufe.set_deflection_enabled` | Doorschakelregel aan/uit via TR-064 (`deflection_id`, `enabled`) |
| `fritzbox_anrufe.create_call_forwarding` | Doorschakeling aanmaken (experimenteel): `mode` (`to`/`from`/`all`), `target`, `from_number`, `dest_type` (`number`/`answering_machine`/`phone`), `dest`, `own_number`, `kind` |
| `fritzbox_anrufe.set_call_forwarding_enabled` | Doorschakeling van de webinterface aan/uit (`uid`, `enabled`; ID's in attribuut `forwardings`) |
| `fritzbox_anrufe.delete_call_forwarding` | Doorschakeling verwijderen (`uid`) |
| `fritzbox_anrufe.check_for_update` | GitHub-versiecontrole direct uitvoeren |
| `fritzbox_anrufe.collect_diagnostics` | Ruwe antwoorden van de box (alleen lezen) voor foutmeldingen; geeft een antwoord terug |

Bij meerdere FRITZ!Boxen geef je ook `entry_id` mee.

### Diagnose bij verkeerde nummers of doorschakeling

Als interne nummers of doorschakelregels ontbreken of niet kloppen, voer je *Ontwikkelaarstools → Acties → `fritzbox_anrufe.collect_diagnostics`* uit. Het antwoord bevat de ruwe antwoorden van de box (TR-064 en de webpagina's `telDevices` en `callHan`, ingekort, zonder sessie-id). Voeg het toe aan een GitHub-issue; het bevat je telefoonnummers, controleer en anonimiseer het dus eerst. Leesfouten staan ook als waarschuwing in het logboek.

### Kaartsleutels

`show_statistik` (standaard `false`), `show_settings_numbers`, `show_settings_alarms`, `show_settings_deflections` (standaard `true`), `entity_stats`, `entry_id`, `color_icon_statistik`. Voorbeeld:

```yaml
type: custom:fritzbox-anrufe-card
entity_eingehend: sensor.fritzbox_anrufe_eingehend
entity_ausgehend: sensor.fritzbox_anrufe_ausgehend
entity_verpasst: sensor.fritzbox_anrufe_verpasst
show_einstellungen: true
show_statistik: true
```

**Correctie:** op FRITZ!OS 8 geeft de pagina `telDev` (niet `telDevices`) HTML met een ingebedde apparatenlijst in plaats van JSON; dit wordt nu gelezen. De structuur is bekeken op een echte FRITZ!Box 5690 Pro (FRITZ!OS 8.40) en de parser ertegen getest; een volledige run in Home Assistant volgt nog. Interne nummers worden getoond zoals ze op de box gekozen worden (`**610`). Is er geen doorschakelregel op de box (pagina `callRedi`, lege regellijst), dan blijft de lijst leeg; de integratie kan geen regels aanmaken.

## Bekende beperkingen

- **Nieuw in 1.6.1 (pre-release):** de Notification Center-koppeling is alleen getest tegen een gesimuleerde event-bus, niet tegen een echt Notification Center. `read_only` werkt voorlopig alleen op dit onderdeel van de kaart.
- Nummers, wekker, doorschakeling, statistiek en updatecontrole zijn **niet op echte hardware getest**.
- Wektijd/weekdagen worden via de webinterface van de box geschreven (ongedocumenteerde formuliervelden); terugleezen voorkomt stille mislukkingen.
- Aanmaken/verwijderen van doorschakelingen loopt via de webinterface van de box (geen AVM-interface) en is **niet op echte hardware getest**; bestaande regels kunnen niet worden bewerkt.
- Interne nummers van analoge/DECT-telefoons kunnen ontbreken, afhankelijk van FRITZ!OS.
- De statistiek telt alleen berichten van het antwoordapparaat.
- Oudere kaartteksten (gesprekslijst, antwoordapparaat, telefoonapparaten) zijn nog alleen Duits; de nieuwe teksten zijn vertaald.

## Probleemoplossing

- Kaart niet bijgewerkt: browser geforceerd verversen (Ctrl+F5), service worker / companion-appcache wissen.
- Zet debug-logging aan voor `custom_components.fritzbox_anrufe` en kijk in *Instellingen → Systeem → Logboeken*.
- Meldingen: https://github.com/Meine-smarte-Welt/fritzbox_anrufe/issues

## Bestandsintegriteit

Elk `.py`-, `.js`- en `.yaml`-bestand begint met een SHA256-commentaar over de inhoud vanaf regel 2 (`tail -n +2 bestand | sha256sum`). JSON-bestanden staan hier (`sha256sum bestand`):

| Bestand | SHA256 (versie 1.6.1) |
| --- | --- |
| `__init__.py` | `75e7a86719935258d2db5076821e287e5285f65124b048fec3370aed9c72c029` |
| `alarm.py` | `83388a40874baafbe11646aabcbc2916eb6f539a6e34b38c347f649bb2cda01a` |
| `base.py` | `8b263a8dd288006c4461a00b5d120548f1b1f7add1e3b7c9faa5f9fc1cd45986` |
| `call_forwarding.py` | `64ccd3a25fbe5256339016884ec4ad80ab1e408369b029b8d9eab6a003d15aa9` |
| `call_log.py` | `06375eae8516c56b35582eb2b12f7ae09910fc908458d7a90912a45edc19c9d5` |
| `call_stats.py` | `1f22199430beba85d4856f64da1c092ebe3b27b800d1b5bc47e9d0ac6a41476b` |
| `config_flow.py` | `8ac23232ffa3d6150e381308ce0a45d86e8c5fa45681db10e2df9fcc73cc86a6` |
| `const.py` | `5e77e3fceb364fdbf519bc939557a5de49516ba59ec668ebceab74b63bd3a53d` |
| `deflection.py` | `3d41277ea2d68fcc428493a14c926cc1b0f1ae3fb8c6b08c8404f7665bb2a3e9` |
| `http.py` | `4d98f8fb1236eb7960d0d3470f0eef1a0e3a45e48e713fe121faa1481a6b70df` |
| `notification_bridge.py` | `92a92c75fe1ebc345a644069f84b250c5f08a8b2dbbd29757fa514324e19194d` |
| `notifications.py` | `f79cbec5112878d23f7b532488daf9463e2c05967989284e0663dea431b9d27a` |
| `sensor.py` | `2e048f7708b1d98c204cc84509e34dcd3c66b2e2bd20b4e412eb09c2d9eb8fc9` |
| `settings_data.py` | `d6ca7cf1a947cbb1ea77291a8bb8f5ef53313980f6a75989f8342afc522b660e` |
| `spam.py` | `026ae8bc8890be324f074d17f5fce1269d87edbb420566bdfc1aae18cf3eea11` |
| `switch.py` | `7cdbb0e5d3c5d1c8fa3cc5cad1cba6fa1f666b6c7eb1e034fbed40861b0e73c2` |
| `tam.py` | `b569e1109b1dbc84a552dd36835fb912aa3ae5b47a29a516c523783e799e09c6` |
| `telephony.py` | `7796cf8c1d6642229f2a42894bd81911236f10b0e30ff34f7ae2e5681606e9ed` |
| `update_check.py` | `00ba17b9ebc578835bbad6ae119b23385377b92e956a28b8e98cfa49621e9461` |
| `voicemail.py` | `235fe1702db39c702d54fd7e8da3d3b9e6fdfa9aed4b877c0f425f01525052c1` |
| `services.yaml` | `ec01b97d3df7d0950cc29bf131acc099e7d7183341d389ea7805a4ae831249af` |
| `www/fritzbox-anrufe-card.js` | `b65125ded927ca5177afffeae7ffe9fe40742cea7296afc889b7addfd4034e00` |
| `manifest.json` | `ca370ff049d940e9c3d941ab02691a6eaec851b06c3c030d9d9058c9a5210c14` |
| `strings.json` | `695cf986dd8eed37f7c5eb2a5191bccf6ab5e86db57dd35921526a9a49349343` |
| `translations/de.json` | `167b377ed501a7a5b425c2ec2322827848d398ab53230babdfb2e915b75411b9` |
| `translations/en.json` | `695cf986dd8eed37f7c5eb2a5191bccf6ab5e86db57dd35921526a9a49349343` |
| `translations/nl.json` | `4366dac7fa63acc24c6e33778f5a73f34ae2eef550cae527f52f1105f2bf72a3` |
| `icons.json` | `02d3f66ee5b0422973449b912573166b921745c8cbf05f8e78487227ce82d669` |
