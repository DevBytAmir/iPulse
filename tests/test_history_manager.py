"""Pytest tests for HistoryManager. Run with: pytest tests/test_history_manager.py"""
import os
import sys
import tempfile
import types

import pytest

sys.path.insert(0, "src")

HISTORY_FILE = os.path.join(tempfile.gettempdir(), "ipulse_test_history.json")

SAMPLE  = {"mean_hr": 72.0, "mean_ppi": 833.0, "rmssd": 45.0, "sdnn": 52.0}
SAMPLE2 = {"mean_hr": 65.0, "mean_ppi": 923.0, "rmssd": 60.0, "sdnn": 70.0}


def _remove_history_file():
    try:
        os.remove(HISTORY_FILE)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def stub_environment(monkeypatch):
    fake_config = types.ModuleType("config")
    fake_config.HISTORY_FILE        = HISTORY_FILE
    fake_config.MAX_HISTORY_ENTRIES = 5
    fake_config.TIMEZONE_OFFSET_H   = 3
    monkeypatch.setitem(sys.modules, "config", fake_config)

    fake_utime = types.ModuleType("utime")
    fake_utime.time      = lambda: 0
    fake_utime.localtime = lambda t=None: (2026, 4, 22, 10, 30, 0, 0, 0)
    monkeypatch.setitem(sys.modules, "utime", fake_utime)


@pytest.fixture(autouse=True)
def clean_history_file(stub_environment):
    _remove_history_file()
    yield
    _remove_history_file()


@pytest.fixture
def history_manager_class():
    from history_manager import HistoryManager

    return HistoryManager


@pytest.fixture
def h(history_manager_class):
    return history_manager_class()


def test_empty_history_no_file(h):
    assert h.count == 0,          "count must be 0 when no file exists"
    assert h.get_entries() == [], "get_entries() must return [] when empty"
    assert h.get_entry(0) is None, "get_entry(0) must be None when empty"


def test_save_entry_and_get_entries_basic_round_trip(h):
    h.save_entry(SAMPLE)
    assert h.count == 1

    entries = h.get_entries()
    assert len(entries) == 1
    e = entries[0]
    assert e["mean_hr"]  == 72.0,  f"mean_hr:  {e['mean_hr']}"
    assert e["mean_ppi"] == 833.0, f"mean_ppi: {e['mean_ppi']}"
    assert e["rmssd"]    == 45.0,  f"rmssd:    {e['rmssd']}"
    assert e["sdnn"]     == 52.0,  f"sdnn:     {e['sdnn']}"


def test_timestamp_format_matches_expected_pattern(h):
    h.save_entry(SAMPLE)
    e = h.get_entries()[0]
    assert e["timestamp"] == "2026-04-22 10:30:00", f"timestamp: {e['timestamp']}"


def test_sequential_id_assigned_at_save_time(h):
    h.save_entry(SAMPLE)
    e = h.get_entries()[0]
    assert e["id"] == 1, f"first entry id must be 1, got {e['id']}"


def test_newest_first_ordering_two_entries(h):
    h.save_entry(SAMPLE)
    h.save_entry(SAMPLE2)
    assert h.count == 2
    entries = h.get_entries()
    assert entries[0]["mean_hr"] == 65.0, "index 0 must be the newest entry"
    assert entries[1]["mean_hr"] == 72.0, "index 1 must be the older entry"
    assert entries[0]["id"] == 2
    assert entries[1]["id"] == 1


def test_get_entry_valid_and_out_of_range_indices(h):
    h.save_entry(SAMPLE)
    h.save_entry(SAMPLE2)
    assert h.get_entry(0)["mean_hr"] == 65.0
    assert h.get_entry(1)["mean_hr"] == 72.0
    assert h.get_entry(2)  is None, "get_entry(2) must be None (only 2 entries)"
    assert h.get_entry(-1) is None, "negative index must return None"
    assert h.get_entry(99) is None, "large index must return None"


def test_optional_sns_pns_fields_copied_when_present(h):
    kubios = {**SAMPLE, "sns": 1.234, "pns": -0.567}
    h.save_entry(kubios)
    e2 = h.get_entry(0)
    assert e2["sns"] == 1.234,  f"sns: {e2.get('sns')}"
    assert e2["pns"] == -0.567, f"pns: {e2.get('pns')}"


def test_sns_pns_absent_when_not_in_input(h):
    h.save_entry(SAMPLE)
    e3 = h.get_entry(0)
    assert "sns" not in e3, "sns must not appear when not in hrv_data"
    assert "pns" not in e3, "pns must not appear when not in hrv_data"


def test_max_history_entries_cap(h):
    """config set to 5 for this test. Save 7 entries; only the 5 newest must survive."""
    for i in range(7):
        h.save_entry({**SAMPLE, "mean_hr": float(i)})

    assert h.count == 5, f"expected 5 entries after cap, got {h.count}"
    entries = h.get_entries()
    assert entries[0]["mean_hr"] == 6.0, f"newest must be 6.0, got {entries[0]['mean_hr']}"
    assert entries[4]["mean_hr"] == 2.0, f"oldest kept must be 2.0, got {entries[4]['mean_hr']}"


def test_persistence_fresh_instance_reloads_from_disk(h, history_manager_class):
    h.save_entry(SAMPLE)
    h.save_entry(SAMPLE2)

    h6 = history_manager_class()
    assert h6.count == 2, f"fresh instance must reload 2 entries, got {h6.count}"
    assert h6.get_entry(0)["mean_hr"] == 65.0, "newest entry must survive reload"
    assert h6.get_entry(1)["mean_hr"] == 72.0, "older entry must survive reload"


def test_reset_clears_memory_and_deletes_file(h):
    h.save_entry(SAMPLE)
    h.reset()
    assert h.count == 0,          "count must be 0 after reset()"
    assert h.get_entries() == [], "get_entries() must return [] after reset()"
    assert not os.path.exists(HISTORY_FILE), "file must be deleted by reset()"


def test_reset_on_fresh_no_file_instance_does_not_crash(h):
    h.reset()
    assert h.count == 0


def test_get_entries_returns_a_copy(h):
    h.save_entry(SAMPLE)
    snapshot = h.get_entries()
    snapshot.clear()
    assert h.count == 1, "mutating get_entries() result must not affect internal state"


def test_corrupt_json_treated_as_empty_history(history_manager_class):
    with open(HISTORY_FILE, "w") as f:
        f.write("not valid json{{{{")
    h9 = history_manager_class()
    assert h9.count == 0, "corrupt JSON must be treated as empty history"


def test_empty_file_treated_as_empty_history(history_manager_class):
    with open(HISTORY_FILE, "w") as f:
        f.write("")
    h10 = history_manager_class()
    assert h10.count == 0, "empty file must be treated as empty history"


def test_non_list_json_object_treated_as_empty_history(history_manager_class):
    with open(HISTORY_FILE, "w") as f:
        f.write('{"mean_hr": 72}')
    h11 = history_manager_class()
    assert h11.count == 0, "non-list JSON must be treated as empty history"


def test_non_list_json_number_treated_as_empty_history(history_manager_class):
    with open(HISTORY_FILE, "w") as f:
        f.write("42")
    h12 = history_manager_class()
    assert h12.count == 0, "numeric JSON must be treated as empty history"


def test_missing_fields_in_hrv_data_default_to_zero(h):
    h.save_entry({})
    e13 = h.get_entry(0)
    assert e13["mean_hr"]  == 0, f"missing mean_hr must default to 0"
    assert e13["mean_ppi"] == 0, f"missing mean_ppi must default to 0"
    assert e13["rmssd"]    == 0, f"missing rmssd must default to 0"
    assert e13["sdnn"]     == 0, f"missing sdnn must default to 0"


def test_count_stays_consistent_after_multiple_save_reset_cycles(h):
    for _ in range(3):
        h.save_entry(SAMPLE)
    assert h.count == 3
    h.reset()
    assert h.count == 0
    h.save_entry(SAMPLE2)
    assert h.count == 1


def test_patient_name_stored_in_entry_when_provided(h):
    h.save_entry(SAMPLE, patient_name="ABC")
    e15 = h.get_entry(0)
    assert e15["name"] == "ABC", f"patient name must be stored, got {e15.get('name')}"

    h.save_entry(SAMPLE2)
    e15b = h.get_entry(0)
    assert "name" not in e15b, "name must be absent when patient_name is None"
