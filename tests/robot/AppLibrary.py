"""Robot Framework keyword library driving iPulse's state machine end to
end without real hardware.

Fakes MenuController's five collaborators: sensor (real HeartRateSensor,
hardware stubbed), display (recording spy), network (always offline),
history (real HistoryManager on a temp file), kubios (unused, bare
stand-in). System-level acceptance layer, not hardware-in-the-loop.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from support.hardware_stubs import (  # noqa: E402
    ensure_import_paths,
    install_fake_clock,
    install_hardware_stubs,
)
from support.synthetic_ppg import ppg_sample  # noqa: E402

ensure_import_paths()
install_hardware_stubs()
_CLOCK_MS = install_fake_clock()

import config  # noqa: E402
from heart_rate_sensor import HeartRateSensor  # noqa: E402
from history_manager import HistoryManager  # noqa: E402
from hrv_analysis import HRVAnalyzer  # noqa: E402
from menu_controller import MenuController  # noqa: E402
from profile_manager import ProfileManager  # noqa: E402


class _SpyDisplay:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def _record(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return _record


class _FakeNetwork:
    is_mqtt_connected = False

    def __init__(self):
        self.calls = []

    def publish_hr(self, *args, **kwargs):
        self.calls.append(("publish_hr", args, kwargs))

    def publish_hrv(self, *args, **kwargs):
        self.calls.append(("publish_hrv", args, kwargs))

    def db_add_record(self, *args, **kwargs):
        self.calls.append(("db_add_record", args, kwargs))


class AppLibrary:
    """Robot Framework keywords for driving the iPulse state machine."""

    ROBOT_LIBRARY_SCOPE = "TEST"

    def __init__(self):
        self.display = None
        self.network = None
        self.sensor = None
        self.menu = None

    def start_application(self, name="AB", age=30, gender="male"):
        """Build a fresh app with a pre-seeded profile (returning-user boot)."""
        _CLOCK_MS[0] = 0.0

        tmp_dir = tempfile.mkdtemp(prefix="ipulse_robot_")
        config.PROFILE_FILE = os.path.join(tmp_dir, "profile.json")
        config.HISTORY_FILE = os.path.join(tmp_dir, "history.json")

        ProfileManager().save(name, int(age), gender)

        self.display = _SpyDisplay()
        self.network = _FakeNetwork()
        self.sensor = HeartRateSensor()

        self.menu = MenuController(
            display=self.display,
            sensor=self.sensor,
            hrv=HRVAnalyzer(),
            network=self.network,
            history=HistoryManager(),
            kubios=None,
        )

        self.advance_clock_ms(config.SPLASH_DURATION_MS + 10)
        self.tick()

    def tick(self):
        self.menu.tick()

    def advance_clock_ms(self, ms):
        _CLOCK_MS[0] += float(ms)

    def press_up(self):
        self.advance_clock_ms(config.DEBOUNCE_MS + 10)
        self.menu._buttons._isr_up(None)

    def press_down(self):
        self.advance_clock_ms(config.DEBOUNCE_MS + 10)
        self.menu._buttons._isr_down(None)

    def press_select(self):
        self.advance_clock_ms(config.DEBOUNCE_MS + 10)
        self.menu._buttons._isr_select(None)

    def simulate_ppg_seconds(self, seconds, bpm=70.0):
        """Feed `seconds` of synthetic PPG samples through the sensor, ticking
        once per sample to match the app's 4 ms sampling and tick cadence.
        """
        sample_period_ms = 1000.0 / config.SAMPLE_RATE_HZ
        n = int(config.SAMPLE_RATE_HZ * float(seconds))
        for _ in range(n):
            _CLOCK_MS[0] += sample_period_ms
            sample = ppg_sample(_CLOCK_MS[0] / 1000.0, bpm=float(bpm))
            self.sensor._update_envelope(sample)
            self.sensor._update_waveform(sample)
            self.sensor._detect_beat(sample)
            self.menu.tick()

    def run_hrv_collection(self, bpm=70.0):
        """Simulate a full collection window plus the extra tick that
        actually processes HRV_SENDING once collection ends.
        """
        self.simulate_ppg_seconds(config.HRV_COLLECTION_DURATION_S, bpm=bpm)
        self.tick()

    def current_state(self):
        return self.menu._state

    def state_should_be(self, expected):
        actual = self.current_state()
        assert actual == expected, f"expected state {expected!r}, got {actual!r}"

    def current_bpm(self):
        return self.sensor.current_bpm

    def displayed_screens(self):
        return [call[0] for call in self.display.calls]

    def last_displayed_screen(self):
        return self.display.calls[-1][0] if self.display.calls else None

    def network_calls(self):
        return [call[0] for call in self.network.calls]
