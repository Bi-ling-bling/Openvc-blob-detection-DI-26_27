"""Regression checks for the existing card design and the motor integration."""
import sys
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import flower_reader as reader
from quadrant_control import QuadrantController, SimulatedTransport


def card_image(bits):
    scale = 7
    frame = np.full((80 * scale, 120 * scale, 3), 180, np.uint8)
    card = frame[10 * scale:70 * scale, 10 * scale:110 * scale]
    card[:] = 255
    cv2.rectangle(card, (3 * scale, 3 * scale), (97 * scale, 57 * scale), (0, 0, 0), -1)
    cv2.rectangle(card, (5 * scale, 5 * scale), (95 * scale, 55 * scale), (255, 255, 255), -1)
    cv2.rectangle(card, (12 * scale, 12 * scale), (18 * scale, 18 * scale), (0, 0, 0), -1)
    for x, bit in zip((20, 40, 60, 80), bits):
        if bit == "1":
            cv2.circle(card, (x * scale, 35 * scale), 4 * scale, (0, 0, 0), -1)
    return frame


class ReaderTests(unittest.TestCase):
    def test_existing_cards_all_codes_in_four_orientations(self):
        for number in range(16):
            bits = f"{number:04b}"
            for rotation in range(4):
                with self.subTest(bits=bits, rotation=rotation):
                    result = reader.detect_card(np.rot90(card_image(bits), rotation).copy())
                    self.assertEqual(result.bits, bits, result.message)

    def test_missing_card_is_not_zero_code(self):
        self.assertIsNone(reader.detect_card(np.full((480, 640, 3), 255, np.uint8)).bits)

    def test_camera_loop_requires_five_consecutive_readings(self):
        # Break the first run with an unreadable frame, then confirm Q4.
        readings = ["1111"] * 4 + [None] + ["1111"] * 5
        transport = SimulatedTransport()
        motor = QuadrantController(transport)
        motor.poll()
        motor.zero()
        motor.poll()
        commands_at_frame = []

        class Capture:
            index = 0

            def isOpened(self):
                return True

            def read(self):
                commands_at_frame.append(len([c for c in transport.commands if c.startswith("Q ")]))
                if self.index == len(readings):
                    return False, None
                self.index += 1
                return True, np.zeros((480, 640, 3), np.uint8)

            def release(self):
                pass

        with (patch.object(sys, "argv", ["flower_reader.py", "--dry-run"]),
              patch.object(reader, "open_controller", return_value=motor),
              patch.object(reader, "detect_card", side_effect=[reader.Reading("test", bits=b) for b in readings]),
              patch.object(cv2, "VideoCapture", return_value=Capture()),
              patch.object(cv2, "namedWindow"), patch.object(cv2, "imshow"),
              patch.object(cv2, "waitKey", return_value=-1),
              patch.object(cv2, "getWindowProperty", return_value=1),
              patch.object(cv2, "destroyAllWindows")):
            self.assertEqual(reader.main(), 0)
        self.assertEqual(commands_at_frame, [0] * 10 + [1])
        self.assertTrue(transport.commands[-1].startswith("STOP "))


if __name__ == "__main__":
    unittest.main()
