# Changelog

## 0.3.1 - 2026-06-20

### Added
- Added MQTT trigger mode for universal button support
- Added configurable MQTT topic for button presses
- Added optional JSON key extraction for MQTT payloads

### Fixed
- Support Zigbee2MQTT buttons that expose actions only through MQTT payloads
- Allow empty button entity when MQTT trigger mode is used

## 0.3.0 - 2026-06-19

### Added
- Added universal button support
- Added optional entity based button trigger
- Added configurable valid button states
- Added cooldown protection for button presses

### Improved
- Homeoffice can now be started or stopped from Zigbee, MQTT, helper or other Home Assistant entities

## 0.2.1 - 2026-06-18

### Improved
- Improved options flow labels
- Added entity selector for worker sensor
- Improved notify service field
- Improved German and English translations

### Fixed
- Avoid technical option names in the Home Assistant UI

## 0.2.0 - 2026-06-18

### Added
- Options flow for automatic start, offline stop, safety stop and notify service
- Automatic Kimai start when work computer sensor turns on within configured start window
- Automatic Kimai stop after configured offline minutes when the sensor turns off
- Automatic Kimai stop at configured safety stop time
- Notification after stopping using a configured notify service

## 0.1.0 - 2026-06-17

### Added
- Initial Home Assistant custom integration for Kimai Homeoffice
- Guided setup through the Home Assistant UI
- Kimai URL and API token configuration
- Project and activity selection during setup
- Sensors for today, week and month
- Sensor for active Kimai timesheet ID
- Sensor for active begin time
- Binary sensor for active tracking state
- Buttons for coming, going, toggle and refresh
- Services: start, stop, toggle and refresh
