"""
How to use this file!!

    HOW TO RUN  (in a terminal, in this folder):
        python my_first_arm.py                  # uses the IP set below
        python my_first_arm.py --ip 192.168.4.1 # use a different IP
        python my_first_arm.py --dry-run        # print the notes, DON'T move the arm
                                                #   (great for learning with zero risk)
        Press Ctrl+C to stop — the arm freezes where it is (it does NOT run home).

    WHAT TO EDIT:
        • ARM_IP  — where your arm lives on the network.
        • POSES   — the movement itself. One line per step. Change the numbers!
        • SPEED   — how fast it moves.

    SAFETY (please read once):
        Never give the arm a pose it can't physically reach — ESPECIALLY one that
        presses it DOWN into the table. The servo will strain at full power trying to
        get there, overheat, and can burn out. Keep the shoulder/elbow numbers so the
        claw stops ABOVE the surface, never crammed into it. The LIMITS below are a
        safety net, but the real safety is choosing sensible numbers.
"""

import argparse
import json
from random import random
import time

import requests

# var meanings/functions:

    # b = base (turns the whole arm left/right) 
        # based on a  0, and its rotation range is 3.14 to -3.14. When the angle increases, the base joint turns left. When the angle decreases, the base joint turns right.
    # s = shoulder (the big up/down)
        # based on a 0, and its rotation range is 1.57 to -1.57. When the angle increases, the shoulder joint moves down. When the angle decreases, the shoulder joint moves up.
    # e = elbow (forearm reach)
        # based on a 1.570796, and its rotation range is 3.14 to 0. When the angle increases, the elbow joint rotates downward. When the angle decreases, the elbow joint rotates reversely.
    # h = claw (grip open/close)
        # base on a 3.141593. RoArm-M2-S adopts the clamp by default with a rotation range of 1.08 to 3.14. When the angle decreases, the clamp joint will open. If you adopt the wrist joint, the rotation range is 1.08 to 5.20. When the angle increases, the wrist joint rotates downward. When the angle increases, the wrist joint rotates upward.
    # speed
        # The rotation speed, measured in steps per second, is used to control the speed of the servos. In this system, one full rotation of a servo corresponds to 4096 steps. A higher numerical value will result in a faster speed, and when the speed value is set to 0, it will rotate at the maximum speed.
    # acc = acceleration
        # The acceleration at the start and end of rotation can be controlled with a numerical value, which should be a value between 0 and 254, measured in 100 steps per second squared. A smaller numerical value results in smoother acceleration and deceleration. For example, if set to 10, it will accelerate and decelerate at 1000 steps per second squared. When the acceleration value is set to 0, it will use the maximum acceleration.

# variables (tinker around with these to change the arm's behavior)

ARM_IP = "192.168.4.1" 
# arm ips:
# 1.  LEFT ARM:
    #STA mode: 192.168.2.239
    #AP mode: 192.168.4.1
# 2.  RIGHT ARM:
    # STA mode: 192.168.2.190
    # AP mode: 192.168.4.1

SPEED = 10               
ACC   = 10              

# the claw -- on this arm a LOW number OPENS, a HIGH number CLOSES.
# (range is 45 - 180)
GRIP_OPEN = 65    
# claw open
GRIP_SHUT = 180   
# claw closed (a "grab")


#  movement/gestures seqeuence -- each line is one pose 
#
#       base      turn the whole arm left/right   (higher = left, lower = right)
#       shoulder  the big up/down   (higher = reach DOWN/forward, lower = UP)
#       elbow     forearm reach     (higher = reach further out/down)
#       claw      GRIP_OPEN or GRIP_SHUT
#       seconds   how long to wait here before the next line

POSES = [
    #  base  shoulder  elbow   claw        seconds   what it does
    (   0,      14,     145,   GRIP_OPEN,   2.0),  # 1. shoulder down (eased), elbow reaches OUT, claw open
    (   0,      32,     118,   GRIP_SHUT,   1.8),  # 2. elbow curls IN + claw closes = GRAB
    (   0,      44,     145,   GRIP_OPEN,   1.8),  # 3. elbow reaches OUT + opens
    (   0,      45,     118,   GRIP_SHUT,   1.8),  # 4. curl IN + GRAB
    (   0,      30,     145,   GRIP_OPEN,   1.8),  # 5. reach OUT + open
    (   0,      22,     118,   GRIP_SHUT,   1.8),  # 6. curl IN + GRAB
    (   0,      22,     145,   GRIP_OPEN,   2.0),  # 7. reach OUT + open  -> loops
]

# safety limits/constraints 

LIMITS = {
    "b": (-45, 45),     
    "s": (-60, 70),     
    "e": ( 30, 160),    
    "h": ( 45, 180),    
}

# connection to da machine >:D


last_note = None    
# remembers the last pose, so Ctrl+C can freeze the arm here

def clamp(joint, value):
    """Force one number inside its safe LIMITS range."""
    low, high = LIMITS[joint]
    return int(max(low, min(high, value)))


def send(ip, note, dry_run):
    """Mail ONE note (a dict) to the arm. This is the only thing that actually
    talks to the hardware. `requests.get` just means 'open this web address'."""
    global last_note
    last_note = note
    text = json.dumps(note)                 # turn the dict into text like {"T":122,...}
    if dry_run:
        print("   would send:", text)       # learning mode: show it, send nothing
        return
    try:
        requests.get(f"http://{ip}/js", params={"json": text}, timeout=5)
    except requests.RequestException as exc:
        print(f"   [!] couldn't reach the arm at {ip}: {exc}")


def move(ip, base, shoulder, elbow, claw, dry_run):
    """Build a move note from four joint angles and send it.
    THIS is the core of everything — one note = one position."""
    note = {
        "T": 122,                           # 122 = 'move all joints, in degrees'
        "b": clamp("b", base),
        "s": clamp("s", shoulder),
        "e": clamp("e", elbow),
        "h": clamp("h", claw),
        "spd": SPEED,
        "acc": ACC,
    }
    send(ip, note, dry_run)


def check_connection(ip, dry_run):
    """Say hello before moving: ask the arm for its status (the {"T":105} note).
    If we can't reach it, stop here instead of flailing."""
    if dry_run:
        print("Dry run - not contacting the arm.\n")
        return True
    try:
        reply = requests.get(f"http://{ip}/js", params={"json": '{"T":105}'}, timeout=5)
        print(f"Connected to the arm at {ip}.")
        print(f"  it says: {reply.text.strip()[:90]}\n")
        return True
    except requests.RequestException as exc:
        print(f"Could NOT reach the arm at {ip}: {exc}")
        print("  - Is your laptop on the arm's WiFi (or the right network)?")
        print("  - Check the IP on the arm's screen, then use --ip <that IP>.\n")
        return False


def main():
    parser = argparse.ArgumentParser(description="Beginner RoArm-M2-S starter.")
    parser.add_argument("--ip", default=ARM_IP, help=f"Arm IP (default {ARM_IP}).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the notes but don't move the arm.")
    args = parser.parse_args()

    print('  my_first_arm - Ctrl+C to stop (it freezes in place).\n')

    if not check_connection(args.ip, args.dry_run):
        return

    REST_EVERY   = 6     # take a break after this many full sweeps
    REST_SECONDS = 30    # how long to rest so the servos cool
    cycle = 0
    try:
        while True:                                   # loop forever
            for (base, shoulder, elbow, claw, seconds) in POSES:
                print(f"  pose: base={base} shoulder={shoulder} "
                      f"elbow={elbow} claw={claw}")
                move(args.ip, base, shoulder, elbow, claw, args.dry_run)
                time.sleep(seconds)                   # give the arm time to arrive
            cycle += 1
            if cycle % REST_EVERY == 0:
                print(f"  --- cooldown rest ({REST_SECONDS}s) ---")
                move(args.ip, 0, -20, 80, GRIP_OPEN, args.dry_run)  # pull up & in, low load
                time.sleep(REST_SECONDS)

    except KeyboardInterrupt:
        # Freeze: re-send the last pose so it holds still where it is.
        print("\n  Stopping - holding the arm where it is.")
        if last_note is not None:
            send(args.ip, last_note, args.dry_run)
        print("  Done. Edit POSES above and run it again.")

if __name__ == "__main__":
    main()
