"""Shared RFCOMM connect helper for Mobilinkd TNC scripts.

Unlike the UV-Pro, the TNC speaks real KISS framing directly over its
classic-Bluetooth SPP link -- there's no application protocol handshake
to probe with, just a plain serial socket. The only unknown is which
RFCOMM channel that SPP service is on: the TNC3 fixes it at 6, the TNC4
at 1 (see the TNC3/TNC4 user guides). Rather than hardcode either, ask
the device's own SDP record first (works for both models unmodified),
and fall back to trying the known defaults if SDP querying isn't
available or doesn't answer.
"""

import re
import socket
import subprocess
import sys

KNOWN_CHANNELS = (1, 6)  # TNC4 default, then TNC3 default
CONNECT_TIMEOUT_SECONDS = 5.0
SDP_TIMEOUT_SECONDS = 10.0


def log(*args) -> None:
    print(*args, file=sys.stderr)


def discover_channel(addr: str) -> int | None:
    """Ask the device's SDP record for its Serial Port channel via
    sdptool (part of bluez-utils). Returns None if sdptool isn't
    installed, times out, or the device has no SP record to query."""
    try:
        result = subprocess.run(
            ["sdptool", "search", "--bdaddr", addr, "SP"],
            capture_output=True, text=True, timeout=SDP_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"Channel:\s*(\d+)", result.stdout)
    return int(match.group(1)) if match else None


def connect_rfcomm(addr: str, channel: int | None = None) -> socket.socket:
    """Open a connected RFCOMM socket to the TNC. Tries `channel` if
    given, otherwise the SDP-reported channel, otherwise both known
    defaults in turn."""
    if channel is not None:
        channels = [channel]
    else:
        sdp_channel = discover_channel(addr)
        if sdp_channel is not None:
            log(f"SDP reports Serial Port on channel {sdp_channel}")
            channels = [sdp_channel]
        else:
            log("SDP lookup unavailable/empty; trying known default "
                f"channels {list(KNOWN_CHANNELS)}...")
            channels = list(KNOWN_CHANNELS)

    last_error: OSError | None = None
    for ch in channels:
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.settimeout(CONNECT_TIMEOUT_SECONDS)
        try:
            s.connect((addr, ch))
            s.settimeout(None)
            log(f"Connected to {addr} on RFCOMM channel {ch}")
            return s
        except OSError as e:
            last_error = e
            s.close()

    raise RuntimeError(
        f"Couldn't open an RFCOMM connection to {addr} on channel(s) "
        f"{channels}: {last_error}. Is the TNC on, in range, and paired?"
    ) from last_error
