# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-09-12

### Added

- Standalone Raspberry Pi Pico W heart-rate and HRV monitor application.
- MicroPython startup flow with `boot.py`, `main.py`, hardware initialization, splash display, optional WiFi setup, optional MQTT setup, and continuous application loop.
- 250 Hz PPG sampling through the RP2040 PIO timer and interrupt-safe FIFO buffering.
- Real-time PPG signal processing with adaptive amplitude envelope tracking, threshold-based beat detection, hysteresis, refractory-period filtering, and rolling BPM calculation.
- Live heart-rate measurement mode with scrolling waveform display and BPM updates.
- PWM-controlled heartbeat LED indicator on GP22.
- Local 30-second HRV analysis with mean PPI, mean HR, RMSSD, and SDNN metrics.
- RMSSD-based heart-state interpretation using age- and gender-specific Nunan et al. reference thresholds.
- Heart-state labels for Excellent, Good, Normal, Stressed, and Fatigued results.
- Kubios Cloud analysis workflow through the MQTT proxy, including SNS and PNS autonomic index display.
- Local measurement history stored as JSON with newest-first ordering, timestamps, patient names, and a configurable 10-record limit.
- OLED UI for splash, WiFi connection status, main menu, measurement instructions, live measurement, HRV collection, result screens, history browsing, Kubios analysis, settings, reset confirmation, and error messages.
- Graphical main menu with bitmap icons and scrollbar.
- MONO_HLSB bitmap icon set for heart, waveform, clock, cloud, gear, and splash artwork.
- 21-state menu controller with explicit state handlers and non-blocking tick-based execution.
- Rotary encoder navigation on GP10/GP11 with push-to-select on GP12.
- Fallback support for three tactile navigation buttons on GP7, GP9, and GP8.
- First-boot profile setup with name entry, optional age, and optional gender.
- Persistent user profile storage for name, age, gender, and database patient ID.
- Settings menu support for editing name, age, and gender independently.
- Full device reset workflow for clearing profile and history data.
- WiFi connection support with timeout-based startup behavior and offline fallback.
- NTP time synchronization for local timestamp generation when WiFi is available.
- MQTT heart-rate publishing to `iPulse/heart_rate`.
- MQTT HRV publishing to `iPulse/hrv`.
- MQTT device registration through `database/devices/add`.
- MQTT database patient registration through `database/patients/add` and `database/response`.
- MQTT database record publishing through `database/records/add`, including optional patient ID and Kubios SNS/PNS values.
- Kubios request and response handling through `kubios/request` and `kubios/response`, matched by device MAC address.
- Centralized configuration for hardware pins, display settings, sampling constants, HRV thresholds, WiFi, MQTT, database topics, timeouts, and UI timing.
- Bundled MicroPython support libraries for FIFO buffering, PWM LED control, PIO timer support, SSD1306 display control, and lightweight MQTT.
- `upload.sh` deployment script for creating device directories, uploading all project files with `mpremote`, and resetting the Pico W.
- Manual `mpremote` deployment instructions in the README.
- `project.toml` with project metadata, MicroPython deployment manifest, target directories, and PC-side test commands.
- Pytest unit test suite for profile persistence, HRV interpretation, HRV metric calculation, and history persistence, using stubbed `config`/`utime` modules so it runs on any Python 3 install with no hardware.
- Performance benchmark suite (`tests/test_performance_benchmark.py`) using `pytest-benchmark`, covering the two pure-logic hot paths: `HeartRateSensor` per-sample processing (envelope tracking and beat detection) and `HRVAnalyzer.compute()`. Each benchmark asserts against a time budget derived from existing project constants (`config.SAMPLE_RATE_HZ` and the main loop's tick cadence) rather than an arbitrary threshold.
- Robot Framework acceptance suite (`tests/robot/`) driving the `MenuController` state machine end to end for the HR measurement and local HRV analysis flows, with hardware I/O stubbed and the network faked as offline. A system-level layer on top of the unit and benchmark tests, verifying real state transitions without requiring the physical device.
- `tests/support/`, hardware stubs and a synthetic PPG waveform generator shared by the performance and acceptance suites, so both fake the same boundary and exercise the same signal model.
- `requirements-dev.txt` listing `pytest`, `pytest-benchmark`, and `robotframework` for running the dev test suites.
- GitHub Actions workflow running the full test suite (unit, benchmark, acceptance) on every push and pull request to `main`.
- README covering features, hardware, wiring, project structure, configuration, deployment, usage, signal processing, HRV metrics, interpretation, Kubios integration, MQTT topics, tests, and architecture.
- Changelog following Keep a Changelog and semantic versioning conventions.

[Unreleased]: https://github.com/DevBytAmir/iPulse/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/DevBytAmir/iPulse/releases/tag/v1.0.0