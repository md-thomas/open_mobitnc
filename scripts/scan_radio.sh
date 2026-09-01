#!/bin/bash
# Scan for nearby BLE devices and highlight the Mobilinkd TNC, so you can
# confirm it's powered on and in range before starting the bridge.
#
# Usage:
#   scripts/scan_radio.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

OUTPUT="$(.venv/bin/python scripts/scan_ble.py)"
echo "$OUTPUT"

if echo "$OUTPUT" | grep -qi "mobilinkd\|TNC3\|TNC4"; then
    echo
    echo "Found: $(echo "$OUTPUT" | grep -i "mobilinkd\|TNC3\|TNC4")"
else
    echo
    echo "TNC not found -- is it powered on and in range?"
    exit 1
fi
