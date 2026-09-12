"""
boot.py -- Early boot script for iPulse.

MicroPython executes this file before main.py on every power-on or reset.
Adds /src to sys.path so that all application modules located in that
directory can be imported without qualification from main.py and from one
another.
"""

import sys
import gc

sys.path.insert(0, "/src")
gc.collect()
