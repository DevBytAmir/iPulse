"""PPG sensor acquisition and beat detection via PIO timer interrupts.

The PIO timer fires an interrupt at exactly SAMPLE_RATE_HZ (250 Hz). The
interrupt handler only reads the ADC and queues the sample into the FIFO.
The main loop calls process() which consumes the FIFO, runs the beat-detection
algorithm, and maintains the rolling BPM estimate.
"""

from machine import ADC, Pin
import utime
import config
from lib.piotimer import Piotimer
from lib.fifo import Fifo
from lib.led import Led


class HeartRateSensor:
    """Manages the PPG sensor from hardware initialisation through beat detection.

    Args:
        on_beat: Called (with no arguments) from the main loop each time a beat
            is confirmed. Safe to use for display updates or counters.
    """

    def __init__(self, on_beat=None) -> None:
        self._adc       = ADC(Pin(config.PPG_ADC_PIN))
        self._fifo      = Fifo(config.FIFO_CAPACITY)
        self._led       = Led(config.LED_HEARTBEAT_PIN)
        self._timer     = None
        self._on_beat   = on_beat

        self._sig_max   = 32768
        self._sig_min   = 32768

        self._above_threshold = False
        self._last_beat_ms    = 0
        self._intervals_ms: list = []

        self._current_bpm   = 0

        self._waveform      = [32] * config.PPG_WAVEFORM_COLS
        self._wave_idx      = 0

        self._running = False

    def start(self) -> None:
        """Start the PIO timer and begin sampling at SAMPLE_RATE_HZ."""
        if self._running:
            return
        self._sig_max           = 32768
        self._sig_min           = 32768
        self._above_threshold   = False
        self._last_beat_ms      = 0
        self._intervals_ms      = []
        self._current_bpm       = 0
        self._running           = True
        self._timer = Piotimer(
            mode=Piotimer.PERIODIC,
            freq=config.SAMPLE_RATE_HZ,
            callback=self._sampling_isr,
        )

    def stop(self) -> None:
        """Stop the PIO timer and release hardware resources."""
        if not self._running:
            return
        self._running = False
        if self._timer is not None:
            self._timer.deinit()
            self._timer = None
        self._led.off()

    def process(self) -> None:
        """Drain the FIFO and run beat detection on each sample.

        Must be called repeatedly from the main loop, NOT from an interrupt.
        """
        while self._fifo.has_data():
            sample = self._fifo.get()
            self._update_envelope(sample)
            self._update_waveform(sample)
            self._detect_beat(sample)

    @property
    def current_bpm(self) -> int:
        """Most recent valid BPM value, or 0 if not yet established."""
        return self._current_bpm

    @property
    def is_running(self) -> bool:
        """True while the PIO timer is active."""
        return self._running

    @property
    def waveform(self) -> list:
        """Current waveform buffer as a list in chronological order.

        Each element is a y-coordinate (pixel row) for direct rendering.
        """
        idx = self._wave_idx
        return self._waveform[idx:] + self._waveform[:idx]

    def get_ppi_list(self) -> list:
        """Return a copy of all PPI values (ms) recorded this session."""
        return list(self._intervals_ms)

    def clear_ppi(self) -> None:
        """Reset the PPI list for a fresh HRV collection window."""
        self._intervals_ms = []

    def _sampling_isr(self, timer) -> None:
        """Read one ADC sample and place it into the lock-free FIFO.

        Minimal ISR: no sleeping, no display calls, no complex logic.
        """
        self._fifo.put(self._adc.read_u16())

    def _update_envelope(self, sample: int) -> None:
        """Track the running signal envelope with a leaky max/min follower.

        The decay constant (0.9995 per sample at 250 Hz) gives a time constant
        of roughly 8 seconds, suitable for slow baseline drift correction.
        """
        decay = 0.9995
        if sample > self._sig_max:
            self._sig_max = sample
        else:
            self._sig_max = int(self._sig_max * decay + sample * (1 - decay))

        if sample < self._sig_min:
            self._sig_min = sample
        else:
            self._sig_min = int(self._sig_min * decay + sample * (1 - decay))

    def _update_waveform(self, sample: int) -> None:
        """Map the raw sample to a display y-coordinate and store it."""
        self._waveform[self._wave_idx] = self._sample_to_y(sample)
        self._wave_idx = (self._wave_idx + 1) % config.PPG_WAVEFORM_COLS

    def _sample_to_y(self, sample: int) -> int:
        """Convert a raw ADC value to a pixel row within the waveform display area."""
        sig_range = self._sig_max - self._sig_min
        if sig_range < config.SIGNAL_MIN_RANGE:
            return (config.PPG_WAVEFORM_Y_TOP + config.PPG_WAVEFORM_Y_BOTTOM) // 2

        display_range = config.PPG_WAVEFORM_Y_BOTTOM - config.PPG_WAVEFORM_Y_TOP
        y = config.PPG_WAVEFORM_Y_BOTTOM - int(
            (sample - self._sig_min) * display_range / sig_range
        )
        return max(config.PPG_WAVEFORM_Y_TOP, min(config.PPG_WAVEFORM_Y_BOTTOM, y))

    def _detect_beat(self, sample: int) -> None:
        """Threshold-crossing detector with hysteresis and a refractory period.

        A beat is registered when the signal crosses above the high threshold
        and the refractory period since the last beat has elapsed. The detector
        then waits for the signal to fall below a lower hysteresis level before
        it can fire again, preventing double-counting a single systolic peak.
        """
        sig_range = self._sig_max - self._sig_min
        if sig_range < config.SIGNAL_MIN_RANGE:
            return

        high_threshold = self._sig_min + int(sig_range * config.PEAK_THRESHOLD_RATIO)
        low_threshold  = self._sig_min + int(sig_range * config.PEAK_THRESHOLD_RATIO * 0.7)

        now_ms     = utime.ticks_ms()
        since_last = utime.ticks_diff(now_ms, self._last_beat_ms)

        if (not self._above_threshold
                and sample > high_threshold
                and since_last > config.REFRACTORY_PERIOD_MS):
            self._above_threshold = True

            if self._last_beat_ms != 0:
                max_interval_ms = int(60_000 / config.MIN_BPM)
                if since_last < max_interval_ms:
                    self._intervals_ms.append(since_last)
                    self._recalculate_bpm()

            self._last_beat_ms = now_ms
            self._led.toggle()

            if self._on_beat is not None:
                self._on_beat()

        elif self._above_threshold and sample < low_threshold:
            self._above_threshold = False

    def _recalculate_bpm(self) -> None:
        """Recompute BPM from the rolling average of the most recent beat intervals.

        Only updates self._current_bpm if the result is within the
        physiologically valid range.
        """
        n = min(len(self._intervals_ms), config.BEAT_AVERAGE_COUNT)
        recent = self._intervals_ms[-n:]
        mean_interval = sum(recent) / len(recent)
        bpm = int(60_000 / mean_interval)
        if config.MIN_BPM <= bpm <= config.MAX_BPM:
            self._current_bpm = bpm
