"""Heart Rate Variability calculations (mean PPI, mean HR, RMSSD, SDNN)."""

import math
import config


class HRVAnalyzer:
    """Stateless HRV computation helper.

    Call compute() with a list of PPI values to obtain a results dictionary.
    """

    _MIN_COUNT = config.MIN_PPI_COUNT

    def compute(self, ppi_list_ms: list) -> dict | None:
        """Compute HRV metrics from a sequence of PPI values.

        Args:
            ppi_list_ms: Peak-to-peak intervals in milliseconds, in recording order.

        Returns:
            Dict with keys ``mean_ppi``, ``mean_hr``, ``rmssd``, ``sdnn`` (all
            floats rounded to one decimal place), or None if the list is too short.
        """
        if len(ppi_list_ms) < self._MIN_COUNT:
            return None

        mean_ppi = self._mean(ppi_list_ms)
        mean_hr  = self._mean_hr(mean_ppi)
        rmssd    = self._rmssd(ppi_list_ms)
        sdnn     = self._sdnn(ppi_list_ms, mean_ppi)

        return {
            "mean_ppi": round(mean_ppi, 1),
            "mean_hr":  round(mean_hr,  1),
            "rmssd":    round(rmssd,    1),
            "sdnn":     round(sdnn,     1),
        }

    def _mean(self, values: list) -> float:
        """Return the arithmetic mean of a non-empty list."""
        return sum(values) / len(values)

    def _mean_hr(self, mean_ppi_ms: float) -> float:
        """Convert mean PPI (ms) to mean heart rate (BPM)."""
        return 60_000.0 / mean_ppi_ms

    def _rmssd(self, ppi_list_ms: list) -> float:
        """Root mean square of successive differences: sqrt(mean((PPI[i+1]-PPI[i])^2))."""
        successive_sq = [
            (ppi_list_ms[i + 1] - ppi_list_ms[i]) ** 2
            for i in range(len(ppi_list_ms) - 1)
        ]
        return math.sqrt(self._mean(successive_sq))

    def _sdnn(self, ppi_list_ms: list, mean_ppi: float) -> float:
        """Standard deviation of all PPI intervals: sqrt(mean((PPI[i]-mean_PPI)^2))."""
        variance = self._mean([(p - mean_ppi) ** 2 for p in ppi_list_ms])
        return math.sqrt(variance)
