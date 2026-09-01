"""Scan for nearby BLE devices to find the Mobilinkd TNC's address.

Run this on the machine with the Bluetooth adapter (the one the TNC is
paired with), inside a venv with bleak installed:

    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python scripts/scan_ble.py
"""

import asyncio

from bleak import BleakScanner


async def main() -> None:
    print("Scanning for BLE devices (10s)...")
    devices = await BleakScanner.discover(timeout=10.0)

    if not devices:
        print("No BLE devices found.")
        return

    for d in sorted(devices, key=lambda d: d.name or ""):
        print(f"{d.address}  {d.name or '(unknown name)'}")


if __name__ == "__main__":
    asyncio.run(main())
