#!/usr/bin/env python3
"""photo2outline: phone photo of parts on a hole-grid plate -> true-scale outlines + STL.

The plate's hole grid is the calibration target: it fixes camera tilt (homography)
and sets scale. Parts are cut out, holes in the plate are ignored, and each part
becomes an extruded STL (2.5D) plus an SVG outline for CAD / foam inserts.

  python photo2outline.py top.jpg --pitch 25.4 --thickness 8 -o out/
"""
import argparse
import os

import cv2
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from shapely.geometry import Polygon


def flatten(gray):
    """Divide out lighting/shadows so dark = dark everywhere."""
    g = gray.astype(np.float32)
    bg = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (151, 151)))
    return g / (cv2.GaussianBlur(bg, (0, 0), 25) + 1)


def find_holes(ratio):
    """Centres + areas of round dark blobs (plate holes)."""
    dark = (ratio < 0.5).astype(np.uint8)
    n, _, st, cen = cv2.connectedComponentsWithStats(dark)
    keep = []
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if 150 < a < 8000 and 0.6 < w / h < 1.6 and a / (w * h) > 0.55:
            keep.append((cen[k], a))
    pts = np.array([c for c, _ in keep])
    areas = np.array([a for _, a in keep])
    return pts, areas


def lattice(pts):
    """Give each hole integer grid coords (i, j) by walking neighbour to neighbour."""
    tree = cKDTree(pts)
    start = np.argmin(np.linalg.norm(pts - pts.mean(0), axis=1))
    # two shortest non-parallel neighbour vectors = local grid basis
    d, idx = tree.query(pts[start], 7)
    vecs = pts[idx[1:]] - pts[start]
    a = vecs[0]
    b = next(v for v in vecs[1:] if abs(a[0] * v[1] - a[1] * v[0]) > 0.5 * np.linalg.norm(a) * np.linalg.norm(v))
    coords = {start: (0, 0)}
    basis = {start: np.array([a, b])}
    queue = [start]
    while queue:
        p = queue.pop(0)
        A = basis[p]
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            guess = pts[p] + di * A[0] + dj * A[1]
            dist, q = tree.query(guess)
            if q in coords or dist > 0.3 * min(np.linalg.norm(A[0]), np.linalg.norm(A[1])):
                continue
            ci, cj = coords[p]
            coords[q] = (ci + di, cj + dj)
            # update basis from the step we just made (tracks perspective drift)
            B = A.copy()
            B[0 if di else 1] = (pts[q] - pts[p]) * (di or dj)
            basis[q] = B
            queue.append(q)
    ids = np.array(list(coords))
    return ids, np.array([coords[i] for i in ids], float)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--pitch", type=float, default=25.4, help="mm between neighbouring plate holes (measure it!)")
    ap.add_argument("--thickness", type=float, default=8.0, help="extrude height mm (caliper the part)")
    ap.add_argument("--offset", type=float, default=0.0, help="grow outline mm (clearance for holster/foam)")
    ap.add_argument("--smooth", type=float, default=1.0, help="round off outline wiggles, mm")
    ap.add_argument("--min-area", type=float, default=2000, help="ignore parts smaller than this, mm^2")
    ap.add_argument("--slot-min", type=float, default=150, help="keep through-slots bigger than this, mm^2")
    ap.add_argument("--ppmm", type=float, default=4.0, help="pixels per mm in the flattened image")
    ap.add_argument("-o", "--out", default="out")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    img = cv2.imread(a.image)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ratio = flatten(gray)

    # 1. grid -> homography (image px <-> plate mm)
    pts, areas = find_holes(ratio)
    ids, ij = lattice(pts)
    H, inl = cv2.findHomography(ij * a.pitch, pts[ids], cv2.RANSAC, 6.0)
    err = np.linalg.norm(cv2.perspectiveTransform((ij * a.pitch)[None], H)[0] - pts[ids], axis=1)
    print(f"grid: {len(pts)} holes found, {len(ids)} on lattice, fit err median {np.median(err):.1f}px")

    # 2. flatten photo to top-down, ppmm px per mm
    Hinv = np.linalg.inv(H)
    h, w = gray.shape
    corners = cv2.perspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]])[None], Hinv)[0]
    lo = corners.min(0)
    hi = corners.max(0)
    S = np.array([[a.ppmm, 0, -lo[0] * a.ppmm], [0, a.ppmm, -lo[1] * a.ppmm], [0, 0, 1]])
    size = tuple(np.ceil((hi - lo) * a.ppmm).astype(int))
    M = S @ Hinv
    top = cv2.warpPerspective(img, M, size)
    valid = cv2.warpPerspective(np.full((h, w), 255, np.uint8), M, size, flags=cv2.INTER_NEAREST) > 0
    r = cv2.warpPerspective(ratio, M, size)
    sat = cv2.cvtColor(top, cv2.COLOR_BGR2HSV)[..., 1]

    # 3. part mask: dark or coloured, minus every plate hole (we know where they all are)
    plate_sat = np.median(sat[valid])
    mask = ((r < 0.45) | (sat > plate_sat + 35)) & valid
    # hole radius in mm, per hole using local px/mm (perspective), take the big ones
    nn = cKDTree(pts[ids]).query(pts[ids], 2)[0][:, 1]
    r_mm = np.sqrt(areas[ids] / np.pi) / (nn / a.pitch)
    hole_mm = np.percentile(r_mm, 90)
    hole_mm = float(np.clip(hole_mm, 2, 0.4 * a.pitch))
    print(f"plate hole radius ~{hole_mm:.1f} mm")
    holes_only = np.zeros(mask.shape, np.uint8)
    imin, jmin = ij.min(0) - 30
    imax, jmax = ij.max(0) + 30
    for i in range(int(imin), int(imax)):
        for j in range(int(jmin), int(jmax)):
            x, y = (np.array([i, j]) * a.pitch - lo) * a.ppmm
            if 0 <= x < size[0] and 0 <= y < size[1]:
                cv2.circle(holes_only, (int(x), int(y)), int((1.5 * hole_mm + 1.5) * a.ppmm), 1, -1)
    # plate holes touching a part leave bumps. Cut every hole disk out, then close
    # (fills notches the cut left in the part's edge, never grows past a straight edge),
    # then keep only pixels that were dark/coloured to begin with.
    k = lambda mm: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(mm * a.ppmm) | 1,) * 2)
    mask = mask.astype(np.uint8)
    cut = mask & (holes_only == 0)
    mask = cv2.morphologyEx(cut, cv2.MORPH_CLOSE, k(2 * (1.5 * hole_mm + 1.5) + 2)) & mask
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k(4))  # bridge shiny spots
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k(2))  # drop specks

    # 4. outlines -> polygons (keep real through-slots, drop specks)
    cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    parts = []
    for n, c in enumerate(cnts):
        if hier[0][n][3] != -1:
            continue
        shell = c[:, 0, :] / a.ppmm + lo
        holes = []
        ch = hier[0][n][2]
        while ch != -1:
            hp = cnts[ch][:, 0, :] / a.ppmm + lo
            if len(hp) > 3 and Polygon(hp).area > a.slot_min:
                holes.append(hp)
            ch = hier[0][ch][0]
        if len(shell) < 4:
            continue
        p = Polygon(shell, holes).buffer(0)
        if p.area < a.min_area:
            continue
        p = p.buffer(a.smooth).buffer(-a.smooth).buffer(-a.smooth).buffer(a.smooth)  # round wiggles
        if a.offset:
            p = p.buffer(a.offset)
        parts.append(p.simplify(0.1))

    # 5. outputs
    over = top.copy()
    svg = []
    for n, p in enumerate(sorted(parts, key=lambda p: p.bounds[0])):
        minx, miny, maxx, maxy = p.bounds
        rect = p.minimum_rotated_rectangle.exterior.coords
        L = sorted([np.hypot(*np.subtract(rect[i], rect[i + 1])) for i in range(2)])
        print(f"part {n}: {L[1]:.1f} x {L[0]:.1f} mm, area {p.area:.0f} mm^2, {len(p.interiors)} slot(s)")
        m = trimesh.creation.extrude_polygon(p, a.thickness)
        m.export(os.path.join(a.out, f"part{n}.stl"))
        for ring in [p.exterior, *p.interiors]:
            xy = ((np.array(ring.coords) - lo) * a.ppmm).astype(np.int32)
            cv2.polylines(over, [xy], True, (0, 255, 0), 3)
            svg.append('<path d="M' + " L".join(f"{x:.2f},{y:.2f}" for x, y in ring.coords) + ' Z"/>')
        cx, cy = ((np.array(p.centroid.coords[0]) - lo) * a.ppmm).astype(int)
        cv2.putText(over, f"part{n} {L[1]:.0f}mm", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
    cv2.imwrite(os.path.join(a.out, "check.jpg"), over)
    with open(os.path.join(a.out, "outlines.svg"), "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{hi[0]-lo[0]:.1f}mm" height="{hi[1]-lo[1]:.1f}mm" '
                f'viewBox="{lo[0]:.2f} {lo[1]:.2f} {hi[0]-lo[0]:.2f} {hi[1]-lo[1]:.2f}">'
                f'<g fill="none" stroke="black" stroke-width="0.2">{"".join(svg)}</g></svg>')
    print(f"wrote {len(parts)} STL(s), outlines.svg, check.jpg -> {a.out}/")


if __name__ == "__main__":
    main()
