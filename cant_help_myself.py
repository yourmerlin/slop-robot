"""
cant_help_myself.py — a RoArm-M2-S homage to "Can't Help Myself"
                      (Sun Yuan & Peng Yu, 2016).

The original is a giant industrial robot trapped in a glass box, endlessly
sweeping a spreading pool of blood-red fluid back toward itself. It had a
repertoire of ~32 moves: mostly the grim functional *sweep*, but also a handful
of weirdly playful little dances. It sped up and panicked when the fluid
escaped, and over its years of running it visibly *tired*.

This recreates the behaviour, not the fluid:

  * a compulsive recurring CONTAINMENT SWEEP (the thing it "can't help"),
  * broken up by expressive FLOURISHES (look around, bow, shake, scratch, fidget),
  * weary RESTS,
  * speed that SPIKES when it panics over a "leak" and SAGS as it tires.

Two dials drive the mood:
  energy  — moment-to-moment arousal (sets speed). Spikes on a leak, drifts down.
  stamina — long, slow decline over the whole run (the "getting tired" arc).
            Lower stamina => slower baseline, longer holds, more frequent rests.
            Disable with --no-fatigue to run at full vigour forever.

Run:
  python cant_help_myself.py                       # AP mode, IP 192.168.4.1
  python cant_help_myself.py --ip 192.168.1.50     # STA mode (IP from OLED)
  python cant_help_myself.py --dry-run             # print the mood log, send nothing
  python cant_help_myself.py --no-fatigue          # never tire
  python cant_help_myself.py --max-spd 50          # cap speed (gentler/safer)

Stop with Ctrl+C — the arm returns home before exiting.
"""

import argparse
import json
import random
import time

import requests

DEFAULT_IP = "192.168.4.1"

# Joint limits (degrees): base, shoulder, elbow, hand/clamp.
LIMITS = {"b": (-60, 60), "s": (-180, 160), "e": (-0, 150), "h": (45, 180)}

# Gripper (clamp) angles. On THIS arm a LOWER hand angle CLOSES the clamp and a
# HIGHER angle OPENS it — the reverse of the Waveshare default, confirmed by
# watching it. If grab/release ever comes out backwards again, swap these two.
GRIP_SHUT = 65    # clamp closed — the "grab"
GRIP_OPEN = 180   # clamp open

# Speed maps from energy: weary .. frantic (deg/sec). Acc: smooth .. snappy.
SPD_WEARY, SPD_FRANTIC = 8, 90
ACC_SMOOTH, ACC_SNAPPY = 4, 20

# Subtle per-frame tremor (degrees) added to base/shoulder/elbow so the arm
# never sits dead still — a faint "alive/bird" jitter. Set to 0 to disable.
JITTER_DEG = 2.0

HOME = {"T": 122, "b": 0, "s": 0, "e": 90, "h": 180, "spd": 20, "acc": 10}

# ---------------------------------------------------------------------------
# Gesture vocabulary.
# A gesture is a list of frames (b, s, e, h, hold_seconds) plus a "tempo"
# multiplier (0..1+) that scales how fast THIS gesture runs relative to the
# current energy. Sweeps are urgent; rests crawl; shakes snap.
# Geometry is chosen to stay safely inside the joint limits; tune the numbers
# to your physical arm and table once you can watch it move.
# ---------------------------------------------------------------------------
def _mirror(frames):
    """Flip a gesture left<->right by negating the base angle."""
    return [(-b, s, e, h, hold) for (b, s, e, h, hold) in frames]


# Sweep dials — the knobs you'll actually tune:
#   SWEEP_B      = WIDTH: base rotation each way (which side the stroke works on).
#   SWEEP_S      = shoulder PLANTED/forward — tip pressing into the slime
#                  (contact depth). Higher presses lower; lower lifts off.
#   SWEEP_S_BACK = shoulder PULLED BACK — far end of the inward drag. The
#                  SWEEP_S <-> SWEEP_S_BACK swing IS the dragging motion; widen
#                  this gap for a longer, bigger drag.
#   SWEEP_E      = forearm reach when planted.
#   SWEEP_E_BACK = forearm reach when pulled back — extends to keep the tip on
#                  the surface as the shoulder lifts (tune so it stays in contact).
SWEEP_B      = 38     # WIDTH: how far out to the side it starts (base degrees)
SWEEP_S      = 40     # PLANTED over the slime — tip in contact, OPEN, ready to grab.
                      # (Eased off 40: too deep and the open claw mashes the board
                      #  and can't close AROUND the slime. Raise if it isn't reaching.)
SWEEP_S_BACK = 10     # shoulder pulled INSIDE — how far in it gathers the slime.
                      # LOWER = comes further inside (toward the base). The
                      # "come more inside" dial.
SWEEP_E      = 132    # forearm reach when planted over the slime
SWEEP_E_BACK = 140    # forearm reach while carrying the grabbed slime inward
                      # (higher keeps it nearer the surface, lower lifts it more)

# A GRAB-and-gather sweep: it reaches out and hovers ABOVE the slime with the
# claw OPEN, then CLOSES as it comes DOWN onto it — grabbing on the way down —
# and the shoulder pulls well INSIDE, carrying/dragging the slime in toward the
# base, then OPENS to release it near the centre. The base also rotates inward
# while the claw is shut, so it gathers across as it comes in. Then it lifts and
# swings back out to grab again. The mirror (sweep_left) works the other side.
# Claw cycle: open (reach) -> shut (close ON THE WAY DOWN + carry in) -> open
# (release). play() adds the living jitter on top.
_SWEEP_R = [
    ( SWEEP_B,      SWEEP_S-14,     SWEEP_E-6,    GRIP_OPEN, 0.38),  # 1. reach OUT, hover ABOVE the slime, claw OPEN
    ( SWEEP_B,      SWEEP_S,        SWEEP_E,      GRIP_SHUT, 0.34),  # 2. come DOWN onto the slime while CLOSING — grab it
    ( SWEEP_B*0.5,  SWEEP_S_BACK,   SWEEP_E_BACK, GRIP_SHUT, 0.55),  # 3. pull IN & MORE INSIDE, holding it (shoulder comes way in)
    ( 0,            SWEEP_S_BACK,   SWEEP_E_BACK, GRIP_SHUT, 0.40),  # 4. carry on inward through the centre
    ( 0,            SWEEP_S_BACK+8, SWEEP_E-8,    GRIP_OPEN, 0.30),  # 5. OPEN — release the slime in toward the base
    ( SWEEP_B*0.6,  SWEEP_S-12,     SWEEP_E-2,    GRIP_OPEN, 0.45),  # 6. lift & swing back out to grab again
]

GESTURES = {
    # name            tempo  frames
    "sweep_right":  {"tempo": 0.7, "frames": _SWEEP_R},
    "sweep_left":   {"tempo": 0.7, "frames": _mirror(_SWEEP_R)},

    # Panic: short, hard passes back and forth. Runs at high energy => fast.
    "frantic_sweep": {"tempo": 1.0, "frames": [
        (55,  20, 135, GRIP_SHUT, 0.18),
        (-55, 25, 140, GRIP_SHUT, 0.22),
        (55,  20, 135, GRIP_SHUT, 0.18),
        (-55, 25, 140, GRIP_SHUT, 0.22),
        (0,   -5,  90, GRIP_SHUT, 0.20),
    ]},

    # # Slow surveil — rises tall and pans, as if scanning for the next leak.
    # "look_around": {"tempo": 0.5, "frames": [
    #     (0,   -20, 70, 110, 0.5),
    #     (-80, -20, 70, 110, 0.8),
    #     (80,  -20, 70, 110, 0.8),
    #     (0,   -10, 90, 120, 0.5),
    # ]},

    # A slow, sad bow (clamp closes like a lowered head).
    "bow": {"tempo": 0.6, "frames": [
        (0, -25,  65,  90, 0.4),
        (0,  45, 120,  60, 0.7),   # deep
        (0,  45, 120,  90, 0.3),
        (0,   0,  90, 120, 0.5),
    ]},

    # The playful wiggle — the piece's infamous "shake your butt".
    # "shake": {"tempo": 1.0, "frames": [
    #     (0,   35, 145, 120, 0.30),
    #     (25,  35, 145, 120, 0.14),
    #     (-25, 35, 145, 120, 0.14),
    #     (25,  35, 145, 120, 0.14),
    #     (-25, 35, 145, 120, 0.14),
    #     (0,   20, 120, 120, 0.30),
    # ]},

    # Fidget — "scratch an itch": little elbow + clamp twitches off to one side.
    "scratch": {"tempo": 0.9, "frames": [
        (30, -5,  95, 130, 0.25),
        (30, -5,  80, 150, 0.15),
        (30, -5, 100, 110, 0.15),
        (30, -5,  80, 150, 0.15),
        (30, -5,  95, 130, 0.20),
    ]},

    # Gripper fidget — open/close in place.
    "flick": {"tempo": 1.0, "frames": [
        (0, 10, 110, 160, 0.12),
        (0, 10, 110,  80, 0.12),
        (0, 10, 110, 160, 0.12),
        (0, 10, 110,  80, 0.12),
    ]},

    # Weary collapse: sink low and hold, almost still. Recovers a little stamina.
    "rest": {"tempo": 0.35, "frames": [
        (0, 40, 150, 130, 0.8),
        (0, 45, 155, 120, 1.6),    # long, near-motionless hold
    ]},
}


def choose_gesture(stamina):
    """Pick the next (non-panic) gesture. The compulsive sweep dominates;
    rests grow more likely as stamina falls."""
    # Sweep-only: just the two containment sweeps. To bring back the flourishes
    # / rests, re-add their names here (they must also exist in GESTURES).
    weights = {
        "sweep_right": 1.0,
        "sweep_left":  1.0,
    }
    names = list(weights)
    return random.choices(names, weights=[weights[n] for n in names])[0]


# ---------------------------------------------------------------------------
# Talking to the arm.
# ---------------------------------------------------------------------------
def clamp(joint, value):
    lo, hi = LIMITS[joint]
    return int(max(lo, min(hi, value)))


def send(ip, cmd, dry_run=False):
    """Send one JSON command (or just print it in dry-run mode)."""
    if dry_run:
        return
    try:
        requests.get(f"http://{ip}/js",
                     params={"json": json.dumps(cmd, separators=(",", ":"))},
                     timeout=5)
    except requests.RequestException as e:
        print(f"  [!] request failed: {e}")


def play(ip, gesture, energy, max_spd, dry_run):
    """Run one gesture's frames at a speed derived from energy * tempo."""
    tempo = gesture["tempo"]
    spd = int(SPD_WEARY + (SPD_FRANTIC - SPD_WEARY) * energy * tempo)
    spd = max(4, min(max_spd, spd))
    acc = int(ACC_SMOOTH + (ACC_SNAPPY - ACC_SMOOTH) * energy)
    # When weary, every pose is held a touch longer.
    hold_scale = 1.4 - 0.7 * energy
    for (b, s, e, h, hold) in gesture["frames"]:
        dwell = hold * hold_scale
        # Never sit perfectly still: split the hold into sub-beats and re-send
        # the pose with a fresh tiny tremor on base/shoulder/elbow each time, so
        # the arm always carries a faint living jitter. The clamp (h) is held
        # steady so grabs stay clean.
        beats = max(1, int(dwell / 0.18))
        for _ in range(beats):
            cmd = {"T": 122,
                   "b": clamp("b", b + random.uniform(-JITTER_DEG, JITTER_DEG)),
                   "s": clamp("s", s + random.uniform(-JITTER_DEG, JITTER_DEG)),
                   "e": clamp("e", e + random.uniform(-JITTER_DEG, JITTER_DEG)),
                   "h": clamp("h", h),
                   "spd": spd, "acc": acc}
            send(ip, cmd, dry_run)
            time.sleep(dwell / beats)
    return spd


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ip", default=DEFAULT_IP, help="Arm IP (default %(default)s)")
    p.add_argument("--no-fatigue", action="store_true",
                   help="Never tire — stamina stays at full.")
    p.add_argument("--leak-prob", type=float, default=0.15,
                   help="Per-beat chance of a 'leak' that triggers a panic sweep.")
    p.add_argument("--fatigue-rate", type=float, default=0.0008,
                   help="How fast stamina drains per beat (smaller = longer arc).")
    p.add_argument("--max-spd", type=int, default=SPD_FRANTIC,
                   help="Hard cap on speed deg/sec (lower = gentler/safer).")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the mood log but send nothing to the arm.")
    p.add_argument("--seed", type=int, default=None,
                   help="Random seed for a repeatable performance.")
    args = p.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    print('  "It can\'t help itself."   Ctrl+C to send it home and stop.\n')
    if args.dry_run:
        print("  (dry run - nothing is being sent to the arm)\n")

    energy = 0.85      # moment-to-moment arousal -> speed
    stamina = 1.0      # the slow, whole-run decline

    try:
        while True:
            # --- mood dynamics -------------------------------------------------
            if not args.no_fatigue:
                stamina = max(0.25, stamina - args.fatigue_rate)
            baseline = 0.55 * stamina                       # tired => calmer baseline
            energy += (baseline - energy) * 0.15            # drift toward baseline
            energy += random.uniform(-0.05, 0.05)           # jitter

            panicking = random.random() < args.leak_prob
            if panicking:
                energy = min(stamina, energy + 0.30)        # spike, but capped by stamina
                name = "frantic_sweep"
            else:
                name = choose_gesture(stamina)
            energy = max(0.05, min(1.0, energy))

            # --- perform -------------------------------------------------------
            gesture = GESTURES[name]
            spd = play(args.ip, gesture, energy, args.max_spd, args.dry_run)

            flag = "!! leak" if panicking else "        "
            print(f"  stamina {stamina:.2f} | energy {energy:.2f} | {flag} "
                  f"{name:13s} spd={spd:>2d}")

            # Rests are a breather: claw back a little energy and stamina.
            if name == "rest":
                energy = min(1.0, energy + 0.10)
                stamina = min(1.0, stamina + 0.003)

    except KeyboardInterrupt:
        print("\n  Enough. Sending it home.")
        send(args.ip, HOME, args.dry_run)
        time.sleep(1.5)
        print("  Done.")


if __name__ == "__main__":
    main()
