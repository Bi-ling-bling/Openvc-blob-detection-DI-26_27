"""419.1 mm hemisphere, four quadrants x three bands, 16 stem holes.

Analytic CadQuery construction; all dimensions in mm. The source stem's
22 mm body uses a 22.5 mm clearance bore. Internal laps are integral to
the 12 main panels and leave a 0.2 mm adhesive gap behind adjacent walls.
"""
from pathlib import Path
import json
import math
import sys
import time

import cadquery as cq

ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent/'generated'
OUT=ROOT/'files'
PARTS=OUT/'panels'
PARTS.mkdir(parents=True,exist_ok=True)
R=419.1/2
H=R
WALL=4.0
RI=R-WALL
BORE=22.5
COLLAR_OD=30.0
SEAT_OD=32.6
SEAT_DEPTH=0.8
GUIDE_EXTRA=10.0
BANDS=[0.0,110.0,170.0,H]
HOLE_TILTS=[70.0,45.0,20.0]
LIP_WIDTH=8.0
LIP_THICK=2.2
LIP_GLUE_GAP=0.2
LIP_ROOT_OVERLAP=0.8
LIP_RISE=6.0
DELTA=math.degrees(LIP_WIDTH/RI)

def log(*args):print(*args,flush=True)
def z_box(lo,hi):
    return cq.Solid.makeBox(4*R,4*R,hi-lo,cq.Vector(-2*R,-2*R,lo))
def wedge(a,b):
    a,b=map(math.radians,(a,b));L=4*R
    return (cq.Workplane('XY').polyline([(0,0),(L*math.cos(a),L*math.sin(a)),(L*math.cos(b),L*math.sin(b))])
            .close().extrude(H+20).translate((0,0,-5)).val())
def sphere(radius):return cq.Workplane('XY').sphere(radius).val()
def shell(outer,inner):return sphere(outer).cut(sphere(inner))
def cylinder(radius,length,start,direction):
    return cq.Solid.makeCylinder(radius,length,cq.Vector(*start),cq.Vector(*direction))
def scale(v,f):return tuple(x*f for x in v)
def refine(shape):
    # Some valid spherical pole/edge combinations cannot be simplified by OCC.
    # Keep their valid unsimplified B-rep rather than altering the geometry.
    try:
        candidate=shape.clean()
        if candidate.isValid():return candidate
    except Exception:
        pass
    assert shape.isValid(),'Invalid Boolean result before simplification'
    return shape

outer=sphere(R)
main_shell=outer.cut(sphere(RI))
quadrant=wedge(0,90)
lip_shell=shell(RI-LIP_GLUE_GAP, RI-LIP_GLUE_GAP-LIP_THICK)
root_shell=shell(RI+LIP_ROOT_OVERLAP, RI-LIP_GLUE_GAP-LIP_THICK)
edge_lip_sector=wedge(90-DELTA,90+DELTA)
edge_root_sector=wedge(90-DELTA,90)
centres=[R*math.cos(math.radians(t)) for t in HOLE_TILTS]
angles=[[22.5,67.5],[45.0],[22.5]]
canonical=[]
hole_table=[]
stats=[]

for level in range(3):
    start=time.time()
    lo,hi=BANDS[level:level+2]
    panel=main_shell.intersect(quadrant).intersect(z_box(lo,hi))
    # Quarter seam: lip behind the next quadrant, with clearance for the
    # preceding band's horizontal lip and for this band's top-lip root.
    v_lo,v_hi=lo+8,hi-3
    vertical_lip=lip_shell.intersect(edge_lip_sector).intersect(z_box(v_lo,v_hi))
    vertical_root=root_shell.intersect(edge_root_sector).intersect(z_box(v_lo,v_hi))
    panel=refine(panel.fuse(vertical_lip,vertical_root))
    if level<2:
        horizontal_lip=lip_shell.intersect(quadrant).intersect(z_box(hi-2.5,hi+LIP_RISE))
        horizontal_root=root_shell.intersect(quadrant).intersect(z_box(hi-2.5,hi))
        panel=refine(panel.fuse(horizontal_lip,horizontal_root))
        # Integral anti-rotation key on the hidden upper lip.
        key=shell(RI+1.0,RI-0.8).intersect(wedge(44,46)).intersect(z_box(hi+1.5,hi+4.5))
        panel=refine(panel.fuse(key))
    if level>0:
        # Bottom-open receiving groove permits the assembled upper ring to
        # lower onto the previous band's key, without an exposed fastener.
        key_slot=shell(RI+1.25,RI-0.9).intersect(wedge(43.85,46.15)).intersect(z_box(lo-0.1,lo+4.75))
        panel=refine(panel.cut(key_slot))

    # Each hole is normal to the hemisphere and has an internal guide sleeve
    # plus a shallow flat seat for the source stem's larger stop lugs.
    z=centres[level]
    rho=math.sqrt(R*R-z*z)
    theta=math.acos(z/R)
    for number,azimuth in enumerate(angles[level]):
        phi=math.radians(azimuth)
        normal=(math.sin(theta)*math.cos(phi),math.sin(theta)*math.sin(phi),math.cos(theta))
        collar_start=R-WALL-GUIDE_EXTRA
        collar_end=R-1.0
        collar=cylinder(COLLAR_OD/2,collar_end-collar_start,scale(normal,collar_start),normal)
        panel=refine(panel.fuse(collar))
        bore_start=collar_start-1
        bore=cylinder(BORE/2,R+2-bore_start,scale(normal,bore_start),normal)
        seat=cylinder(SEAT_OD/2,SEAT_DEPTH+2,scale(normal,R-SEAT_DEPTH),normal)
        panel=refine(panel.cut(bore,seat))
        hole_table.append({'level':level+1,'local_angle_deg':azimuth,
                           'global_angle_Q1_deg':azimuth-45,
                           'outer_center':[rho*math.cos(phi),rho*math.sin(phi),z],
                           'normal':normal,'height':z,
                           'tilt_from_vertical_deg':math.degrees(theta)})
    assert panel.isValid(),f'Invalid level {level+1}'
    assert len(panel.Solids())==1,(level+1,len(panel.Solids()))
    # No connector, seat or sleeve may protrude outside the nominal sphere.
    outside=panel.cut(outer).Volume()
    assert outside<1e-4,(level,outside)
    canonical.append(panel)
    bb=panel.BoundingBox()
    stats.append({'level':level+1,'volume':panel.Volume(),
                  'raw_bounds':[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax],
                  'print_bounds_mm':[bb.xlen,bb.ylen,bb.zlen],
                  'holes':len(angles[level]),'valid':panel.isValid(),'solids':len(panel.Solids())})
    cq.exporters.export(panel,str(ROOT/f'canonical_L{level+1}.brep'))
    log('Built level',level+1,'in',round(time.time()-start,2),'s; print bounds',stats[-1]['print_bounds_mm'])

assembly=cq.Assembly(name='Dome_16_5in_4_quadrants_3_levels')
all_panels=[]
for q in range(4):
    rotation=90*q-45
    for level,panel in enumerate(canonical,1):
        name=f'Q{q+1}_L{level}_'+('LOWER' if level==1 else 'MIDDLE' if level==2 else 'UPPER')
        bb=panel.BoundingBox()
        printable=panel.translate((-bb.xmin,-bb.ymin,-bb.zmin))
        cq.exporters.export(printable,str(PARTS/(name+'.stl')),tolerance=0.03,angularTolerance=0.05)
        placed=panel.rotate((0,0,0),(0,0,1),rotation)
        all_panels.append((name,placed))
        color=cq.Color(*((0.82,.88,.92) if level==1 else (.54,.72,.82) if level==2 else (.27,.48,.65)))
        assembly.add(placed,name=name,color=color)

assembly.export(str(OUT/'dome_16_5in_assembled.step'))
step_path=OUT/'dome_16_5in_assembled.step'
step_path.write_text('\n'.join(line.rstrip() for line in step_path.read_text().splitlines())+'\n')
manifest={'diameter_in':16.5,'diameter_mm':2*R,'height_mm':H,'shape':'hemisphere',
          'wall_thickness_mm':WALL,'stem_body_mm':22.0,'hole_diameter_mm':BORE,
          'hole_count':16,'main_piece_count':12,'levels':3,'quadrants':4,
          'holes_per_quadrant_by_level':[2,1,1],
          'level_order':'L1 lower, L2 middle, L3 upper',
          'band_cut_heights_mm':BANDS,
          'hole_center_heights_mm':centres,
          'guide_outer_diameter_mm':COLLAR_OD,'guide_extra_inward_mm':GUIDE_EXTRA,
          'stem_stop_seat_diameter_mm':SEAT_OD,'stem_stop_seat_depth_mm':SEAT_DEPTH,
          'glue_lip_width_mm':LIP_WIDTH,'glue_lip_thickness_mm':LIP_THICK,
          'glue_gap_mm':LIP_GLUE_GAP,'upper_band_lip_extension_mm':LIP_RISE,
          'hidden_alignment_keys_per_band_joint':4,
          'canonical_holes':hole_table,'canonical_parts':stats,
          'total_volume_mm3':4*sum(p.Volume() for p in canonical),
          'solid_PLA_mass_kg':4*sum(p.Volume() for p in canonical)*1.24e-6,
          'placement':'Print panels individually in their local STL poses; STEP shows assembly. Q1 center is +X.'}
(OUT/'dimensions.json').write_text(json.dumps(manifest,indent=2))
log('Finished 12 STL panels and STEP assembly.')
