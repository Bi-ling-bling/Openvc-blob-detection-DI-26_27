# Quadrant serial protocol, version 1

USB serial, **115200 baud, 8N1**, ASCII lines ending in LF (`\n`). CR is ignored.
Commands are case-sensitive. Maximum input is 47 characters before LF; longer
or nonprintable lines are discarded as a whole. Numbers are decimal. IDs are
1–999999 and correlate ACK and completion; ID 0 is reserved for parser errors.
The client sends only one command at a time, except STOP can preempt any command.
There is no automatic retry or persistent command-ID cache.

Boot/reset always emits `READY NEED_ZERO`. No absolute quadrant move is accepted
until manual zero is established. No previous calibration is restored from disk
or EEPROM. All positions below are pulse coordinates relative to declared zero.

| Host command | Arduino response | Behavior |
|---|---|---|
| `PING` | `PONG` | Link heartbeat; no movement. |
| `ZERO id` | `ACK id`, then `DONE id ZERO POS 0` | While idle, declare current physical position Q1/zero; no pulses. |
| `JOG id pulses` | `ACK id`, then `DONE id JOG POS p` | Before calibration only; nonzero −800..800 pulses relative motion, with acceleration. GUI uses ±40. Jog completion does not calibrate. |
| `Q id q` | `ACK id`, then `DONE id Q q POS p` | After calibration only; q=1..4; shortest path to p=0/800/1600/2400. |
| `STOP id` | `ACK id`, then `DONE id STOP NEED_ZERO` | Immediate pulse stop, even during motion; retains ENABLE LOW, cancels prior command, invalidates zero. |

ACK means accepted; DONE means the requested pulse movement finished. If already
at the requested quadrant, both replies are sent without any pulses. An interrupted
command gets no DONE; the STOP response supersedes it. No quadrants are queued in
the Arduino. Additional Q/ZERO/JOG commands during motion return `ERR id BUSY`.

Typical exchange (each displayed line ends in LF):

```text
Arduino -> READY NEED_ZERO
Host    -> ZERO 1
Arduino -> ACK 1
Arduino -> DONE 1 ZERO POS 0
Host    -> Q 2 4
Arduino -> ACK 2
Host    -> PING
Arduino -> PONG
Arduino -> DONE 2 Q 4 POS 2400
```

That Q1 → Q4 move emits **800 pulses in the negative direction**, not 2400
positive pulses. Normal positioning accelerates/decelerates; an exact half turn
chooses the positive direction. Position is normalized to 0..3199 on completion,
including jogs, but a jog coordinate is never considered a calibrated position.
`POS` is the software pulse count, not a sensor/encoder measurement.

Rejected commands emit `ERR id reason`, without ACK or command-induced movement:

| Reason | Meaning |
|---|---|
| `BAD_COMMAND` | Unknown command, invalid ID, invalid number, or wrong argument count. |
| `RANGE` | Quadrant outside 1..4 or jog outside allowed nonzero ±800 pulses. |
| `LINE_TOO_LONG` | Whole oversized/nonprintable line discarded (ID 0). |
| `BUSY` | Motion active; only STOP/PING can interrupt/interact with it. |
| `NEED_ZERO` | Absolute quadrant command before calibration. |
| `ALREADY_ZEROED` | Jog requested after calibration; STOP first to re-align. |

The Python controller sends a heartbeat every 0.5 seconds without blocking the
camera loop. During motion, the Arduino requires valid contact within 3000 ms;
on timeout it immediately stops pulses, invalidates calibration, and emits
`FAULT LINK_TIMEOUT NEED_ZERO`. It never resumes that movement automatically.

Python waits up to 6 seconds for boot, 2 seconds for a command ACK, and 20 seconds
from command transmission for DONE (with live heartbeat replies). A silent
Arduino for more than 3 seconds also faults the client. Each timeout, serial
failure, malformed reply, ERR, wrong completion position, or FAULT causes a
best-effort STOP and disarms the client. Restart it and manually zero again.
An unexpected READY clears outstanding work and calibration immediately.
STALE ACK/DONE IDs after STOP are ignored; physical state is never inferred from
an old completion. No automatic reconnect or command replay is performed.

Only a five-frame-confirmed four-bit reading can request a quadrant. While a
command is outstanding, the Python application retains the latest confirmed
reading, discards it if it becomes unreadable/unconfirmed, and sends it after
completion only when its quadrant differs from the reached quadrant. All four
bits remain in the application; the Arduino receives just the quadrant. When
software STOP is used, the frame-confirmation history is also cleared.
