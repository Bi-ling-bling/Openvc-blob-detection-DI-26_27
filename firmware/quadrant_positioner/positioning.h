#pragma once

// Shared by the sketch and native tests. Positive ties (180 degrees) are fixed.
inline long normalizedPosition(long position) {
  long result = position % 3200L;
  return result < 0 ? result + 3200L : result;
}

inline long shortestDelta(long position, int quadrant) {
  long delta = normalizedPosition((quadrant - 1) * 800L - normalizedPosition(position));
  return delta > 1600L ? delta - 3200L : delta;
}
