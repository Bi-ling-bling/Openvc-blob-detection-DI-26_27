"""Read four-bit flower cards using OpenCV.

Run:
    python flower_reader.py

Generate printable cards:
    python flower_reader.py --print-cards flower_cards.html
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import sys

import cv2
import numpy as np


# Approved physical layout, measured in millimetres.
# The perspective-corrected image starts at the outside of the black border.
SCALE = 8
SIZE = (94 * SCALE, 54 * SCALE)
DOTS = [(x, 35) for x in (20, 40, 60, 80)]
MARKER = (15, 15)
STABLE_FRAMES = 5


@dataclass
class Reading:
    message: str
    bits: str | None = None
    quad: np.ndarray | None = None
    card: np.ndarray | None = None


def point(x: float, y: float) -> tuple[int, int]:
    """Convert physical card coordinates to corrected-image coordinates."""
    return round((x - 3) * SCALE), round((y - 3) * SCALE)


def inspect_symbol(
    gray: np.ndarray,
    center: tuple[int, int],
    square=False,
):
    """Return 0 for empty, 1 for filled, or None for unclear."""
    x, y = center
    r = 8 * SCALE
    patch = gray[y-r:y+r+1, x-r:x+r+1]

    if patch.shape != (2*r+1, 2*r+1):
        return None

    yy, xx = np.ogrid[-r:r+1, -r:r+1]
    distance = np.sqrt(xx*xx + yy*yy) / SCALE

    paper = patch[(distance >= 6) & (distance <= 8)]
    white = float(np.median(paper))

    # Reject very dark paper or strong variation around the symbol.
    if (
        white < 75
        or np.percentile(paper, 90) - np.percentile(paper, 10) > 55
    ):
        return None

    dark = (patch < white * 0.65).astype(np.uint8)
    core = distance <= 2
    search = distance <= 5.5
    surrounding = (distance >= 6) & (distance <= 8)

    if dark[search].mean() < 0.035:
        return 0

    if dark[core].mean() < 0.90 or dark[surrounding].mean() > 0.04:
        return None

    contours, _ = cv2.findContours(
        dark,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    containing = [
        contour
        for contour in contours
        if cv2.pointPolygonTest(
            contour, (float(r), float(r)), False
        ) >= 0
    ]

    if len(containing) != 1:
        return None

    contour = containing[0]
    area = cv2.contourArea(contour)
    expected = (36 if square else np.pi * 16) * SCALE**2

    if not 0.70 * expected <= area <= 1.30 * expected:
        return None

    moments = cv2.moments(contour)
    if moments["m00"] == 0:
        return None

    cx = moments["m10"] / moments["m00"]
    cy = moments["m01"] / moments["m00"]

    if np.hypot(cx-r, cy-r) > 1.1 * SCALE:
        return None

    _, _, width, height = cv2.boundingRect(contour)
    if not 0.78 <= width / height <= 1.28:
        return None

    perimeter = cv2.arcLength(contour, True)

    if square:
        shape_ok = area / (width * height) > 0.80
    else:
        shape_ok = (
            perimeter > 0
            and 4 * np.pi * area / perimeter**2 > 0.70
        )

    # Reject additional marks close to the expected symbol.
    if dark[search].sum() - area > 0.15 * expected:
        return None

    return 1 if shape_ok else None


def border_is_dark(gray: np.ndarray) -> bool:
    """Check strips through the middle of the expected black border."""
    s = SCALE
    strips = (
        gray[s//2:3*s//2, 5*s:-5*s],
        gray[-3*s//2:-s//2, 5*s:-5*s],
        gray[5*s:-5*s, s//2:3*s//2],
        gray[5*s:-5*s, -3*s//2:-s//2],
    )
    paper = np.percentile(gray, 80)

    return paper >= 75 and all(
        (strip < paper * 0.65).mean() > 0.70
        for strip in strips
    )


def detect_card(frame: np.ndarray) -> Reading:
    """Detect one card without modifying the input frame."""
    scale = min(1.0, 960 / frame.shape[1])
    small = (
        cv2.resize(frame, None, fx=scale, fy=scale)
        if scale < 1
        else frame
    )

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    adaptive = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        51,
        7,
    )
    _, global_mask = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
    )

    candidates = []

    for mask in (adaptive, global_mask):
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 10000 or area > gray.size * 0.95:
                continue

            quad = cv2.approxPolyDP(
                contour,
                0.02 * cv2.arcLength(contour, True),
                True,
            )

            if len(quad) != 4 or not cv2.isContourConvex(quad):
                continue

            quad = quad.reshape(4, 2).astype(np.float32)
            center = quad.mean(axis=0)
            angles = np.arctan2(
                quad[:, 1] - center[1],
                quad[:, 0] - center[0],
            )
            quad = quad[np.argsort(angles)]

            sides = np.linalg.norm(
                quad - np.roll(quad, 1, axis=0),
                axis=1,
            )
            if np.min(sides) < 80:
                continue

            if any(
                np.linalg.norm(quad - old) < 12
                for _, old in candidates
            ):
                continue

            candidates.append((area, quad))

    width, height = SIZE
    destination = np.float32([
        [0, 0],
        [width-1, 0],
        [width-1, height-1],
        [0, height-1],
    ])

    unclear = None
    valid = []

    candidates.sort(key=lambda item: item[0], reverse=True)

    for _, quad in candidates[:12]:
        for shift in range(4):
            oriented = np.roll(quad, shift, axis=0)
            transform = cv2.getPerspectiveTransform(
                oriented, destination
            )
            card = cv2.warpPerspective(small, transform, SIZE)
            card_gray = cv2.cvtColor(card, cv2.COLOR_BGR2GRAY)

            if not border_is_dark(card_gray):
                continue

            if inspect_symbol(
                card_gray, point(*MARKER), square=True
            ) != 1:
                continue

            symbols = [
                inspect_symbol(card_gray, point(*position))
                for position in DOTS
            ]
            bits = "".join(
                "?" if bit is None else str(bit)
                for bit in symbols
            )

            preview = card.copy()
            cv2.rectangle(
                preview,
                point(11, 11),
                point(19, 19),
                (255, 160, 0),
                2,
            )

            for position, bit in zip(DOTS, symbols):
                color = (
                    (0, 180, 0)
                    if bit is not None
                    else (0, 160, 255)
                )
                cv2.circle(
                    preview,
                    point(*position),
                    round(5.5 * SCALE),
                    color,
                    2,
                )
                cv2.putText(
                    preview,
                    "?" if bit is None else str(bit),
                    point(position[0]-2, 46),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    color,
                    2,
                )

            result = Reading(
                "Code unclear: " + bits,
                None,
                oriented / scale,
                preview,
            )

            if None in symbols:
                unclear = result
            else:
                result.bits = bits
                result.message = "Code " + bits
                valid.append(result)

    if len(valid) > 1:
        return Reading(
            "Multiple cards or ambiguous detection: show one card"
        )

    if valid:
        return valid[0]

    return unclear or Reading(
        "No readable card: show border and top-left marker"
    )


def write_templates(path: Path) -> None:
    """Generate all 16 cards across three A4 landscape pages."""
    cards = []

    for number in range(16):
        bits = f"{number:04b}"
        circles = "".join(
            f'<circle cx="{x}" cy="35" r="4" fill="black"/>'
            for (x, _), bit in zip(DOTS, bits)
            if bit == "1"
        )
        cards.append(
            f'''<div class="card">
<svg xmlns="http://www.w3.org/2000/svg"
     width="100mm" height="60mm" viewBox="0 0 100 60">
<rect width="100" height="60" fill="white"/>
<rect x="4" y="4" width="92" height="52"
      fill="none" stroke="black" stroke-width="2"/>
<rect x="12" y="12" width="6" height="6" fill="black"/>
{circles}
</svg>
<div class="caption">{bits} — Flower {number+1}
(cut off caption)</div>
</div>'''
        )

    pages = "".join(
        "<section>" + "".join(cards[i:i+6]) + "</section>"
        for i in range(0, 16, 6)
    )

    html = '''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Flower cards</title>
<style>
@page { size: A4 landscape; margin: 10mm; }
body { margin: 0; font-family: sans-serif; }
section {
    display: grid;
    grid-template-columns: repeat(2, 100mm);
    column-gap: 10mm;
    break-after: page;
}
section:last-child { break-after: auto; }
.card {
    width: 100mm;
    height: 63mm;
    break-inside: avoid;
}
svg { display: block; outline: 0.2mm dashed #aaa; }
.caption {
    font-size: 7pt;
    line-height: 3mm;
    height: 3mm;
    white-space: nowrap;
}
@media print { .instructions { display: none; } }
</style>
</head>
<body>
<p class="instructions">
All 16 cards on three pages (6 + 6 + 4).
Print at 100% / actual size, A4 landscape,
with headers and footers disabled.
Measure each card: 100 × 60 mm.
Cut around the dashed outline and remove captions.
Use white matte paper.
</p>
''' + pages + "</body></html>"

    path.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default="0",
        help="Camera index, video file, or stream URL (default: 0)",
    )
    parser.add_argument(
        "--print-cards",
        type=Path,
        metavar="HTML",
        help="Write printable cards and exit",
    )
    args = parser.parse_args()

    if args.print_cards:
        if args.print_cards.exists():
            parser.error(
                "Output already exists; choose a new filename."
            )
        write_templates(args.print_cards)
        print(
            f"Wrote {args.print_cards}. "
            "Print at 100% / actual size in A4 landscape."
        )
        return 0

    source = (
        int(args.source)
        if args.source.isdecimal()
        else args.source
    )
    capture = cv2.VideoCapture(source)

    if not capture.isOpened():
        capture.release()
        print(
            "Cannot open video source. Check camera index, "
            "permissions, or other camera apps.",
            file=sys.stderr,
        )
        return 1

    history = deque(maxlen=STABLE_FRAMES)

    try:
        cv2.namedWindow("Flower reader", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Corrected card", cv2.WINDOW_NORMAL)

        while True:
            ok, frame = capture.read()
            if not ok:
                print(
                    "No frame received: source ended or disconnected.",
                    file=sys.stderr,
                )
                break

            reading = detect_card(frame)

            if reading.bits is None:
                history.clear()
                message = reading.message
            else:
                if history and history[-1] != reading.bits:
                    history.clear()

                history.append(reading.bits)

                if len(history) == STABLE_FRAMES:
                    flower = int(reading.bits, 2) + 1
                    message = f"{reading.bits}  Flower {flower}"
                else:
                    message = (
                        f"Checking {reading.bits} "
                        f"({len(history)}/{STABLE_FRAMES})"
                    )

            if reading.quad is not None:
                cv2.polylines(
                    frame,
                    [reading.quad.astype(np.int32)],
                    True,
                    (0, 200, 0),
                    2,
                )

            for color, thickness in [
                ((0, 0, 0), 4),
                ((255, 255, 255), 1),
            ]:
                cv2.putText(
                    frame,
                    message,
                    (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.58,
                    color,
                    thickness,
                )

            cv2.imshow("Flower reader", frame)

            preview = (
                reading.card
                if reading.card is not None
                else np.zeros(
                    (SIZE[1], SIZE[0], 3),
                    dtype=np.uint8,
                )
            )
            cv2.imshow("Corrected card", preview)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

            if any(
                cv2.getWindowProperty(
                    name, cv2.WND_PROP_VISIBLE
                ) < 1
                for name in ("Flower reader", "Corrected card")
            ):
                break

    except KeyboardInterrupt:
        pass
    finally:
        capture.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())