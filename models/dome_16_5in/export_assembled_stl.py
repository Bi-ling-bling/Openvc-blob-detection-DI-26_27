"""Fuse the existing assembled STEP into a single closed-solid STL.

Requires CadQuery (created with 2.7). Run this script without arguments to
export beside the supplied STEP, or provide --step and --output paths.
Dimensions and STL coordinates are in millimeters.
"""
import argparse
from pathlib import Path

import cadquery as cq


def main():
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--step', type=Path, default=folder / 'dome_16_5in_assembled.step')
    parser.add_argument('--output', type=Path, default=folder / 'dome_16_5in_assembled.stl')
    args = parser.parse_args()
    source = cq.importers.importStep(str(args.step)).val()
    solids = source.Solids()
    if len(solids) != 12 or not source.isValid():
        raise ValueError('Expected the valid 12-panel assembled STEP.')
    assembled = solids[0].fuse(*solids[1:])
    # At the inner spherical pole the four seam lips meet along one edge.
    # Fill only that sub-millimeter internal pinch so the single-piece STL
    # is manifold. The exterior and all stem sockets remain unchanged.
    assembled = assembled.fuse(cq.Solid.makeCylinder(0.5, 2.6, cq.Vector(0, 0, 203.05)))
    # OCC cannot always simplify the spherical pole edges. A valid fused
    # shape can be exported directly without that optional simplification.
    try:
        simplified = assembled.clean()
        if simplified.isValid():
            assembled = simplified
    except Exception:
        pass
    if not assembled.isValid() or len(assembled.Solids()) != 1:
        raise ValueError('Assembly did not fuse into one valid solid.')
    cq.exporters.export(assembled, str(args.output), tolerance=0.03, angularTolerance=0.05)
    print(f'Exported one fused assembled dome: {args.output}')


if __name__ == '__main__':
    main()
