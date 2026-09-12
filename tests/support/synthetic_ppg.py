"""Deterministic PPG-like waveform generator shared by the performance and
acceptance test suites.
"""

import math


def ppg_sample(t_seconds: float, bpm: float = 70.0, baseline: int = 32768, amplitude: int = 8000) -> int:
    """One ADC-range sample of a cubed sine wave at `bpm`.

    The cube gives a sharper systolic peak than a plain sine. Keep
    `amplitude` above config.SIGNAL_MIN_RANGE so beat detection engages.
    """
    freq_hz = bpm / 60.0
    wave = math.sin(2 * math.pi * freq_hz * t_seconds)
    return int(baseline + amplitude * wave**3)


def ppg_window(sample_rate_hz: int, seconds: float, bpm: float = 70.0, baseline: int = 32768, amplitude: int = 8000) -> list:
    """A full list of samples for `seconds` at `sample_rate_hz`."""
    n = int(sample_rate_hz * seconds)
    return [
        ppg_sample(i / sample_rate_hz, bpm=bpm, baseline=baseline, amplitude=amplitude)
        for i in range(n)
    ]
