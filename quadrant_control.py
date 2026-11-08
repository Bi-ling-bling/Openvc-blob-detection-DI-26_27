"""Nonblocking quadrant protocol client; no OpenCV or serial dependency at import."""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

STEPS_PER_REV = 3200
STEPS_PER_QUADRANT = 800
MAX_SPEED = 600.0
ACCELERATION = 300.0


def quadrant_for_bits(bits: str) -> int:
    """Bits stay in the reader's left-to-right order; retain all four bits."""
    if not isinstance(bits, str) or len(bits) != 4 or set(bits) - {"0", "1"}:
        raise ValueError("Expected exactly four binary digits")
    return int(bits[:2], 2) + 1


def shortest_delta(position: int, quadrant: int) -> int:
    if quadrant not in (1, 2, 3, 4):
        raise ValueError("Quadrant must be 1..4")
    delta = ((quadrant - 1) * STEPS_PER_QUADRANT - position) % STEPS_PER_REV
    return delta - STEPS_PER_REV if delta > STEPS_PER_REV // 2 else delta


@dataclass
class Pending:
    token: int
    command: str
    argument: int | None
    sent: float
    acknowledged: bool = False


class QuadrantController:
    """Call poll() every camera frame. All reads/writes use nonblocking transport.

    Only a DONE reply establishes a reached quadrant. No automatic command
    retries, reconnects, or restoration of calibration after resets/faults.
    """

    def __init__(self, transport, clock=time.monotonic):
        self.transport = transport
        self.clock = clock
        self.ready = False
        self.calibrated = False
        self.failed = False
        self.pending: Pending | None = None
        self.bits: str | None = None
        self.reached: int | None = None
        self.message = "Waiting for Arduino boot; then align zero and press z"
        self._buffer = bytearray()
        self._token = 0
        self._opened = clock()
        self._heartbeat = clock()
        self._last_reply = clock()
        self.reset_count = 0

    def observe(self, bits: str | None):
        """Pass only a five-frame confirmed code, or None when unconfirmed."""
        if bits is not None:
            try:
                quadrant_for_bits(bits)
            except ValueError:
                bits = None
        self.bits = bits

    def _write(self, line: str):
        data = (line + "\n").encode("ascii")
        if self.transport.write(data) != len(data):
            raise OSError("Incomplete serial write")

    def _command(self, command: str, argument: int | None = None):
        self._token = self._token % 999999 + 1
        self.pending = Pending(self._token, command, argument, self.clock())
        line = f"{command} {self._token}"
        if argument is not None:
            line += f" {argument}"
        self._write(line)
        self.message = f"Waiting: {command}" + (f" {argument}" if argument is not None else "")

    def zero(self):
        if self.ready and not self.failed and self.pending is None:
            # Require a fresh five-frame confirmation following calibration.
            self.bits = None
            self.calibrated = False
            self.reached = None
            try:
                self._command("ZERO")
            except (OSError, ValueError) as exc:
                self._fail(str(exc))

    def jog(self, pulses: int):
        if (self.ready and not self.failed and not self.calibrated
                and self.pending is None and pulses in (-40, 40)):
            try:
                self._command("JOG", pulses)
            except (OSError, ValueError) as exc:
                self._fail(str(exc))

    def stop(self):
        """Preempt any motion immediately; manual zero is required afterwards."""
        self.calibrated = False
        self.bits = None
        self.reached = None
        if self.ready and not self.failed:
            try:
                self._command("STOP")
            except (OSError, ValueError) as exc:
                self._fail(str(exc))

    def _fail(self, reason: str):
        # Best effort STOP. Firmware also times out if heartbeats cease in motion.
        try:
            self._token = self._token % 999999 + 1
            self._write(f"STOP {self._token}")
        except (OSError, ValueError):
            pass
        self.failed = True
        self.calibrated = False
        self.ready = False
        self.pending = None
        self.bits = None
        self.reached = None
        self.message = f"Motor link fault: {reason}; restart and zero again"

    def _receive(self, line: str):
        self._last_reply = self.clock()
        fields = line.split()
        if fields == ["READY", "NEED_ZERO"]:
            self.reset_count += 1
            self.ready = True
            self.calibrated = False
            self.pending = None
            self.bits = None
            self.reached = None
            self.message = "Align Q1 zero with [ / ]; press z to calibrate"
            return
        if fields == ["PONG"]:
            return
        if fields[:1] == ["FAULT"]:
            raise ValueError(line)
        if len(fields) < 2 or fields[0] not in ("ACK", "DONE", "ERR"):
            raise ValueError(f"Malformed reply: {line}")
        try:
            token = int(fields[1])
        except ValueError as exc:
            raise ValueError(f"Malformed reply: {line}") from exc
        if fields[0] == "ERR":
            raise ValueError(line)
        pending = self.pending
        if pending is None or token != pending.token:
            return  # A STOP may have superseded this reply.
        if fields[0] == "ACK":
            if len(fields) != 2:
                raise ValueError(line)
            pending.acknowledged = True
            return
        if not pending.acknowledged:
            raise ValueError("DONE received without ACK")
        if pending.command == "Q":
            q = pending.argument
            expected = ["DONE", str(token), "Q", str(q), "POS", str((q - 1) * 800)]
            if fields != expected:
                raise ValueError(f"Unexpected target completion: {line}")
            self.reached = q
            self.message = f"Holding Q{q} at {(q - 1) * 90} deg"
        elif pending.command == "ZERO":
            if fields != ["DONE", str(token), "ZERO", "POS", "0"]:
                raise ValueError(line)
            self.calibrated = True
            self.reached = 1
            self.message = "Zero calibrated; holding Q1"
        elif pending.command == "STOP":
            if fields != ["DONE", str(token), "STOP", "NEED_ZERO"]:
                raise ValueError(line)
            self.message = "Stopped; align Q1 and press z to recalibrate"
        elif pending.command == "JOG":
            if len(fields) != 5 or fields[2:4] != ["JOG", "POS"]:
                raise ValueError(line)
            int(fields[-1])
            self.message = "Jog complete; align Q1, then press z"
        self.pending = None

    def poll(self):
        if self.failed:
            return
        try:
            self._buffer.extend(self.transport.read(4096))
            if len(self._buffer) > 4096:
                raise ValueError("Oversized serial reply")
            while b"\n" in self._buffer:
                line, _, rest = self._buffer.partition(b"\n")
                self._buffer = bytearray(rest)
                if line.strip():
                    self._receive(line.decode("ascii").strip())
            now = self.clock()
            if not self.ready:
                if now - self._opened > 6:
                    raise OSError("No READY from Arduino")
                return
            if now - self._heartbeat >= 0.5:
                self._write("PING")
                self._heartbeat = now
            if now - self._last_reply > 3:
                raise OSError("Arduino heartbeat lost")
            if self.pending is not None:
                limit = 20 if self.pending.acknowledged else 2
                if now - self.pending.sent > limit:
                    raise OSError("Command acknowledgment/completion timed out")
            elif self.calibrated and self.bits is not None:
                q = quadrant_for_bits(self.bits)
                if q != self.reached:
                    self._command("Q", q)
        except (OSError, ValueError, UnicodeError) as exc:
            self._fail(str(exc))

    def close(self):
        self.stop()
        self.transport.close()


class SimulatedTransport:
    """Time-based protocol simulation. Never opens a serial port or toggles pins."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.output = bytearray(b"READY NEED_ZERO\n")
        self.calibrated = False
        self.position = 0
        self.motion = None
        self.commands = []

    def _emit(self, line):
        self.output.extend((line + "\n").encode("ascii"))

    def write(self, data):
        line = data.decode("ascii").strip()
        self.commands.append(line)
        if line == "PING":
            self._emit("PONG")
            return len(data)
        fields = line.split()
        command, token = fields[:2]
        if command == "STOP":
            self.motion = None
            self.calibrated = False
            self._emit(f"ACK {token}")
            self._emit(f"DONE {token} STOP NEED_ZERO")
        elif self.motion is not None:
            self._emit(f"ERR {token} BUSY")
        elif command == "ZERO":
            self.position = 0
            self.calibrated = True
            self._emit(f"ACK {token}")
            self._emit(f"DONE {token} ZERO POS 0")
        elif command == "Q" and not self.calibrated:
            self._emit(f"ERR {token} NEED_ZERO")
        elif command in ("Q", "JOG"):
            argument = int(fields[2])
            delta = shortest_delta(self.position, argument) if command == "Q" else argument
            target = (self.position + delta) % 3200
            self._emit(f"ACK {token}")
            distance = abs(delta)
            ramp_distance = MAX_SPEED ** 2 / ACCELERATION
            duration = (2 * math.sqrt(distance / ACCELERATION) if distance < ramp_distance
                        else distance / MAX_SPEED + MAX_SPEED / ACCELERATION)
            reply = (f"DONE {token} Q {argument} POS {target}" if command == "Q"
                     else f"DONE {token} JOG POS {target}")
            self.motion = (self.clock() + duration, target, reply)
        else:
            self._emit(f"ERR {token} BAD_COMMAND")
        return len(data)

    def read(self, size):
        if self.motion is not None and self.clock() >= self.motion[0]:
            _, self.position, reply = self.motion
            self.motion = None
            self._emit(reply)
        data = bytes(self.output[:size])
        del self.output[:size]
        return data

    def close(self):
        self.motion = None


def open_controller(port: str | None = None, dry_run=False):
    if dry_run:
        return QuadrantController(SimulatedTransport())
    # Keep detection-only and dry-run usable without pyserial installed.
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("Install pyserial in your venv: python -m pip install pyserial") from exc
    return QuadrantController(serial.Serial(port, 115200, timeout=0, write_timeout=0))


def main():
    """Camera-free, accelerated-time demo using the same protocol client."""
    import argparse

    parser = argparse.ArgumentParser(description="Simulate quadrant commands; no hardware is opened")
    parser.add_argument("bits", nargs="*", default=["0011", "0101", "1010", "1111", "0011"])
    args = parser.parse_args()
    for bits in args.bits:
        try:
            quadrant_for_bits(bits)
        except ValueError as exc:
            parser.error(str(exc))
    now = [0.0]
    clock = lambda: now[0]
    transport = SimulatedTransport(clock)
    controller = QuadrantController(transport, clock)
    controller.poll()
    controller.zero()
    controller.poll()
    print("DRY RUN: simulated zero established; no physical motor connected")
    for bits in args.bits:
        q = quadrant_for_bits(bits)
        delta = shortest_delta(transport.position, q)
        controller.observe(bits)
        controller.poll()
        for _ in range(250):
            now[0] += 0.1
            controller.poll()
            if controller.pending is None:
                break
        if controller.failed or controller.pending is not None:
            raise RuntimeError(controller.message)
        print(f"{bits} -> Q{q}: {delta:+d} pulses; {controller.message}")
    controller.close()


if __name__ == "__main__":
    main()
