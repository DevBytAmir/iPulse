"""Performance benchmarks for the PC-testable signal-processing hot path.

Run with: pytest tests/test_performance_benchmark.py -v

Benchmarks two pure-logic paths against time budgets derived from this
project's own constants:

1. HeartRateSensor per-sample processing (envelope tracking + beat
   detection): config.SAMPLE_RATE_HZ = 250, so a new sample arrives every
   1000/250 = 4.0 ms; per-sample processing must stay under that.
2. HRVAnalyzer.compute(): runs once per tick() inside main.py's loop
   (`while True: self._menu.tick(); utime.sleep_ms(4)`), so a single call
   must also fit inside that 4 ms cadence.

Hardware stubbing and the synthetic PPG waveform are shared with the Robot
Framework suite in tests/robot/ via tests/support/.
"""

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support.hardware_stubs import (  # noqa: E402
    ensure_import_paths,
    install_fake_clock,
    install_hardware_stubs,
)
from support.synthetic_ppg import ppg_window  # noqa: E402


@pytest.fixture
def heart_rate_sensor():
    ensure_import_paths()
    install_hardware_stubs()
    clock_ms = install_fake_clock()

    import config
    from heart_rate_sensor import HeartRateSensor

    sensor = HeartRateSensor()
    return sensor, config, clock_ms


def test_beat_detection_hot_path_benchmark(benchmark, heart_rate_sensor):
    sensor, config, clock_ms = heart_rate_sensor
    samples = ppg_window(config.SAMPLE_RATE_HZ, config.HRV_COLLECTION_DURATION_S, bpm=70.0)
    sample_period_ms = 1000.0 / config.SAMPLE_RATE_HZ

    def setup():
        clock_ms[0] = 0.0
        sensor._sig_max = 32768
        sensor._sig_min = 32768
        sensor._above_threshold = False
        sensor._last_beat_ms = 0
        sensor._intervals_ms = []

    def process_window():
        for sample in samples:
            clock_ms[0] += sample_period_ms
            sensor._update_envelope(sample)
            sensor._update_waveform(sample)
            sensor._detect_beat(sample)

    # iterations=1: each round is exactly one full window, so the mean
    # divides cleanly by len(samples) below.
    benchmark.pedantic(process_window, setup=setup, rounds=50, warmup_rounds=5, iterations=1)

    # Sanity check that beat detection actually engaged, not a no-op.
    ppi_list = sensor.get_ppi_list()
    expected_beats = config.HRV_COLLECTION_DURATION_S * 70.0 / 60.0
    assert expected_beats * 0.5 <= len(ppi_list) <= expected_beats * 1.2, (
        f"synthetic signal produced {len(ppi_list)} beats, expected roughly "
        f"{expected_beats:.0f}"
    )

    per_call_seconds = benchmark.stats.stats.mean
    per_sample_ms = (per_call_seconds / len(samples)) * 1000
    benchmark.extra_info["per_sample_us"] = round(per_sample_ms * 1000, 3)
    benchmark.extra_info["sample_budget_us"] = round(sample_period_ms * 1000, 3)
    benchmark.extra_info["headroom_x"] = round(sample_period_ms / per_sample_ms, 1)

    assert per_sample_ms < sample_period_ms, (
        f"per-sample processing ({per_sample_ms:.4f} ms) exceeds the "
        f"{sample_period_ms:.1f} ms budget derived from "
        f"config.SAMPLE_RATE_HZ={config.SAMPLE_RATE_HZ}"
    )


def test_hrv_metrics_benchmark(benchmark):
    ensure_import_paths()
    import config
    from hrv_analysis import HRVAnalyzer

    max_ppi_count = int(config.MAX_BPM / 60.0 * config.HRV_COLLECTION_DURATION_S)

    rng = random.Random(42)
    mean_ppi_ms = 60_000.0 / 85.0
    ppi_list = [round(rng.gauss(mean_ppi_ms, 40.0)) for _ in range(max_ppi_count)]

    analyzer = HRVAnalyzer()

    def compute():
        return analyzer.compute(ppi_list)

    benchmark.pedantic(compute, rounds=50, warmup_rounds=5, iterations=1)

    result = analyzer.compute(ppi_list)
    assert result is not None
    assert set(result.keys()) == {"mean_ppi", "mean_hr", "rmssd", "sdnn"}

    main_loop_budget_ms = 4.0
    per_call_ms = benchmark.stats.stats.mean * 1000
    benchmark.extra_info["per_call_us"] = round(per_call_ms * 1000, 3)
    benchmark.extra_info["budget_us"] = round(main_loop_budget_ms * 1000, 3)
    benchmark.extra_info["headroom_x"] = round(main_loop_budget_ms / per_call_ms, 1)

    assert per_call_ms < main_loop_budget_ms, (
        f"compute() over {max_ppi_count} PPI values ({per_call_ms:.4f} ms) "
        f"exceeds the {main_loop_budget_ms:.1f} ms main-loop tick budget "
        f"(main.py: utime.sleep_ms(4))"
    )
