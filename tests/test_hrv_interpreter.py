"""Pytest tests for HRVInterpreter. Run with: pytest tests/test_hrv_interpreter.py"""
import sys

sys.path.insert(0, "src")

from hrv_interpreter import HRVInterpreter  # noqa: E402

C = HRVInterpreter.classify


def test_male_15_25_band_boundaries():
    assert C(0,   20, "male") == "Fatigued",  f"rmssd=0   male 15-25: {C(0,20,'male')}"
    assert C(19,  20, "male") == "Fatigued",  f"rmssd=19  male 15-25: {C(19,20,'male')}"
    assert C(20,  20, "male") == "Stressed",  f"rmssd=20  male 15-25: {C(20,20,'male')}"
    assert C(34,  20, "male") == "Stressed",  f"rmssd=34  male 15-25: {C(34,20,'male')}"
    assert C(35,  20, "male") == "Normal",    f"rmssd=35  male 15-25: {C(35,20,'male')}"
    assert C(54,  20, "male") == "Normal",    f"rmssd=54  male 15-25: {C(54,20,'male')}"
    assert C(55,  20, "male") == "Good",      f"rmssd=55  male 15-25: {C(55,20,'male')}"
    assert C(79,  20, "male") == "Good",      f"rmssd=79  male 15-25: {C(79,20,'male')}"
    assert C(80,  20, "male") == "Excellent", f"rmssd=80  male 15-25: {C(80,20,'male')}"
    assert C(200, 20, "male") == "Excellent", f"rmssd=200 male 15-25: {C(200,20,'male')}"


def test_female_15_25_band_boundaries():
    assert C(24,  22, "female") == "Fatigued"
    assert C(25,  22, "female") == "Stressed"
    assert C(39,  22, "female") == "Stressed"
    assert C(40,  22, "female") == "Normal"
    assert C(59,  22, "female") == "Normal"
    assert C(60,  22, "female") == "Good"
    assert C(84,  22, "female") == "Good"
    assert C(85,  22, "female") == "Excellent"


def test_male_26_35_band_boundaries():
    assert C(17,  30, "male") == "Fatigued"
    assert C(18,  30, "male") == "Stressed"
    assert C(29,  30, "male") == "Stressed"
    assert C(30,  30, "male") == "Normal"
    assert C(49,  30, "male") == "Normal"
    assert C(50,  30, "male") == "Good"
    assert C(74,  30, "male") == "Good"
    assert C(75,  30, "male") == "Excellent"


def test_female_26_35_band_boundaries():
    assert C(22,  30, "female") == "Fatigued"
    assert C(23,  30, "female") == "Stressed"
    assert C(34,  30, "female") == "Stressed"
    assert C(35,  30, "female") == "Normal"
    assert C(54,  30, "female") == "Normal"
    assert C(55,  30, "female") == "Good"
    assert C(79,  30, "female") == "Good"
    assert C(80,  30, "female") == "Excellent"


def test_male_36_45_band_boundaries():
    assert C(14,  40, "male") == "Fatigued"
    assert C(15,  40, "male") == "Stressed"
    assert C(24,  40, "male") == "Stressed"
    assert C(25,  40, "male") == "Normal"
    assert C(44,  40, "male") == "Normal"
    assert C(45,  40, "male") == "Good"
    assert C(69,  40, "male") == "Good"
    assert C(70,  40, "male") == "Excellent"


def test_female_36_45_band_boundaries():
    assert C(19,  40, "female") == "Fatigued"
    assert C(20,  40, "female") == "Stressed"
    assert C(29,  40, "female") == "Stressed"
    assert C(30,  40, "female") == "Normal"
    assert C(49,  40, "female") == "Normal"
    assert C(50,  40, "female") == "Good"
    assert C(74,  40, "female") == "Good"
    assert C(75,  40, "female") == "Excellent"


def test_male_46_60_band_boundaries():
    assert C(11,  50, "male") == "Fatigued"
    assert C(12,  50, "male") == "Stressed"
    assert C(19,  50, "male") == "Stressed"
    assert C(20,  50, "male") == "Normal"
    assert C(34,  50, "male") == "Normal"
    assert C(35,  50, "male") == "Good"
    assert C(54,  50, "male") == "Good"
    assert C(55,  50, "male") == "Excellent"


def test_female_46_60_band_boundaries():
    assert C(16,  50, "female") == "Fatigued"
    assert C(17,  50, "female") == "Stressed"
    assert C(24,  50, "female") == "Stressed"
    assert C(25,  50, "female") == "Normal"
    assert C(39,  50, "female") == "Normal"
    assert C(40,  50, "female") == "Good"
    assert C(59,  50, "female") == "Good"
    assert C(60,  50, "female") == "Excellent"


def test_male_61_plus_band_boundaries():
    assert C(9,   65, "male") == "Fatigued"
    assert C(10,  65, "male") == "Stressed"
    assert C(16,  65, "male") == "Stressed"
    assert C(17,  65, "male") == "Normal"
    assert C(29,  65, "male") == "Normal"
    assert C(30,  65, "male") == "Good"
    assert C(44,  65, "male") == "Good"
    assert C(45,  65, "male") == "Excellent"


def test_female_61_plus_band_boundaries():
    assert C(14,  70, "female") == "Fatigued"
    assert C(15,  70, "female") == "Stressed"
    assert C(21,  70, "female") == "Stressed"
    assert C(22,  70, "female") == "Normal"
    assert C(34,  70, "female") == "Normal"
    assert C(35,  70, "female") == "Good"
    assert C(49,  70, "female") == "Good"
    assert C(50,  70, "female") == "Excellent"


def test_none_age_and_gender_uses_fallback_boundaries():
    assert C(14,  None, None) == "Fatigued"
    assert C(15,  None, None) == "Stressed"
    assert C(24,  None, None) == "Stressed"
    assert C(25,  None, None) == "Normal"
    assert C(44,  None, None) == "Normal"
    assert C(45,  None, None) == "Good"
    assert C(69,  None, None) == "Good"
    assert C(70,  None, None) == "Excellent"


def test_partial_profile_uses_fallback():
    assert C(35,  25, None) == "Normal",   "age-only (no gender) must use fallback"
    assert C(35,  None, "male") == "Normal", "gender-only (no age) must use fallback"


def test_out_of_range_age_uses_fallback():
    assert C(25, 14, "male") == "Normal",   f"age=14 should use fallback: {C(25,14,'male')}"
    assert C(25, 100, "male") == "Normal",  f"age=100 should use fallback: {C(25,100,'male')}"


def test_rmssd_zero_is_fatigued_with_and_without_profile():
    assert C(0, 20, "male")   == "Fatigued"
    assert C(0, None, None)   == "Fatigued"


def test_rmssd_very_high_is_excellent_with_and_without_profile():
    assert C(999, 20, "male")   == "Excellent"
    assert C(999, None, None)   == "Excellent"
