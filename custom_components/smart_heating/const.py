DOMAIN = "smart_heating"
CONF_ROOMS = "rooms"
CONF_GAS_ENTITY = "gas_entity"
CONF_OUTDOOR_ENTITY = "outdoor_entity"
CONF_HDD_BASE = "hdd_base"
CONF_BOILER_ENTITY = "boiler_entity"
CONF_PERSONS = "persons"
CONF_ARRIVAL_ENTITIES = "arrival_entities"
CONF_BOILER_LOW = "boiler_low"
CONF_BOILER_HIGH = "boiler_high"
DEFAULT_BOILER_LOW = 15.0
DEFAULT_BOILER_HIGH = 22.0
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

# Manual changes.
CONF_TRV_SETTLE_MINUTES = "trv_settle_minutes"
CONF_BOILER_SETTLE_MINUTES = "boiler_settle_minutes"
CONF_BOILER_MANUAL_HOLD_MINUTES = "boiler_manual_hold_minutes"

# Alert thresholds.
CONF_TRV_OFFLINE_MINUTES = "trv_offline_minutes"
CONF_TARGET_WINDOW_HOURS = "target_window_hours"
CONF_OUTAGE_FAILURES = "outage_after_failures"
CONF_SENSOR_STALE_HOURS = "sensor_stale_hours"
CONF_BATTERY_LOW_PERCENT = "battery_low_percent"

# Presence: heading home detected from the GPS position of tracked people.
CONF_AUTO_ARRIVAL = "auto_arrival"
DEFAULT_AUTO_ARRIVAL = True

# Vacation from a calendar: events whose title or description has one of the keywords.
CONF_VACATION_CALENDAR = "vacation_calendar"
CONF_VACATION_KEYWORDS = "vacation_keywords"
DEFAULT_VACATION_KEYWORDS = "vacation, holiday, vakantie"

# TRVs on Zigbee2MQTT without an external-temperature number entity get it over MQTT.
CONF_Z2M_BASE_TOPIC = "z2m_base_topic"
