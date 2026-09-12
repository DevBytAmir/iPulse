"""Application state machine and button-driven navigation.

The MenuController owns the current application state and orchestrates all
other components (sensor, display, network, Kubios, history). The main loop
calls tick() on every iteration.

All navigation is available via the rotary encoder (CW/CCW/PUSH) with the
three tactile buttons (UP/DOWN/SELECT) as a fallback. In every state:
  CW  = same as DOWN (next / increase)
  CCW = same as UP   (previous / decrease / back)
  PUSH = same as SELECT (confirm / enter)

The name-entry state is the exception: CW/CCW scroll the alphabet and
PUSH picks the highlighted character.

Navigation summary
------------------
MAIN_MENU          CW/DOWN = next | CCW/UP = prev | PUSH/SEL = enter
HR_INSTRUCTION     PUSH/SEL = start | CCW/UP = back
HR_MEASURING       PUSH/SEL = stop
HR_STOPPED         PUSH/SEL = back to menu
HRV_INSTRUCTION    PUSH/SEL = start | CCW/UP = back
HRV_COLLECTING     automatic advance when 30 s elapses | CCW/UP = cancel
HRV_SENDING        automatic (no user input)
HRV_RESULTS        PUSH/SEL = back to menu
HISTORY_LIST       CW/DN = next | CCW/UP = prev / back at top | PUSH/SEL = view
HISTORY_DETAIL     PUSH/SEL = back to list
KUBIOS_INSTRUCTION PUSH/SEL = start | CCW/UP = back
KUBIOS_COLLECTING  automatic | CCW/UP = cancel
KUBIOS_SENDING     automatic
KUBIOS_RESULTS     PUSH/SEL = back to menu
PROFILE_NAME       CW/DOWN = next char | CCW/UP = prev char | PUSH/SEL = pick
PROFILE_AGE        CW/UP = increase age | CCW/DN = decrease | PUSH/SEL = confirm
PROFILE_GENDER     CW/CCW/DN = toggle | PUSH/SEL = confirm | UP = skip/back
SETTINGS_MENU      CW/DN = next | CCW/UP = prev / back at top | PUSH/SEL = enter
SETTINGS_RESET_CONFIRM  UP = confirm reset+reboot | PUSH/SEL = cancel
"""

from machine import Pin
import utime
import config
from profile_manager import ProfileManager
from hrv_interpreter import HRVInterpreter


class _State:
    SPLASH              = "splash"
    MAIN_MENU           = "main_menu"
    HR_INSTRUCTION      = "hr_instruction"
    HR_MEASURING        = "hr_measuring"
    HR_STOPPED          = "hr_stopped"
    HRV_INSTRUCTION     = "hrv_instruction"
    HRV_COLLECTING      = "hrv_collecting"
    HRV_SENDING         = "hrv_sending"
    HRV_RESULTS         = "hrv_results"
    HISTORY_LIST        = "history_list"
    HISTORY_DETAIL      = "history_detail"
    KUBIOS_INSTRUCTION  = "kubios_instruction"
    KUBIOS_COLLECTING   = "kubios_collecting"
    KUBIOS_SENDING      = "kubios_sending"
    KUBIOS_RESULTS      = "kubios_results"
    ERROR               = "error"
    PROFILE_NAME            = "profile_name"
    PROFILE_AGE             = "profile_age"
    PROFILE_GENDER          = "profile_gender"
    SETTINGS_MENU           = "settings_menu"
    SETTINGS_RESET_CONFIRM  = "settings_reset_confirm"


class _ButtonHandler:
    """Interrupt-driven input driver for three navigation buttons and a rotary encoder.

    Button events and rotary events are written by ISRs and consumed in the
    main-loop context via the consume_* methods, ensuring each event is handled
    exactly once.
    """

    def __init__(self) -> None:
        self._btn_up     = Pin(config.BUTTON_UP_PIN,     Pin.IN, Pin.PULL_UP)
        self._btn_down   = Pin(config.BUTTON_DOWN_PIN,   Pin.IN, Pin.PULL_UP)
        self._btn_select = Pin(config.BUTTON_SELECT_PIN, Pin.IN, Pin.PULL_UP)

        self._up_flag     = False
        self._down_flag   = False
        self._select_flag = False
        self._last_ms     = 0

        self._btn_up.irq(    trigger=Pin.IRQ_FALLING, handler=self._isr_up)
        self._btn_down.irq(  trigger=Pin.IRQ_FALLING, handler=self._isr_down)
        self._btn_select.irq(trigger=Pin.IRQ_FALLING, handler=self._isr_select)

        self._rot_a    = Pin(config.ROT_A_PIN,    Pin.IN, Pin.PULL_UP)
        self._rot_b    = Pin(config.ROT_B_PIN,    Pin.IN, Pin.PULL_UP)
        self._rot_push = Pin(config.ROT_PUSH_PIN, Pin.IN, Pin.PULL_UP)

        self._rot_cw_flag   = False
        self._rot_ccw_flag  = False
        self._rot_push_flag = False
        self._last_rot_ms      = 0
        self._last_rot_push_ms = 0

        self._rot_a.irq(   trigger=Pin.IRQ_FALLING, handler=self._isr_rot)
        self._rot_push.irq(trigger=Pin.IRQ_FALLING, handler=self._isr_rot_push)

    def _isr_up(self, _pin) -> None:
        if self._debounce():
            self._up_flag = True

    def _isr_down(self, _pin) -> None:
        if self._debounce():
            self._down_flag = True

    def _isr_select(self, _pin) -> None:
        if self._debounce():
            self._select_flag = True

    def _isr_rot(self, _pin) -> None:
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._last_rot_ms) >= config.ROT_DEBOUNCE_MS:
            self._last_rot_ms = now
            if self._rot_b.value() == 1:
                self._rot_cw_flag = True
            else:
                self._rot_ccw_flag = True

    def _isr_rot_push(self, _pin) -> None:
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._last_rot_push_ms) >= config.DEBOUNCE_MS:
            self._last_rot_push_ms = now
            self._rot_push_flag = True

    def _debounce(self) -> bool:
        """Return True and reset the timer when outside the debounce window."""
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._last_ms) >= config.DEBOUNCE_MS:
            self._last_ms = now
            return True
        return False

    def consume_up(self) -> bool:
        if self._up_flag:
            self._up_flag = False
            return True
        return False

    def consume_down(self) -> bool:
        if self._down_flag:
            self._down_flag = False
            return True
        return False

    def consume_select(self) -> bool:
        if self._select_flag:
            self._select_flag = False
            return True
        return False

    def consume_rot_cw(self) -> bool:
        if self._rot_cw_flag:
            self._rot_cw_flag = False
            return True
        return False

    def consume_rot_ccw(self) -> bool:
        if self._rot_ccw_flag:
            self._rot_ccw_flag = False
            return True
        return False

    def consume_rot_push(self) -> bool:
        if self._rot_push_flag:
            self._rot_push_flag = False
            return True
        return False


class MenuController:
    """Central application controller.

    Owns the state machine and delegates rendering, sensing, networking,
    and storage to the injected component objects.

    Args:
        display: DisplayManager instance.
        sensor: HeartRateSensor instance.
        hrv: HRVAnalyzer instance.
        network: NetworkManager instance.
        history: HistoryManager instance.
        kubios: KubiosClient instance.
    """

    _MENU_ITEM_COUNT = 5
    _SETTINGS_ITEMS  = 4

    # A–Z (0–25) + SPACE (26) + DEL (27) + OK (28)
    _ALPHA     = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "
    _ALPHA_LEN = 29

    def __init__(self, display, sensor, hrv, network, history, kubios) -> None:
        self._display   = display
        self._sensor    = sensor
        self._hrv       = hrv
        self._network   = network
        self._history   = history
        self._kubios    = kubios
        self._profile   = ProfileManager()
        self._buttons   = _ButtonHandler()

        self._state    = _State.SPLASH
        self._state_ms = utime.ticks_ms()

        self._menu_cursor = 0

        self._collection_start_ms = 0
        self._hrv_result          = None

        self._history_cursor = 0

        self._last_bpm_ms   = 0
        self._displayed_bpm = 0

        self._name_buffer    = []
        self._name_alpha_idx = 0

        self._profile_age_cursor    = 1
        self._profile_gender_idx    = 0
        self._profile_return_state  = _State.MAIN_MENU
        self._profile_edit_field    = "all"

        self._settings_cursor = 0
        self._hrv_state       = None

        p = self._profile.load()
        self._patient_name = p.get("name") or "Patient"
        self._patient_id   = p.get("patient_id")

    def tick(self) -> None:
        """Advance the state machine by one step.

        Must be called on every main-loop iteration.
        """
        if self._sensor.is_running:
            self._sensor.process()

        handler = self._state_handlers().get(self._state)
        if handler is not None:
            handler()

    def _state_handlers(self) -> dict:
        return {
            _State.SPLASH:                  self._handle_splash,
            _State.MAIN_MENU:               self._handle_main_menu,
            _State.HR_INSTRUCTION:          self._handle_hr_instruction,
            _State.HR_MEASURING:            self._handle_hr_measuring,
            _State.HR_STOPPED:              self._handle_hr_stopped,
            _State.HRV_INSTRUCTION:         self._handle_hrv_instruction,
            _State.HRV_COLLECTING:          self._handle_hrv_collecting,
            _State.HRV_SENDING:             self._handle_hrv_sending,
            _State.HRV_RESULTS:             self._handle_hrv_results,
            _State.HISTORY_LIST:            self._handle_history_list,
            _State.HISTORY_DETAIL:          self._handle_history_detail,
            _State.KUBIOS_INSTRUCTION:      self._handle_kubios_instruction,
            _State.KUBIOS_COLLECTING:       self._handle_kubios_collecting,
            _State.KUBIOS_SENDING:          self._handle_kubios_sending,
            _State.KUBIOS_RESULTS:          self._handle_kubios_results,
            _State.ERROR:                   self._handle_error,
            _State.PROFILE_NAME:            self._handle_profile_name,
            _State.PROFILE_AGE:             self._handle_profile_age,
            _State.PROFILE_GENDER:          self._handle_profile_gender,
            _State.SETTINGS_MENU:           self._handle_settings_menu,
            _State.SETTINGS_RESET_CONFIRM:  self._handle_settings_reset_confirm,
        }

    # ------------------------------------------------------------------
    # Splash / main menu
    # ------------------------------------------------------------------

    def _handle_splash(self) -> None:
        elapsed = utime.ticks_diff(utime.ticks_ms(), self._state_ms)
        if elapsed >= config.SPLASH_DURATION_MS or self._buttons.consume_select() or self._buttons.consume_rot_push():
            if not self._profile.exists():
                self._name_buffer          = []
                self._name_alpha_idx       = 0
                self._profile_age_cursor   = 1
                self._profile_gender_idx   = 0
                self._profile_return_state = _State.MAIN_MENU
                self._profile_edit_field   = "all"
                self._transition(_State.PROFILE_NAME)
                self._display.show_profile_name(self._name_buffer, self._alpha_char())
            else:
                self._transition(_State.MAIN_MENU)
                self._display.show_main_menu(self._menu_cursor)

    def _handle_main_menu(self) -> None:
        changed = False
        if self._buttons.consume_up() or self._buttons.consume_rot_ccw():
            self._menu_cursor = (self._menu_cursor - 1) % self._MENU_ITEM_COUNT
            changed = True
        elif self._buttons.consume_down() or self._buttons.consume_rot_cw():
            self._menu_cursor = (self._menu_cursor + 1) % self._MENU_ITEM_COUNT
            changed = True
        if changed:
            self._display.show_main_menu(self._menu_cursor)

        if self._buttons.consume_select() or self._buttons.consume_rot_push():
            destinations = [
                _State.HR_INSTRUCTION,
                _State.HRV_INSTRUCTION,
                _State.HISTORY_LIST,
                _State.KUBIOS_INSTRUCTION,
                _State.SETTINGS_MENU,
            ]
            self._transition(destinations[self._menu_cursor])
            self._render_current_state()

    # ------------------------------------------------------------------
    # HR measurement
    # ------------------------------------------------------------------

    def _handle_hr_instruction(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_rot_ccw():
            self._transition(_State.MAIN_MENU)
            self._display.show_main_menu(self._menu_cursor)
        elif self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._sensor.start()
            self._sensor.clear_ppi()
            self._displayed_bpm = 0
            self._transition(_State.HR_MEASURING)
            self._display.show_hr_measuring(0, self._sensor.waveform)

    def _handle_hr_measuring(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._sensor.stop()
            self._transition(_State.HR_STOPPED)
            self._display.show_hr_stopped(self._sensor.current_bpm)
            return

        now   = utime.ticks_ms()
        delta = utime.ticks_diff(now, self._last_bpm_ms)
        bpm   = self._sensor.current_bpm

        if delta >= config.BPM_UPDATE_MS or bpm != self._displayed_bpm:
            self._displayed_bpm = bpm
            self._last_bpm_ms   = now
            self._display.show_hr_measuring(bpm, self._sensor.waveform)

            if self._network.is_mqtt_connected and bpm > 0:
                self._network.publish_hr(bpm, patient_name=self._patient_name)

    def _handle_hr_stopped(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._transition(_State.MAIN_MENU)
            self._display.show_main_menu(self._menu_cursor)

    # ------------------------------------------------------------------
    # Local HRV analysis
    # ------------------------------------------------------------------

    def _handle_hrv_instruction(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_rot_ccw():
            self._transition(_State.MAIN_MENU)
            self._display.show_main_menu(self._menu_cursor)
        elif self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._sensor.start()
            self._sensor.clear_ppi()
            self._collection_start_ms = utime.ticks_ms()
            self._transition(_State.HRV_COLLECTING)
            self._display.show_hrv_collecting(0, 0)

    def _handle_hrv_collecting(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_rot_ccw():
            self._sensor.stop()
            self._transition(_State.MAIN_MENU)
            self._display.show_main_menu(self._menu_cursor)
            return

        elapsed_ms = utime.ticks_diff(utime.ticks_ms(), self._collection_start_ms)
        elapsed_s  = elapsed_ms // 1000
        beat_count = len(self._sensor.get_ppi_list()) + 1
        self._display.show_hrv_collecting(elapsed_s, beat_count)

        if elapsed_s >= config.HRV_COLLECTION_DURATION_S:
            self._sensor.stop()
            self._transition(_State.HRV_SENDING)

    def _handle_hrv_sending(self) -> None:
        self._display.show_hrv_sending()
        ppi_list         = self._sensor.get_ppi_list()
        self._hrv_result = self._hrv.compute(ppi_list)
        self._hrv_state  = None

        if self._hrv_result is not None:
            profile = self._profile.load()
            self._hrv_state = HRVInterpreter.classify(
                self._hrv_result["rmssd"],
                profile["age"],
                profile["gender"],
            )
            self._history.save_entry(self._hrv_result, patient_name=profile.get("name"))
            self._network.publish_hrv(self._hrv_result, patient_name=self._patient_name)
            self._network.db_add_record(self._hrv_result, patient_id=self._patient_id)

        self._transition(_State.HRV_RESULTS)
        if self._hrv_result is not None:
            self._display.show_hrv_results(self._hrv_result, heart_state=self._hrv_state)
        else:
            self._display.show_error("Not enough data. Try again.")

    def _handle_hrv_results(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._transition(_State.MAIN_MENU)
            self._display.show_main_menu(self._menu_cursor)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _handle_history_list(self) -> None:
        entries = self._history.get_entries()

        if self._buttons.consume_up() or self._buttons.consume_rot_ccw():
            if self._history_cursor > 0:
                self._history_cursor -= 1
                self._display.show_history_list(entries, self._history_cursor)
            else:
                self._transition(_State.MAIN_MENU)
                self._display.show_main_menu(self._menu_cursor)
            return

        if self._buttons.consume_down() or self._buttons.consume_rot_cw():
            if self._history_cursor < len(entries) - 1:
                self._history_cursor += 1
            self._display.show_history_list(entries, self._history_cursor)
            return

        if (self._buttons.consume_select() or self._buttons.consume_rot_push()) and entries:
            self._transition(_State.HISTORY_DETAIL)
            self._display.show_history_detail(entries[self._history_cursor])
            return

        if self._just_entered():
            self._history_cursor = 0
            self._display.show_history_list(entries, self._history_cursor)

    def _handle_history_detail(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._transition(_State.HISTORY_LIST)
            entries = self._history.get_entries()
            self._display.show_history_list(entries, self._history_cursor)

    # ------------------------------------------------------------------
    # Kubios Cloud analysis
    # ------------------------------------------------------------------

    def _handle_kubios_instruction(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_rot_ccw():
            self._transition(_State.MAIN_MENU)
            self._display.show_main_menu(self._menu_cursor)
        elif self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._sensor.start()
            self._sensor.clear_ppi()
            self._collection_start_ms = utime.ticks_ms()
            self._transition(_State.KUBIOS_COLLECTING)
            self._display.show_kubios_collecting(0, 0)

    def _handle_kubios_collecting(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_rot_ccw():
            self._sensor.stop()
            self._transition(_State.MAIN_MENU)
            self._display.show_main_menu(self._menu_cursor)
            return

        elapsed_ms = utime.ticks_diff(utime.ticks_ms(), self._collection_start_ms)
        elapsed_s  = elapsed_ms // 1000
        beat_count = len(self._sensor.get_ppi_list()) + 1
        self._display.show_kubios_collecting(elapsed_s, beat_count)

        if elapsed_s >= config.HRV_COLLECTION_DURATION_S:
            self._sensor.stop()
            self._transition(_State.KUBIOS_SENDING)

    def _handle_kubios_sending(self) -> None:
        self._display.show_kubios_sending()

        if not self._kubios.is_available():
            self._transition(_State.ERROR)
            self._display.show_error("No WiFi or MQTT. Connect and retry.")
            return

        ppi_list = self._sensor.get_ppi_list()
        result   = self._kubios.analyze(
            ppi_list,
            progress_callback=self._display.show_kubios_sending,
        )

        if result is None:
            self._transition(_State.ERROR)
            self._display.show_error("Kubios timeout or error.")
            return

        profile = self._profile.load()
        self._history.save_entry(result, patient_name=profile.get("name"))
        self._network.publish_hrv(result, patient_name=self._patient_name)
        self._network.db_add_record(result, patient_id=self._patient_id)

        self._transition(_State.KUBIOS_RESULTS)
        self._display.show_kubios_results(result)

    def _handle_kubios_results(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._transition(_State.MAIN_MENU)
            self._display.show_main_menu(self._menu_cursor)

    def _handle_error(self) -> None:
        if self._buttons.consume_up() or self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._transition(_State.MAIN_MENU)
            self._display.show_main_menu(self._menu_cursor)

    # ------------------------------------------------------------------
    # Profile setup / editing
    # ------------------------------------------------------------------

    def _handle_profile_name(self) -> None:
        if self._just_entered():
            self._display.show_profile_name(self._name_buffer, self._alpha_char())

        scrolled = False
        if self._buttons.consume_rot_cw() or self._buttons.consume_down():
            self._name_alpha_idx = (self._name_alpha_idx + 1) % self._ALPHA_LEN
            scrolled = True
        elif self._buttons.consume_rot_ccw() or self._buttons.consume_up():
            self._name_alpha_idx = (self._name_alpha_idx - 1) % self._ALPHA_LEN
            scrolled = True

        if scrolled:
            self._display.show_profile_name(self._name_buffer, self._alpha_char())
            return

        if self._buttons.consume_rot_push() or self._buttons.consume_select():
            alpha_len = len(self._ALPHA)
            idx       = self._name_alpha_idx
            if idx < alpha_len:
                if len(self._name_buffer) < config.PROFILE_NAME_MAX_LEN:
                    self._name_buffer.append(self._ALPHA[idx])
                    self._display.show_profile_name(self._name_buffer, self._alpha_char())
            elif idx == alpha_len:
                if self._name_buffer:
                    self._name_buffer.pop()
                    self._display.show_profile_name(self._name_buffer, self._alpha_char())
            else:
                if self._name_buffer:
                    if self._profile_edit_field == "name":
                        existing   = self._profile.load()
                        name       = "".join(self._name_buffer)
                        patient_id = self._register_patient(name)
                        self._profile.save(
                            name, existing["age"], existing["gender"], patient_id
                        )
                        self._update_patient_cache()
                        self._finish_profile_setup()
                    else:
                        self._transition(_State.PROFILE_AGE)
                        self._display.show_profile_age(
                            self._cursor_to_age(self._profile_age_cursor)
                        )

    def _handle_profile_age(self) -> None:
        _MAX_CURSOR = 85

        if self._just_entered():
            self._display.show_profile_age(self._cursor_to_age(self._profile_age_cursor))

        if self._buttons.consume_up() or self._buttons.consume_rot_cw():
            self._profile_age_cursor = min(_MAX_CURSOR, self._profile_age_cursor + 1)
            self._display.show_profile_age(self._cursor_to_age(self._profile_age_cursor))

        elif self._buttons.consume_down() or self._buttons.consume_rot_ccw():
            if self._profile_age_cursor > 0:
                self._profile_age_cursor -= 1
                self._display.show_profile_age(self._cursor_to_age(self._profile_age_cursor))

        elif self._buttons.consume_select() or self._buttons.consume_rot_push():
            if self._profile_edit_field == "age":
                existing = self._profile.load()
                self._profile.save(
                    existing["name"],
                    self._cursor_to_age(self._profile_age_cursor),
                    existing["gender"],
                    existing["patient_id"],
                )
                self._update_patient_cache()
                self._finish_profile_setup()
            elif self._profile_age_cursor == 0:
                name       = "".join(self._name_buffer) if self._name_buffer else None
                patient_id = self._register_patient(name)
                self._profile.save(name, None, None, patient_id)
                self._update_patient_cache()
                self._finish_profile_setup()
            else:
                self._transition(_State.PROFILE_GENDER)
                self._display.show_profile_gender(self._profile_gender_idx)

    def _handle_profile_gender(self) -> None:
        if self._just_entered():
            self._display.show_profile_gender(self._profile_gender_idx)

        if self._buttons.consume_down() or self._buttons.consume_rot_cw() or self._buttons.consume_rot_ccw():
            self._profile_gender_idx = 1 - self._profile_gender_idx
            self._display.show_profile_gender(self._profile_gender_idx)

        elif self._buttons.consume_up():
            if self._profile_edit_field == "gender":
                self._finish_profile_setup()
            else:
                name       = "".join(self._name_buffer) if self._name_buffer else None
                age        = self._cursor_to_age(self._profile_age_cursor)
                patient_id = self._register_patient(name)
                self._profile.save(name, age, None, patient_id)
                self._update_patient_cache()
                self._finish_profile_setup()

        elif self._buttons.consume_select() or self._buttons.consume_rot_push():
            gender = "male" if self._profile_gender_idx == 0 else "female"
            if self._profile_edit_field == "gender":
                existing = self._profile.load()
                self._profile.save(
                    existing["name"], existing["age"], gender, existing["patient_id"]
                )
                self._update_patient_cache()
                self._finish_profile_setup()
            else:
                name       = "".join(self._name_buffer) if self._name_buffer else None
                age        = self._cursor_to_age(self._profile_age_cursor)
                patient_id = self._register_patient(name)
                self._profile.save(name, age, gender, patient_id)
                self._update_patient_cache()
                self._finish_profile_setup()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _handle_settings_menu(self) -> None:
        if self._just_entered():
            self._settings_cursor = 0
            self._display.show_settings_menu(self._settings_cursor)

        if self._buttons.consume_up() or self._buttons.consume_rot_ccw():
            if self._settings_cursor > 0:
                self._settings_cursor -= 1
                self._display.show_settings_menu(self._settings_cursor)
            else:
                self._transition(_State.MAIN_MENU)
                self._display.show_main_menu(self._menu_cursor)

        elif self._buttons.consume_down() or self._buttons.consume_rot_cw():
            self._settings_cursor = min(self._SETTINGS_ITEMS - 1, self._settings_cursor + 1)
            self._display.show_settings_menu(self._settings_cursor)

        elif self._buttons.consume_select() or self._buttons.consume_rot_push():
            existing = self._profile.load()
            if self._settings_cursor == 0:
                existing_name       = existing.get("name") or ""
                self._name_buffer   = list(existing_name[:config.PROFILE_NAME_MAX_LEN])
                self._name_alpha_idx       = 0
                self._profile_return_state = _State.SETTINGS_MENU
                self._profile_edit_field   = "name"
                self._transition(_State.PROFILE_NAME)
                self._display.show_profile_name(self._name_buffer, self._alpha_char())

            elif self._settings_cursor == 1:
                existing_age = existing.get("age")
                self._profile_age_cursor   = (existing_age - 14) if existing_age else 0
                self._profile_return_state = _State.SETTINGS_MENU
                self._profile_edit_field   = "age"
                self._transition(_State.PROFILE_AGE)
                self._display.show_profile_age(self._cursor_to_age(self._profile_age_cursor))

            elif self._settings_cursor == 2:
                existing_gender    = existing.get("gender")
                self._profile_gender_idx   = 1 if existing_gender == "female" else 0
                self._profile_return_state = _State.SETTINGS_MENU
                self._profile_edit_field   = "gender"
                self._transition(_State.PROFILE_GENDER)
                self._display.show_profile_gender(self._profile_gender_idx)

            else:
                self._transition(_State.SETTINGS_RESET_CONFIRM)
                self._display.show_settings_reset_confirm()

    def _handle_settings_reset_confirm(self) -> None:
        if self._buttons.consume_up():
            self._profile.reset()
            self._history.reset()
            import machine
            machine.reset()

        elif self._buttons.consume_select() or self._buttons.consume_rot_push():
            self._transition(_State.SETTINGS_MENU)
            self._display.show_settings_menu(self._settings_cursor)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _alpha_char(self) -> str:
        """Resolve the current alphabet scroll index to a display string."""
        alpha_len = len(self._ALPHA)
        if self._name_alpha_idx < alpha_len:
            return self._ALPHA[self._name_alpha_idx]
        return "DEL" if self._name_alpha_idx == alpha_len else "OK"

    def _register_patient(self, name: str | None) -> int | None:
        """Register the patient in the database if connected and return the ID."""
        if name and self._network.is_mqtt_connected:
            return self._network.db_register_patient(
                name,
                progress_callback=self._display.show_profile_registering,
            )
        return None

    def _update_patient_cache(self) -> None:
        """Reload patient name and ID from the saved profile into local cache."""
        p = self._profile.load()
        self._patient_name = p.get("name") or "Patient"
        self._patient_id   = p.get("patient_id")

    def _finish_profile_setup(self) -> None:
        """Transition to the correct destination after profile save completes."""
        dest = self._profile_return_state
        self._transition(dest)
        if dest == _State.SETTINGS_MENU:
            self._display.show_settings_menu(self._settings_cursor)
        else:
            self._display.show_main_menu(self._menu_cursor)

    @staticmethod
    def _cursor_to_age(cursor: int) -> int | None:
        """Convert age cursor (0 = Skip, 1–85 → ages 15–99) to int or None."""
        if cursor == 0:
            return None
        return cursor + 14

    def _transition(self, new_state: str) -> None:
        """Record the state change and reset the entry timestamp."""
        self._state    = new_state
        self._state_ms = utime.ticks_ms()

    def _just_entered(self) -> bool:
        """Return True on the very first tick after a state transition."""
        return utime.ticks_diff(utime.ticks_ms(), self._state_ms) < 50

    def _render_current_state(self) -> None:
        """Trigger the initial render for a newly entered state."""
        renders = {
            _State.HR_INSTRUCTION:     self._display.show_hr_instruction,
            _State.HRV_INSTRUCTION:    self._display.show_hrv_instruction,
            _State.KUBIOS_INSTRUCTION: self._display.show_kubios_instruction,
            _State.SETTINGS_MENU:      lambda: self._display.show_settings_menu(self._settings_cursor),
            _State.HISTORY_LIST:       lambda: self._display.show_history_list(
                self._history.get_entries(), 0
            ),
        }
        render_fn = renders.get(self._state)
        if render_fn is not None:
            render_fn()
