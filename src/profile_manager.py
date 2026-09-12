"""Persistent user profile storage for name, age, gender, and patient ID."""

import json
import os
import config


class ProfileManager:
    """Reads and writes the user profile to a JSON file on the Pico W flash.

    A profile is considered complete when ``name`` is non-None. Age, gender,
    and patient_id are optional fields. I/O errors are silenced so a storage
    failure never raises.
    """

    def __init__(self) -> None:
        self._data: dict = self._load_raw()

    def exists(self) -> bool:
        """Returns True when a non-None name has been saved."""
        return self._data.get("name") is not None

    def load(self) -> dict:
        """Returns the stored profile fields.

        Returns:
            A dict with keys ``name`` (str or None), ``age`` (int or None),
            ``gender`` (``"male"``, ``"female"``, or None), and
            ``patient_id`` (int or None).
        """
        return {
            "name":       self._data.get("name"),
            "age":        self._data.get("age"),
            "gender":     self._data.get("gender"),
            "patient_id": self._data.get("patient_id"),
        }

    def save(
        self,
        name: str | None,
        age: int | None,
        gender: str | None,
        patient_id: int | None = None,
    ) -> None:
        """Persists all profile fields to flash.

        Args:
            name: Patient initials (1-PROFILE_NAME_MAX_LEN chars), or None.
            age: Integer in the range 15-99, or None to mark as skipped.
            gender: ``"male"``, ``"female"``, or None to mark as skipped.
            patient_id: Database-assigned patient ID returned after registration,
                or None if registration has not been performed.
        """
        self._data = {
            "name":       name,
            "age":        age,
            "gender":     gender,
            "patient_id": patient_id,
        }
        try:
            with open(config.PROFILE_FILE, "w") as fh:
                json.dump(self._data, fh)
        except OSError:
            pass

    def reset(self) -> None:
        """Deletes the profile file and clears the in-memory state."""
        self._data = {}
        try:
            os.remove(config.PROFILE_FILE)
        except OSError:
            pass

    def _load_raw(self) -> dict:
        try:
            with open(config.PROFILE_FILE, "r") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
        except (OSError, ValueError):
            pass
        return {}
