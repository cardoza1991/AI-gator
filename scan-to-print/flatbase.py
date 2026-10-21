#!/usr/bin/env python3
"""flatbase: FARO scan of a part lying on a flat plate -> watertight solid with flat bottom.

Only the top is scanned; the face on the plate is flat. So the part is a height map:
solid = everything between the plate plane and the scanned top. Holes, missing
patches and the open underside are handled by construction, no Mesh Doctor.

  python flatbase.py scan.ply -o part.stl
  python flatbase.py scan.stl --res 0.25 --smooth 0.5 --offset 0 -o part.stl

Scan may include the plate (best: plane is fit to it) or not (plane fit to the
part's lowest edge). Mesh (stl/ply/obj) or points (ply/xyz/asc/txt) both work.
"""
import argparse
import os

import numpy as np
import trimesh
from scipy import ndimage
from skimage import measure


def load_points(path, n=2_000_000):
    if path.lower().endswith((".xyz", ".asc", ".txt", ".csv")):
        pts = np.loadtxt(path, delimiter="," if path.endswith(".csv") else None, usecols=(0, 1, 2))
        return pts, None
    g = trimesh.load(path)
    if isinstance(g, trimesh.Scene):
        g = g.dump(concatenate=True)
    if isinstance(g, trimesh.PointCloud):
        return np.asarray(g.vertices), None
    pts = g.sample(min(n, max(200_000, int(g.area * 20)))) if len(g.faces) else g.vertices
    return np.vstack([pts, g.vertices]), g


def fit_plane(pts, tol, iters=400, seed=0):
    """RANSAC plane. Returns (normal, d, inlier mask)."""
    rng = np.random.default_rng(seed)
    best = (None, None, np.zeros(len(pts), bool))
    sub = pts[rng.choice(len(pts), min(len(pts), 200_000), replace=False)]
    for _ in range(iters):
        p = sub[rng.choice(len(sub), 3, replace=False)]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        if np.linalg.norm(n) < 1e-9:
            continue
        n /= np.linalg.norm(n)
        inl = np.abs((pts - p[0]) @ n) < tol
        if inl.sum() > best[2].sum():
            best = (n, -p[0] @ n, inl)
    # refine with least squares on inliers
    q = pts[best[2]]
    c = q.mean(0)
    n = np.linalg.svd(q - c, full_matrices=False)[2][-1]
    return n, -c @ n, np.abs((pts - c) @ n) < tol


def to_plane_frame(pts, n, d):
    """Rotate/translate so plane is z=0 and the part is on +z."""
    if np.median(pts @ n + d) < 0:
        n, d = -n, -d
    z = n
    x = np.cross(z, [1, 0, 0] if abs(z[0]) < 0.9 else [0, 1, 0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.array([x, y, z])
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = -R @ (-d * n)
    return T


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scan")
    ap.add_argument("-o", "--out", default="part.stl")
    ap.add_argument("--res", type=float, default=0.25, help="grid mm. 0.25 detailed, 0.5 fast")
    ap.add_argument("--smooth", type=float, default=0.5, help="blur mm. 0 keeps texture/pitting, 1-2 = clean")
    ap.add_argument("--offset", type=float, default=0.0, help="grow sides+top mm (clearance), bottom stays on plate")
    ap.add_argument("--plate-tol", type=float, default=0.3, help="mm: points this close to the plate count as plate")
    ap.add_argument("--fill", type=float, default=3.0, help="mm: close scan gaps up to about this wide")
    ap.add_argument("--faces", type=int, default=200000, help="target face count for slicer")
    ap.add_argument("--min-height", type=float, default=0.5, help="mm above plate to count as part")
    a = ap.parse_args()
    for f in [v for k, v in vars(a).items() if k in ("scan", "ai", "side_a", "side_b", "image") and v]:
        if not os.path.isfile(f):
            raise SystemExit(f"file not found: {f}\n  (run from the folder that has it, or give the full path, e.g. C:\\scans\\part.stl)")

    pts, _ = load_points(a.scan)
    print(f"scan: {len(pts):,} points, size {np.ptp(pts, 0).round(1)} mm")

    # 1. plate plane: big flat set if the plate was scanned, else the part's lowest points
    n, d, inl = fit_plane(pts, a.plate_tol)
    if inl.mean() > 0.15:
        print(f"plate found ({inl.mean():.0%} of points)")
    else:
        h = pts @ n + d
        low = pts[np.abs(h - np.percentile(h, 2)) < 1.0] if np.median(h) > 0 else pts[np.abs(h - np.percentile(h, 98)) < 1.0]
        n, d, _ = fit_plane(low, a.plate_tol)
        print("no plate in scan, using part's lowest edge as the base plane")
    T = to_plane_frame(pts, n, d)
    p = trimesh.transform_points(pts, T)
    p = p[p[:, 2] > a.min_height]  # drop plate + noise under the part
    if len(p) < 100:
        raise SystemExit("nothing above the plate; check --min-height / units")

    # 2. height map: tallest point per cell
    lo = p[:, :2].min(0) - (a.fill + a.offset + 3 * a.smooth + 2)
    hi = p[:, :2].max(0) + (a.fill + a.offset + 3 * a.smooth + 2)
    shape = np.ceil((hi - lo) / a.res).astype(int) + 1
    ij = ((p[:, :2] - lo) / a.res).astype(int)
    H = np.zeros(shape, np.float32)
    np.maximum.at(H, (ij[:, 0], ij[:, 1]), p[:, 2].astype(np.float32))
    # drop isolated junk cells (stray points, dust)
    have = H > 0
    lab, nlab = ndimage.label(ndimage.binary_dilation(have, iterations=2))
    if nlab > 1:
        sizes = ndimage.sum(have, lab, range(1, nlab + 1))
        keep = np.isin(lab, 1 + np.flatnonzero(sizes > 0.02 * sizes.max()))
        have &= keep
        H[~have] = 0

    # 3. footprint: close gaps, fill pinholes, but keep real through-slots
    k = max(1, int(round(a.fill / a.res / 2)))
    foot = ndimage.binary_closing(have, iterations=k, border_value=0)
    # fill missing heights from nearest scanned cell
    idx = ndimage.distance_transform_edt(~have, return_distances=False, return_indices=True)
    Hf = H[idx[0], idx[1]] * foot
    if a.offset:
        grow = ndimage.distance_transform_edt(~foot) * a.res <= a.offset
        idx = ndimage.distance_transform_edt(~foot, return_distances=False, return_indices=True)
        Hf = np.where(foot, Hf, Hf[idx[0], idx[1]] * grow) + a.offset * grow
        foot = grow

    # 4. voxel solid on z>=0, blur with mirror at the plate (bottom edge stays sharp),
    #    one empty slice under it so marching cubes closes a dead-flat bottom
    zs = np.arange(a.res / 2, Hf.max() + 3 * a.smooth + 2 * a.res, a.res)
    if shape[0] * shape[1] * len(zs) > 800e6:
        raise SystemExit("grid too big, raise --res")
    vol = ((zs[None, None, :] <= Hf[:, :, None]) & foot[:, :, None]).astype(np.float32)
    if a.smooth:
        vol = ndimage.gaussian_filter(vol, a.smooth / a.res, mode=("constant", "constant", "reflect"))
    vol = np.pad(vol, ((1, 1), (1, 1), (1, 1)))
    v, f, _, _ = measure.marching_cubes(vol, 0.5, spacing=(a.res,) * 3)
    v -= a.res  # undo pad
    v[:, :2] += lo
    v[:, 2] = np.maximum(v[:, 2] - a.res / 2 + zs[0] - a.res / 2, 0)  # bottom -> z=0
    m = trimesh.Trimesh(v, f[:, ::-1])
    m.fix_normals()
    if len(m.faces) > a.faces:
        try:
            m = m.simplify_quadric_decimation(face_count=a.faces)
        except Exception as e:  # needs fast-simplification
            print(f"  decimate skipped ({e})")
    print(f"part: {np.ptp(m.vertices, 0).round(2)} mm, {len(m.faces):,} faces, watertight={m.is_watertight}")
    m.export(a.out)
    print(f"wrote {a.out} (bottom on z=0)")


if __name__ == "__main__":
    main()
