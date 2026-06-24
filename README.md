# RoArm-M2-S — WiFi/JSON control

Tinkering with a **Waveshare RoArm-M2-S** robot arm: driving it and programming
movement sequences at different speeds, continuously / looping.

## Hardware

Waveshare **RoArm-M2-S** — a 4-DOF desktop robotic arm, ESP32-based, with serial
bus servos.

> Note: originally started on the RoArm-M1 ESP32/Arduino tutorial by mistake —
> the arm is actually the M2-S.

## Approach (no ROS2, no VM, no Arduino re-flash)

The arm serves a built-in web control panel over its own WiFi.

1. Connect your computer to the arm's WiFi access point
   (default SSID `RoArm-M2-S`, password `12345678`).
2. Browse to `http://192.168.4.1` for the control panel — there's a command box
   that accepts JSON commands.
3. The same JSON commands also work over plain HTTP:
   `http://192.168.4.1/js?json={...}`

This is the path used here. The alternatives were ruled out:

- **USB-to-serial** wasn't showing up in Windows Device Manager — a
  connection/driver issue (CH340 or CP2102 chip). Not needed for this path.
- **Arduino IDE**: correct board is "ESP32 Dev Module" (NOT "Arduino Nano
  ESP32" — that triggers a DFU upload error). ArduinoJson must be v6.x, not
  v7.x. Not needed for this path.
- **Waveshare Foxglove/ROS2 tutorial** requires Linux/ROS2 commands
  (`ros2 run`, `sudo apt`) inside an Ubuntu VirtualBox VM — too heavy, skipped.

## Key JSON commands

| Command | Meaning |
| --- | --- |
| `{"T":122,"b":0,"s":0,"e":90,"h":180,"spd":10,"acc":10}` | Move all joints by **angle**. `b`=base, `s`=shoulder, `e`=elbow, `h`=hand/clamp. `spd`=speed deg/sec (higher=faster, 0=max). `acc`=accel smoothness 0–254. |
| `{"T":100}` | Go home |
| `{"T":105}` | Report current angles / coords / loads |

**Angle ranges:** base −180..180, shoulder −90..90, elbow 0..180, hand 45..180.

## The script: `robot.py`

Sends these commands over HTTP in a loop. Defines a `SEQUENCE` list of
`(pose, wait-time)` pairs, each pose carrying its own `spd`/`acc`, and runs
forever until Ctrl+C (then returns home). Uses the `requests` library.

```sh
pip install requests
python robot.py                  # default IP 192.168.4.1 (AP mode)
python robot.py --ip 192.168.1.50   # STA mode: IP from the OLED screen
python robot.py --loops 3        # run the sequence 3 times then stop
```

## Possible next steps

- Add gripper open/close helpers.
- Record poses by hand and replay them.
- Refine / expand the movement sequences.
- Scale up the control logic.
