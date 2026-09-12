"""iPulse application entry point.

Execution order:
1. Initialise hardware (I2C, OLED).
2. Show the splash screen immediately so the user sees feedback at once.
3. Connect to WiFi and sync NTP during the splash timer.
4. Connect to MQTT and register device.
5. Hand control to the MenuController main loop.

If WiFi or MQTT are unavailable the device continues in offline mode:
heart-rate measurement and local HRV analysis still work fully.
"""

import gc
import utime
from machine import I2C, Pin

import config
from lib.ssd1306 import SSD1306_I2C
from display_manager import DisplayManager
from heart_rate_sensor import HeartRateSensor
from hrv_analysis import HRVAnalyzer
from history_manager import HistoryManager
from network_manager import NetworkManager
from kubios_client import KubiosClient
from menu_controller import MenuController


class Application:
    """Top-level application object.

    Owns all hardware and software components and manages the startup
    sequence before entering the main loop.
    """

    def __init__(self) -> None:
        i2c  = I2C(
            config.I2C_BUS,
            sda=Pin(config.I2C_SDA_PIN),
            scl=Pin(config.I2C_SCL_PIN),
            freq=config.DISPLAY_I2C_FREQ,
        )
        oled = SSD1306_I2C(
            config.DISPLAY_WIDTH,
            config.DISPLAY_HEIGHT,
            i2c,
            addr=config.DISPLAY_I2C_ADDR,
        )

        self._display   = DisplayManager(oled)
        self._sensor    = HeartRateSensor()
        self._hrv       = HRVAnalyzer()
        self._history   = HistoryManager()
        self._network   = NetworkManager()
        self._kubios    = KubiosClient(network=self._network)
        self._menu      = MenuController(
            display = self._display,
            sensor  = self._sensor,
            hrv     = self._hrv,
            network = self._network,
            history = self._history,
            kubios  = self._kubios,
        )

    def run(self) -> None:
        """Execute the startup sequence and then run the application loop."""
        self._startup()
        while True:
            self._menu.tick()
            utime.sleep_ms(4)

    def _startup(self) -> None:
        """Run the ordered startup sequence."""
        self._display.show_splash()

        splash_start = utime.ticks_ms()
        self._display.show_wifi_connecting()

        connected = self._network.connect_wifi(
            progress_callback=self._display.show_wifi_connecting
        )
        if connected:
            self._network.sync_ntp()
            self._network.connect_mqtt()
            self._network.db_register_device()

        elapsed   = utime.ticks_diff(utime.ticks_ms(), splash_start)
        remaining = config.SPLASH_DURATION_MS - elapsed
        if remaining > 0:
            utime.sleep_ms(remaining)

        self._display.show_splash()
        utime.sleep_ms(500)

        gc.collect()


app = Application()
app.run()
