"""All OLED rendering for iPulse.

Each public method renders one complete screen. The caller decides when to
call a render method; this module only handles the how.

The SSD1306 is 128 x 64 pixels. Text uses the built-in 8 x 8 font, giving a
maximum of 16 characters per row and 8 rows. No blocking or sleeping here.
"""

import framebuf
import utime
import config
import icons


class DisplayManager:
    """Centralises all OLED drawing operations.

    Args:
        oled: An initialised SSD1306_I2C display object (from lib/ssd1306.py).
    """

    _MENU_LABELS = [
        "Measure HR",
        "HRV Analysis",
        "History",
        "Kubios",
        "Settings",
    ]

    _SPINNER = ["-", "\\", "|", "/"]

    def __init__(self, oled) -> None:
        self._oled          = oled
        self._spinner_idx   = 0
        self._last_spin_ms  = 0

        self._fb_heart  = self._make_fb(bytearray(icons.HEART_8x8),  8,  8)
        self._fb_wave   = self._make_fb(bytearray(icons.WAVE_8x8),   8,  8)
        self._fb_clock  = self._make_fb(bytearray(icons.CLOCK_8x8),  8,  8)
        self._fb_cloud  = self._make_fb(bytearray(icons.CLOUD_8x8),  8,  8)
        self._fb_banana = self._make_fb(bytearray(icons.BANANA_16x16), 16, 16)
        self._fb_gear   = self._make_fb(bytearray(icons.GEAR_8x8),    8,  8)

        self._icon_fbs = [
            self._fb_heart,
            self._fb_wave,
            self._fb_clock,
            self._fb_cloud,
            self._fb_gear,
        ]

    def show_splash(self) -> None:
        """Animated splash screen with a contrast fade-in effect."""
        self._draw_splash_frame()
        self._oled.show()

        for level in range(0, 256, 16):
            self._oled.contrast(level)
            utime.sleep_ms(30)

    def _draw_splash_frame(self) -> None:
        """Compose the static splash layout (logo + tagline)."""
        self._oled.fill(0)
        self._oled.blit(self._fb_banana, 8, 18)
        self._oled.text("iPulse", 44, 20, 1)
        self._oled.hline(40, 32, 80, 1)
        self._oled.text("Heart Rate", 44, 36, 1)
        self._oled.text("Monitor", 44, 46, 1)
        self._oled.rect(0, 0, 128, 64, 1)

    def show_main_menu(self, cursor: int) -> None:
        """Render the scrollable main menu (4 visible rows, scrollbar on right).

        Args:
            cursor: Index of the currently highlighted item (0 to len-1).
        """
        self._oled.fill(0)
        self._oled.text("-- iPulse --", 8, 1, 1)
        self._oled.hline(0, 11, 128, 1)

        total       = len(self._MENU_LABELS)
        visible     = 4
        row_height  = 13
        window_start = max(0, min(cursor - visible + 1, total - visible))

        for row_idx in range(visible):
            abs_idx = window_start + row_idx
            if abs_idx >= total:
                break
            label = self._MENU_LABELS[abs_idx]
            y = 13 + row_idx * row_height
            if abs_idx == cursor:
                self._oled.fill_rect(0, y - 1, 123, row_height, 1)
                self._oled.blit(self._icon_fbs[abs_idx], 2, y, 0)
                self._oled.text(label, 13, y, 0)
            else:
                self._oled.blit(self._icon_fbs[abs_idx], 2, y)
                self._oled.text(label, 13, y, 1)

        bar_x = 125
        bar_y = 13
        bar_h = 51
        self._oled.rect(bar_x, bar_y, 3, bar_h, 1)
        thumb_h = max(4, bar_h * visible // total)
        max_offset = total - visible
        thumb_y = bar_y + (bar_h - thumb_h) * window_start // max(1, max_offset)
        self._oled.fill_rect(bar_x + 1, thumb_y, 1, thumb_h, 1)

        self._oled.show()

    def show_hr_instruction(self) -> None:
        """Prompt the user to place their finger and press SELECT."""
        self._oled.fill(0)
        self._oled.text("Measure HR", 16, 2, 1)
        self._oled.hline(0, 12, 128, 1)
        self._oled.text("Place finger", 4, 18, 1)
        self._oled.text("on sensor.", 4, 28, 1)
        self._oled.hline(0, 40, 128, 1)
        self._oled.text("[SEL] Start", 4, 44, 1)
        self._oled.text("[UP]  Back", 4, 54, 1)
        self._oled.show()

    def show_hr_measuring(self, bpm: int, waveform: list) -> None:
        """Live heart-rate screen: scrolling PPG waveform + current BPM.

        Args:
            bpm: Current BPM value (0 = not yet established).
            waveform: Sequence of y-coordinates (pixel rows) in chronological
                order. Length must equal config.PPG_WAVEFORM_COLS.
        """
        self._oled.fill(0)

        bpm_str = str(bpm) if bpm > 0 else "---"
        self._oled.text(bpm_str, 100, 4, 1)
        self._oled.text("BPM", 100, 14, 1)

        prev_y = waveform[0]
        for x, y in enumerate(waveform):
            self._oled.line(x, prev_y, x + 1, y, 1)
            prev_y = y

        self._oled.vline(98, 0, 64, 1)
        self._oled.hline(0, 57, 98, 1)
        self._oled.text("[SEL]Stop", 0, 58, 1)

        self._oled.show()

    def show_hr_stopped(self, bpm: int) -> None:
        """Show the final BPM after the user stops a measurement."""
        self._oled.fill(0)
        self._oled.text("Result", 36, 4, 1)
        self._oled.hline(0, 14, 128, 1)

        bpm_str = str(bpm) if bpm > 0 else "---"
        self._oled.text(bpm_str + " BPM", 24, 26, 1)

        self._oled.hline(0, 48, 128, 1)
        self._oled.text("[UP] Main menu", 0, 52, 1)
        self._oled.show()

    def show_hrv_instruction(self) -> None:
        """Prompt the user to start a 30-second HRV collection."""
        self._oled.fill(0)
        self._oled.text("HRV Analysis", 4, 2, 1)
        self._oled.hline(0, 12, 128, 1)
        self._oled.text("Place finger", 4, 18, 1)
        self._oled.text("on sensor.", 4, 28, 1)
        self._oled.text("30 s capture.", 4, 38, 1)
        self._oled.hline(0, 50, 128, 1)
        self._oled.text("[SEL] Start", 4, 54, 1)
        self._oled.show()

    def show_hrv_collecting(self, elapsed_s: int, beat_count: int) -> None:
        """Progress screen during the 30-second HRV collection window.

        Args:
            elapsed_s: Seconds elapsed since collection started (0-30).
            beat_count: Number of beats detected so far.
        """
        self._oled.fill(0)
        self._oled.text("Collecting...", 4, 2, 1)
        self._oled.hline(0, 12, 128, 1)

        duration = config.HRV_COLLECTION_DURATION_S
        pct      = min(100, int(elapsed_s * 100 / duration))
        self._draw_progress_bar(4, 20, 120, 10, pct)

        time_str = "{:d}/{:d} s".format(elapsed_s, duration)
        self._oled.text(time_str, 30, 34, 1)
        self._oled.text("Beats: " + str(beat_count), 30, 46, 1)

        self._oled.hline(0, 56, 128, 1)
        self._oled.text("[UP] Cancel", 4, 57, 1)
        self._oled.show()

    def show_hrv_sending(self) -> None:
        """Spinner screen shown while HRV data is being sent over MQTT."""
        self._oled.fill(0)
        self._oled.text("Sending data", 4, 20, 1)
        spinner = self._SPINNER[self._advance_spinner()]
        self._oled.text(spinner, 60, 36, 1)
        self._oled.show()

    def show_hrv_results(self, hrv_data: dict, heart_state: str | None = None) -> None:
        """Display HRV metrics and optional heart state label.

        Args:
            hrv_data: Keys: ``mean_hr``, ``mean_ppi``, ``rmssd``, ``sdnn``.
            heart_state: One of ``"Excellent"``, ``"Good"``, ``"Normal"``,
                ``"Stressed"``, ``"Fatigued"``, or None to omit the state line.
        """
        self._oled.fill(0)
        self._oled.text("HRV Results", 8, 1, 1)
        self._oled.hline(0, 11, 128, 1)

        self._oled.text(
            "HR:{:.0f} PPI:{:.0f}".format(
                hrv_data.get("mean_hr", 0), hrv_data.get("mean_ppi", 0)
            ),
            4, 14, 1,
        )
        self._oled.text(
            "RMSSD:{:.1f}".format(hrv_data.get("rmssd", 0)), 4, 24, 1
        )
        self._oled.text(
            "SDNN: {:.1f}".format(hrv_data.get("sdnn",  0)), 4, 34, 1
        )

        if heart_state is not None:
            self._oled.hline(0, 44, 128, 1)
            self._oled.text("State:" + heart_state, 4, 46, 1)
            self._oled.hline(0, 57, 128, 1)
            self._oled.text("[UP] Menu", 4, 58, 1)
        else:
            self._oled.hline(0, 46, 128, 1)
            self._oled.text("[UP] Menu", 4, 55, 1)

        self._oled.show()

    def show_profile_name(self, buffer: list, current_char: str) -> None:
        """Name-entry screen driven by the rotary encoder.

        Args:
            buffer: Characters selected so far (up to config.PROFILE_NAME_MAX_LEN).
            current_char: The character currently highlighted by the rotary
                selector, one of ``'A'``-``'Z'``, ``'DEL'``, or ``'OK'``.
        """
        self._oled.fill(0)

        count_str = "{}/{}".format(len(buffer), config.PROFILE_NAME_MAX_LEN)
        title     = "Enter Name"
        spaces    = max(1, 16 - len(title) - len(count_str))
        self._oled.text(title + " " * spaces + count_str, 0, 1, 1)
        self._oled.hline(0, 11, 128, 1)

        text = "".join(buffer)
        if len(text) >= 16:
            display_text = text[-16:]
        else:
            display_text = text + "_"
        self._oled.text(display_text, 0, 16, 1)

        self._oled.hline(0, 27, 128, 1)

        if current_char == "DEL":
            label = ">DEL<"
        elif current_char == "OK":
            label = "> OK <"
        elif current_char == " ":
            label = ">SPC<"
        else:
            label = "> " + current_char + " <"
        x_lbl = (128 - len(label) * 8) // 2
        self._oled.text(label, x_lbl, 33, 1)

        self._oled.hline(0, 45, 128, 1)
        self._oled.text("PUSH:add OK:done", 0, 49, 1)
        self._oled.show()

    def show_profile_registering(self) -> None:
        """Spinner shown while the patient name is being registered in the database."""
        self._oled.fill(0)
        self._oled.text("Registering", 12, 20, 1)
        self._oled.text("patient...", 20, 30, 1)
        spinner = self._SPINNER[self._advance_spinner()]
        self._oled.text(spinner, 60, 44, 1)
        self._oled.show()

    def show_profile_age(self, age_value: int | None) -> None:
        """Age selection screen.

        Args:
            age_value: Current scrolled age (15-99), or None when cursor is on 'Skip'.
        """
        self._oled.fill(0)
        self._oled.text("Your Age", 24, 1, 1)
        self._oled.hline(0, 11, 128, 1)

        if age_value is None:
            self._oled.text("> Skip <", 24, 26, 1)
        else:
            self._oled.text("> {:d} <".format(age_value), 40, 26, 1)

        self._oled.hline(0, 42, 128, 1)
        self._oled.text("UP/DN:change", 4, 44, 1)
        self._oled.text("SEL:ok", 4, 54, 1)
        self._oled.show()

    def show_profile_gender(self, gender_idx: int) -> None:
        """Gender selection screen.

        Args:
            gender_idx: 0 = Male, 1 = Female.
        """
        self._oled.fill(0)
        self._oled.text("Your Gender", 12, 1, 1)
        self._oled.hline(0, 11, 128, 1)

        options = ["Male", "Female"]
        for i, label in enumerate(options):
            y = 20 + i * 14
            if i == gender_idx:
                self._oled.fill_rect(0, y - 1, 128, 12, 1)
                self._oled.text("> " + label, 4, y, 0)
            else:
                self._oled.text("  " + label, 4, y, 1)

        self._oled.hline(0, 50, 128, 1)
        self._oled.text("SEL:ok  UP:skip", 0, 54, 1)
        self._oled.show()

    def show_settings_menu(self, cursor: int) -> None:
        """Four-item Settings sub-menu.

        Args:
            cursor: 0 = Edit Name, 1 = Edit Age, 2 = Edit Gender, 3 = Full Reset.
        """
        self._oled.fill(0)
        self._oled.text("Settings", 28, 1, 1)
        self._oled.hline(0, 11, 128, 1)

        options = ["Edit Name", "Edit Age", "Edit Gender", "Full Reset"]
        for i, label in enumerate(options):
            y = 13 + i * 12
            if i == cursor:
                self._oled.fill_rect(0, y - 1, 128, 11, 1)
                self._oled.text("> " + label, 4, y, 0)
            else:
                self._oled.text("  " + label, 4, y, 1)

        self._oled.show()

    def show_settings_reset_confirm(self) -> None:
        """Confirmation screen before a full device reset."""
        self._oled.fill(0)
        self._oled.text("Reset All?", 16, 2, 1)
        self._oled.hline(0, 12, 128, 1)
        self._oled.text("Deletes history", 0, 18, 1)
        self._oled.text("and profile.", 0, 28, 1)
        self._oled.hline(0, 40, 128, 1)
        self._oled.text("UP:YES  SEL:NO", 0, 44, 1)
        self._oled.show()

    def show_history_list(self, entries: list, cursor: int) -> None:
        """Scrollable list of past HRV measurements (up to 4 rows visible).

        Args:
            entries: History records as returned by HistoryManager.get_entries().
            cursor: Index of the highlighted entry.
        """
        self._oled.fill(0)
        self._oled.text("History", 36, 1, 1)
        self._oled.hline(0, 11, 128, 1)

        if not entries:
            self._oled.text("No records yet.", 4, 28, 1)
            self._oled.show()
            return

        visible_rows   = 4
        row_height     = 12
        window_start   = max(0, cursor - visible_rows + 1)
        visible        = entries[window_start: window_start + visible_rows]

        for row_idx, entry in enumerate(visible):
            abs_idx = window_start + row_idx
            y       = 14 + row_idx * row_height
            label   = "M{:02d} {}".format(
                entry.get("id", abs_idx + 1),
                entry.get("timestamp", "")[:10],
            )
            if abs_idx == cursor:
                self._oled.fill_rect(0, y - 1, 128, row_height, 1)
                self._oled.text(label, 2, y, 0)
            else:
                self._oled.text(label, 2, y, 1)

        self._oled.hline(0, 56, 128, 1)
        self._oled.text("[SEL]View [UP]Back", 0, 57, 1)
        self._oled.show()

    def show_history_detail(self, entry: dict) -> None:
        """Full-detail view of a single history record.

        Args:
            entry: One record as returned by HistoryManager.get_entry().
        """
        self._oled.fill(0)
        ts   = entry.get("timestamp", "N/A")
        name = entry.get("name")
        if name:
            header = "{} {}".format(name, ts[:10])
        else:
            header = ts[:16]
        self._oled.text(header, 0, 1, 1)
        self._oled.hline(0, 11, 128, 1)

        self._oled.text(
            "HR:   {:.0f} bpm".format(entry.get("mean_hr",  0)), 4, 14, 1
        )
        self._oled.text(
            "PPI:  {:.0f} ms".format(entry.get("mean_ppi", 0)), 4, 24, 1
        )
        self._oled.text(
            "RMSSD:{:.1f}".format(entry.get("rmssd", 0)), 4, 34, 1
        )
        self._oled.text(
            "SDNN: {:.1f}".format(entry.get("sdnn",  0)), 4, 44, 1
        )

        self._oled.hline(0, 55, 128, 1)
        self._oled.text("[UP] Back", 4, 56, 1)
        self._oled.show()

    def show_kubios_instruction(self) -> None:
        """Instruction screen before Kubios data collection starts."""
        self._oled.fill(0)
        self._oled.text("Kubios Cloud", 8, 2, 1)
        self._oled.hline(0, 12, 128, 1)
        self._oled.text("Place finger", 4, 18, 1)
        self._oled.text("on sensor.", 4, 28, 1)
        self._oled.text("30 s capture.", 4, 38, 1)
        self._oled.hline(0, 50, 128, 1)
        self._oled.text("[SEL] Start", 4, 54, 1)
        self._oled.show()

    def show_kubios_collecting(self, elapsed_s: int, beat_count: int) -> None:
        """Progress screen during Kubios data collection."""
        self._oled.fill(0)
        self._oled.text("Kubios collect", 0, 2, 1)
        self._oled.hline(0, 12, 128, 1)

        duration = config.HRV_COLLECTION_DURATION_S
        pct      = min(100, int(elapsed_s * 100 / duration))
        self._draw_progress_bar(4, 20, 120, 10, pct)

        time_str = "{:d}/{:d} s".format(elapsed_s, duration)
        self._oled.text(time_str, 30, 34, 1)
        self._oled.text("Beats: " + str(beat_count), 30, 46, 1)

        self._oled.hline(0, 56, 128, 1)
        self._oled.text("[UP] Cancel", 4, 57, 1)
        self._oled.show()

    def show_kubios_sending(self) -> None:
        """Spinner screen shown while data is being sent to Kubios Cloud."""
        self._oled.fill(0)
        self._oled.text("Kubios Cloud", 8, 16, 1)
        self._oled.text("Analyzing...", 8, 28, 1)
        spinner = self._SPINNER[self._advance_spinner()]
        self._oled.text(spinner, 60, 44, 1)
        self._oled.show()

    def show_kubios_results(self, results: dict) -> None:
        """Display the Kubios analysis result including SNS and PNS indices.

        Args:
            results: Keys: ``mean_hr``, ``mean_ppi``, ``rmssd``, ``sdnn``,
                ``sns``, ``pns``.
        """
        self._oled.fill(0)
        self._oled.text("Kubios Result", 4, 1, 1)
        self._oled.hline(0, 11, 128, 1)

        self._oled.text(
            "HR:{:.0f} PPI:{:.0f}".format(
                results.get("mean_hr", 0), results.get("mean_ppi", 0)
            ),
            4, 14, 1,
        )
        self._oled.text(
            "RMSSD:{:.1f}".format(results.get("rmssd", 0)), 4, 24, 1
        )
        self._oled.text(
            "SDNN: {:.1f}".format(results.get("sdnn",  0)), 4, 34, 1
        )
        self._oled.text(
            "SNS:  {:.3f}".format(results.get("sns",   0)), 4, 44, 1
        )
        self._oled.text(
            "PNS:  {:.3f}".format(results.get("pns",   0)), 4, 54, 1
        )
        self._oled.show()

    def show_wifi_connecting(self) -> None:
        """Display a status message while WiFi association is in progress."""
        self._oled.fill(0)
        self._oled.text("Connecting to", 8, 20, 1)
        self._oled.text("WiFi...", 28, 32, 1)
        spinner = self._SPINNER[self._advance_spinner()]
        self._oled.text(spinner, 60, 48, 1)
        self._oled.show()

    def show_error(self, message: str) -> None:
        """Generic error screen.

        Args:
            message: Short description; truncated to 16 characters per line.
        """
        self._oled.fill(0)
        self._oled.text("! Error !", 20, 4, 1)
        self._oled.hline(0, 14, 128, 1)
        line_len = 16
        for line_idx, chunk in enumerate(self._wrap_text(message, line_len)):
            self._oled.text(chunk, 0, 18 + line_idx * 10, 1)
        self._oled.hline(0, 52, 128, 1)
        self._oled.text("[UP] Back", 4, 54, 1)
        self._oled.show()

    def _make_fb(self, buf: bytearray, width: int, height: int):
        """Return a MONO_HLSB FrameBuffer backed by *buf*."""
        return framebuf.FrameBuffer(buf, width, height, framebuf.MONO_HLSB)

    def _draw_progress_bar(self, x: int, y: int, width: int, height: int, percent: int) -> None:
        """Draw a rectangular progress bar filled to *percent* (0-100)."""
        self._oled.rect(x, y, width, height, 1)
        filled = int((width - 2) * percent / 100)
        if filled > 0:
            self._oled.fill_rect(x + 1, y + 1, filled, height - 2, 1)

    def _advance_spinner(self) -> int:
        """Advance the spinner animation at SPINNER_STEP_MS intervals.

        Returns:
            Index of the current spinner character.
        """
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._last_spin_ms) >= config.SPINNER_STEP_MS:
            self._spinner_idx   = (self._spinner_idx + 1) % len(self._SPINNER)
            self._last_spin_ms  = now
        return self._spinner_idx

    def _wrap_text(self, text: str, line_len: int) -> list:
        """Split *text* into a list of strings each at most *line_len* chars."""
        words   = text.split()
        lines   = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= line_len:
                current = (current + " " + word).strip()
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
