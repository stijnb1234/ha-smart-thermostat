DOMAIN = "smart_heating"
CONF_ROOMS = "rooms"
CONF_GAS_ENTITY = "gas_entity"
CONF_OUTDOOR_ENTITY = "outdoor_entity"
CONF_HDD_BASE = "hdd_base"
CONF_EASYCONTROL_ENTITY = "easycontrol_entity"
CONF_PERSONS = "persons"
CONF_EASYCONTROL_LOW = "easycontrol_low"
CONF_EASYCONTROL_HIGH = "easycontrol_high"
DEFAULT_EASYCONTROL_LOW = 15.0
DEFAULT_EASYCONTROL_HIGH = 22.0
UPDATE_INTERVAL_SECONDS = 60
DASHBOARD_FILE = "smart_heating_dashboard.yaml"

# Timed requests (minutes).
CONF_BOOST_MINUTES = "boost_minutes"
CONF_MANUAL_OVERRIDE_MINUTES = "manual_override_minutes"
DEFAULT_BOOST_MINUTES = 60
DEFAULT_MANUAL_OVERRIDE_MINUTES = 120

# Bedroom preset: comfort window before bed (HH:MM).
CONF_PRE_BED_START = "pre_bed_start"
CONF_PRE_BED_END = "pre_bed_end"
DEFAULT_PRE_BED_START = "21:30"
DEFAULT_PRE_BED_END = "22:30"

# Boiler call policy.
CONF_DEBOUNCE_MINUTES = "debounce_minutes"
CONF_BACKOFF_BASE_MINUTES = "backoff_base_minutes"
CONF_BACKOFF_MAX_MINUTES = "backoff_max_minutes"
CONF_DEMAND_HYSTERESIS = "demand_hysteresis"

# Alert thresholds.
CONF_TRV_OFFLINE_MINUTES = "trv_offline_minutes"
CONF_TARGET_WINDOW_HOURS = "target_window_hours"
CONF_OUTAGE_FAILURES = "outage_after_failures"
CONF_SENSOR_STALE_HOURS = "sensor_stale_hours"
CONF_BATTERY_LOW_PERCENT = "battery_low_percent"
