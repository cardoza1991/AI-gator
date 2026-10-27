# scan-to-print

Turn FARO scans and phone photos into print-ready, watertight STLs without
manual Mesh Doctor cleanup.

| Tool | Input | Use for |
|---|---|---|
| `twoside.py` | Two FARO scans: side A up, then flipped, side B up | Parts shaped on both faces. Main workflow. |
| `flatbase.py` | One FARO scan of the top, part lying on the plate | Parts whose underside is flat (top can be any shape) |
| `photo2outline.py` | One top-down photo on the hole-grid plate | Quick true-scale profiles, foam inserts, shadow boards |
| `smoothprint.py` | Full 3D scan (optionally + AI mesh from photos) | Shapes scanned from all sides |

Install (Python 3.13 works):

    py -3.13 -m pip install -r requirements.txt

Export scans from Geomagic Wrap as raw points or mesh, with no cleanup
(File > Save As > .stl or .asc). The tools can't read `.wrp` projects.

Units: output is always mm. If the scan is under 40 units long the tools assume
it was exported in inches and convert (they say so). Force with `--units mm` / `--units in`.
Example inputs/outputs for the pliers test are in `examples/pliers/`.

## smoothprint.py: full 3D scan (+ optional AI mesh) -> smooth solid

    python smoothprint.py scan.stl --voxel 0.5 --smooth 1.5 -o print.stl
    python smoothprint.py scan.stl --ai ai.glb --voxel 0.5 --smooth 1.5 -o print.stl

Works on meshes or point clouds. Drops specks floating away from the part
(scan passes that touch the part are kept, however small), optionally aligns an AI mesh made from photos (Hunyuan3D,
TRELLIS, Meshy, Tripo) to the scan to fill large holes (scan sets the size),
then voxelizes in the part's own frame, seals gaps, blurs and re-surfaces.
If side walls have big gaps the shell can't seal, it fills between the top and
bottom surfaces instead. It stops with a message rather than writing scrap.

- `--voxel` mm per voxel. 0.2-0.4 fine, 1.0 blobby. Smaller = slower.
- `--smooth` blur in voxels. 0 keeps scratches, 3+ melts edges.
- `--close` seals scan gaps up to ~2x this many voxels. Bigger holes: use `--ai`.
- `--offset` grow outward N mm (sheath/holster clearance, leather thickness).
- `--faces` output triangle cap.

Limits: an AI mesh is a guess. Both surfaces are merged, so a poor fit adds
bumps; check the printed alignment error. Tight-tolerance features (bearing
bores, mating faces) still belong in CAD.

## twoside.py: scan side A, flip, scan side B -> one solid

For parts with shape on both faces. Lay the part on the plate, scan everything
the arm can see (include some plate), flip it, scan again. Export both from
Wrap as raw points or mesh, no cleanup, no manual registration.

    python twoside.py sideA.xyz sideB.xyz --voxel 0.3 --smooth 1 -o part.stl

Strips the plate from each scan, turns side B over and matches footprints,
then refines with ICP that only pairs surfaces facing the same way (so the two
faces can't collapse onto each other). Merged points are rebuilt as a voxel
solid. Also writes `part_merged.xyz` so you can check the alignment in Wrap.

Check the printed `median gap`: a few tenths of a mm is good. If it's mm-scale,
the auto-alignment missed; register the two scans in Wrap instead and run
`smoothprint.py` on the combined export.

Test on a synthetic plier half (shaped top and bottom, random scan poses,
noise): surface error median 0.07 mm, 95th percentile 0.26 mm, volume +2.7%.

- `--voxel` grid mm (0.3 default). `--smooth` 0 keeps pitting/rust.
- `--offset` grow outward mm for clearance.
- Scan the side walls from both sides: that overlap is what aligns the halves.

## photo2outline.py: phone photo -> true-scale outline + STL (no scanner)

Lay parts flat on the hole-grid plate and take one photo from roughly above.
The hole grid corrects camera tilt and sets scale. Plate holes touching the
part get removed from the outline automatically.

    python photo2outline.py top.jpg --pitch 25.4 --thickness 8 --offset 0 -o out/

Outputs per part: `partN.stl` (constant-thickness extrusion), `outlines.svg`
(true mm, for CAD / foam inserts / laser), `check.jpg` (overlay, LOOK AT IT).

- `--pitch` hole spacing in mm. Measure your plate.
- `--thickness` caliper the part. Single height only (2.5D).
- `--offset` clearance for foam cutouts, holsters, shadow boards.
- `--slot-min` through-slots smaller than this (mm^2) get filled.

## flatbase.py: FARO scan of the top only -> solid with flat bottom

For parts lying on the plate where the underside is flat. Scan the top (include
some plate around it if you can), export points or mesh from Wrap with NO cleanup.

    python flatbase.py scan.xyz --res 0.25 --smooth 0.5 -o part.stl

Finds the plate plane (or the part's lowest edge), levels the part, treats it as
a height map, fills gaps, closes a dead-flat bottom at z=0. Always watertight.

- `--smooth` 0 keeps pitting/rust texture, 1-2 gives clean surfaces.
- `--fill` closes scan gaps up to about this many mm; real slots bigger than that stay open.
- `--offset` grows sides + top for clearance (bottom stays on the plate).
- Limit: undercuts (anything overhanging when seen from above) get filled straight down.

## image2part.py: logo / sign artwork -> cut files + printable plate

Black = material, white = cut away (`--invert` for the opposite).

    python image2part.py logo.jpg --width 300 --thickness 3 -o out/
    python image2part.py logo.jpg --width 300 --thickness 3 --backing 1.2 -o out/

Outputs `cut.dxf` + `cut.svg` at true size (laser, plasma, waterjet, CAD),
`plate.stl`, and `check.png` marking problems:
- red: islands, pieces not connected to the rest (centers of D, O, A...) that
  fall out when cut. Bridge them in the art, cut them loose, or for 3D printing
  use `--backing` so they sit on a solid back plate.
- orange: features thinner than `--min-feature` mm at this size.
