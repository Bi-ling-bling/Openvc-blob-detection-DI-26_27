// Host Arduino I/O shim. Motion calculations use the real AccelStepper library.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <sstream>
#include <string>

using byte = uint8_t;
using boolean = bool;
using std::max;
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define F(text) reinterpret_cast<const __FlashStringHelper *>(text)
class __FlashStringHelper;

template <typename T> T constrain(T value, T low, T high) {
  return std::min(std::max(value, low), high);
}

extern uint64_t simulatedMicros;
inline unsigned long micros() { return simulatedMicros; }
inline unsigned long millis() { return simulatedMicros / 1000; }
inline void delayMicroseconds(unsigned int delay) { simulatedMicros += delay; }
inline void yield() {}
void pinMode(int pin, int mode);
void digitalWrite(int pin, int value);

class TestSerial {
 public:
  std::deque<char> input;
  std::string output;
  void begin(long baud) { if (baud != 115200) std::abort(); }
  int available() { return input.size(); }
  char read() { char result = input.front(); input.pop_front(); return result; }
  void print(const __FlashStringHelper *text) { output += reinterpret_cast<const char *>(text); }
  template <typename T> void print(T value) {
    std::ostringstream stream; stream << value; output += stream.str();
  }
  template <typename T> void println(T value) { print(value); output += '\n'; }
};

extern TestSerial Serial;
