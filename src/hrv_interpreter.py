"""RMSSD-based heart state classifier using Nunan et al. (2010) norms."""


class HRVInterpreter:
    """Stateless RMSSD classifier. Call classify() directly, no instance needed."""

    _TABLE = [
        (15, 25, "male",   [20, 35, 55, 80]),
        (15, 25, "female", [25, 40, 60, 85]),
        (26, 35, "male",   [18, 30, 50, 75]),
        (26, 35, "female", [23, 35, 55, 80]),
        (36, 45, "male",   [15, 25, 45, 70]),
        (36, 45, "female", [20, 30, 50, 75]),
        (46, 60, "male",   [12, 20, 35, 55]),
        (46, 60, "female", [17, 25, 40, 60]),
        (61, 99, "male",   [10, 17, 30, 45]),
        (61, 99, "female", [15, 22, 35, 50]),
    ]

    _FALLBACK = [15, 25, 45, 70]

    @staticmethod
    def classify(rmssd: float, age: int | None, gender: str | None) -> str:
        """Return the heart state label for the given RMSSD value.

        Args:
            rmssd: RMSSD in milliseconds.
            age: Patient age, or None to use the population-average fallback.
            gender: ``"male"`` or ``"female"``, or None for the fallback.

        Returns:
            One of ``"Fatigued"``, ``"Stressed"``, ``"Normal"``, ``"Good"``,
            ``"Excellent"``.
        """
        thresholds = HRVInterpreter._FALLBACK

        if age is not None and gender is not None:
            for min_a, max_a, g, t in HRVInterpreter._TABLE:
                if min_a <= age <= max_a and g == gender:
                    thresholds = t
                    break

        t1, t2, t3, t4 = thresholds
        if rmssd < t1:
            return "Fatigued"
        if rmssd < t2:
            return "Stressed"
        if rmssd < t3:
            return "Normal"
        if rmssd < t4:
            return "Good"
        return "Excellent"
