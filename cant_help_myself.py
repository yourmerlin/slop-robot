"""
cant_help_myself.py — RoArm-M2-S "Can't Help Myself" slime grab & sweep.

Drives a Waveshare RoArm-M2-S over WiFi to endlessly GRAB and SWEEP a pool of
slime, like the Sun Yuan & Peng Yu robot. It runs ONE motion on a loop, with a
little randomness so it still looks alive — no random gestures, no panic.

────────────────────────────────────────────────────────────────────────────
HOW TO RUN
  1. Power on the arm and get this computer onto it over WiFi:
       • AP mode  — join the arm's own WiFi "RoArm-M2-S" (password 12345678);
                    its address is 192.168.4.1 (the default below).
       • STA mode — arm + computer on the SAME WiFi; use the IP shown on the
                    arm's little screen:   --ip 192.168.x.x
  2. In a terminal, inside this folder:
       python cant_help_myself.py
       python cant_help_myself.py --ip 192.168.1.50
       python cant_help_myself.py --dry-run        # print only, move nothing
  3. Press Ctrl+C to FREEZE the arm where it is (it does NOT go home), so you
     can edit the numbers below and run it again.

WHAT YOU'LL EDIT  (everything is grouped + labelled below)
  • SWEEP   — the motion itself: one line per step, plain numbers. Start here.
  • GRIP    — how far the claw opens / closes.
  • SPEED   — how fast it moves;  JITTER — how much it trembles.
  • LIMITS  — safety min/max per joint; a typo can never push past these.
────────────────────────────────────────────────────────────────────────────
"""

import argparse
import json
import random
import time

import requests


# ════════════════════════════════════════════════════════════════════════
#  CONNECTION
# ════════════════════════════════════════════════════════════════════════
DEFAULT_IP = "192.168.2.239"      # arm's address (AP mode). Override with --ip.


# ════════════════════════════════════════════════════════════════════════
#  CLAW  — Waveshare docs: the clamp's valid range is 45–180 degrees; 180 is
#  CLOSED, and the angle DECREASING opens it (~45 = wide open). If grab/release
#  comes out backwards on your arm, just swap these two numbers (and re-test).
# ════════════════════════════════════════════════════════════════════════
GRIP_SHUT = 180     # claw CLOSED (the "grab")   [valid 45–180; 180 = fully shut]
GRIP_OPEN = 65      # claw OPEN                   [valid 45–180; ~45 = fully open]


# ════════════════════════════════════════════════════════════════════════
#  SPEED & FEEL
# ════════════════════════════════════════════════════════════════════════
SPEED_MIN = 18      # deg/sec — each loop picks a random speed between these two,
SPEED_MAX = 34      #           so the pace varies a little (looks less robotic).
ACC       = 10      # acceleration 0–254 (lower = smoother starts/stops).
JITTER    = 2.0     # tiny random tremor in degrees, so it never sits dead still.


# ════════════════════════════════════════════════════════════════════════
#  JOINT LIMITS  — hard safety clamps in degrees. Every value is forced into
#  [min, max] before it's sent, so a bad number in SWEEP can't slam the arm.
#    b = base (turn L/R)        s = shoulder (DOWN is +, UP is −)
#    e = elbow (reach)          h = hand/claw  (MUST span both GRIP values!)
# ════════════════════════════════════════════════════════════════════════
LIMITS = {
    "b": (-20,  20),    # base: kept near 0 so it stays roughly stagnant
    "s": (-90,  90),    # shoulder
    "e": (  0, 180),    # elbow
    "h": ( 45, 180),    # claw  ← per Waveshare docs the valid range is 45–180
}


# ════════════════════════════════════════════════════════════════════════
#  THE SWEEP  — the entire motion, one step per line. Loops forever.
#
#  Each line is:   (base, shoulder, elbow, claw, seconds)
#     base      turn left/right   (small = base barely moves)
#     shoulder  HIGHER = reach DOWN/forward,   LOWER = lift UP
#     elbow     HIGHER = forearm reaches out further / pushed back
#     claw      GRIP_OPEN  or  GRIP_SHUT
#     seconds   how long to dwell on this step before the next
#
#  This motion: it comes DOWN with the claw OPENING, presses in with the elbow
#  pushed back, then CLOSES the claw as it LIFTS — scooping the slime up and
#  carrying it inward, before swinging back out to do it again.
# ════════════════════════════════════════════════════════════════════════
SWEEP = [
    #  base  shoulder  elbow   claw        sec    what it does
    (   0,     14,      115,   GRIP_SHUT,  0.40),  # 1. up & in, claw CLOSED (carrying)
    (   6,     32,      128,   GRIP_OPEN,  0.45),  # 2. swing out & start DOWN — claw OPENS
    (   6,     44,      140,   GRIP_OPEN,  0.50),  # 3. DOWN on the slime, elbow pushed back, fully OPEN
    (   3,     30,      126,   GRIP_SHUT,  0.45),  # 4. LIFT up & in — claw CLOSES (scoops it up)
    (   0,     16,      116,   GRIP_SHUT,  0.40),  # 5. carry up & inward, CLOSED  → loops to step 1
]


# ════════════════════════════════════════════════════════════════════════
#  ── machinery below; you don't need to touch this to change the motion ──
# ════════════════════════════════════════════════════════════════════════
LAST_CMD = None     # remember the last pose so Ctrl+C can freeze the arm there


def clamp(joint, value):
    """Force a joint value inside its safe LIMITS range, as a whole number."""
    low, high = LIMITS[joint]
    return int(max(low, min(high, value)))


def send(ip, cmd, dry_run):
    """Send one JSON command to the arm (or just print it, in --dry-run)."""
    global LAST_CMD
    LAST_CMD = cmd
    text = json.dumps(cmd, separators=(",", ":"))
    if dry_run:
        print("   ", text)
        return
    try:
        requests.get(f"http://{ip}/js", params={"json": text}, timeout=5)
    except requests.RequestException as exc:
        print(f"   [!] could not reach the arm at {ip}: {exc}")


def step(ip, base, shoulder, elbow, claw, speed, seconds, dry_run):
    """Move to one pose, then tremble gently in place for `seconds` so the arm
    never looks frozen. The claw is NOT trembled, so grabs stay clean."""
    nudges = max(1, int(seconds / 0.18))        # a few tiny re-sends across the hold
    for _ in range(nudges):
        send(ip, {
            "T": 122,
            "b": clamp("b", base     + random.uniform(-JITTER, JITTER)),
            "s": clamp("s", shoulder + random.uniform(-JITTER, JITTER)),
            "e": clamp("e", elbow    + random.uniform(-JITTER, JITTER)),
            "h": clamp("h", claw),
            "spd": speed,
            "acc": ACC,
        }, dry_run)
        time.sleep(seconds / nudges)


def run(ip, dry_run):
    print("  Grab & sweep.  Ctrl+C to FREEZE the arm in place.\n")
    if dry_run:
        print("  (dry run - printing commands, moving nothing)\n")
    try:
        while True:
            speed = random.randint(SPEED_MIN, SPEED_MAX)      # a little pace variety
            for (base, shoulder, elbow, claw, seconds) in SWEEP:
                # a touch of timing variety too, so the loop isn't metronomic
                step(ip, base, shoulder, elbow, claw, speed,
                     seconds * random.uniform(0.9, 1.1), dry_run)
    except KeyboardInterrupt:
        # Freeze where it is — re-send the last pose, do NOT drive home.
        print("\n  Stopping - holding the arm where it is (not going home).")
        if LAST_CMD is not None:
            send(ip, LAST_CMD, dry_run)
        print("  Stopped. Edit the numbers above and run it again.")


def main():
    parser = argparse.ArgumentParser(
        description="RoArm-M2-S endless grab & sweep.")
    parser.add_argument("--ip", default=DEFAULT_IP,
                        help=f"Arm IP address (default {DEFAULT_IP}).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands instead of sending them.")
    args = parser.parse_args()
    run(args.ip, args.dry_run)


if __name__ == "__main__":
    main()
