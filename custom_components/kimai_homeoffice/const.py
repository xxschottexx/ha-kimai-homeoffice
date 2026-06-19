"""Constants for the Kimai Homeoffice integration."""

from homeassistant.const import Platform

DOMAIN = "kimai_homeoffice"

CONF_BASE_URL = "base_url"
CONF_API_TOKEN = "api_token"
CONF_PROJECT_ID = "project_id"
CONF_ACTIVITY_ID = "activity_id"

CONF_AUTO_START = "auto_start"
CONF_WORKER_SENSOR = "worker_sensor"
CONF_START_AFTER = "start_after"
CONF_START_BEFORE = "start_before"

CONF_OFFLINE_STOP = "offline_stop"
CONF_OFFLINE_MINUTES = "offline_minutes"

CONF_SAFETY_STOP = "safety_stop"
CONF_SAFETY_STOP_TIME = "safety_stop_time"

CONF_NOTIFY = "notify"
CONF_NOTIFY_SERVICE = "notify_service"

CONF_BUTTON_ENABLED = "button_enabled"
CONF_BUTTON_ENTITY = "button_entity"
CONF_BUTTON_VALID_STATES = "button_valid_states"
CONF_BUTTON_COOLDOWN_SECONDS = "button_cooldown_seconds"

CONF_MQTT_BUTTON = "mqtt_button"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_MQTT_PAYLOAD = "mqtt_payload"

DEFAULT_NAME = "Kimai Homeoffice"
DEFAULT_SCAN_INTERVAL = 60

DEFAULT_AUTO_START = False
DEFAULT_OFFLINE_STOP = False
DEFAULT_OFFLINE_MINUTES = 5
DEFAULT_SAFETY_STOP = False
DEFAULT_NOTIFY = False
DEFAULT_START_AFTER = "05:00"
DEFAULT_START_BEFORE = "17:00"
DEFAULT_SAFETY_STOP_TIME = "17:15"
DEFAULT_BUTTON_ENABLED = False
DEFAULT_BUTTON_VALID_STATES = "on,single,press,toggle,button_1_single"
DEFAULT_BUTTON_COOLDOWN_SECONDS = 2

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]
