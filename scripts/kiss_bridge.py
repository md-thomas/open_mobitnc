"""Bridge the Mobilinkd TNC to a standard KISS pty, so Linux's AX.25
stack (and anything built on it, e.g. Pat) can use it as a packet TNC
over Bluetooth.

Unlike the UV-Pro, the TNC already speaks real KISS framing directly on
its RFCOMM serial link -- there's no fragmentation/reassembly or command
protocol underneath to translate, just raw bytes both ways. This script
relays them, exposing a pty to kissattach/Pat the same way open_uvpro's
bridge does.

Usage:
    python scripts/kiss_bridge.py [XX:XX:XX:XX:XX:XX] [pty_symlink_path] [channel]

device address defaults to tnc_config.DEFAULT_DEVICE_UUID (override via
the MOBITNC_ADDR env var) if omitted.

The pty symlink defaults to ~/.cache, not /tmp: kissattach runs as root
via sudo, and the kernel's fs.protected_symlinks hardening (on by
default) refuses to let root follow a symlink owned by another user
sitting in a sticky world-writable directory like /tmp -- it fails with
"open: Permission denied" even though the file permissions look fine.
~/.cache isn't sticky/world-writable, so that restriction never triggers.

Then, in another terminal (see NOTES.md for the one-time axports setup):
    sudo kissattach ~/.cache/mobitnc-kisstnc wl2k
    pat connect ax25:///SOME-CALL

If the RFCOMM link drops mid-session, the pty/symlink stay put; only the
RFCOMM connection is retried (with backoff), so kissattach doesn't need
to be re-run -- it just sees a stall while we reconnect.
"""

import asyncio
import errno
import os
import pty
import signal
import sys
import termios

from rfcomm_connect import connect_rfcomm, log
from tnc_config import DEFAULT_DEVICE_UUID

DEFAULT_PTY_PATH = os.path.expanduser("~/.cache/mobitnc-kisstnc")
RECONNECT_BACKOFF_SECONDS = 15


def make_pty(symlink_path: str) -> int:
    master_fd, slave_fd = pty.openpty()
    slave_path = os.ttyname(slave_fd)

    # Raw mode: no echo, no line editing, no CR/NL translation -- KISS is
    # a binary framing and must pass through untouched.
    tty_attrs = termios.tcgetattr(slave_fd)
    tty_attrs[3] &= ~(termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN)
    tty_attrs[0] &= ~(termios.IXON | termios.IXOFF | termios.ICRNL | termios.INLCR)
    tty_attrs[1] &= ~termios.OPOST
    termios.tcsetattr(slave_fd, termios.TCSANOW, tty_attrs)
    os.close(slave_fd)

    os.makedirs(os.path.dirname(symlink_path) or ".", exist_ok=True)
    if os.path.islink(symlink_path) or os.path.exists(symlink_path):
        os.remove(symlink_path)
    os.symlink(slave_path, symlink_path)

    return master_fd


async def run_bridge(device_uuid: str, symlink_path: str, channel: int | None) -> None:
    master_fd = make_pty(symlink_path)
    log(f"KISS TNC available at {symlink_path} -> {os.readlink(symlink_path)}")
    log("Attach it with: sudo kissattach " + symlink_path + " wl2k")

    try:
        while True:
            try:
                await _run_one_connection(device_uuid, channel, master_fd)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"TNC connection lost ({e!r}); reconnecting in "
                    f"{RECONNECT_BACKOFF_SECONDS}s...")
                await asyncio.sleep(RECONNECT_BACKOFF_SECONDS)
    finally:
        os.close(master_fd)
        os.remove(symlink_path)


async def _run_one_connection(
    device_uuid: str, channel: int | None, master_fd: int
) -> None:
    sock = connect_rfcomm(device_uuid, channel)
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    link_broken = asyncio.Event()

    def on_master_readable() -> None:
        try:
            data = os.read(master_fd, 4096)
        except OSError as e:
            if e.errno == errno.EIO:
                # No process currently has the pty slave open (e.g.
                # before kissattach attaches, or after it exits). The fd
                # stays readable-with-error in this state, so without
                # backing off here the event loop would call this
                # callback in an unthrottled spin.
                log("pty slave not open yet (EIO); waiting for kissattach...")
            else:
                log(f"pty read error: {e!r}")
            loop.remove_reader(master_fd)
            loop.call_later(1.0, lambda: loop.add_reader(master_fd, on_master_readable))
            return
        if not data:
            loop.remove_reader(master_fd)
            loop.call_later(1.0, lambda: loop.add_reader(master_fd, on_master_readable))
            return
        try:
            sock.send(data)
        except OSError as e:
            log(f"RFCOMM send error: {e!r}")
            loop.remove_reader(master_fd)
            link_broken.set()

    loop.add_reader(master_fd, on_master_readable)

    try:
        log("Bridge active. Ctrl+C to stop.")
        while True:
            recv_task = asyncio.ensure_future(loop.sock_recv(sock, 4096))
            broken_task = asyncio.ensure_future(link_broken.wait())
            done, _ = await asyncio.wait(
                {recv_task, broken_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if broken_task in done:
                recv_task.cancel()
                raise ConnectionError("pty send to TNC failed")
            broken_task.cancel()
            data = recv_task.result()
            if not data:
                raise ConnectionError("TNC closed the RFCOMM connection")
            os.write(master_fd, data)
    finally:
        loop.remove_reader(master_fd)
        sock.close()


if __name__ == "__main__":
    device_uuid = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DEVICE_UUID
    symlink_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PTY_PATH
    channel = int(sys.argv[3]) if len(sys.argv) > 3 else None

    if not device_uuid:
        log(f"Usage: {sys.argv[0]} <XX:XX:XX:XX:XX:XX> [pty_symlink_path] [channel]")
        sys.exit(1)

    async def main() -> None:
        task = asyncio.ensure_future(run_bridge(device_uuid, symlink_path, channel))
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, task.cancel)
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(main())
