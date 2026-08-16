# Kimai Homeoffice for Home Assistant

Inoffizielle Home-Assistant-Custom-Integration zur Zeiterfassung in Kimai. Sie verbindet Home Assistant mit einer Kimai-Instanz und stellt Arbeitszeiten, Status, Ziele sowie Schaltflächen zum Ein- und Ausstempeln bereit.

Dieses Projekt ist nicht mit Kimai verbunden und wird von Kimai weder unterstützt noch gesponsert.

## Features

- Einrichtung vollständig über die Home-Assistant-Oberfläche
- Auswahl von Kimai-Projekt und -Aktivität
- Kommen, Gehen und Umschalten direkt aus Home Assistant
- Arbeitszeiten für heute, Woche, Monat und den aktiven Arbeitsblock
- Konfigurierbare Tages- und Wochenziele mit Saldo und Restzeit
- Optionale Zeitrundung für die Anzeige in Home Assistant
- Automatischer Start, Offline-Stopp und täglicher Sicherheits-Stopp
- Optionale Benachrichtigung nach erfolgreichem Ausstempeln
- Entity- und MQTT-/Zigbee2MQTT-Button-Unterstützung
- Aktualisierung über den vorhandenen Coordinator ungefähr alle 60 Sekunden

## Installation über HACS

1. HACS öffnen.
2. Über das Drei-Punkte-Menü **Benutzerdefinierte Repositories** öffnen.
3. `https://github.com/xxschottexx/ha-kimai-homeoffice` als Repository hinzufügen.
4. Als Kategorie **Integration** auswählen.
5. **Kimai Homeoffice** herunterladen.
6. Home Assistant neu starten.

Alternativ kann `custom_components/kimai_homeoffice` manuell nach `/config/custom_components/kimai_homeoffice` kopiert werden. Nach einem Update muss Home Assistant neu gestartet werden.

## Kimai vorbereiten

Du benötigst die erreichbare URL deiner Kimai-Instanz, beispielsweise `https://kimai.example.com` oder im lokalen Netz `http://192.168.x.x`, einen gültigen API-Token sowie ein sichtbares Projekt und eine sichtbare Aktivität. Der Kimai-Benutzer muss Zeiteinträge lesen, starten und stoppen dürfen.

## Integration einrichten

1. In Home Assistant **Einstellungen → Geräte & Dienste** öffnen.
2. **Integration hinzufügen** wählen und nach **Kimai Homeoffice** suchen.
3. Kimai-URL und API-Token eingeben.
4. Projekt und Aktivität auswählen.

## Optionen konfigurieren

Unter **Einstellungen → Geräte & Dienste → Kimai Homeoffice → Konfigurieren** stehen automatischer Start, Startzeitfenster, Offline- und Sicherheits-Stopp, Benachrichtigungen, Button-Steuerung, Tages- und Wochenziele sowie Zeitrundung zur Verfügung. Optionsänderungen werden durch einen Reload übernommen; ein vollständiger Neustart ist normalerweise nicht erforderlich.

## Automatischer Start

Aktiviere **Automatischer Start** und wähle einen Sensor oder Binary Sensor für den Arbeitsrechner. Wechselt dieser innerhalb des Startzeitfensters auf `on`, startet eine Kimai-Erfassung, sofern noch keine aktiv ist. Mit **Offline-Stopp** kann sie nach einer konfigurierbaren Wartezeit beendet werden.

## Sicherheits-Stopp

Der Sicherheits-Stopp beendet eine noch aktive Erfassung täglich zur eingestellten Uhrzeit und schützt vor versehentlich weiterlaufenden Einträgen.

## Benachrichtigung

Nach erfolgreichem Ausstempeln kann ein Notify-Dienst aufgerufen werden. Richtig ist beispielsweise `notify.mobile_app_your_phone`; falsch ist `notify_service.notify.mobile_app_your_phone`.

## MQTT-/Zigbee2MQTT-Button

Für eine JSON-Payload wie `{"action":"on"}`:

- **Button-Steuerung aktivieren:** Ein
- **Auslöser-Typ:** `mqtt`
- **Button-MQTT-Topic:** `zigbee2mqtt/YOUR_BUTTON_NAME`
- **Button-MQTT-JSON-Key:** `action`
- **Gültige Tastendrücke:** `on`

Für ein eigenes `/action`-Topic:

- **Button-MQTT-Topic:** `zigbee2mqtt/YOUR_BUTTON_NAME/action`
- **Button-MQTT-JSON-Key:** leer lassen
- **Gültige Tastendrücke:** `on`

Alternativ zeigt [examples/mqtt_button_zigbee2mqtt.yaml](examples/mqtt_button_zigbee2mqtt.yaml) die Steuerung über eine Home-Assistant-Automation.

## Tagesziel und Wochenziel

Beide Ziele lassen sich getrennt in Stunden und Minuten konfigurieren. Die Integration berechnet daraus Tages-Saldo, Restzeit, voraussichtliche Zielzeit und Wochen-Saldo. Bei einem Tagesziel von `07:00` ergibt `06:30` beispielsweise `-00:30` Saldo und `00:30` Restzeit.

## Zeitrundung

Aktiviere **Zeitrundung**, wähle beispielsweise `5` Minuten und eine Rundungsart:

- **Aufrunden:** zum nächsten Schritt
- **Abrunden:** zum vorherigen Schritt
- **Nächster Wert:** mathematisch zum nächsten Schritt

Bei Aufrundung auf fünf Minuten gilt: `07:21` → `07:25`, `07:23` → `07:25` und `07:25` → `07:25`.

Die Rundung verändert keine Kimai-Einträge. Sie betrifft nur Anzeige und Berechnung in Home Assistant. Laufzeit sowie Tages- und Wochenziel bleiben ungerundet.

## Sensoren

Typische Entity-IDs sind:

- `binary_sensor.kimai_homeoffice_eingestempelt`
- `sensor.kimai_homeoffice_heute`
- `sensor.kimai_homeoffice_woche`
- `sensor.kimai_homeoffice_monat`
- `sensor.kimai_homeoffice_laufzeit`
- `sensor.kimai_homeoffice_tagesziel`
- `sensor.kimai_homeoffice_saldo_heute`
- `sensor.kimai_homeoffice_restzeit_heute`
- `sensor.kimai_homeoffice_ziel_erreicht_um`
- `sensor.kimai_homeoffice_wochenziel`
- `sensor.kimai_homeoffice_saldo_woche`
- `sensor.kimai_homeoffice_aktive_id`
- `sensor.kimai_homeoffice_beginn`
- `button.kimai_homeoffice_kommen`
- `button.kimai_homeoffice_gehen`
- `button.kimai_homeoffice_toggle`

Home Assistant kann Entity-IDs automatisch anpassen. Suche unter **Entwicklerwerkzeuge → Zustände** nach `kimai_homeoffice` und passe Beispiele bei Bedarf an.

## Dashboard-Beispiele

- [Einfaches Dashboard](examples/dashboard_basic.yaml)
- [Dashboard mit Tages- und Wochenzielen](examples/dashboard_with_goals.yaml)

Öffne den Raw-Konfigurationseditor eines Dashboards und übernimm die gewünschten Ansichten oder Karten. Prüfe zuvor alle Entity-IDs.

## AWTRIX-Beispiel

[examples/awtrix_homeoffice.yaml](examples/awtrix_homeoffice.yaml) enthält eine direkt kopierbare Automation. Sie aktualisiert eine AWTRIX-Custom-App jede Minute und leert sie nach dem Ausstempeln. MQTT muss eingerichtet sein; passe das Topic an deine AWTRIX-Konfiguration an.

## Troubleshooting

### Button reagiert nicht

- Button-Steuerung und Auslöser-Typ prüfen.
- MQTT-Topic, JSON-Key und gültige Tastendrücke prüfen.
- Zigbee2MQTT-Logs kontrollieren.
- Integration nach Optionsänderungen neu laden oder Home Assistant neu starten, falls nötig.

### Entity nicht gefunden

- Unter **Entwicklerwerkzeuge → Zustände** nach `kimai_homeoffice` suchen.
- Home Assistant kann IDs ändern oder nummerierte Suffixe ergänzen.

### Notify funktioniert nicht

- Richtig: `notify.mobile_app_your_phone`
- Falsch: `notify_service.notify.mobile_app_your_phone`

### Werte aktualisieren sich nicht

- Der Coordinator aktualisiert ungefähr alle 60 Sekunden.
- Nach einem Update Home Assistant neu starten.
- Home-Assistant-Protokolle auf Kimai-Verbindungsfehler prüfen.

### Rundung stimmt nicht

- Aktivierung, Minutenintervall und Rundungsart prüfen.
- Kimai- und Home-Assistant-Rundung sind getrennte Einstellungen.

## Services

- `kimai_homeoffice.start`
- `kimai_homeoffice.stop`
- `kimai_homeoffice.toggle`
- `kimai_homeoffice.refresh`

## Lizenz

MIT License. Kimai ist eine Marke des jeweiligen Rechteinhabers.
