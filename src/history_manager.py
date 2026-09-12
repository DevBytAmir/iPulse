"""Persistent HRV measurement history stored as a JSON array on flash."""

import json
import utime
import config


class HistoryManager:
    """Manages reading and writing HRV measurement records to a local JSON file.

    Records are kept in newest-first order so index 0 is always the most
    recent measurement.
    """

    def __init__(self) -> None:
        self._entries: list = []
        self._load()

    def save_entry(self, hrv_data: dict, patient_name: str | None = None) -> None:
        """Prepend a new HRV result to the history and persist to disk.

        Args:
            hrv_data: Must contain at least ``mean_ppi``, ``mean_hr``, ``rmssd``,
                ``sdnn``. An NTP timestamp and sequential ID are added automatically.
                Optional keys ``sns`` and ``pns`` are copied when present.
            patient_name: Patient initials to store alongside the record. Omitted
                from the entry when None.
        """
        entry = {
            "id":        len(self._entries) + 1,
            "timestamp": self._formatted_timestamp(),
            "mean_hr":   hrv_data.get("mean_hr",  0),
            "mean_ppi":  hrv_data.get("mean_ppi", 0),
            "rmssd":     hrv_data.get("rmssd",    0),
            "sdnn":      hrv_data.get("sdnn",     0),
        }
        if patient_name is not None:
            entry["name"] = patient_name
        for key in ("sns", "pns"):
            if key in hrv_data:
                entry[key] = hrv_data[key]

        self._entries.insert(0, entry)

        if len(self._entries) > config.MAX_HISTORY_ENTRIES:
            self._entries = self._entries[: config.MAX_HISTORY_ENTRIES]

        self._save()

    def get_entries(self) -> list:
        """Return a copy of all stored entries, newest first."""
        return list(self._entries)

    def get_entry(self, index: int) -> dict | None:
        """Return the entry at *index* (0 = newest), or None if out of range."""
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None

    @property
    def count(self) -> int:
        """Number of stored entries."""
        return len(self._entries)

    def reset(self) -> None:
        """Delete the history file and clear in-memory entries."""
        self._entries = []
        try:
            import os
            os.remove(config.HISTORY_FILE)
        except OSError:
            pass

    def _load(self) -> None:
        """Load entries from the JSON file; silently start fresh on errors."""
        try:
            with open(config.HISTORY_FILE, "r") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    self._entries = data
        except OSError:
            self._entries = []
        except ValueError:
            self._entries = []

    def _save(self) -> None:
        """Persist the current entry list to disk."""
        try:
            with open(config.HISTORY_FILE, "w") as fh:
                json.dump(self._entries, fh)
        except OSError:
            pass

    def _formatted_timestamp(self) -> str:
        """Return the current local time as ``'YYYY-MM-DD HH:MM:SS'``."""
        t = utime.localtime(utime.time() + config.TIMEZONE_OFFSET_H * 3600)
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        )
