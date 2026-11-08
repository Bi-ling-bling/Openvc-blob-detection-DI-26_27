#include "Arduino.h"
#include <cassert>
#include <iostream>
#include <vector>

uint64_t simulatedMicros = 0;
TestSerial Serial;
struct Pulse { uint64_t time; int direction; };
std::vector<Pulse> pulses;
int pinValues[5] = {};
uint64_t lastDirection = 0, pulseStart = 0;

void pinMode(int pin, int mode) {
  assert(pin == 2 || pin == 3 || pin == 4);
  assert(mode == OUTPUT);
}

void digitalWrite(int pin, int value) {
  assert(pin == 2 || pin == 3 || pin == 4);
  if (pin == 4) assert(value == LOW);
  if (pin == 3) lastDirection = simulatedMicros;
  if (pin == 2 && value == HIGH) {
    assert(simulatedMicros - lastDirection >= 10);
    pulseStart = simulatedMicros;
    pulses.push_back({simulatedMicros, pinValues[3]});
  }
  if (pin == 2 && value == LOW && pinValues[2] == HIGH) {
    assert(simulatedMicros - pulseStart >= 10);
  }
  pinValues[pin] = value;
}

#include "../../firmware/quadrant_positioner/quadrant_positioner.ino"

void send(const std::string &line) {
  for (char value : line + "\n") Serial.input.push_back(value);
  while (Serial.available()) loop();
}

void finishMotion(bool heartbeat = true) {
  uint64_t lastPing = simulatedMicros;
  for (int count = 0; moving && count < 200000; ++count) {
    simulatedMicros += 100;
    if (heartbeat && simulatedMicros - lastPing >= 500000) {
      send("PING"); lastPing = simulatedMicros;
    }
    loop();
  }
  assert(!moving);
}

int main() {
  setup();
  assert(Serial.output == "READY NEED_ZERO\n");
  assert(pulses.empty() && pinValues[4] == LOW);
  send("Q 1 4");
  assert(Serial.output.find("ERR 1 NEED_ZERO") != std::string::npos);
  assert(pulses.empty());
  send("JOG 2 -40"); finishMotion();
  assert(pulses.size() == 40 && !calibrated);
  send("ZERO 3");
  assert(calibrated && motor.currentPosition() == 0);

  for (long position = -6400; position <= 6400; position += 40) {
    for (int q = 1; q <= 4; ++q) {
      long delta = shortestDelta(position, q);
      assert(std::abs(delta) <= 1600);
      assert(normalizedPosition(position + delta) == (q - 1) * 800);
    }
  }

  // Real acceleration, pulse count, negative shortest path, and final ACK/DONE.
  pulses.clear();
  send("Q 4 4"); finishMotion();
  assert(pulses.size() == 800 && motor.currentPosition() == 2400);
  for (const auto &pulse : pulses) assert(pulse.direction == LOW);
  assert(Serial.output.find("ACK 4\n") != std::string::npos);
  assert(Serial.output.find("DONE 4 Q 4 POS 2400\n") != std::string::npos);
  auto interval = [](size_t index) { return pulses[index].time - pulses[index - 1].time; };
  assert(interval(2) > interval(100));       // Accelerating.
  assert(interval(799) > interval(700));     // Decelerating.
  for (size_t i = 1; i < pulses.size(); ++i) assert(interval(i) >= 1000000 / MAX_SPEED);
  size_t previous = pulses.size();
  send("Q 5 4");
  assert(!moving && pulses.size() == previous);
  send("Q 6 1"); finishMotion();
  assert(pulses.size() - previous == 800);
  assert(motor.currentPosition() == 0);
  for (size_t i = previous; i < pulses.size(); ++i) assert(pulses[i].direction == HIGH);

  // All sixteen quadrant transitions, with exact pulse counts and completion.
  unsigned int id = 10;
  for (int from = 1; from <= 4; ++from) {
    for (int to = 1; to <= 4; ++to) {
      motor.setCurrentPosition((from - 1) * 800L);
      long delta = shortestDelta(motor.currentPosition(), to);
      previous = pulses.size();
      send("Q " + std::to_string(id) + " " + std::to_string(to)); finishMotion();
      assert(pulses.size() - previous == static_cast<size_t>(std::abs(delta)));
      assert(motor.currentPosition() == (to - 1) * 800);
      assert(Serial.output.find("DONE " + std::to_string(id++) + " Q " + std::to_string(to)) != std::string::npos);
    }
  }
  previous = pulses.size();
  for (const char *line : {"Q 30 0", "Q 31 5", "Q 32 2 extra", "Q x 2", "ZERO 33 extra",
                                 "JOG 34 900", "Q 99999999 1", "unknown 35", "Q 36 1x"}) send(line);
  send(std::string(80, 'X'));
  assert(pulses.size() == previous && !moving);
  assert(Serial.output.find("LINE_TOO_LONG") != std::string::npos);

  send("Q 40 2");
  send("ZERO 41");
  assert(Serial.output.find("ERR 41 BUSY") != std::string::npos);
  send("STOP 42");
  assert(!moving && !calibrated && pinValues[4] == LOW);
  previous = pulses.size();
  finishMotion();
  assert(pulses.size() == previous);
  assert(Serial.output.find("DONE 42 STOP NEED_ZERO") != std::string::npos);
  send("ZERO 43"); send("Q 44 3"); finishMotion(false);
  assert(!calibrated);
  assert(Serial.output.find("FAULT LINK_TIMEOUT NEED_ZERO") != std::string::npos);
  std::cout << "Firmware tests passed: pin levels, TB6600 timing, acceleration/deceleration,\n"
               "all quadrant paths, pulse counts, protocol validation, STOP and link watchdog.\n";
}
