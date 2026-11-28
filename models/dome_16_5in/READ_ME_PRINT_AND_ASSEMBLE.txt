16.5-INCH FLOWER DOME - 12 MAIN PRINTED PANELS

DESIGN
419.1 mm outside diameter; 209.55 mm high open-bottom hemisphere.
Four quadrants, three horizontal levels, four panels per level.
L1 = lower (8 holes), L2 = middle (4 holes), L3 = upper (4 holes).
Each quadrant has 2 lower, 1 middle and 1 upper socket: 16 total.
Middle and upper rows are staggered by 22.5 degrees.
4 mm nominal shell wall. All dimensions and STL units are millimeters.

STEM FIT
Designed around the supplied final stem.stl: 22 mm body, 7 mm peg,
and larger upper lugs. Socket bores are 22.5 mm, giving 0.5 mm nominal
diametral clearance. The 22 mm flush AMS cap also passes through.
Insert the peg/cap end inward. The larger upper lugs stay outside and
rest at the shallow 32.6 mm stop seats. Sleeves extend 10 mm inside
the shell to guide the stems. No separate stem locking mechanism.
The modeled 95 mm inward stem/cap envelopes do not collide. This is
a geometry check; the dome has not been physically printed or load-tested.

PRINT THE OPTIONAL FIT TEST FIRST
OPTIONAL_stem_clearance_test.stl is a separate test coupon, not a dome panel.
It is 130 x 44 x 15 mm, with 3 bores. The raised pips identify them:
  1 pip  = 22.3 mm
  2 pips = 22.5 mm (used throughout the supplied dome)
  3 pips = 22.7 mm
Print at 100% scale in the intended material and profile; try your actual
stem and AMS cap. If the 22.5 mm bore binds, adjust the slicer's hole
compensation and repeat the coupon before printing the full dome.
Do not globally scale the panels: that changes the dome diameter/joints.

FILES / PRINT QUANTITIES
panels/Q1_L1_LOWER.stl through panels/Q4_L3_UPPER.stl: print one of each.
Panels of the same level have identical geometry; the Q names organize
assembly. Printing any one lower, middle and upper STL four times also
produces the same 12-piece dome. All joint features are integral.
dome_16_5in_assembled.step is an assembled CAD reference, not a single
object to print. The individual STLs are already moved onto Z=0.
Use 100% scale and do not merge all 12 STLs into an overlapping object.

ASSEMBLED STL (SEPARATE DOWNLOAD)
dome_16_5in_assembled.stl contains the complete dome in its assembled
position as one fused, closed solid. All 16 sockets and internal joint
features are retained; shared panel interface faces are removed.
An internal 0.5 mm-radius apex seam fill removes a mesh pinch where the
four top-panel lips meet. The exterior and stem sockets are unchanged.
Size: 419.1 x 419.1 x 209.55 mm. This whole-dome STL exceeds a 256 mm bed;
use the individual panels for that printer. No scaling is needed to view
the assembly. Keep 100% scale to preserve the existing stem socket fit.
The original 12-panel ZIP remains the panel-printing package; this new
assembled STL is downloaded separately from the same model folder.
assembled_stl_validation.json records its CAD and mesh checks.
To regenerate, install CadQuery and run python3 export_assembled_stl.py.

PRINTER SIZE / STARTING SETTINGS
Your printer model is unconfirmed. Prepared for a 256 x 256 mm or larger
bed. Verify the sliced footprint before printing.
  Lower panel: 217.6 x 209.6 x 116.0 mm (rounding up)
  Middle:      184.9 x 178.4 x 66.0 mm
  Upper:       126.6 x 122.6 x 39.6 mm
A 5 mm brim adds 10 mm to each XY dimension. These supplied upright
poses do not fit a 180 x 180 mm bed. They fit the geometric build envelope
of the A1, P1 and X1 256 mm printers; check supports/brim and machine
keep-out areas in your own slicer. AMS is optional for this dome.

Starting point: 0.4 mm nozzle, 0.2 mm layers, 4 wall loops, 15-20% infill,
and a 5 mm brim where needed. Enable supports for inward guide sleeves,
joint overhangs and the upper dome undersides. Inspect the sliced preview
so every island is supported and supports can be removed from the bores
and hidden glue faces. These are suggested settings, not a validated
printer profile. The geometry is about 1.18 liters of solid material
(1.46 kg if entirely solid PLA), before supports. Actual usage depends
on walls, infill, supports and material. Use the slicer estimate.

HIDDEN FLUSH JOINTS
Every panel has a clockwise seam lip behind its neighbor. L1 and L2
also have upper lips plus hidden anti-rotation keys. L2 and L3 have
matching bottom-open key slots. The glue space behind the neighboring
wall is 0.2 mm; the exterior faces meet on the same spherical surface.
No exterior screw heads, separate connectors or visible joint steps.
Actual print seams may need light sanding/filling to finish flush.

ASSEMBLY
1. Remove supports, clean bores and glue faces, and label panels by level
   using removable tape. Dry-fit a stem and the joints before gluing.
2. For each level separately, join Q1+Q2 and Q3+Q4 into two half-rings.
   Fit each lip behind the next panel's plain edge. Slide the two halves
   together to close the ring. Glue the hidden lips with an adhesive
   compatible with your filament and hold the exterior edges flush.
3. After all three rings cure, lower the complete middle ring onto the
   lower ring's upper lip. Match the four keys to their open slots.
4. Lower the complete upper ring onto the middle ring the same way.
   Dry-fit first; glue inside and remove squeeze-out. Do not force keys.
5. Let the adhesive cure fully, then insert stems peg/cap end first.
   The larger lugs stop at the exterior seats. The bottom remains open.

Keep the three level rings aligned: Q1 above Q1, etc. Q1 is centered
along +X in the STEP, Q2 +Y, Q3 -X and Q4 -Y. The hole_layout.csv gives
the full layout. The preview colors distinguish levels only; a single
color print has the same flush surface.

SCOPE AND VALIDATION
12 main parts; 16 sockets; no separate assembly hardware required.
CAD solids are valid. Exported meshes are closed, consistently oriented
single components. All 66 pairs of assembled panels were checked for
solid overlap. See validation.json for numerical results.
The open dome does not include a base, bearing, motor hub or mount.
The scanner, serial protocol, Arduino pins and motor code are unchanged.

EDITABLE SOURCE
build_dome.py requires Python plus CadQuery (created using 2.7).
Run: python3 build_dome.py ./generated
It regenerates the 12 panels, the assembled STEP and dimensions.json.
The bore setting is BORE=22.5. Recheck print fit and joint clearance after
changing parameters. No need to install CadQuery just to print the STLs.
