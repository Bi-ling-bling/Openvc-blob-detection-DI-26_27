# Four-dot flower reader and quadrant positioning

The existing 100 × 60 mm matte cards still work. The reader's border detection,
perspective correction, orientation marker, dot checks, left-to-right bit order,
and five-consecutive-frame confirmation are preserved. Only the confirmed result
is passed to the new motor controller. All four bits remain available for the
flower ID (`int(bits, 2) + 1`); only the first two select the quadrant.

| First two bits | Quadrant | Angle from manual zero | Position, pulses |
|---|---|---|---|
| 00 | 1 | 0° | 0 |
| 01 | 2 | 90° | 800 |
| 10 | 3 | 180° | 1600 |
| 11 | 4 | 270° | 2400 |

The Arduino tracks emitted pulses and picks the shortest move, at most 1600
pulses. An exactly 180° move uses the positive direction consistently. For
example, Q1 → Q4 is −800 pulses and Q4 → Q1 is +800 pulses. Each completed move
normalizes the coordinate to 0–3199. Repeated detections of the reached quadrant,
including codes with different final two bits, cause no further movement.
When a card becomes unreadable, an already accepted move finishes, and no new
target is guessed or sent. Nothing returns to zero automatically.

## Existing hardware: retain it exactly

| TB6600 | Mega 2560 |
|---|---|
| PUL+ | D2 |
| PUL− | GND |
| DIR+ | D3 |
| DIR− | GND |
| ENA+ | D4 |
| ENA− | GND |

Retain the PUL−/DIR− jumper and both existing ground connections. Keep the Mega
on laptop USB and the TB6600 on the separate 12.6 V supply. The 9 V battery is
unused. Keep the TB6600's tested 3200-pulse/revolution microstep setting. The
motor is the STEPPERONLINE NEMA 17 17HS19-2004S1; there is no gearbox, encoder,
or homing sensor. This repository contained no previous Arduino motor sketch;
the firmware therefore uses the exact working constants supplied for this task.

```cpp
const int STEP_PIN = 2;
const int DIR_PIN = 3;
const int ENA_PIN = 4;
const int STEPS_PER_REV = 3200;
```

ENABLE stays **LOW**, including while stationary and after STOP, to preserve
the working hold setting. Normal motion uses AccelStepper acceleration and
deceleration, initially 600 pulses/s maximum and 300 pulses/s² acceleration
(about 11.25 rpm maximum). Each step has 10 µs of direction setup and a 10 µs
HIGH pulse. No other actuators are controlled.

## Install and upload

In your existing project directory on openSUSE, activate your existing virtual
environment (Python 3.13 is supported):

```bash
cd ~/di-blob-detection
source .venv/bin/activate
python -m pip install -r requirements.txt
```

In Arduino IDE, install **AccelStepper 1.64 by Mike McCauley** using Library
Manager. Open `firmware/quadrant_positioner/quadrant_positioner.ino`, select
**Arduino Mega or Mega 2560 / ATmega2560**, select its USB port, and upload.
Keep `positioning.h` in the same sketch folder. Close Serial Monitor before
starting Python: only one program should use the port.

Find your port:

```bash
python -m serial.tools.list_ports -v
```

Use the listed device, typically `/dev/ttyACM0`, or its stable
`/dev/serial/by-id/...` path. If permission is denied, check your openSUSE serial
device permissions/group membership. Do not run the entire reader as root.

## Start with simulation

No camera, Arduino, or pyserial is needed for the accelerated-time command demo:

```bash
python quadrant_control.py
python quadrant_control.py 1111 0011 1010 0101
```

The second example reports −800, +800, +1600, and −800 pulses, respectively.
This is a protocol/position simulation, not evidence of mechanical accuracy.

To use the same printed cards and webcam with a simulated motor:

```bash
python flower_reader.py --dry-run
```

The screen shows `SIM`, waits for `z` to establish a **simulated** zero, and then
shows the selected quadrant and completion status. It never opens a serial port.
Running `python flower_reader.py` without options retains detection-only use.
`--source` still accepts a camera number, video file, or stream URL; for example
`python flower_reader.py --source 0 --dry-run`.

## Establish physical zero and run

1. Leave the wiring and TB6600 DIP switches as tested. Clear the rotation path
   for this first positioning test. Start the reader with your actual port:

   ```bash
   python flower_reader.py --serial /dev/ttyACM0
   ```

2. After `READY`, the firmware will not accept quadrant moves until zeroed.
   With the Flower reader window focused, use `[` and `]` for −40/+40-pulse
   calibration jogs (4.5° each). Wait for each jog to finish before the next.
   Align the shaft/dome's reference mark with the physical Q1/0° mark. Do not
   force the energized shaft by hand. Alternatively, align while motor power is
   off, restore power, and verify the actual alignment before declaring zero.
3. Once aligned and stationary, press **z**. This declares the present physical
   position to be zero; it does not find or rotate to zero. Wait for
   `Zero calibrated; holding Q1`. Keep cards out of view during alignment;
   detections resume after five matching frames following `z`.
4. Present `0011` (Flower 4): Q1, no move. Present `0101` (Flower 6): Q2,
   +800 pulses. Present `1010` (Flower 11): Q3, +800 more. Present `1111`
   (Flower 16): Q4, +800 more. A normal 90° move takes roughly 3.3 seconds.
   Wait for `Holding Qn` after every move.
5. Keep the same card in view: the motor holds still. Switch `1111` to `1100`:
   it still holds Q4 because the quadrant bits are unchanged. Remove the card:
   it holds the last target. Try Q4 → Q1 and Q1 → Q4: each takes one quarter
   revolution, in opposite directions.
6. **s** sends software STOP immediately, cancels the current command, and
   invalidates calibration. Re-align Q1 and press **z** before proceeding.
   Jogging is available only before calibration; press `s` to re-enter alignment.
   **q**, Esc, closing a window, a camera failure, or Ctrl+C also sends a
   best-effort STOP on exit.

Positive rotation initially means DIR HIGH. The previous motor test did not
specify which physical direction this represents. Verify the positive jog and
place Q2/Q3/Q4 in that direction. If your intended quadrant order runs the other
way, change only `POSITIVE_DIR_LEVEL` from `HIGH` to `LOW` in the sketch and
upload again, then recalibrate. Pins, wiring, and the 800-pulse spacing stay the
same.

STOP is an immediate pulse stop, so it can lose steps; it intentionally requires
new calibration. It retains holding torque and is not a power-isolating hardware
emergency stop. If application heartbeats cease during a move, the firmware
stops within about three seconds and requires zero again. USB errors, missing
ACK/DONE, malformed responses, and unexpected resets invalidate the Python
controller's calibration; it does not blindly retry motion. After a link fault,
restart the reader and manually zero again. Following power loss, a reset,
a stall, or external shaft movement, never reuse the old software position.
Without an encoder the firmware can acknowledge pulse completion, but cannot
detect mechanical missed steps; confirm the marks locally under the actual load.

### Jogging disabled or “Malformed reply”

A motor link fault disables the jog keys. Before checking motor wiring, confirm
that `quadrant_positioner.ino` was successfully uploaded to the Mega; the old
continuous-rotation test sketch cannot speak this protocol. Close Serial Monitor
and other serial tools, quit the reader, then start the updated reader with:

```bash
python flower_reader.py --serial /dev/ttyACM0 --serial-debug
```

Use your actual port. The terminal prints the complete received/transmitted
serial bytes, including escaped nonprintable characters. Wait for
`READY NEED_ZERO` and the alignment prompt before pressing `[` or `]`; keep
cards out of view and do not press `z` until Q1 is physically aligned. A jog
should produce `JOG id 40` (or −40), `ACK id`, and `DONE id JOG POS p` in the log.

The client now ignores stale startup lines until the exact READY handshake,
without enabling any movement or accepting old acknowledgments. If READY never
arrives within six seconds, the terminal reports the received startup data and
asks you to check the uploaded sketch and the port. Unexpected/corrupt replies
after READY still stop and disarm the client. A short camera-overlay message
points to the terminal for the full fault; restart and recalibrate after fixing
the cause. If it still fails, use the terminal's complete RX/error lines to
distinguish an old sketch, incorrect port, or corrupted serial data.

## Existing cards

Continue using your current 100 × 60 mm matte cards: 2 mm black border inset
3 mm; four 8 mm dots centered at x=20/40/60/80 mm, y=35 mm; a 6 mm square
orientation marker centered at (15,15) mm. Zeros are empty white positions.
The existing template command remains available if replacements are needed:

```bash
python flower_reader.py --print-cards flower_cards.html
```

Print at 100% actual size with browser headers/footers disabled. Show the whole
border and marker in diffuse light. Orange `?` regions remain unreadable and
cannot request a new target.

## Tests and changed files

```bash
python -m unittest discover -v
```

The 28 Python tests cover the existing 16 cards in four orientations, the real
camera loop's five-consecutive-frame gate, all mappings and shortest paths,
deduplication, ACK/DONE, calibration, STOP, resets, invalid results, timeouts,
and disconnections. Three tests use real pyserial with Linux virtual serial ports
(skipped when pyserial or POSIX PTYs are unavailable).
Startup-noise recovery, old-firmware diagnosis, jog acknowledgments, and serial
diagnostic logging are also covered; malformed replies after READY still disarm.

For the native firmware tests, point `ACCELSTEPPER_SRC` to the installed
AccelStepper 1.64 library's `src` directory (which contains `AccelStepper.cpp`):

```bash
mkdir -p work
ACCELSTEPPER_SRC=/path/to/AccelStepper/src
g++ -std=c++11 -Wall -Wextra -DARDUINO=10819 -I tests/firmware -I "$ACCELSTEPPER_SRC" tests/firmware/firmware_test.cpp "$ACCELSTEPPER_SRC/AccelStepper.cpp" -o work/firmware_test
work/firmware_test
```

These tests execute the actual sketch with the actual acceleration library and
simulated Arduino I/O. They check all 16 transitions, pulse counts and direction,
acceleration/deceleration, pulse timing, pin assignments/ENABLE LOW, invalid
commands, STOP, and the link watchdog. The sketch was also compiled and linked
for ATmega2560 using Arduino AVR core 1.8.7 and AVR GCC 14.2. Physical webcam,
USB Mega, motor load, and vibration tests must be run on your laptop/hardware.
Real OpenCV windows were also checked here using generated card video: simulated
manual zero, Q4 completion, and STOP on exit all passed.

| File | Change |
|---|---|
| `flower_reader.py` | Optional serial/simulation integration, status overlay, and calibration/STOP keys. Detection functions and card generation are unchanged. |
| `quadrant_control.py` | Nonblocking protocol client, mapping, timeout/fault handling, dry-run transport, camera-free demo. |
| `firmware/quadrant_positioner/quadrant_positioner.ino` | Mega/TB6600 firmware, calibrated motion, acceleration, command parser, watchdog. |
| `firmware/quadrant_positioner/positioning.h` | Bounded coordinate and shortest-path math. |
| `requirements.txt` | OpenCV, NumPy, and pyserial dependencies. |
| `test_flower_reader.py` | Card/layout regression and camera-loop confirmation checks. |
| `test_quadrant_control.py` | Mapping, positioning, and controller/fault tests. |
| `test_serial_pty.py` | Real pyserial protocol and disconnect checks on virtual serial ports. |
| `tests/firmware/Arduino.h`, `tests/firmware/firmware_test.cpp` | Native firmware test harness. |
| `SERIAL_PROTOCOL.md` | Serial commands, acknowledgments, errors, and timing. |
| `README.md` | Installation, calibration, use, and testing guide. |

`Test.py` is unchanged. No wiring, card templates/layout, DIP switches,
environment settings, or other actuators are modified.
