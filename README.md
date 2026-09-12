<div align="center">

# iPulse

### Heart rate and HRV monitor for the Raspberry Pi Pico W

[![Release](https://img.shields.io/github/v/release/DevBytAmir/iPulse?style=for-the-badge&color=FF8C00&labelColor=1a1a1a)](https://github.com/DevBytAmir/iPulse/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-3DDC97?style=for-the-badge&labelColor=1a1a1a)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/DevBytAmir/iPulse/tests.yml?branch=main&style=for-the-badge&label=Tests&labelColor=1a1a1a)](https://github.com/DevBytAmir/iPulse/actions/workflows/tests.yml)
<br/>
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%20Pico%20W-455A64?style=for-the-badge&labelColor=1a1a1a)](#hardware-requirements)
[![Runtime](https://img.shields.io/badge/Runtime-MicroPython-2f6f9f?style=for-the-badge&labelColor=1a1a1a)](#deployment)
[![Sampling](https://img.shields.io/badge/Sampling-250%20Hz-1f7a5a?style=for-the-badge&labelColor=1a1a1a)](#signal-processing)

A standalone heart rate and Heart Rate Variability (HRV) monitor built on the Raspberry Pi Pico W. iPulse samples a PPG sensor at 250 Hz using the RP2040 PIO hardware timer, detects heartbeats in real time, and displays a live waveform on an SSD1306 OLED display. Results are classified against clinical reference data and optionally uploaded to an MQTT broker or Kubios Cloud for advanced analysis.

</div>

> **Not a medical device.** iPulse is a personal/educational hardware project. It is not certified, cleared, or intended for medical diagnosis, treatment, or monitoring of any health condition. Readings should not be relied on for clinical decisions.


## Table of Contents

1. [Features](#features)
2. [Hardware Requirements](#hardware-requirements)
3. [Wiring](#wiring)
4. [Project Structure](#project-structure)
5. [Configuration](#configuration)
6. [Deployment](#deployment)
7. [Usage](#usage)
8. [Signal Processing](#signal-processing)
9. [HRV Metrics](#hrv-metrics)
10. [Heart State Interpretation](#heart-state-interpretation)
11. [Kubios Cloud Integration](#kubios-cloud-integration)
12. [Network & MQTT](#network--mqtt)
13. [Testing](#testing)
14. [Architecture Notes](#architecture-notes)


## Features

| Level | Feature |
|-------|---------|
| 1 | Standalone operation, no PC required after deployment |
| 1 | PIO timer + FIFO interrupt-driven PPG sampling at 250 Hz |
| 1 | LED heartbeat indicator (GP22, PWM-dimmable) |
| 1 | Live BPM display updated every second |
| 2 | Graphical OLED menu with bitmap icons and scrollbar |
| 2 | Rotary encoder navigation with push-to-select, plus three-button fallback |
| 2 | 30-second local HRV analysis (mean PPI, mean HR, RMSSD, SDNN) |
| 2 | WiFi connectivity and MQTT publishing |
| 3 | Five-option menu: Measure HR, HRV Analysis, History, Kubios, Settings |
| 3 | Measurement history stored in JSON with NTP timestamps (10 entries) |
| 3 | Patient registration and record publishing through MQTT database topics |
| 3 | Kubios Cloud integration with SNS and PNS autonomic indices |
| 4 | Live scrolling PPG waveform during heart-rate measurement |
| 4 | Patient name included in heart-rate, HRV, history, and database workflows |
| 5 | Animated fade-in splash screen with MONO_HLSB bitmap icons |
| 5 | User profile (name, age, gender, patient ID) stored on device |
| 5 | Heart state classification: Excellent / Good / Normal / Stressed / Fatigued |
| 5 | Settings menu with profile editing by field and full device reset |


## Hardware Requirements

| Component | Specification |
|-----------|---------------|
| Raspberry Pi Pico W | MicroPython firmware ≥ 1.20 |
| PPG sensor | Analog output (e.g. Crowtail Pulse Sensor) |
| SSD1306 OLED | 128 × 64 pixels, I2C interface |
| LED | Any colour; requires external 220 Ω current-limiting resistor |
| Push buttons | 3 × normally-open momentary; internal pull-ups used |
| Rotary encoder | Quadrature A/B outputs with integrated push switch; internal pull-ups used |


## Wiring

```
Pico W Pin    Signal             Connected to
-----------   ----------------   --------------------------------
GP26 (ADC0)   PPG analog input   PPG sensor signal output
GP14 (SDA)    I2C data           OLED SDA
GP15 (SCL)    I2C clock          OLED SCL
GP7           Button UP          Push button → GND
GP9           Button DOWN        Push button → GND
GP8           Button SELECT      Push button → GND
GP10          Rotary A           Encoder A → GND switching
GP11          Rotary B           Encoder B → GND switching
GP12          Rotary PUSH        Encoder push switch → GND
GP22          LED heartbeat      LED anode (cathode → 220 Ω → GND)
3V3           VCC                OLED VCC, PPG sensor VCC
GND           Ground             Common ground
```

> All pin assignments can be changed in `src/config.py` without modifying any other file.


## Project Structure

```
iPulse/
├── boot.py                       MicroPython early-boot (adds /src to sys.path)
├── main.py                       Application entry point (Application class)
├── upload.sh                     One-command deployment script (mpremote)
├── requirements-dev.txt          Dev dependencies (pytest, pytest-benchmark, robotframework)
├── project.toml                  Project metadata and mpremote deploy manifest
├── CHANGELOG.md                  Release changelog
│
├── src/
│   ├── config.py                 All constants: pins, timing, credentials
│   ├── icons.py                  MONO_HLSB bitmap data (heart, wave, clock, cloud, gear, banana)
│   ├── profile_manager.py        Persistent name/age/gender/patient ID profile (profile.json)
│   ├── hrv_interpreter.py        RMSSD heart state classifier (Nunan 2010 norms)
│   ├── display_manager.py        All OLED screen rendering (23 screen methods)
│   ├── heart_rate_sensor.py      PPG acquisition and beat detection
│   ├── hrv_analysis.py           Local HRV calculations (mean PPI, mean HR, RMSSD, SDNN)
│   ├── history_manager.py        JSON measurement history, up to 10 entries
│   ├── network_manager.py        WiFi, NTP, MQTT, Kubios proxy, database API
│   ├── kubios_client.py          Kubios Cloud MQTT proxy wrapper
│   └── menu_controller.py        Application state machine, 21 states
│
├── lib/
│   ├── fifo.py                   Interrupt-safe circular buffer (ISR ↔ main loop)
│   ├── led.py                    PWM-dimmable LED driver
│   ├── piotimer.py               RP2040 PIO-based hardware timer (250 Hz)
│   ├── ssd1306.py                SSD1306 OLED driver (I2C + SPI)
│   └── umqtt/
│       └── simple.py             Lightweight MQTT client for MicroPython
│
├── tests/
│   ├── test_profile_manager.py       Unit tests for ProfileManager
│   ├── test_hrv_interpreter.py       Unit tests for HRVInterpreter
│   ├── test_hrv_analyzer.py          Unit tests for HRVAnalyzer
│   ├── test_history_manager.py       Unit tests for HistoryManager
│   ├── test_performance_benchmark.py Timing-budget benchmarks for the signal-processing hot path
│   ├── support/                      Hardware stubs and synthetic PPG generator shared across suites
│   └── robot/                        Robot Framework acceptance suite for the HR/HRV flows
│
└── .github/workflows/tests.yml   CI: runs the full test suite on every push and pull request
```


## Configuration

Edit `src/config.py` before deploying. Site-specific values:

```python
# WiFi credentials
WIFI_SSID     = "your_network_name"
WIFI_PASSWORD = "your_password"

# MQTT broker (local IP of your broker)
MQTT_BROKER   = "192.168.x.x"

# Device identity used in database registration
DEVICE_NAME   = "iPulse"
```

Patient identity is collected on device during first boot and stored in `profile.json`, together with optional age, gender, and database patient ID. All hardware pin numbers, sampling rate, HRV thresholds, MQTT topics, timeout values, and timing constants are centrally controlled from `config.py` using named constants.


## Deployment

Connect the Pico W via USB, then run:

```bash
./upload.sh
```

This creates the required directories, uploads all files in the correct order, and resets the device. Requires [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html) installed on the host.


## Usage

### Input Reference

All navigation is available through the rotary encoder. The three tactile buttons provide the same controls as a fallback.

| Input | Context | Action |
|-------|---------|--------|
| Rotary clockwise | Menus and selectors | Move cursor down / next item / increase where applicable |
| Rotary counter-clockwise | Menus and selectors | Move cursor up / previous item / back where applicable |
| Rotary push | Menus and prompts | Confirm / enter / start |
| UP button | Menus and prompts | Move up / go back / cancel |
| DOWN button | Menus and prompts | Move down / next item |
| SELECT button | Menus and prompts | Confirm / enter / start |
| Rotary push, SELECT, or UP | Heart-rate measurement | Stop measurement |
| UP button or rotary counter-clockwise | HRV/Kubios collection | Cancel collection |
| Rotary push, SELECT, or UP | Results screen | Return to main menu |

During name entry, the rotary encoder is the primary control: turn to scroll through `A-Z`, space, `DEL`, and `OK`; push to add the highlighted character or select the command.

### Main Menu

Navigate with the rotary encoder or UP/DOWN buttons. A scrollbar on the right indicates when more items are available below.

| # | Option | Description |
|---|--------|-------------|
| 1 | Measure HR | Continuous heart rate with live scrolling PPG waveform |
| 2 | HRV Analysis | 30-second collection → local metrics + heart state |
| 3 | History | Browse up to 10 past HRV measurements |
| 4 | Kubios | 30-second collection → cloud analysis with SNS/PNS indices |
| 5 | Settings | Edit profile or perform full device reset |

### First Boot

On first power-up (or after a full reset), the device prompts for a user profile:

1. **Name screen**: rotate to select letters, space, `DEL`, or `OK`; press the encoder or SELECT to add a character or confirm. Names are stored up to 20 characters.
2. **Age screen**: rotate or use UP/DOWN to scroll from 15 to 99. Select the top "Skip" item to leave age and gender unset. Press the encoder or SELECT to confirm.
3. **Gender screen**: rotate or press DOWN to toggle Male/Female. Press the encoder or SELECT to confirm. UP skips gender while preserving the saved name and age.

The profile is used for MQTT payloads, history labels, database patient registration, and personalised heart state interpretation. The device works without age or gender, using population-average reference values for HRV classification when those fields are missing.


## Signal Processing

All signal processing runs in the main loop after draining the interrupt-driven FIFO. No computation occurs inside the ISR.

### Adaptive Amplitude Envelope

The peak-to-peak signal range is tracked continuously with a leaky max/min follower. The decay constant α = 0.9995 per sample at 250 Hz gives a time constant of τ = 1 / ((1 − α) × f_s) = 1 / (0.0005 × 250) **≈ 8 seconds**, which follows slow baseline drift without suppressing heartbeat peaks.

```
sig_max[n] = sample[n]                               if sample[n] > sig_max[n-1]
           = α·sig_max[n-1] + (1-α)·sample[n]       otherwise

sig_min[n] = sample[n]                               if sample[n] < sig_min[n-1]
           = α·sig_min[n-1] + (1-α)·sample[n]       otherwise

where α = 0.9995,  f_s = 250 Hz
```

The envelope is considered valid only when `Δ = sig_max − sig_min > 500` (raw ADC units). Below this threshold, no finger is assumed to be present.

### Beat Detection

A systolic peak is detected using a dual-threshold (hysteresis) comparator plus a hard refractory period:

```
Δ              = sig_max − sig_min          (signal amplitude range)
high_threshold = sig_min + Δ × 0.65        (rising-edge trigger)
low_threshold  = sig_min + Δ × 0.455       (falling-edge reset = 0.65 × 0.7)

Refractory period = ⌊60,000 / 220⌋ = 272 ms  (enforces MAX_BPM = 220)
```

A beat is registered when:
1. The signal rises **above** `high_threshold`, and
2. At least 272 ms have elapsed since the previous beat.

The detector resets only when the signal falls **below** `low_threshold`, preventing a single broad systolic peak from being counted twice.

### Rolling BPM

Each confirmed beat records the time elapsed since the previous beat as a peak-to-peak interval (PPI):

```
PPI_n = t_n − t_{n-1}                  (ms between consecutive beat timestamps)
BPM   = 60,000 / mean(PPI_{last 6})    (rolling average over BEAT_AVERAGE_COUNT = 6)
```

The result is accepted only when `30 ≤ BPM ≤ 220`.

### Waveform Pixel Mapping

The live PPG waveform is scaled to the 100 × 40-pixel display strip (y = 16 to y = 56):

```
display_range = y_bottom − y_top = 56 − 16 = 40 pixels
y = y_bottom − ⌊(sample − sig_min) × display_range / Δ⌋
  = 56 − ⌊(sample − sig_min) × 40 / Δ⌋

clamped to [16, 56]
```

When no finger is detected (Δ < 500), all samples are mapped to the midpoint y = 36.


## HRV Metrics

All HRV calculations run locally on the Pico W with no cloud dependency. Let **N** denote the number of PPI values collected.

| Metric | Formula | Description |
|--------|---------|-------------|
| Mean PPI | PPĪ = (1/N) Σ PPI_i | Arithmetic mean of all PPI values (ms) |
| Mean HR | HR = 60,000 / PPĪ | Mean heart rate (BPM) |
| RMSSD | √( (1/(N−1)) Σ (PPI_{i+1} − PPI_i)² ) | Root mean square of successive differences, the primary short-term variability and stress indicator |
| SDNN | √( (1/N) Σ (PPI_i − PPĪ)² ) | Standard deviation of all PPI intervals, overall variability |

```
RMSSD = sqrt( mean( (PPI[1]-PPI[0])², (PPI[2]-PPI[1])², …, (PPI[N-1]-PPI[N-2])² ) )

SDNN  = sqrt( mean( (PPI[0]-PPĪ)², (PPI[1]-PPĪ)², …, (PPI[N-1]-PPĪ)² ) )
```

A minimum of **N = 20** PPI values (~20 seconds at 60 BPM) is required for a valid result. The collection window is 30 seconds.

---

## Heart State Interpretation

After an HRV Analysis, the results screen displays a heart state label derived from RMSSD using age- and gender-specific reference thresholds from **Nunan et al. (2010)** normative database.

| Label | Meaning |
|-------|---------|
| **Excellent** | Very high HRV, strong recovery and parasympathetic activity |
| **Good** | Above-average HRV, well-rested and low physiological stress |
| **Normal** | HRV within the expected range for your age and gender |
| **Stressed** | Below-average HRV, possible fatigue or elevated sympathetic activity |
| **Fatigued** | Low HRV, consider rest; may indicate overtraining or illness |

Thresholds are personalised when age and gender are set. Without age and gender, the device falls back to 36–45 year male population averages.

### RMSSD Reference Thresholds

| Age | Gender | Fatigued | Stressed | Normal | Good | Excellent |
|-----|--------|----------|----------|--------|------|-----------|
| 15–25 | Male | < 20 ms | 20–34 | 35–54 | 55–79 | ≥ 80 |
| 15–25 | Female | < 25 ms | 25–39 | 40–59 | 60–84 | ≥ 85 |
| 26–35 | Male | < 18 ms | 18–29 | 30–49 | 50–74 | ≥ 75 |
| 26–35 | Female | < 23 ms | 23–34 | 35–54 | 55–79 | ≥ 80 |
| 36–45 | Male | < 15 ms | 15–24 | 25–44 | 45–69 | ≥ 70 |
| 36–45 | Female | < 20 ms | 20–29 | 30–49 | 50–74 | ≥ 75 |
| 46–60 | Male | < 12 ms | 12–19 | 20–34 | 35–54 | ≥ 55 |
| 46–60 | Female | < 17 ms | 17–24 | 25–39 | 40–59 | ≥ 60 |
| 61+ | Male | < 10 ms | 10–16 | 17–29 | 30–44 | ≥ 45 |
| 61+ | Female | < 15 ms | 15–21 | 22–34 | 35–49 | ≥ 50 |

*Source: Nunan D, Sandercock GR, Brodie DA. A quantitative systematic review of normal values for short-term heart rate variability in healthy adults. Pacing Clin Electrophysiol. 2010.*


## Kubios Cloud Integration

The Kubios option performs a full frequency-domain analysis via a broker-hosted MQTT proxy:

1. Collects 30 seconds of PPI data.
2. Publishes a request to `kubios/request` (JSON with MAC address, PPI array, analysis type).
3. Waits up to 30 seconds for a response on `kubios/response` (MAC-matched).
4. Displays: mean HR, mean PPI, RMSSD, SDNN, **SNS index**, **PNS index**.
5. Saves the result to local history.

**SNS index** (Sympathetic Nervous System): higher values indicate more stress or activation.
**PNS index** (Parasympathetic Nervous System): higher values indicate more relaxation or recovery.

Requires an active WiFi and MQTT connection. If the request times out, the device shows an error and returns to the main menu without losing data.


## Network & MQTT

### Topics published by the device

| Topic | Payload | When |
|-------|---------|------|
| `iPulse/heart_rate` | `{"patient": "...", "bpm": N}` | Every BPM update during HR measurement |
| `iPulse/hrv` | `{"patient": "...", "mean_hr": N, ...}` | After each HRV analysis |
| `kubios/request` | `{"mac": "...", "type": "RRI", "data": [...]}` | Kubios analysis request |
| `database/devices/add` | `{"mac": "...", "device_name": "iPulse"}` | Once on startup |
| `database/patients/add` | `{"mac": "...", "patient_name": "..."}` | When a named profile is saved while MQTT is connected |
| `database/records/add` | `{"mac": "...", "timestamp": N, "mean_hr": N, ...}` | After HRV or Kubios analysis |

### Topics consumed by the device

| Topic | Payload | When |
|-------|---------|------|
| `kubios/response` | Kubios proxy response matched by MAC address | During Kubios analysis |
| `database/response` | Database response matched by MAC address | During patient registration |


## Testing

Every test suite runs on a PC with no hardware attached, using stubbed `machine`, `utime`, and `config` modules.

```bash
pip install -r requirements-dev.txt
```

### Unit tests

Pure-logic modules covered with pytest:

```bash
pytest tests/test_profile_manager.py tests/test_hrv_interpreter.py tests/test_hrv_analyzer.py tests/test_history_manager.py
```

| Test file | What it covers |
|-----------|---------------|
| `test_profile_manager.py` | Save/load/reset, boundary ages, None fields, corrupt/empty JSON, multi-instance persistence |
| `test_hrv_interpreter.py` | All 10 age/gender bands, every threshold boundary, fallback paths, edge RMSSD values |
| `test_hrv_analyzer.py` | RMSSD/SDNN formulas, mean HR, rounding, minimum count enforcement |
| `test_history_manager.py` | Newest-first ordering, cap enforcement, sns/pns passthrough, persistence, corrupt file handling |

### Performance benchmarks

```bash
pytest tests/test_performance_benchmark.py -v
```

Benchmarks the signal-processing hot path (`HeartRateSensor` per-sample processing and `HRVAnalyzer.compute()`) against time budgets derived from `config.SAMPLE_RATE_HZ` and the main loop's tick cadence, not arbitrary numbers.

### Acceptance tests

```bash
robot tests/robot/
```

Drives the full `MenuController` state machine through the HR measurement and local HRV analysis flows with hardware stubbed, verifying real state transitions end to end. See `tests/robot/AppLibrary.py` for the keyword library.

---

## Architecture Notes

### Interrupt-driven sampling

The PIO timer ISR fires at exactly 250 Hz. The handler does only two things: reads the ADC and calls `FIFO.put()`. All signal processing (envelope tracking, beat detection, BPM calculation) happens in the main loop by draining the FIFO.

### Non-blocking main loop

`MenuController.tick()` is called every ~4 ms. No state handler may block. Network operations use timeout-based polling. Display refreshes are throttled (1 s for BPM, 200 ms for spinners).

### State machine

21 discrete states in `MenuController._State`. Every state has a registered handler. Transitions are explicit and every state has a path back to `MAIN_MENU`, no dead ends.

### Graceful degradation

WiFi and MQTT are optional. The device operates fully offline for HR measurement, local HRV analysis, and history browsing. Network failures are non-fatal and silently skipped.

### Code conventions

- All constants in `config.py`, no magic numbers elsewhere.
- All state in instance attributes, no module-level variables.
- Private methods and attributes prefixed with `_`.
- ISR handlers contain only flag writes or FIFO puts, no allocation, no I/O.

## License

This project is licensed under the **MIT License**.  
See the [LICENSE](LICENSE) file for details.