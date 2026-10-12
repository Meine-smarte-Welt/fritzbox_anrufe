[🇩🇪 Deutsch](README.md) · [🇬🇧 English](README.en.md) · 🇳🇱 Nederlands

# FRITZ!Box Gesprekken

Home Assistant-integratie voor de gesprekkenmonitor en gesprekslijsten
(inkomend, uitgaand, gemist) van een AVM FRITZ!Box, met berichten van het
antwoordapparaat, een dashboardkaart en – nieuw in 1.6.0 – telefoonnummers,
wekker, doorschakeling en gespreksstatistiek.

> **Let op:** De Duitse [README.md](README.md) is de volledige referentie
> (alle opties, kaartsleutels, spamherkenning, meerdere antwoordapparaten,
> versiegeschiedenis). Deze pagina behandelt installatie, instelling en alles
> wat nieuw is in 1.6.0.

## Functies

- Live gesprekkenmonitor (overgaan / kiezen / bellen / inactief) via de FRITZ!Box-callmonitor (TCP-poort 1012).
- Sensoren voor inkomende, uitgaande en gemiste gesprekken en antwoordapparaat-berichten (tot 5 apparaten, optionele aan/uit-schakelaar).
- Meegeleverde dashboardkaart `fritzbox-anrufe-card` met grafische editor; elke categorie kan afzonderlijk aan of uit.
- Spammarkering, afspelen van berichten, events voor nieuwe berichten en gemiste gesprekken.
- **Nieuw in 1.6.0:** externe en interne telefoonnummers, wekker, doorschakeling (tonen / schakelen), gespreksstatistiek, versieweergave met updatemelding, kaartteksten in Duits, Engels en Nederlands.

## Vereisten

- Home Assistant 2025.6 of nieuwer, een AVM FRITZ!Box.
- Callmonitor ingeschakeld op de box (`#96*5*` op een aangesloten telefoon).
- Een FRITZ!Box-gebruiker met rechten voor telefonie, TR-064 en smarthome / FRITZ!Box-instellingen. Schrijfacties (wekker, doorschakeling) werken alleen voor Home Assistant-beheerders.

## Installatie

**HACS:** HACS → Aangepaste repositories → `https://github.com/Meine-smarte-Welt/fritzbox_anrufe` → categorie *Integratie* → downloaden → Home Assistant herstarten → browser geforceerd verversen (Ctrl+F5).

**Handmatig:** kopieer `custom_components/fritzbox_anrufe` naar je configuratiemap en herstart Home Assistant.

## Instellen

*Instellingen → Apparaten & diensten → Integratie toevoegen → "FRITZ!Box Anrufe"*; vul host, gebruiker, wachtwoord en telefoonboek in. Opties (geschiedenisdiepte, spam, antwoordapparaten) vind je onder *Configureren*. De kaart wordt automatisch geregistreerd; in YAML-modus voeg je de resource handmatig toe.

## Nieuw in 1.6.0

**Teststatus, eerlijk:** alles hieronder is getest tegen een *gesimuleerde* FRITZ!Box (19 automatische tests) en de kaart is in een browser met testdata gecontroleerd. **Het is niet getest op echte FRITZ!Box-hardware.**

| Functie | Wat het doet |
| --- | --- |
| Telefoonnummers | Tabblad Instellingen → "Nummers": externe nummers (TR-064 `GetNumbers`) en interne nummers per apparaat. IP-telefoons/apps komen via TR-064; analoge/DECT-nummers komen nog uit de webinterface van de box en zijn gemarkeerd als "niet geverifieerd". Ontbrekende waarden tonen "–". Of FHEM interne nummers toont kon ik niet bevestigen; de implementatie volgt de AVM-documentatie. |
| Wekker | Toont tijd, weekdagen, naam en status. **Aan/uit zetten** gebruikt de gedocumenteerde TR-064-aanroep. AVM heeft **geen** TR-064-aanroep voor tijd/weekdagen, dus een wekker *wijzigen* (de box heeft vaste plaatsen, meestal 3) is **experimenteel** via de webinterface; het resultaat wordt teruggelezen en een afwijking wordt als fout gemeld. |
| Doorschakeling | Toont bestaande regels en schakelt ze aan/uit (bevestiging met twee klikken, alleen beheerder, terugleescontrole). **Regels aanmaken en het doelnummer wijzigen is bewust niet geïmplementeerd** – AVM biedt geen interface en geraden formuliervelden kunnen verkeerde regels aanmaken. Gebruik *Telefonie → Oproepbehandeling* op de box. |
| Gespreksstatistiek | `sensor.fritzbox_anrufe_anrufstatistik` (totaal, nieuw, vandaag, laatste 7/30 dagen, laatste gesprek, laatste 14 dagen, per uur, lijst) en `sensor.fritzbox_anrufe_letzter_ab_anruf` (tijdstempel). Telt wat de box nu op het antwoordapparaat bewaart – niet alle gesprekken. Kaarttabblad "Statistiek" (`show_statistik`, standaard uit). |
| Versie en updatemelding | Op drie plekken: kaart → tandwiel → "App-versie", bovenaan de kaarteditor, optiesdialoog. De integratie controleert de GitHub-releases bij het starten en elke 12 uur; een nieuwere versie is oranje gemarkeerd. Is GitHub niet bereikbaar, dan werkt alles gewoon door. |

### Services (alleen beheerders)

| Service | Doel |
| --- | --- |
| `fritzbox_anrufe.set_alarm_clock_enabled` | Wekker aan/uit (`index`, `enabled`) |
| `fritzbox_anrufe.set_alarm_clock` | Tijd / weekdagen / naam / status instellen (experimenteel) |
| `fritzbox_anrufe.set_deflection_enabled` | Doorschakelregel aan/uit (`deflection_id`, `enabled`) |
| `fritzbox_anrufe.check_for_update` | GitHub-versiecontrole direct uitvoeren |

Bij meerdere FRITZ!Boxen geef je ook `entry_id` mee.

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

## Bekende beperkingen

- Nummers, wekker, doorschakeling, statistiek en updatecontrole zijn **niet op echte hardware getest**.
- Wektijd/weekdagen worden via de webinterface van de box geschreven (ongedocumenteerde formuliervelden); terugleezen voorkomt stille mislukkingen.
- Doorschakelregels kunnen niet worden aangemaakt en hun doel kan niet worden gewijzigd.
- Interne nummers van analoge/DECT-telefoons kunnen ontbreken, afhankelijk van FRITZ!OS.
- De statistiek telt alleen berichten van het antwoordapparaat.
- Oudere kaartteksten (gesprekslijst, antwoordapparaat, telefoonapparaten) zijn nog alleen Duits; de nieuwe teksten zijn vertaald.

## Probleemoplossing

- Kaart niet bijgewerkt: browser geforceerd verversen (Ctrl+F5), service worker / companion-appcache wissen.
- Zet debug-logging aan voor `custom_components.fritzbox_anrufe` en kijk in *Instellingen → Systeem → Logboeken*.
- Meldingen: https://github.com/Meine-smarte-Welt/fritzbox_anrufe/issues

## Bestandsintegriteit

Elk `.py`-, `.js`- en `.yaml`-bestand begint met een SHA256-commentaar over de inhoud vanaf regel 2 (`tail -n +2 bestand | sha256sum`). JSON-bestanden staan hier (`sha256sum bestand`):

| Bestand | SHA256 (versie 1.6.0) |
| --- | --- |
| `__init__.py` | `208eb4a9910087daf8a2dc7001bc38ce84a76d83d12ef5a7713c117cb6e0c8b2` |
| `alarm.py` | `83388a40874baafbe11646aabcbc2916eb6f539a6e34b38c347f649bb2cda01a` |
| `base.py` | `8b263a8dd288006c4461a00b5d120548f1b1f7add1e3b7c9faa5f9fc1cd45986` |
| `call_log.py` | `06375eae8516c56b35582eb2b12f7ae09910fc908458d7a90912a45edc19c9d5` |
| `call_stats.py` | `1f22199430beba85d4856f64da1c092ebe3b27b800d1b5bc47e9d0ac6a41476b` |
| `config_flow.py` | `05f952f04180995f565d3efd765ee2781948e11b725bc620427d319b820879d4` |
| `const.py` | `cef8a0326ca6dcf343b8ec1eabc020dc8317e716f2acbeed76c70c805b557cbb` |
| `deflection.py` | `3949dfa6993bc5a6d43c17c635784b19c96d5414c70e44088813be37e5d55e98` |
| `http.py` | `4d98f8fb1236eb7960d0d3470f0eef1a0e3a45e48e713fe121faa1481a6b70df` |
| `sensor.py` | `77de2f6e7e1a085ae3ef12232faefefbfae8e8ab9c14ff13e03ae491d42f11d2` |
| `settings_data.py` | `28bd262ad9c688caec2d99866c36e0b4cd49bc3d0b7fd54571f3eabd317387a8` |
| `spam.py` | `026ae8bc8890be324f074d17f5fce1269d87edbb420566bdfc1aae18cf3eea11` |
| `switch.py` | `7cdbb0e5d3c5d1c8fa3cc5cad1cba6fa1f666b6c7eb1e034fbed40861b0e73c2` |
| `tam.py` | `b569e1109b1dbc84a552dd36835fb912aa3ae5b47a29a516c523783e799e09c6` |
| `telephony.py` | `8c1faec0cb58d198a68d133689b564516ca95680b71869af927d4730ee92762a` |
| `update_check.py` | `119559a29413fd478bb94053336f6e90e150a3c2737d2966371b7800e4e508c6` |
| `voicemail.py` | `564dc067bc31355e96e5521884969f228cf27bba73cae7bfb1b6d8ac9633a7f0` |
| `services.yaml` | `2f3c794bf601f4e765950e72a1f261c8819c7384187280a4b04c57706026c941` |
| `www/fritzbox-anrufe-card.js` | `0f09b0cefd3c83f0bbe38cdf09aefb687d56b21ba1e942c29260a1bf415b2861` |
| `manifest.json` | `b3f4ed0a2a922bdcc2c67699116f1261aba317d463b0011fe9d1f902005223a3` |
| `strings.json` | `2aaa2e8a4a8f6c71f438bfef33fa1b93252cf4bf7b692f72a274c1a8f112d407` |
| `translations/de.json` | `4bd7cf62ba3a6216754fb28e5653440970ced12cf1e169f0c5962091fb763b64` |
| `translations/en.json` | `2aaa2e8a4a8f6c71f438bfef33fa1b93252cf4bf7b692f72a274c1a8f112d407` |
| `translations/nl.json` | `c4c1a621e53677648e1c433300b1784db8e286a1a5a939ed95acf186f845b426` |
| `icons.json` | `8b2283029eee6310b46153248f2261bbf5cf1f42a84f56e2da8544fbc743515d` |
