"""Connect to the Mobilinkd TNC over RFCOMM and confirm the link is up.

Usage:
    python scripts/connect_test.py [XX:XX:XX:XX:XX:XX] [channel]

device address defaults to tnc_config.DEFAULT_DEVICE_UUID (override via
the MOBITNC_ADDR env var) if omitted. channel defaults to auto-discovery
(see rfcomm_connect.py) if omitted.
"""

import sys

from rfcomm_connect import connect_rfcomm, log
from tnc_config import DEFAULT_DEVICE_UUID


def main() -> None:
    addr = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DEVICE_UUID
    if not addr:
        log(f"Usage: {sys.argv[0]} <XX:XX:XX:XX:XX:XX> [channel]")
        sys.exit(1)
    channel = int(sys.argv[2]) if len(sys.argv) > 2 else None

    sock = connect_rfcomm(addr, channel)
    sock.close()
    print("OK: RFCOMM link to the TNC established and closed cleanly.")


if __name__ == "__main__":
    main()
