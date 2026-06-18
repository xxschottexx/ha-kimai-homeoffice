# Kimai Homeoffice for Home Assistant

Unofficial Home Assistant custom integration for Kimai-based homeoffice time tracking.

This project is not affiliated with, endorsed by, or sponsored by Kimai.

## Features

- Guided setup through the Home Assistant UI
- Connects to a local Kimai instance via API token
- Select Kimai project and activity during setup
- Start, stop and toggle time tracking from Home Assistant
- Sensors for today, week and month
- Binary sensor for active time tracking status
- Buttons for coming, going, toggle and refresh

## Installation

Copy `custom_components/kimai_homeoffice` to
`/config/custom_components/kimai_homeoffice` and restart Home Assistant.

## HACS

Add this repository as a custom repository in HACS and select type
`Integration`.

## Setup

After installation, add the integration in Home Assistant through
`Settings` > `Devices & services` and enter your Kimai URL and API token.

During setup you can select the Kimai project and activity that should be used
when starting a new time entry from Home Assistant.

## Services

- `kimai_homeoffice.start`
- `kimai_homeoffice.stop`
- `kimai_homeoffice.toggle`
- `kimai_homeoffice.refresh`

## Disclaimer

Kimai is a trademark of its respective owner. This integration only uses the Kimai API and is not an official Kimai project.

## License

MIT License
