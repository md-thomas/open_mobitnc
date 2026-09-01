"""Shared helpers for open_mobitnc's kiss_gui.py: remembered-device
persistence, BLE scan-line parsing, and OS-level process/Bluetooth
status checks.
"""

import json
import re
import subprocess
from pathlib import Path

DEVICE_STATE_PATH = Path.home() / ".cache" / "mobitnc-gui-device.json"
MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\s*(.*)$")


def pgrep(pattern: str) -> list[int]:
    try:
        out = subprocess.run(
            ["pgrep", "-f", pattern], capture_output=True, text=True
        ).stdout
        return [int(p) for p in out.split()]
    except Exception:
        return []


def bt_connected(addr: str) -> bool:
    try:
        out = subprocess.run(
            ["bluetoothctl", "info", addr], capture_output=True, text=True, timeout=5
        ).stdout
        return "Connected: yes" in out
    except Exception:
        return False


def load_remembered_device() -> tuple[str, str] | None:
    try:
        data = json.loads(DEVICE_STATE_PATH.read_text())
        addr = data.get("address", "")
        name = data.get("name") or addr
        if MAC_RE.match(addr):
            return name, addr
    except Exception:
        pass
    return None


def save_remembered_device(name: str, addr: str) -> None:
    try:
        DEVICE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEVICE_STATE_PATH.write_text(json.dumps({"name": name, "address": addr}))
    except Exception:
        pass


def disambiguate(devices: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Append the address to any label (device name) shared by more than
    one scanned device, so a combobox never shows duplicate entries."""
    counts: dict[str, int] = {}
    for label, _ in devices:
        counts[label] = counts.get(label, 0) + 1
    return [
        (f"{label} ({addr})" if counts[label] > 1 else label, addr)
        for label, addr in devices
    ]


def make_textbox_readonly(box) -> None:
    """Keep a text widget (e.g. CTkTextbox) effectively read-only while
    still letting the user select and copy its text.

    Using state="disabled" for this is tempting but wrong: on the
    underlying tkinter.Text widget it inconsistently blocks mouse
    selection and Ctrl+C copy too, not just typing (Tk-version/platform
    dependent). Instead, leave state="normal" always (so selection/copy
    work normally) and swallow keystrokes that would edit the content,
    letting Control-combos (copy, select-all, ...) and pure navigation
    keys through.
    """
    def _on_key(event):
        if event.state & 0x4:  # Control (or Command on some platforms) held
            return None
        if event.keysym in (
            "Left", "Right", "Up", "Down", "Home", "End",
            "Prior", "Next", "Shift_L", "Shift_R", "Tab",
        ):
            return None
        return "break"

    box.bind("<Key>", _on_key)
