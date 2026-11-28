// Standalone Mega 2560 + TB6600 test. Install AccelStepper via Library Manager.
// Starts automatically: one full turn, repeated in the SAME direction.
// Serial Monitor at 115200 baud: s = stop and hold; r = restart.
// Upload quadrant_positioner.ino again before using the flower reader.
#include <AccelStepper.h>

const int STEP_PIN = 2;
const int DIR_PIN = 3;
const int ENA_PIN = 4;
const int STEPS_PER_REV = 3200;
const int TEST_DIR_LEVEL = HIGH;
const float MAX_SPEED = 600.0;     // Pulses/second; about 11.25 rpm at full speed.
const float ACCELERATION = 300.0;  // Pulses/second squared.

// Reuse the tested quadrant firmware's direction setup and pulse timing.
class TB6600Stepper : public AccelStepper {
 public:
  TB6600Stepper() : AccelStepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN) {}
 protected:
  void step(long) override {
    digitalWrite(DIR_PIN, TEST_DIR_LEVEL);
    delayMicroseconds(10);
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(STEP_PIN, LOW);
  }
};

TB6600Stepper motor;
bool running = true;

void startTurn() {
  // Called while stationary. Bound the coordinate so it cannot overflow.
  motor.setCurrentPosition(0);
  motor.moveTo(STEPS_PER_REV);
}

void setup() {
  pinMode(STEP_PIN, OUTPUT);
  digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT);
  digitalWrite(DIR_PIN, TEST_DIR_LEVEL);
  digitalWrite(ENA_PIN, LOW);
  pinMode(ENA_PIN, OUTPUT);
  motor.setMaxSpeed(MAX_SPEED);
  motor.setAcceleration(ACCELERATION);
  Serial.begin(115200);
  Serial.println(F("ONE DIRECTION TEST: automatically repeating 3200-pulse turns."));
  Serial.println(F("s = immediate stop/hold; r = restart. ENABLE stays LOW."));
  startTurn();
}

void loop() {
  for (byte count = 0; count < 32 && Serial.available(); ++count) {
    const char command = Serial.read();
    if (command == 's' || command == 'S') {
      motor.setCurrentPosition(0);  // Cancel the move and reset speed to zero.
      running = false;
      Serial.println(F("STOPPED: holding. Send r to restart."));
    } else if ((command == 'r' || command == 'R') && !running) {
      startTurn();
      running = true;
      Serial.println(F("RUNNING: same direction, 3200 pulses per turn."));
    }
  }
  if (!running) return;
  motor.run();
  if (motor.distanceToGo() == 0) startTurn();
}
