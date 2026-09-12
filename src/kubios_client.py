"""Kubios HRV analysis via a broker-hosted MQTT proxy.

Requests are routed through the proxy: publish PPI data to kubios/request,
receive result from kubios/response (matched by MAC address).
The NetworkManager owns the MQTT connection; this class is a focused interface
that the MenuController can use without knowing the MQTT details.
"""

class KubiosClient:
    """Thin interface over the Kubios MQTT proxy.

    Args:
        network: The application's shared NetworkManager instance.
    """

    def __init__(self, network) -> None:
        self._network = network

    def is_available(self) -> bool:
        """Return True when a Kubios analysis request can be attempted.

        Requires both WiFi and an active MQTT connection.
        """
        return (
            self._network.is_wifi_connected
            and self._network.is_mqtt_connected
        )

    def analyze(self, ppi_list_ms: list, progress_callback=None) -> dict | None:
        """Submit PPI data to the Kubios proxy and return the analysis result.

        Args:
            ppi_list_ms: Peak-to-peak intervals in milliseconds.
            progress_callback: Called every 100 ms while waiting for the proxy
                response so the display can show a live spinner.

        Returns:
            Dict with keys ``mean_hr``, ``mean_ppi``, ``rmssd``, ``sdnn``,
            ``sns``, ``pns``, or None if the request timed out or an error occurred.
        """
        return self._network.kubios_analyze(
            ppi_list_ms,
            progress_callback=progress_callback,
        )
