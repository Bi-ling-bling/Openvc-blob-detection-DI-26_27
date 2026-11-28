All 16 flower codes, 0000 through 1111.

Print flower_all_16_codes_12mm_letter.pdf on US Letter at 100% / Actual size.
Disable Fit, Shrink and Scale to fit. Verify the printed 50 mm reference.

Rectangle outside dimensions: 20.8889 mm wide x 12 mm high.
Dot diameter: 1.7778 mm. Border thickness: 0.4444 mm.
Corner marker: 1.3333 mm square.
Cut-out paper size: 22.2222 x 13.3333 mm.
Use matte white paper and black ink. Cut on the light dashed guide;
remove captions and keep the white margin. Show one code at a time.

Layout matches flower_reader.py. The first two bits select Q1-Q4.
No scanner or Arduino code changes. Camera focus and sufficient image
size still matter; the existing minimum candidate size is unchanged.

Validation: all sixteen PDF labels were rendered at 600 dpi and read
by the existing detector in all four orientations (64 successful checks).
This checks the digital PDF; physical printing/webcam performance depends
on print settings, focus, lighting and camera distance.
