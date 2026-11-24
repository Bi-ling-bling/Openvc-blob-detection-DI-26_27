AMS TWO-COLOR FLUSH CAP - CODE 1010

START HERE
Open 1010_cap_AMS.3mf in Bambu Studio. It contains one assembled object
with two aligned parts: WHITE cap and BLACK 1010 inlays.
If prompted about a non-Bambu project, import its model/geometry and use
your own printer profile. This is a model assembly, not sliced G-code.

1. Select your actual Bambu printer and nozzle profile.
2. Add a white filament and a black filament of the same material,
   for example white PLA and black PLA.
3. In Objects, expand the cap and assign WHITE cap to the white filament
   and BLACK 1010 inlays to the black filament. The file uses logical
   filament 1 for white and logical filament 2 for black; map these to
   whichever AMS slots actually contain the matching colors.
4. Keep the supplied label-face-down orientation. Center/arrange the
   entire assembled object on the build plate as needed.
5. Slice and inspect Preview. Confirm a complete black rectangular
   border, two filled black dots, and one black corner square on white.
   The empty bit locations stay white. The model is specifically 1010.
6. Print one sample and check scanner recognition and the peg fit before
   producing a batch.

THIN FEATURES
The preserved black border is 0.444 mm wide; dots are 1.778 mm diameter
and the corner marker is 1.333 mm square. With a 0.4 mm nozzle, Arachne
walls and a first-layer line width around 0.42 mm are a sensible starting
point. Inspect Preview to ensure the entire border survives slicing.
A 0.2 mm layer height and 0.2 mm first layer put the black inlays in the
first three layers. Keep sufficient black-to-white purge for clean white.
No printer-specific temperature, machine, or AMS-slot settings are assumed.

WHAT CHANGED
The paper recess was filled in and the actual black code geometry was
inlaid 0.6 mm deep into the white face. Black and white end at the same
surface, so the face is flush and the code needs no paper or adhesive.
The four black solids (frame, two dots, marker) are grouped as one black
part. The white body is one continuous solid.

DIMENSIONS / FIT
Outer profile: matches the original 22 mm cylinder profile.
Cap length along the stem axis: 24 mm.
Peg socket: 7.3 mm diameter, 12.3 mm deep, with the same lead-in.
The original 7 mm x 12 mm peg inserts until the cap meets the cylinder
shoulder. The cap extends 12 mm beyond the old peg tip.
Black rectangle: 20.889 x 12 mm, rotated lengthwise on the cap.
The scanner supports this rotated card orientation without code changes.

PRINT ORIENTATION
The assembly is rotated so the flat code face lies on the build plate.
Its build dimensions are approximately 22 x 24 x 19.284 mm. The 24 mm
cap length therefore runs along the plate, not along the print Z axis.
Only the first 0.6 mm contains black, limiting the color-change layers.
The socket is horizontal in this orientation; check bridging/support
in your chosen printer profile and verify the printed fit.

STL FALLBACK
Import 1010_cap_WHITE.stl and 1010_inlays_BLACK.stl simultaneously.
Choose a single object with multiple parts when prompted. Their shared
coordinates provide the alignment. Assign white and black to those parts
and keep the object assembled when arranging it on the plate.

FILES / VALIDATION
1010_cap_AMS.3mf: portable two-part assembly with colors and part mappings.
1010_cap_WHITE.stl: white body, with the inlay cavities.
1010_inlays_BLACK.stl: all four black features, already aligned.
1010_cap_AMS.step: colored CAD assembly for editing.
1010_cap_AMS_preview.png: overview of the assembled design.
dimensions.json: exact dimensions and material volumes.

The 3MF was read back in strict mode by lib3mf without warnings. CAD
checks confirm no material overlaps, a common flush face, and an unchanged
outer envelope. Exported meshes are closed, consistently oriented shells.
The rendered code was checked with the existing reader as 1010.
An actual Bambu Studio slice and physical multicolor print still need
to be checked using your printer, filaments, and current profiles.
