ONE-DIRECTION MOTOR TEST - Arduino Mega 2560 + TB6600

Preserves the working wiring and ENABLE setting:
  PUL+ -> D2; DIR+ -> D3; ENA+ -> D4; ENABLE LOW.
  PUL-, DIR- and ENA- share Arduino GND, including your existing jumpers.
  Keep the tested motor-coil wiring and 3200 pulses/revolution setting.
  Mega uses USB; TB6600 uses the separate 12.6 V supply.

1. Quit flower_reader.py and close other serial programs.
2. Keep the motor rotation path clear; use the unloaded motor for this test.
3. Open one_direction_test.ino in Arduino IDE.
4. Install AccelStepper by Mike McCauley if it is not already installed.
5. Select Arduino Mega or Mega 2560 / ATmega2560 and the Mega USB port.
6. Upload. The motor starts automatically after upload/reset.

The sketch repeats full 3200-pulse turns in one direction. Every turn
ramps up and down, slowing to zero between turns before starting again.
At 600 pulses/second and 300 pulses/second squared, each turn takes
about 7.3 seconds. It does not reverse and needs no zero calibration,
camera, scanner program, homing sensor, gearbox or encoder.

To stop pulses: open Serial Monitor at 115200 baud, enter s, click Send.
To resume: send r. Uppercase S/R also work. Any line-ending setting works.
Opening Serial Monitor can reset the Mega, which restarts this automatic
test. The s command stops pulses immediately; ENABLE remains LOW, so the
motor stays energized. Switch off the TB6600 power supply to remove motor
power. Do not disconnect the motor leads while the driver is powered.

DIR HIGH selects one physical direction; this test does not assume which
direction is clockwise. To test the opposite direction, change only
TEST_DIR_LEVEL from HIGH to LOW and upload again.

IMPORTANT: This is a temporary standalone sketch. Before using the flower
reader again, upload firmware/quadrant_positioner/quadrant_positioner.ino,
close Serial Monitor, start the reader and manually calibrate Q1 with z.
The test sketch does not speak the scanner's serial positioning protocol.

Validation: compiled/linked for ATmega2560 with Arduino AVR core 1.8.7 and
AccelStepper 1.64. Native simulation verified two 3200-pulse turns in the
same direction, acceleration/deceleration, stop/resume, pins D2/D3/D4,
ENABLE LOW, 10 us direction setup and 10 us STEP HIGH. Physical motor
behavior must be checked on your hardware.
