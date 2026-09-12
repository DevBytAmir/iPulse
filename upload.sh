#!/bin/bash
# upload.sh -- Deploy iPulse to Raspberry Pi Pico W via mpremote
set -e

echo "Creating directories..."
mpremote mkdir lib 2>/dev/null || true
mpremote mkdir lib/umqtt 2>/dev/null || true
mpremote mkdir src 2>/dev/null || true

echo "Uploading lib files..."
mpremote cp lib/fifo.py      :lib/fifo.py
mpremote cp lib/led.py       :lib/led.py
mpremote cp lib/piotimer.py  :lib/piotimer.py
mpremote cp lib/ssd1306.py   :lib/ssd1306.py
mpremote cp lib/umqtt/simple.py :lib/umqtt/simple.py

echo "Uploading src files..."
mpremote cp src/config.py           :src/config.py
mpremote cp src/icons.py            :src/icons.py
mpremote cp src/profile_manager.py  :src/profile_manager.py
mpremote cp src/hrv_interpreter.py  :src/hrv_interpreter.py
mpremote cp src/display_manager.py  :src/display_manager.py
mpremote cp src/heart_rate_sensor.py :src/heart_rate_sensor.py
mpremote cp src/hrv_analysis.py     :src/hrv_analysis.py
mpremote cp src/history_manager.py  :src/history_manager.py
mpremote cp src/network_manager.py  :src/network_manager.py
mpremote cp src/kubios_client.py    :src/kubios_client.py
mpremote cp src/menu_controller.py  :src/menu_controller.py

echo "Uploading root files..."
mpremote cp boot.py :boot.py
mpremote cp main.py :main.py

echo "Resetting device..."
mpremote reset

echo "Done."
