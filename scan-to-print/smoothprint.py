#!/usr/bin/env python3
"""smoothprint: messy scan (+ optional AI mesh from photos) -> smooth watertight STL.

Scan = truth for size. AI mesh (Hunyuan3D / TRELLIS / Meshy output) = fills scan holes.
No mesh doctor. Everything goes through a voxel volume, so holes, spikes,
self-intersections and flipped normals vanish by construction.

  python smoothprint.py scan.stl -o out.stl
  python smoothprint.py scan.stl --ai ai.glb --smooth 2.0 --voxel 0.5 -o out.stl
"""
import argparse
import os

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import measure


def load(path):
    m = trimesh.load(path, force="mesh")
    m.remove_unreferenced_vertices()
    return m


def drop_junk(mesh, keep_frac=0.02):
    """Delete floating islands (dust, turntable bits) smaller than keep_frac of biggest."""
    parts = mesh.split(only_watertight=False)
    if len(parts) <= 1:
        return mesh
    biggest = max(p.area for p in parts)
    return trimesh.util.concatenate([p for p in parts if p.area >= keep_frac * biggest])


def pca_frame(pts):
    c = pts.mean(0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    return c, vt


def align_ai_to_scan(ai, scan, iters=40):
    """Scale + rotate + move AI mesh onto scan. PCA guess (8 axis flips) then scaled ICP."""
    src = ai.sample(20000)
    dst = scan.sample(20000)
    tree = cKDTree(dst)
    cs, vs = pca_frame(src)
    cd, vd = pca_frame(dst)
    scale0 = np.sqrt(((dst - cd) ** 2).sum(1).mean() / ((src - cs) ** 2).sum(1).mean())

    best = None
    for flips in np.array(np.meshgrid([1, -1], [1, -1], [1, -1])).T.reshape(-1, 3):
        R = vd.T @ np.diag(flips) @ vs
        if np.linalg.det(R) < 0:
            continue
        T = np.eye(4)
        T[:3, :3] = R * scale0
        T[:3, 3] = cd - (R * scale0) @ cs
        moved = trimesh.transform_points(src, T)
        for _ in range(iters):
            d, idx = tree.query(moved)
            keep = d < np.percentile(d, 90)  # ignore AI parts scan never saw
            M, _, _ = trimesh.registration.procrustes(
                moved[keep], dst[idx[keep]], reflection=False, scale=True, return_cost=True
            )
            moved = trimesh.transform_points(moved, M)
            T = M @ T
        err = np.median(tree.query(moved)[0])
        if best is None or err < best[0]:
            best = (err, T)
    print(f"  AI align median err: {best[0]:.3f} (scan units)")
    out = ai.copy()
    out.apply_transform(best[1])
    return out


def surface_points(mesh, voxel):
    """Dense enough samples that every voxel the surface crosses gets hit."""
    return mesh.sample(int(mesh.area / (voxel * voxel) * 4) + 1000)


def voxel_shell(clouds, voxel, smooth, close, offset=0.0):
    """Rasterize surface points, close gaps, fill inside, blur, re-surface. Always watertight."""
    pad = (close + 4 * smooth + 3) * voxel + offset
    lo = np.min([c.min(0) for c in clouds], 0) - pad
    hi = np.max([c.max(0) for c in clouds], 0) + pad
    shape = np.ceil((hi - lo) / voxel).astype(int) + 1
    if np.prod(shape) > 600e6:
        raise SystemExit(f"grid {shape} too big, raise --voxel")
    grid = np.zeros(shape, bool)
    for pts in clouds:
        ijk = np.round((pts - lo) / voxel).astype(int)
        grid[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True

    ball = ndimage.generate_binary_structure(3, 1)
    # thicken skin so gaps <= 2*close voxels seal, fill inside, shrink back
    k = close + 1
    shell = ndimage.binary_dilation(grid, ball, iterations=k)
    grid = ndimage.binary_fill_holes(shell)
    if grid.sum() < 1.5 * shell.sum():
        print("  WARN: shell did not close (hole too big). use --ai or raise --close")
    grid = ndimage.binary_erosion(grid, ball, iterations=k, border_value=0)
    grid = ndimage.binary_opening(grid, ball, iterations=1)  # kill spikes
    lab, n = ndimage.label(grid)
    if n > 1:  # keep biggest solid
        grid = lab == (np.bincount(lab.ravel())[1:].argmax() + 1)

    if offset:  # grow outward, e.g. clearance for leather / sheath buck
        grid = ndimage.distance_transform_edt(~grid) * voxel <= offset
    vol = ndimage.gaussian_filter(grid.astype(np.float32), sigma=smooth) if smooth else grid.astype(np.float32)
    v, f, _, _ = measure.marching_cubes(vol, 0.5, spacing=(voxel,) * 3)
    out = trimesh.Trimesh(v + lo, f[:, ::-1])
    out.fix_normals()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scan", help="raw scan mesh (stl/ply/obj)")
    ap.add_argument("--ai", help="AI mesh made from photos (glb/obj/stl); fills scan holes")
    ap.add_argument("-o", "--out", default="smooth.stl")
    ap.add_argument("--voxel", type=float, default=0.5, help="grid size in scan units (mm). bigger = blobbier, faster")
    ap.add_argument("--smooth", type=float, default=1.5, help="blur in voxels. 0 = keep detail, 3+ = soap bar")
    ap.add_argument("--close", type=int, default=3, help="voxels of gap to seal in scan")
    ap.add_argument("--offset", type=float, default=0.0, help="grow surface outward by this many mm (clearance)")
    ap.add_argument("--faces", type=int, default=200000, help="target face count for slicer")
    a = ap.parse_args()
    for f in [v for k, v in vars(a).items() if k in ("scan", "ai", "side_a", "side_b", "image") and v]:
        if not os.path.isfile(f):
            raise SystemExit(f"file not found: {f}\n  (run from the folder that has it, or give the full path, e.g. C:\\scans\\part.stl)")

    scan = drop_junk(load(a.scan))
    print(f"scan: {len(scan.faces)} faces, size {scan.extents.round(2)}")
    meshes = [scan]
    if a.ai:
        ai = drop_junk(load(a.ai))
        meshes.append(align_ai_to_scan(ai, scan))

    out = voxel_shell([surface_points(m, a.voxel) for m in meshes], a.voxel, a.smooth, a.close, a.offset)
    if len(out.faces) > a.faces:
        try:
            out = out.simplify_quadric_decimation(face_count=a.faces)
        except Exception as e:  # needs fast-simplification pkg
            print(f"  decimate skipped ({e})")
    print(f"out: {len(out.faces)} faces, size {out.extents.round(2)}, watertight={out.is_watertight}")
    out.export(a.out)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
