// Arduino Mega 2560 + TB6600. Install AccelStepper 1.64 via Library Manager.
#include <AccelStepper.h>
#include <stdlib.h>
#include <string.h>
#include "positioning.h"

const int STEP_PIN = 2;
const int DIR_PIN = 3;
const int ENA_PIN = 4;
const int STEPS_PER_REV = 3200;
const int POSITIVE_DIR_LEVEL = HIGH;  // Flip HIGH/LOW only if positive is reversed.
const float MAX_SPEED = 600.0;        // pulses / second
const float ACCELERATION = 300.0;     // pulses / second squared
const unsigned long LINK_TIMEOUT_MS = 3000;

// Explicit TB6600 direction setup and pulse width, including after a reversal.
class TB6600Stepper : public AccelStepper {
 public:
  TB6600Stepper() : AccelStepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN) {}
 protected:
  void step(long) override {
    digitalWrite(DIR_PIN, speed() > 0 ? POSITIVE_DIR_LEVEL : !POSITIVE_DIR_LEVEL);
    delayMicroseconds(10);
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(STEP_PIN, LOW);
  }
};

TB6600Stepper motor;
bool calibrated = false;
bool moving = false;
bool jogging = false;
unsigned long activeId = 0;
int activeQuadrant = 0;
unsigned long lastContact = 0;
char inputLine[48];
byte inputLength = 0;
bool discardLine = false;

void ack(unsigned long id) {
  Serial.print(F("ACK ")); Serial.println(id);
}

void error(unsigned long id, const __FlashStringHelper *reason) {
  Serial.print(F("ERR ")); Serial.print(id); Serial.print(' '); Serial.println(reason);
}

void haltMotion() {
  // Immediate pulse stop. Do not drop ENABLE: preserve the working LOW hold.
  motor.setCurrentPosition(motor.currentPosition());
  moving = false;
  calibrated = false;
}

void completed() {
  // Keep the software coordinate bounded to one revolution after every move.
  motor.setCurrentPosition(normalizedPosition(motor.currentPosition()));
  Serial.print(F("DONE ")); Serial.print(activeId);
  if (jogging) {
    Serial.print(F(" JOG POS "));
  } else {
    Serial.print(F(" Q ")); Serial.print(activeQuadrant); Serial.print(F(" POS "));
  }
  Serial.println(motor.currentPosition());
  moving = false;
}

bool parseNumber(const char *text, long &value) {
  if (!text || !*text) return false;
  char *end;
  // Limit numeric lengths before strtol (AVR long is signed 32-bit).
  if (strlen(text) > 7) return false;
  value = strtol(text, &end, 10);
  return *end == '\0';
}

void handleLine(char *line) {
  if (strcmp(line, "PING") == 0) {
    lastContact = millis();
    Serial.println(F("PONG"));
    return;
  }
  char *context;
  char *command = strtok_r(line, " ", &context);
  char *idText = strtok_r(NULL, " ", &context);
  char *argumentText = strtok_r(NULL, " ", &context);
  char *extra = strtok_r(NULL, " ", &context);
  long parsedId = 0, argument = 0;
  if (!command || !parseNumber(idText, parsedId) || parsedId < 1 || parsedId > 999999) {
    error(0, F("BAD_COMMAND")); return;
  }
  unsigned long id = (unsigned long)parsedId;
  bool quadrant = strcmp(command, "Q") == 0;
  bool jog = strcmp(command, "JOG") == 0;
  bool zero = strcmp(command, "ZERO") == 0;
  bool stop = strcmp(command, "STOP") == 0;
  if (extra || !(quadrant || jog || zero || stop)
      || ((quadrant || jog) && !parseNumber(argumentText, argument))
      || ((zero || stop) && argumentText)) {
    error(id, F("BAD_COMMAND")); return;
  }
  if ((quadrant && (argument < 1 || argument > 4))
      || (jog && (argument == 0 || argument < -800 || argument > 800))) {
    error(id, F("RANGE")); return;
  }
  lastContact = millis();
  if (stop) {
    haltMotion();
    ack(id);
    Serial.print(F("DONE ")); Serial.print(id); Serial.println(F(" STOP NEED_ZERO"));
    return;
  }
  if (moving) { error(id, F("BUSY")); return; }
  if (zero) {
    motor.setCurrentPosition(0);
    calibrated = true;
    ack(id);
    Serial.print(F("DONE ")); Serial.print(id); Serial.println(F(" ZERO POS 0"));
    return;
  }
  if (quadrant && !calibrated) { error(id, F("NEED_ZERO")); return; }
  if (jog && calibrated) { error(id, F("ALREADY_ZEROED")); return; }
  jogging = jog;
  activeId = id;
  activeQuadrant = (int)argument;
  long delta = jog ? argument : shortestDelta(motor.currentPosition(), (int)argument);
  motor.moveTo(motor.currentPosition() + delta);
  moving = true;
  ack(id);
  if (delta == 0) completed();
}

void setup() {
  pinMode(STEP_PIN, OUTPUT);
  digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT);
  digitalWrite(ENA_PIN, LOW);
  pinMode(ENA_PIN, OUTPUT);
  motor.setMaxSpeed(MAX_SPEED);
  motor.setAcceleration(ACCELERATION);
  Serial.begin(115200);
  lastContact = millis();
  Serial.println(F("READY NEED_ZERO"));
}

void loop() {
  // Bound input processing so continuous serial traffic cannot starve stepping.
  for (byte count = 0; count < 32 && Serial.available(); ++count) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      if (discardLine) error(0, F("LINE_TOO_LONG"));
      else if (inputLength) {
        inputLine[inputLength] = '\0';
        handleLine(inputLine);
      }
      inputLength = 0;
      discardLine = false;
    } else if (ch < 32 || ch > 126 || inputLength >= sizeof(inputLine) - 1) {
      discardLine = true;
    } else if (!discardLine) {
      inputLine[inputLength++] = ch;
    }
  }
  if (moving && millis() - lastContact > LINK_TIMEOUT_MS) {
    haltMotion();
    Serial.println(F("FAULT LINK_TIMEOUT NEED_ZERO"));
  }
  if (moving) {
    motor.run();
    if (motor.distanceToGo() == 0) completed();
  }
}
