# Changelog

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