"""Shared default TNC address for open_mobitnc scripts.

All the entry-point scripts (connect_test.py, kiss_bridge.py,
start_radio.sh) fall back to this when no device address is given on the
command line, so day-to-day use doesn't require typing the MAC each
time. Find it with scan_radio.sh, then either set the default here or
override per-invocation with the MOBITNC_ADDR environment variable.
"""

import os

DEFAULT_DEVICE_UUID = os.environ.get("MOBITNC_ADDR", "")
