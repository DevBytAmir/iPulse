"""WiFi, NTP, MQTT publishing, Kubios proxy, and database API.

All network I/O is centralised here. Higher-level modules never touch the
MQTT client directly. Kubios analysis uses a broker-hosted MQTT proxy rather
than the Kubios REST API: publish PPI list to kubios/request and subscribe
for a response on kubios/response (matched by device MAC address).
"""

import network
import utime
import ntptime
import json
import config
from lib.umqtt.simple import MQTTClient


class NetworkManager:
    """Handles WiFi association, NTP sync, MQTT publishing, Kubios proxy, and database API."""

    def __init__(self) -> None:
        self._wlan      = network.WLAN(network.STA_IF)
        self._mqtt      = None
        self._wifi_ok   = False
        self._mqtt_ok   = False

    def connect_wifi(self, progress_callback=None) -> bool:
        """Associate with the configured access point.

        Args:
            progress_callback: Called every 200 ms while waiting for association
                so the caller can animate a spinner.

        Returns:
            True on success, False on timeout.
        """
        self._wlan.active(True)
        if self._wlan.isconnected():
            self._wifi_ok = True
            return True

        self._wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        deadline = utime.ticks_add(
            utime.ticks_ms(), config.WIFI_CONNECT_TIMEOUT_S * 1000
        )
        while not self._wlan.isconnected():
            if utime.ticks_diff(deadline, utime.ticks_ms()) <= 0:
                self._wifi_ok = False
                return False
            if progress_callback is not None:
                progress_callback()
            utime.sleep_ms(200)

        self._wifi_ok = True
        return True

    def sync_ntp(self) -> None:
        """Synchronise the RTC via NTP. Silently skips if not connected."""
        if not self._wifi_ok:
            return
        try:
            ntptime.settime()
        except OSError:
            pass

    @property
    def is_wifi_connected(self) -> bool:
        """True when an active WiFi link is confirmed."""
        return self._wifi_ok and self._wlan.isconnected()

    def get_mac_str(self) -> str:
        """Return the Pico W MAC address as an uppercase hex string (e.g. ``'A1B2C3D4E5F6'``)."""
        mac_bytes = self._wlan.config("mac")
        return "".join("{:02X}".format(b) for b in mac_bytes)

    def connect_mqtt(self) -> bool:
        """Open an MQTT session with the configured broker.

        Returns:
            True on success, False on any error.
        """
        if not self.is_wifi_connected:
            return False
        try:
            self._mqtt = MQTTClient(
                config.MQTT_CLIENT_ID,
                config.MQTT_BROKER,
                port=config.MQTT_PORT,
            )
            self._mqtt.connect()
            self._mqtt_ok = True
            return True
        except OSError:
            self._mqtt_ok = False
            return False

    @property
    def is_mqtt_connected(self) -> bool:
        """True when an active MQTT session exists."""
        return self._mqtt_ok and self._mqtt is not None

    def publish_hr(self, bpm: int, patient_name: str = "Patient") -> None:
        """Publish current BPM to the custom HR topic.

        Args:
            bpm: Current heart rate in beats per minute.
            patient_name: Patient initials or name to include in the payload.
        """
        if not self.is_mqtt_connected:
            return
        payload = json.dumps({
            "patient": patient_name,
            "bpm":     bpm,
        })
        self._safe_publish(config.MQTT_TOPIC_HR, payload)

    def publish_hrv(self, hrv_data: dict, patient_name: str = "Patient") -> None:
        """Publish HRV result set to the custom HRV topic.

        Args:
            hrv_data: Dict with keys ``mean_hr``, ``mean_ppi``, ``rmssd``, ``sdnn``.
            patient_name: Patient initials or name to include in the payload.
        """
        if not self.is_mqtt_connected:
            return
        payload = json.dumps({
            "patient":  patient_name,
            "mean_hr":  hrv_data.get("mean_hr",  0),
            "mean_ppi": hrv_data.get("mean_ppi", 0),
            "rmssd":    hrv_data.get("rmssd",    0),
            "sdnn":     hrv_data.get("sdnn",     0),
        })
        self._safe_publish(config.MQTT_TOPIC_HRV, payload)

    def db_register_device(self) -> None:
        """Register this device in the database.

        Safe to call on every boot; the server ignores duplicate MAC addresses.
        """
        if not self.is_mqtt_connected:
            return
        payload = json.dumps({
            "mac":         self.get_mac_str(),
            "device_name": config.DEVICE_NAME,
        })
        self._safe_publish(config.MQTT_TOPIC_DB_DEVICES_ADD, payload)

    def db_register_patient(self, name: str, progress_callback=None) -> int | None:
        """Register a patient in the database and return the assigned patient ID.

        Publishes to ``database/patients/add`` and waits for a response on
        ``database/response`` matched by this device's MAC address.

        Args:
            name: Patient name or initials.
            progress_callback: Called each polling iteration to animate a spinner.

        Returns:
            Integer patient ID on success, or None on timeout or error.
        """
        if not self.is_mqtt_connected:
            return None

        mac = self.get_mac_str()
        request_payload = json.dumps({
            "mac":          mac,
            "patient_name": name,
        })

        response_holder = [None]

        def _on_message(topic, msg):
            try:
                data = json.loads(msg)
                if data.get("mac") == mac and data.get("message") == "OK":
                    response_holder[0] = data
            except Exception:
                pass

        self._mqtt.set_callback(_on_message)
        self._mqtt.subscribe(config.MQTT_TOPIC_DB_RESPONSE)
        self._mqtt.publish(config.MQTT_TOPIC_DB_PATIENTS_ADD, request_payload)

        start_ms = utime.ticks_ms()
        while response_holder[0] is None:
            elapsed = utime.ticks_diff(utime.ticks_ms(), start_ms)
            if elapsed > config.DB_RESPONSE_TIMEOUT_MS:
                return None
            try:
                self._mqtt.check_msg()
            except OSError:
                self._mqtt_ok = False
                return None
            if progress_callback is not None:
                progress_callback()
            utime.sleep_ms(100)

        patient_id = response_holder[0].get("data")
        return patient_id if isinstance(patient_id, int) else None

    def db_add_record(self, hrv_data: dict, patient_id: int | None = None) -> None:
        """Submit an HRV record to the database API.

        Args:
            hrv_data: Must contain ``mean_hr``. Optionally ``mean_ppi``, ``rmssd``,
                ``sdnn``, ``sns``, ``pns``.
            patient_id: Database patient ID to associate this record with a specific
                patient. Omitted from the payload when None.
        """
        if not self.is_mqtt_connected:
            return
        payload = {
            "mac":       self.get_mac_str(),
            "timestamp": utime.time(),
            "mean_hr":   hrv_data.get("mean_hr", 0),
        }
        for key in ("mean_ppi", "rmssd", "sdnn", "sns", "pns"):
            if key in hrv_data:
                payload[key] = hrv_data[key]
        if patient_id is not None:
            payload["patient_id"] = patient_id

        self._safe_publish(config.MQTT_TOPIC_DB_RECORDS_ADD, json.dumps(payload))

    def kubios_analyze(self, ppi_list_ms: list, progress_callback=None) -> dict | None:
        """Send PPI data to the Kubios MQTT proxy and wait for the response.

        Publishes to ``kubios/request`` and polls ``kubios/response`` until a
        message arrives whose ``mac`` field matches this device's MAC address.

        Args:
            ppi_list_ms: Peak-to-peak intervals in milliseconds.
            progress_callback: Called on each polling iteration so the caller can
                update the display while waiting.

        Returns:
            Dict with keys ``mean_hr``, ``mean_ppi``, ``rmssd``, ``sdnn``,
            ``sns``, ``pns``, or None on timeout or error.
        """
        if not self.is_mqtt_connected:
            return None

        mac = self.get_mac_str()
        request_payload = json.dumps({
            "mac":      mac,
            "type":     "RRI",
            "data":     [int(p) for p in ppi_list_ms],
            "analysis": {"type": "readiness"},
        })

        response_holder = [None]

        def _on_message(topic, msg):
            try:
                data = json.loads(msg)
                if data.get("mac") == mac:
                    response_holder[0] = data
            except Exception:
                pass

        self._mqtt.set_callback(_on_message)
        self._mqtt.subscribe(config.MQTT_TOPIC_KUBIOS_RESPONSE)
        self._mqtt.publish(config.MQTT_TOPIC_KUBIOS_REQUEST, request_payload)

        start_ms = utime.ticks_ms()
        while response_holder[0] is None:
            elapsed = utime.ticks_diff(utime.ticks_ms(), start_ms)
            if elapsed > config.KUBIOS_RESPONSE_TIMEOUT_MS:
                return None
            try:
                self._mqtt.check_msg()
            except OSError:
                self._mqtt_ok = False
                return None
            if progress_callback is not None:
                progress_callback()
            utime.sleep_ms(100)

        return self._parse_kubios_response(response_holder[0])

    def _parse_kubios_response(self, data: dict) -> dict | None:
        """Extract HRV metrics from the Kubios proxy response envelope.

        Returns:
            Parsed metrics dict, or None if the status is not ``'ok'``.
        """
        inner    = data.get("data", {})
        if inner.get("status") != "ok":
            return None
        analysis = inner.get("analysis", {})
        return {
            "mean_hr":  round(float(analysis.get("mean_hr_bpm", 0)), 1),
            "mean_ppi": round(float(analysis.get("mean_rr_ms",  0)), 1),
            "rmssd":    round(float(analysis.get("rmssd_ms",    0)), 1),
            "sdnn":     round(float(analysis.get("sdnn_ms",     0)), 1),
            "sns":      round(float(analysis.get("sns_index",   0)), 3),
            "pns":      round(float(analysis.get("pns_index",   0)), 3),
        }

    def _safe_publish(self, topic: str, payload: str) -> None:
        """Publish and attempt one reconnect if the broker dropped us."""
        try:
            self._mqtt.publish(topic, payload)
        except OSError:
            self._mqtt_ok = False
            if self.connect_mqtt():
                try:
                    self._mqtt.publish(topic, payload)
                except OSError:
                    pass
