"""Shared MicroPython hardware stubs for PC-side testing.

Fakes `machine` and `lib.piotimer`, the two hardware-only dependencies of
heart_rate_sensor.py and menu_controller.py. lib/fifo.py and lib/led.py
are pure Python and used for real.
"""

import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src"


def ensure_import_paths() -> None:
    for path in (str(REPO_ROOT), str(SRC_DIR)):
        if path not in sys.path:
            sys.path.insert(0, path)


def install_hardware_stubs() -> None:
    machine = types.ModuleType("machine")

    class Pin:
        OUT = 1
        IN = 0
        PULL_UP = 2
        IRQ_FALLING = 1
        IRQ_RISING = 2

        def __init__(self, *args, **kwargs):
            self._value = 1

        def irq(self, *args, **kwargs):
            pass

        def value(self, *args):
            if args:
                self._value = args[0]
            else:
                return self._value

    class ADC:
        def __init__(self, *args, **kwargs):
            pass

        def read_u16(self):
            return 32768

    class PWM:
        def __init__(self, *args, **kwargs):
            self._duty = 0

        def freq(self, *args, **kwargs):
            pass

        def duty_u16(self, *args):
            if args:
                self._duty = args[0]
            else:
                return self._duty

    machine.Pin = Pin
    machine.ADC = ADC
    machine.PWM = PWM
    sys.modules["machine"] = machine

    lib_piotimer = types.ModuleType("lib.piotimer")

    class Piotimer:
        PERIODIC = 1
        ONE_SHOT = 0

        def __init__(self, *args, **kwargs):
            pass

        def deinit(self):
            pass

    lib_piotimer.Piotimer = Piotimer
    sys.modules["lib.piotimer"] = lib_piotimer


def install_fake_clock() -> list:
    """Returns the mutable [ms] container the caller advances over time."""
    clock_ms = [0.0]
    utime = types.ModuleType("utime")
    utime.ticks_ms = lambda: clock_ms[0]
    utime.ticks_diff = lambda a, b: a - b
    utime.time = lambda: 1_800_000_000
    utime.localtime = lambda t=None: (2026, 1, 1, 0, 0, 0, 0, 0)
    utime.sleep_ms = lambda ms: None
    sys.modules["utime"] = utime
    return clock_ms
