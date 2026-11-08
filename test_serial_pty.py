"""Exercise pyserial itself using Linux virtual serial terminals, without a motor."""
import os
import unittest

from quadrant_control import QuadrantController

try:
    import serial
except ImportError:
    serial = None


@unittest.skipUnless(serial is not None and hasattr(os, "openpty"), "Requires pyserial and POSIX PTYs")
class SerialTerminalTests(unittest.TestCase):
    def setUp(self):
        self.master, self.slave = os.openpty()
        self.port = serial.Serial(os.ttyname(self.slave), 115200, timeout=0, write_timeout=0)
        self.controller = QuadrantController(self.port)
        os.write(self.master, b"READY NEED_ZERO\n")
        self.controller.poll()

    def tearDown(self):
        self.port.close()
        if self.master is not None:
            os.close(self.master)
        os.close(self.slave)

    def test_real_serial_ack_and_completion(self):
        self.controller.zero()
        self.assertEqual(os.read(self.master, 128), b"ZERO 1\n")
        os.write(self.master, b"ACK 1\nDONE 1 ZERO POS 0\n")
        self.controller.poll()
        self.assertTrue(self.controller.calibrated)
        self.controller.observe("1111")
        self.controller.poll()
        self.assertEqual(os.read(self.master, 128), b"Q 2 4\n")
        os.write(self.master, b"ACK 2\n")
        self.controller.poll()
        self.assertNotEqual(self.controller.reached, 4)
        os.write(self.master, b"DONE 2 Q 4 POS 2400\n")
        self.controller.poll()
        self.assertEqual(self.controller.reached, 4)

    def test_real_serial_disconnect_disarms(self):
        os.close(self.master)
        self.master = None
        self.controller.poll()
        self.assertTrue(self.controller.failed)
        self.assertFalse(self.controller.calibrated)


if __name__ == "__main__":
    unittest.main()
