"""Pytest tests for HRVAnalyzer. Run with: pytest tests/test_hrv_analyzer.py"""
import math
import sys
import types

import pytest

sys.path.insert(0, "src")


@pytest.fixture(autouse=True)
def stub_config(monkeypatch):
    fake_config = types.ModuleType("config")
    fake_config.MIN_PPI_COUNT = 20
    monkeypatch.setitem(sys.modules, "config", fake_config)


@pytest.fixture
def analyzer():
    from hrv_analysis import HRVAnalyzer

    return HRVAnalyzer()


def test_compute_returns_none_below_minimum_count(analyzer):
    assert analyzer.compute([]) is None,          "empty list must return None"
    assert analyzer.compute([1000]) is None,      "single value must return None"
    assert analyzer.compute([1000] * 19) is None, "19 values (< 20) must return None"


def test_compute_returns_result_at_exactly_min_ppi_count(analyzer):
    result = analyzer.compute([1000] * 20)
    assert result is not None, "exactly 20 values must return a result"
    assert set(result.keys()) == {"mean_ppi", "mean_hr", "rmssd", "sdnn"}, \
        f"wrong keys: {result.keys()}"


def test_constant_ppi_list_yields_zero_variability(analyzer):
    """[1000] * 20: mean_ppi=1000, mean_hr=60, rmssd=0 (no successive differences), sdnn=0"""
    r = analyzer.compute([1000] * 20)
    assert r["mean_ppi"] == 1000.0, f"mean_ppi: {r['mean_ppi']}"
    assert r["mean_hr"]  == 60.0,  f"mean_hr:  {r['mean_hr']}"
    assert r["rmssd"]    == 0.0,   f"rmssd:    {r['rmssd']}"
    assert r["sdnn"]     == 0.0,   f"sdnn:     {r['sdnn']}"


def test_alternating_ppi_list_known_exact_results(analyzer):
    """[900, 1100] * 10, known exact results.

    mean_ppi = 1000, mean_hr = 60
    RMSSD: 19 successive diffs each +/-200 -> sqrt(mean(40000)) = 200.0
    SDNN : 10 values at +/-100 from mean  -> sqrt(10000) = 100.0
    """
    r = analyzer.compute([900, 1100] * 10)
    assert r["mean_ppi"] == 1000.0, f"mean_ppi: {r['mean_ppi']}"
    assert r["mean_hr"]  == 60.0,  f"mean_hr:  {r['mean_hr']}"
    assert r["rmssd"]    == 200.0, f"rmssd:    {r['rmssd']}"
    assert r["sdnn"]     == 100.0, f"sdnn:     {r['sdnn']}"


def test_small_alternating_ppi_list(analyzer):
    """[999, 1001] * 10.

    RMSSD: successive diffs +/-2 -> sqrt(4) = 2.0
    SDNN : deviations +/-1       -> sqrt(1) = 1.0
    """
    r = analyzer.compute([999, 1001] * 10)
    assert r["mean_ppi"] == 1000.0
    assert r["rmssd"]    == 2.0,  f"rmssd: {r['rmssd']}"
    assert r["sdnn"]     == 1.0,  f"sdnn:  {r['sdnn']}"


def test_mean_hr_formula(analyzer):
    """mean_hr formula: HR = 60,000 / mean_ppi"""
    r = analyzer.compute([600] * 20)
    assert r["mean_ppi"] == 600.0
    assert r["mean_hr"]  == 100.0, f"600 ms PPI -> 100 BPM, got {r['mean_hr']}"

    r = analyzer.compute([2000] * 20)
    assert r["mean_ppi"] == 2000.0
    assert r["mean_hr"]  == 30.0,  f"2000 ms PPI -> 30 BPM, got {r['mean_hr']}"

    r = analyzer.compute([750] * 20)
    assert r["mean_ppi"] == 750.0
    assert r["mean_hr"]  == 80.0,  f"750 ms PPI -> 80 BPM, got {r['mean_hr']}"


def test_rounding_to_one_decimal_place(analyzer):
    """[1000]*19 + [1001]: rmssd = sqrt(1/19), sdnn = sqrt(0.0475) -> both round to 0.2"""
    ppi_near_const = [1000] * 19 + [1001]
    r = analyzer.compute(ppi_near_const)
    expected_rmssd = round(math.sqrt(1 / 19), 1)          # ~= 0.2
    expected_sdnn  = round(math.sqrt(0.95 / 20), 1)       # ~= 0.2
    assert r["rmssd"] == expected_rmssd, f"rmssd: {r['rmssd']} != {expected_rmssd}"
    assert r["sdnn"]  == expected_sdnn,  f"sdnn:  {r['sdnn']}  != {expected_sdnn}"

    # Non-trivial mean_hr rounding: 800 ms -> 75.0 BPM
    r = analyzer.compute([800] * 20)
    assert r["mean_hr"] == 75.0, f"800 ms PPI -> 75.0 BPM, got {r['mean_hr']}"


def test_large_dataset_still_works(analyzer):
    """Large dataset: MIN_PPI_COUNT + many extra values must still work."""
    r = analyzer.compute([1000] * 100)
    assert r is not None
    assert r["mean_ppi"] == 1000.0
    assert r["rmssd"]    == 0.0
    assert r["sdnn"]     == 0.0


def test_non_trivial_mean_ppi_mixed_values(analyzer):
    """[800, 1200] * 10 style mix: mean = 1000, but check fractional cases."""
    r = analyzer.compute([900] * 10 + [1000] * 10)
    expected_mean = (900 * 10 + 1000 * 10) / 20   # 950.0
    assert r["mean_ppi"] == 950.0, f"mean_ppi: {r['mean_ppi']}"
    assert r["mean_hr"]  == round(60000 / 950.0, 1), f"mean_hr: {r['mean_hr']}"


def test_all_values_equal_yields_zero_rmssd_and_sdnn(analyzer):
    """All values equal: RMSSD and SDNN must be exactly 0 for any constant."""
    for bpm_ppi in [400, 600, 857, 1000, 1500, 2000]:
        r = analyzer.compute([bpm_ppi] * 20)
        assert r["rmssd"] == 0.0, f"PPI={bpm_ppi}: expected rmssd=0, got {r['rmssd']}"
        assert r["sdnn"]  == 0.0, f"PPI={bpm_ppi}: expected sdnn=0,  got {r['sdnn']}"
