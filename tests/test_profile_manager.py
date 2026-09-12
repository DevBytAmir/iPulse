"""Pytest tests for ProfileManager. Run with: pytest tests/test_profile_manager.py"""
import os
import sys
import tempfile
import types

import pytest

sys.path.insert(0, "src")

PROFILE_FILE = os.path.join(tempfile.gettempdir(), "ipulse_test_profile.json")


def _remove_profile_file():
    try:
        os.remove(PROFILE_FILE)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def stub_config(monkeypatch):
    fake_config = types.ModuleType("config")
    fake_config.PROFILE_FILE = PROFILE_FILE
    monkeypatch.setitem(sys.modules, "config", fake_config)


@pytest.fixture(autouse=True)
def clean_profile_file(stub_config):
    _remove_profile_file()
    yield
    _remove_profile_file()


@pytest.fixture
def pm():
    from profile_manager import ProfileManager

    return ProfileManager()


def test_no_file_means_no_profile(pm):
    assert not pm.exists(), "exists() must be False when file is missing"
    p = pm.load()
    assert p["name"] is None
    assert p["age"] is None
    assert p["gender"] is None
    assert p["patient_id"] is None


def test_exists_requires_name(pm):
    pm.save(None, 30, "male")
    assert not pm.exists(), "exists() must be False when name is None"

    pm.save("AB", None, None)
    assert pm.exists(), "exists() must be True when name is set"


def test_full_save_and_load(pm):
    pm.save("ABC", 25, "female", patient_id=7)
    assert pm.exists()
    data = pm.load()
    assert data["name"]       == "ABC",    f"name: {data['name']}"
    assert data["age"]        == 25,       f"age: {data['age']}"
    assert data["gender"]     == "female", f"gender: {data['gender']}"
    assert data["patient_id"] == 7,        f"patient_id: {data['patient_id']}"


def test_patient_id_defaults_to_none(pm):
    pm.save("XY", 40, "male")
    assert pm.load()["patient_id"] is None


def test_skip_age_gender_still_valid_if_name_set(pm):
    pm.save("AB", None, None)
    assert pm.exists()
    assert pm.load()["age"] is None
    assert pm.load()["gender"] is None


def test_boundary_ages(pm):
    pm.save("A", 15, "female")
    assert pm.load()["age"] == 15
    pm.save("A", 99, "male")
    assert pm.load()["age"] == 99


def test_persistence_across_instances(pm):
    from profile_manager import ProfileManager

    pm.save("XY", 32, "female", patient_id=3)
    pm2 = ProfileManager()
    assert pm2.exists()
    data2 = pm2.load()
    assert data2["name"]       == "XY"
    assert data2["age"]        == 32
    assert data2["gender"]     == "female"
    assert data2["patient_id"] == 3


def test_multiple_saves_overwrite(pm):
    pm.save("AB", 20, "male")
    pm.save("CD", 35, "female", patient_id=9)
    data = pm.load()
    assert data["name"]       == "CD"
    assert data["age"]        == 35
    assert data["gender"]     == "female"
    assert data["patient_id"] == 9


def test_reset(pm):
    pm.save("AB", 40, "female")
    pm.reset()
    assert not pm.exists()
    data = pm.load()
    assert data["name"] is None
    assert data["age"] is None
    assert data["gender"] is None


def test_reset_on_missing_file(pm):
    pm.reset()
    assert not pm.exists()


def test_corrupt_json_treated_as_missing_profile(stub_config):
    from profile_manager import ProfileManager

    with open(PROFILE_FILE, "w") as f:
        f.write("not-json{{{")
    pm4 = ProfileManager()
    assert not pm4.exists(), "Corrupt JSON must be treated as missing profile"
    assert pm4.load()["name"] is None


def test_empty_file_treated_as_missing_profile(stub_config):
    from profile_manager import ProfileManager

    with open(PROFILE_FILE, "w") as f:
        f.write("")
    pm5 = ProfileManager()
    assert not pm5.exists(), "Empty file must be treated as missing profile"


def test_non_dict_json_treated_as_missing_profile(stub_config):
    from profile_manager import ProfileManager

    with open(PROFILE_FILE, "w") as f:
        f.write("[1, 2, 3]")
    pm6 = ProfileManager()
    assert not pm6.exists(), "Non-dict JSON must be treated as missing profile"
