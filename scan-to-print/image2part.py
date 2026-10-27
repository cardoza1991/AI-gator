#!/usr/bin/env python3
"""image2part: black-and-white artwork (logo, sign, stencil) -> cut files + printable plate.

Black = material, white = cut away. Outputs true-size DXF + SVG (laser / plasma /
waterjet / CAD) and an extruded STL. Flags pieces that would fall out when cut
("islands", e.g. the middle of a D or O) and features too thin to cut or print.

  python image2part.py logo.jpg --width 300 --thickness 3 -o out/
  python image2part.py logo.jpg --width 300 --thickness 3 --backing 1.2 -o out/   # islands stay put
"""
import argparse
import os

import cv2
import numpy as np
import trimesh
from scipy import ndimage
from shapely.geometry import Polygon
from shapely.ops import unary_union


def polygons(mask, mm_per_px, smooth):
    """Black pixels -> shapely polygons in mm (y up), holes included."""
    cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    h = mask.shape[0]
    to_mm = lambda c: np.c_[c[:, 0, 0], h - c[:, 0, 1]] * mm_per_px
    out = []
    for i, c in enumerate(cnts):
        if hier[0][i][3] != -1 or len(c) < 4:
            continue
        holes = []
        ch = hier[0][i][2]
        while ch != -1:
            if len(cnts[ch]) >= 4:
                holes.append(to_mm(cnts[ch]))
            ch = hier[0][ch][0]
        p = Polygon(to_mm(c), holes).buffer(0)
        if smooth:
            p = p.buffer(smooth).buffer(-2 * smooth).buffer(smooth)
        if not p.is_empty:
            out.append(p.simplify(mm_per_px * 0.3))
    return out


def rings(geom):
    for p in getattr(geom, "geoms", [geom]):
        yield p.exterior
        yield from p.interiors


def write_dxf(path, geoms):
    lines = ["0", "SECTION", "2", "ENTITIES"]
    for g in geoms:
        for r in rings(g):
            xy = np.array(r.coords)[:-1]
            lines += ["0", "LWPOLYLINE", "8", "CUT", "90", str(len(xy)), "70", "1"]
            for x, y in xy:
                lines += ["10", f"{x:.4f}", "20", f"{y:.4f}"]
    lines += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w") as f:
        f.write("\n".join(lines))


def add_bridges(mask, width_px, per_island=2):
    """Tie every floating piece to the main piece with straight strips across the gap
    (stencil bridges): shortest one first, then one on the opposite side."""
    added = []
    for _ in range(50):
        n, lab, st, cen = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if n <= 2:
            break
        main_id = 1 + np.argmax(st[1:, 4])
        k = next(i for i in range(1, n) if i != main_id)
        isl = lab == k
        edge = isl & ~ndimage.binary_erosion(isl)
        d, (iy, ix) = ndimage.distance_transform_edt(lab != main_id, return_indices=True)
        ey, ex = np.nonzero(edge)
        dd = d[ey, ex]
        ang = np.arctan2(ey - cen[k][1], ex - cen[k][0])
        first = None
        for _b in range(per_island):
            ok = np.ones(len(dd), bool)
            if first is not None:  # opposite side: at least 120 degrees away
                ok = np.abs(np.angle(np.exp(1j * (ang - first)))) > np.radians(120)
                if not ok.any():
                    break
            j = np.flatnonzero(ok)[np.argmin(dd[ok])]
            p0 = (int(ex[j]), int(ey[j]))
            p1 = (int(ix[ey[j], ex[j]]), int(iy[ey[j], ex[j]]))
            cv2.line(mask, p0, p1, 1, max(1, int(round(width_px))))
            added.append((p0, p1, dd[j]))
            first = ang[j] if first is None else first
    return added


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--width", type=float, default=300, help="finished width of the artwork, mm")
    ap.add_argument("--thickness", type=float, default=3.0, help="plate thickness, mm")
    ap.add_argument("--backing", type=float, default=0.0,
                    help="mm of solid backing plate under the art (3D print): islands stay attached")
    ap.add_argument("--min-feature", type=float, default=1.0, help="warn about features thinner than this, mm")
    ap.add_argument("--smooth", type=float, default=0.15, help="round pixel steps off edges, mm")
    ap.add_argument("--bridge", type=float, default=1.5,
                    help="mm width of strips added to hold floating pieces (0 = don't add, just warn)")
    ap.add_argument("--invert", action="store_true", help="white is material instead of black")
    ap.add_argument("-o", "--out", default="out")
    a = ap.parse_args()
    if not os.path.isfile(a.image):
        raise SystemExit(f"file not found: {a.image}")
    os.makedirs(a.out, exist_ok=True)

    g = cv2.imread(a.image, cv2.IMREAD_GRAYSCALE)
    mask = ((g > 128) if a.invert else (g < 128)).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))  # jpeg specks
    ys, xs = np.nonzero(mask)
    mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    mm_per_px = a.width / mask.shape[1]
    print(f"artwork {mask.shape[1]} x {mask.shape[0]} px -> {a.width:.1f} x {mask.shape[0] * mm_per_px:.1f} mm "
          f"({mm_per_px:.3f} mm/px)")

    bridges = []
    if a.bridge:
        bridges = add_bridges(mask, a.bridge / mm_per_px)
        if bridges:
            lens = [b[2] * mm_per_px for b in bridges]
            print(f"added {len(bridges)} bridge(s), {a.bridge} mm wide, {min(lens):.1f}-{max(lens):.1f} mm long "
                  f"(green in check.png)")

    # pieces: the biggest is the part, every other separate piece falls out when cut
    n, lab, st, cen = cv2.connectedComponentsWithStats(mask, connectivity=8)
    main_id = 1 + np.argmax(st[1:, 4])
    islands = [k for k in range(1, n) if k != main_id]
    if islands:
        print(f"WARNING: {len(islands)} island(s) not connected to the main piece (fall out when cut):")
        for k in islands:
            x, y = cen[k] * mm_per_px
            print(f"  - {st[k, 2] * mm_per_px:.1f} x {st[k, 3] * mm_per_px:.1f} mm at x={x:.0f}, y={y:.0f} mm from top-left")
        print("  fix: --bridge 1.5 adds holding strips, or cut them loose, or print with --backing")

    # thinnest features (2x distance to edge along the skeleton)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5) * 2 * mm_per_px
    ridge = (dist > 0) & (dist >= cv2.dilate(dist, np.ones((3, 3))) - 1e-6)
    thin = ridge & (dist < a.min_feature)
    if thin.any():
        print(f"WARNING: features down to {dist[ridge].min():.2f} mm wide (below {a.min_feature} mm); "
              f"check fine details at this size")
    else:
        print(f"thinnest feature ~{np.percentile(dist[ridge], 1):.2f} mm: OK at this size")

    # check image: grey = material, red = islands, orange rings = too-thin spots
    chk = cv2.cvtColor(np.where(mask, 90, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    for k in islands:
        chk[lab == k] = (0, 0, 255)
        x, y, bw, bh = st[k, :4]
        cv2.circle(chk, (int(x + bw / 2), int(y + bh / 2)), int(max(bw, bh)) + 12, (0, 0, 255), 3)
    for p0, p1, _ in bridges:
        cv2.line(chk, p0, p1, (0, 170, 0), max(2, int(round(a.bridge / mm_per_px))))
        cv2.circle(chk, ((p0[0] + p1[0]) // 2, (p0[1] + p1[1]) // 2), 18, (0, 170, 0), 2)
    for y, x in zip(*np.nonzero(thin)):
        cv2.circle(chk, (int(x), int(y)), 6, (0, 140, 255), 1)
    cv2.imwrite(os.path.join(a.out, "check.png"), chk)

    geoms = polygons(mask, mm_per_px, a.smooth)
    art = unary_union(geoms)
    write_dxf(os.path.join(a.out, "cut.dxf"), [art])
    w, h = mask.shape[1] * mm_per_px, mask.shape[0] * mm_per_px
    paths = "".join('<path d="M' + " L".join(f"{x:.3f},{h - y:.3f}" for x, y in r.coords) + ' Z"/>' for r in rings(art))
    with open(os.path.join(a.out, "cut.svg"), "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.3f} {h:.3f}">'
                f'<g fill="black" fill-rule="evenodd" stroke="none">{paths}</g></svg>')

    meshes = [trimesh.creation.extrude_polygon(p, a.thickness + a.backing) for p in getattr(art, "geoms", [art])]
    for m in meshes:  # art reaches down into the backing: overlapping solids, no shared faces
        m.apply_translation([0, 0, -a.backing])
    if a.backing:
        back = unary_union([Polygon(p.exterior) for p in getattr(art, "geoms", [art])])
        b = trimesh.creation.extrude_polygon(back, a.backing - 0.01)
        b.apply_translation([0, 0, -a.backing + 0.005])
        meshes.append(b)
    plate = trimesh.util.concatenate(meshes)
    plate.export(os.path.join(a.out, "plate.stl"))
    print(f"wrote cut.dxf, cut.svg, plate.stl, check.png ({plate.extents.round(1)} mm) -> {a.out}/")


if __name__ == "__main__":
    main()
