# open_mobitnc

Interface for the Mobilinkd TNC (TNC3/TNC4), bridging its Bluetooth KISS
link to Linux's AX.25 stack so tools like Pat (Winlink) can use it as a
packet TNC.

Unlike some Bluetooth TNCs, the Mobilinkd TNC speaks real KISS framing
directly over its classic-Bluetooth SPP serial link -- no vendor command
protocol to translate, just bytes relayed between a pty and the RFCOMM
socket.

## Install/Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Find the TNC's Bluetooth address with `scripts/scan_radio.sh`, then
either pass it to the scripts below or set the `MOBITNC_ADDR`
environment variable so you don't have to type it each time.

One-time AX.25 setup:

```bash
sudo apt install ax25-tools ax25-apps
echo "wl2k    N0CALL-1 1200    255     2       Mobilinkd TNC" | sudo tee -a /etc/ax25/axports
```

(Replace `N0CALL` with your callsign.) Optionally run
`sudo scripts/install_sudo_rules.sh` once so `start_radio.sh`/
`stop_radio.sh` don't prompt for a sudo password every time.

## Usage

```bash
scripts/scan_radio.sh              # confirm the TNC is powered on and in range
python scripts/connect_test.py     # confirm an RFCOMM link can be established
scripts/start_radio.sh             # start the bridge and attach it as ax0
scripts/start_pat.sh               # pat http, at http://localhost:8080
scripts/stop_pat.sh
scripts/stop_radio.sh
```

`start_radio.sh` runs `kiss_bridge.py` in the background (log at
`~/.cache/mobitnc-bridge.log`, pid at `~/.cache/mobitnc-bridge.pid`),
waits for the KISS pty to appear, then runs `sudo kissattach` in the
foreground so you only enter your password once.
