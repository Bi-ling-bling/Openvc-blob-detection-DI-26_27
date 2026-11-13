import unittest

from quadrant_control import QuadrantController, SimulatedTransport, quadrant_for_bits, shortest_delta


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.transport = SimulatedTransport(lambda: self.now)
        self.controller = QuadrantController(self.transport, lambda: self.now)
        self.controller.poll()

    def advance(self, seconds=6):
        for _ in range(round(seconds * 10)):
            self.now += 0.1
            self.controller.poll()

    def zero(self):
        self.controller.zero()
        self.controller.poll()
        self.assertTrue(self.controller.calibrated)

    def targets(self):
        return [line for line in self.transport.commands if line.startswith("Q ")]

    def test_all_sixteen_patterns(self):
        for code in range(16):
            self.assertEqual(quadrant_for_bits(f"{code:04b}"), code // 4 + 1)

    def test_invalid_patterns(self):
        for bits in (None, "", "000", "00000", "10?0", " 001", 1010, "abcd"):
            with self.subTest(bits=bits):
                with self.assertRaises(ValueError):
                    quadrant_for_bits(bits)
                self.controller.observe(bits)
                self.controller.poll()
                self.assertEqual(self.targets(), [])

    def test_all_shortest_paths_and_wrapped_positions(self):
        for position in range(-6400, 6401, 40):
            for q in range(1, 5):
                delta = shortest_delta(position, q)
                self.assertLessEqual(abs(delta), 1600)
                self.assertEqual((position + delta) % 3200, (q - 1) * 800)
        self.assertEqual(shortest_delta(0, 4), -800)
        self.assertEqual(shortest_delta(2400, 1), 800)
        self.assertEqual(shortest_delta(0, 3), 1600)

    def test_no_motion_without_zero(self):
        self.controller.observe("1111")
        self.advance()
        self.assertEqual(self.targets(), [])

    def test_all_quadrants_ack_done_and_repeat_suppression(self):
        self.zero()
        for q, bits in enumerate(("0011", "0101", "1010", "1111"), 1):
            self.controller.observe(bits)
            self.controller.poll()
            self.advance()
            self.assertEqual(self.controller.reached, q)
            self.assertEqual(self.transport.position, (q - 1) * 800)
        count = len(self.targets())
        for bits in ("1111", None, "1100", "1110", "1111"):
            self.controller.observe(bits)
            self.advance()
        self.assertEqual(len(self.targets()), count)
        self.assertEqual(self.controller.bits, "1111")

    def test_only_latest_stable_target_after_inflight_motion(self):
        self.zero()
        self.controller.observe("0101")
        self.controller.poll()
        self.controller.observe("1010")
        self.controller.observe("1111")
        self.advance(12)
        self.assertEqual([line.split()[-1] for line in self.targets()], ["2", "4"])
        self.assertEqual(self.controller.reached, 4)

    def test_unreadable_cancels_unsent_target(self):
        self.zero()
        self.controller.observe("0101")
        self.controller.poll()
        self.controller.observe("1111")
        self.controller.observe(None)
        self.advance()
        self.assertEqual(len(self.targets()), 1)
        self.assertEqual(self.controller.reached, 2)

    def test_stop_preempts_and_requires_new_zero(self):
        self.zero()
        self.controller.observe("1010")
        self.controller.poll()
        self.controller.stop()
        self.controller.poll()
        self.assertIsNone(self.transport.motion)
        self.assertFalse(self.controller.calibrated)
        self.controller.observe("1111")
        self.advance()
        self.assertEqual(len(self.targets()), 1)
        self.assertFalse(self.controller.failed)

    def test_jog_only_before_zero(self):
        self.controller.jog(-40)
        self.advance(2)
        self.assertFalse(self.controller.failed)
        self.assertFalse(self.controller.calibrated)
        self.zero()
        before = len(self.transport.commands)
        self.controller.jog(40)
        self.assertEqual(len(self.transport.commands), before)

    def test_unexpected_reset_invalidates_position(self):
        self.zero()
        self.controller.observe("1010")
        self.controller.poll()
        self.transport.motion = None
        self.transport.calibrated = False
        self.transport._emit("READY NEED_ZERO")
        self.controller.poll()
        self.assertFalse(self.controller.calibrated)
        self.assertIsNone(self.controller.pending)
        self.assertIsNone(self.controller.bits)

    def test_bad_reply_or_device_fault_fails_closed(self):
        for line in ("garbage", "ACK nope", "FAULT LINK_TIMEOUT NEED_ZERO", "ERR 1 RANGE"):
            with self.subTest(line=line):
                self.setUp()
                self.zero()
                self.transport._emit(line)
                self.controller.poll()
                self.assertTrue(self.controller.failed)
                self.assertFalse(self.controller.calibrated)
                self.assertTrue(self.transport.commands[-1].startswith("STOP "))

    def test_wrong_done_position_is_rejected(self):
        self.zero()
        self.controller.observe("1111")
        self.controller.poll()
        token = self.controller.pending.token
        self.transport._emit(f"DONE {token} Q 4 POS 0")
        self.controller.poll()
        self.assertTrue(self.controller.failed)

    def test_serial_read_and_write_failures(self):
        self.zero()
        self.transport.read = lambda size: (_ for _ in ()).throw(OSError("USB unplugged"))
        self.controller.poll()
        self.assertTrue(self.controller.failed)
        self.setUp()
        self.transport.write = lambda data: (_ for _ in ()).throw(OSError("USB unplugged"))
        self.controller.zero()
        self.assertTrue(self.controller.failed)

    def test_no_ack_timeout(self):
        self.transport.write = lambda data: len(data)
        self.controller.zero()
        self.advance(2.5)
        self.assertTrue(self.controller.failed)

    def test_heartbeat_and_boot_timeouts(self):
        self.transport.write = lambda data: len(data)
        self.advance(3.5)
        self.assertTrue(self.controller.failed)
        self.setUp()
        self.controller.ready = False
        self.transport.output.clear()
        self.advance(6.5)
        self.assertTrue(self.controller.failed)

    def test_done_timeout_despite_live_heartbeat(self):
        self.zero()
        self.controller.observe("1010")
        self.controller.poll()
        end, position, reply = self.transport.motion
        self.transport.motion = (end + 100, position, reply)
        self.advance(21)
        self.assertTrue(self.controller.failed)

    def test_fragmented_serial_replies(self):
        self.controller.zero()
        output = bytes(self.transport.output)
        self.transport.output.clear()
        for value in output:
            self.transport.output.append(value)
            self.controller.poll()
        self.assertTrue(self.controller.calibrated)

    def test_startup_chatter_then_ready_allows_calibration_and_jog(self):
        self.transport = SimulatedTransport(lambda: self.now)
        self.transport.output = bytearray(b"old test banner\r\n\x00\xff\r\nACK 90\nDONE 90 ZERO POS 0\n")
        self.controller = QuadrantController(self.transport, lambda: self.now)
        with self.assertLogs("quadrant_control", level="WARNING"):
            self.controller.poll()
        self.assertFalse(self.controller.ready)
        self.assertFalse(self.controller.calibrated)
        self.assertFalse(self.controller.failed)
        self.controller.zero()
        self.controller.jog(40)
        self.assertEqual(self.transport.commands, [])
        self.transport._emit("READY NEED_ZERO")
        self.controller.poll()
        self.controller.jog(40)
        self.advance(2)
        self.assertEqual(self.transport.position, 40)
        self.assertFalse(self.controller.failed)
        self.assertFalse(self.controller.calibrated)
        self.zero()

    def test_old_firmware_times_out_with_upload_instructions(self):
        self.transport.output = bytearray(b"Starting continuous motor test\n")
        self.controller = QuadrantController(self.transport, lambda: self.now)
        with self.assertLogs("quadrant_control", level="WARNING") as captured:
            self.advance(6.5)
        self.assertTrue(self.controller.failed)
        self.assertFalse(self.controller.calibrated)
        self.assertIn("Upload quadrant_positioner.ino", self.controller.fault_reason)
        self.assertIn("Starting continuous motor test", self.controller.fault_reason)
        self.assertIn("115200", self.controller.fault_reason)
        self.assertIn("Upload quadrant_positioner.ino", "\n".join(captured.output))
        self.assertFalse(any(command.startswith(("Q ", "JOG ", "ZERO "))
                             for command in self.transport.commands))

    def test_control_bytes_after_ready_are_visible_and_still_disarm(self):
        self.transport.output.extend(b"\x00\n")
        with self.assertLogs("quadrant_control", level="ERROR") as captured:
            self.controller.poll()
        self.assertTrue(self.controller.failed)
        self.assertIn("\\x00", self.controller.fault_reason)
        self.assertIn("\\x00", "\n".join(captured.output))
        self.assertIn("see terminal", self.controller.message)

    def test_non_ascii_after_ready_still_disarms(self):
        self.transport.output.extend(b"\xff\n")
        with self.assertLogs("quadrant_control", level="ERROR"):
            self.controller.poll()
        self.assertTrue(self.controller.failed)
        self.assertIn("Non-ASCII", self.controller.fault_reason)

    def test_serial_debug_logs_complete_rx_and_tx(self):
        with self.assertLogs("quadrant_control", level="DEBUG") as captured:
            self.zero()
        output = "\n".join(captured.output)
        self.assertIn("Arduino TX: 'ZERO 1'", output)
        self.assertIn("DONE 1 ZERO POS 0", output)


if __name__ == "__main__":
    unittest.main()
