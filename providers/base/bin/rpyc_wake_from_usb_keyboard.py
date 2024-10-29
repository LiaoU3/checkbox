#!/usr/bin/env python3
import os
import struct
import sys
import threading
import time
import subprocess
import time
from enum import Enum
from pathlib import Path
from argparse import ArgumentParser
from rpyc_keyboard_test import get_rpyc_kbd_device
from checkbox_support.scripts.rpyc_proxy import rpyc_run  # noqa: E402

ROBOT_INIT = """
*** Settings ***
Library    libraries/rpycHid.py

*** Test Cases ***
Do nothing
    Log    Re-configure HID device
"""

# ROBOT_DELAY_SEND_ENTER_KEY = """
# *** Settings ***
# Library    libraries/rpycHid.py

# *** Tasks ***
# Wait and press ENTER
#     ${{enter}}=     Create List     ENTER
#     Sleep         {}
#     Keys Combo    ${{enter}}
# """
ROBOT_DELAY_SEND_ENTER_KEY = """
*** Settings ***
Library    libraries/rpycHid.py

*** Tasks ***
Wait and press ENTER
    ${combo}	Create List		ENTER
    Sleep   		60
    Keys Combo		${combo}
"""


def send_enter_key(host):
    rpyc_run(
        host,
        "robot_run",
        ROBOT_DELAY_SEND_ENTER_KEY.encode(),
        {},
        {},
    )


def arg_parser():
    parser = ArgumentParser()
    parser.add_argument(
        "host",
        help=("Address of rpyc to connect to."),
    )
    parser.add_argument(
        "--rtc",
        default="/dev/rtc0",
        help="RTC device to use (default: /dev/rtc0).",
    )
    parser.add_argument(
        "--sleep-delay",
        default=60,
        type=int,
        help="Delay in seconds waiting for the system to sleep. (default: 60).",
    )
    parser.add_argument(
        "--wait-delay",
        default=120,
        type=int,
        help="Delay in seconds waiting for the system to wake up. (default: 120).",
    )
    return parser


def main():
    parser = arg_parser()
    args = parser.parse_args()

    # A simple robot-run to initialize the rpyc HID device
    rpyc_run(args.host, "robot_run", ROBOT_INIT.encode(), {}, {})

    try:
        rpyc_kbd = get_rpyc_kbd_device()
    except FileNotFoundError as exc:
        raise SystemExit("Cannot find rpyc Keyboard.") from exc

    if not os.access(rpyc_kbd, os.R_OK):
        raise SystemExit("Cannot read from rpyc Keyboard.")
    background_thread = threading.Thread(target=send_enter_key, args=(args.host,))
    background_thread.start()

    time.sleep(5)
    start = time.time()
    cmd = "rtcwake -d {} -m no -s {} && systemctl suspend || exit 1".format(
        args.rtc, args.wait_delay
    )
    subprocess.run(cmd, shell=True)

    time.sleep(5)
    end = time.time()
    if end - start > 120:
        raise SystemExit(
            "Suspend timed out. System cannot wake up by USB keyboard."
        )
    print("System successfully be woken up by USB keyboard.")


if __name__ == "__main__":
    main()
