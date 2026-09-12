"""All constants for iPulse: pins, timing, credentials, and thresholds.

Edit this file before deploying. No other file contains numeric literals.
"""

PPG_ADC_PIN         = 26
BUTTON_UP_PIN       = 7
BUTTON_DOWN_PIN     = 9
BUTTON_SELECT_PIN   = 8
LED_HEARTBEAT_PIN   = 22
I2C_BUS             = 1
I2C_SDA_PIN         = 14
I2C_SCL_PIN         = 15

ROT_A_PIN           = 10
ROT_B_PIN           = 11
ROT_PUSH_PIN        = 12
ROT_DEBOUNCE_MS     = 5

DISPLAY_WIDTH       = 128
DISPLAY_HEIGHT      = 64
DISPLAY_I2C_ADDR    = 0x3C
DISPLAY_I2C_FREQ    = 400_000

SAMPLE_RATE_HZ      = 250
FIFO_CAPACITY       = 500

MIN_BPM                 = 30
MAX_BPM                 = 220
REFRACTORY_PERIOD_MS    = int(60_000 / MAX_BPM)
PEAK_THRESHOLD_RATIO    = 0.65
BEAT_AVERAGE_COUNT      = 6
SIGNAL_MIN_RANGE        = 500

PPG_WAVEFORM_COLS       = 100
PPG_WAVEFORM_Y_TOP      = 16
PPG_WAVEFORM_Y_BOTTOM   = 56

HRV_COLLECTION_DURATION_S   = 30
MIN_PPI_COUNT               = 20

HISTORY_FILE            = "hrv_history.json"
MAX_HISTORY_ENTRIES     = 10
PROFILE_FILE            = "profile.json"
PROFILE_NAME_MAX_LEN    = 20

WIFI_SSID               = ""
WIFI_PASSWORD           = r""
WIFI_CONNECT_TIMEOUT_S  = 16

MQTT_BROKER     = ""
MQTT_PORT       = 0000
MQTT_CLIENT_ID  = ""

MQTT_TOPIC_HR   = ""
MQTT_TOPIC_HRV  = ""

MQTT_TOPIC_KUBIOS_REQUEST   = "kubios/request"
MQTT_TOPIC_KUBIOS_RESPONSE  = "kubios/response"
KUBIOS_RESPONSE_TIMEOUT_MS  = 30_000

MQTT_TOPIC_DB_DEVICES_ADD   = "database/devices/add"
MQTT_TOPIC_DB_PATIENTS_ADD  = "database/patients/add"
MQTT_TOPIC_DB_RECORDS_ADD   = "database/records/add"
MQTT_TOPIC_DB_RESPONSE      = "database/response"
DB_RESPONSE_TIMEOUT_MS      = 5_000

DEVICE_NAME     = ""

TIMEZONE_OFFSET_H   = 3

SPLASH_DURATION_MS  = 2500
DEBOUNCE_MS         = 220
BPM_UPDATE_MS       = 1000
SPINNER_STEP_MS     = 200
