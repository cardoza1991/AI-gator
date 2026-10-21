#!/usr/bin/env python3
"""twoside: two FARO scans of a part (side A up, then flipped, side B up) -> one watertight solid.

For parts with shape on both faces. Each scan may include the plate; it is found
and stripped. Side B is flipped onto side A automatically (footprint match, then
ICP that only pairs surfaces facing the same way, so the two faces can't collapse
onto each other). The merged points are rebuilt as a voxel solid, no Mesh Doctor.

  python twoside.py sideA.xyz sideB.xyz -o part.stl
  python twoside.py sideA.stl sideB.stl --voxel 0.3 --smooth 1 --offset 1.5 -o part.stl
"""
import argparse

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from flatbase import fit_plane, load_points, to_plane_frame
from smoothprint import voxel_shell


def strip_plate(pts, tol, min_height):
    """Level the scan onto its plate (z=0, part on +z) and drop the plate."""
    n, d, inl = fit_plane(pts, tol)
    if inl.mean() < 0.15:
        print("  no plate found, using the scan as-is (assumes it's already only the part)")
        return pts - [0, 0, pts[:, 2].min()], False
    h = pts @ n + d
    if (h > min_height).sum() < (h < -min_height).sum():  # part on the other side
        n, d = -n, -d
    p = trimesh.transform_points(pts, to_plane_frame(pts, n, d))
    return p[p[:, 2] > min_height], True


def normals(pts, k=16):
    """PCA normals, oriented toward the scanner (+z) or outward from the part axis."""
    tree = cKDTree(pts)
    _, idx = tree.query(pts, k)
    nb = pts[idx] - pts[idx].mean(1, keepdims=True)
    n = np.linalg.eigh(np.einsum("nki,nkj->nij", nb, nb))[1][:, :, 0]
    out = pts[:, :2] - pts[:, :2].mean(0)
    flip = np.where(np.abs(n[:, 2]) > 0.5, n[:, 2] < 0, (n[:, :2] * out).sum(1) < 0)
    n[flip] *= -1
    return n


def footprint_frame(p):
    c = p[:, :2].mean(0)
    w, v = np.linalg.eigh(np.cov((p[:, :2] - c).T))
    return c, v[:, ::-1]  # major axis first


def align_b_to_a(A, B, iters=60, sample=30000):
    """Flip B, match footprints (4 yaw candidates), then normal-aware trimmed ICP."""
    rng = np.random.default_rng(0)
    A = A[rng.choice(len(A), min(sample, len(A)), replace=False)]
    B0 = B[rng.choice(len(B), min(sample, len(B)), replace=False)]
    nA = normals(A)
    tree = cKDTree(A)
    ca, va = footprint_frame(A)
    flipT = np.diag([1.0, -1.0, -1.0, 1.0])  # turn over about x
    Bf = trimesh.transform_points(B0, flipT)
    cb, vb = footprint_frame(Bf)
    best = None
    for sx, sy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
        R2 = va @ np.diag([sx, sy]) @ vb.T
        if np.linalg.det(R2) < 0:  # flipping already handled; no mirror images
            continue
        T = np.eye(4)
        T[:2, :2] = R2
        T[:2, 3] = ca - R2 @ cb
        T[2, 3] = -Bf[:, 2].min()  # both sides rest on the plate: bottom of flipped B at z=0
        T = T @ flipT
        nB = normals(B0)  # normals in B's own frame, moved with T below
        for _ in range(iters):
            Bt = trimesh.transform_points(B0, T)
            nBt = nB @ T[:3, :3].T
            d, idx = tree.query(Bt, 6)
            ok = (nA[idx] * nBt[:, None, :]).sum(2) > 0.3  # only same-facing surfaces pair up
            first = np.where(ok.any(1), ok.argmax(1), -1)
            m = first >= 0
            j = idx[np.arange(len(Bt)), np.maximum(first, 0)][m]
            dist = d[np.arange(len(Bt)), np.maximum(first, 0)][m]
            if m.sum() < 50:
                break
            keep = dist < max(np.percentile(dist, 70), 1e-6)  # overlap is only the side walls
            M, _, _ = trimesh.registration.procrustes(
                Bt[m][keep], A[j][keep], reflection=False, scale=False, return_cost=True
            )
            T = M @ T
        err = np.median(dist[keep]) if m.sum() >= 50 else np.inf
        if best is None or err < best[0]:
            best = (err, T, int(keep.sum()))
    print(f"  side B -> A: median gap {best[0]:.3f} mm over {best[2]} overlapping points")
    return trimesh.transform_points(B, best[1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("side_a")
    ap.add_argument("side_b", help="same part flipped over")
    ap.add_argument("-o", "--out", default="part.stl")
    ap.add_argument("--voxel", type=float, default=0.3, help="grid mm")
    ap.add_argument("--smooth", type=float, default=1.0, help="blur in voxels. 0 keeps pitting/rust")
    ap.add_argument("--close", type=int, default=4, help="voxels of gap to seal")
    ap.add_argument("--offset", type=float, default=0.0, help="grow outward mm (clearance)")
    ap.add_argument("--plate-tol", type=float, default=0.3)
    ap.add_argument("--min-height", type=float, default=0.3, help="mm above plate that counts as part")
    ap.add_argument("--faces", type=int, default=200000)
    a = ap.parse_args()

    sides = []
    for name in (a.side_a, a.side_b):
        pts, _ = load_points(name)
        p, plate = strip_plate(pts, a.plate_tol, a.min_height)
        print(f"{name}: {len(pts):,} pts -> {len(p):,} on part, height {np.ptp(p[:, 2]):.2f} mm")
        sides.append(p)
    A, B = sides
    B = align_b_to_a(A, B)

    out = voxel_shell([A, B], a.voxel, a.smooth, a.close, a.offset)
    if len(out.faces) > a.faces:
        try:
            out = out.simplify_quadric_decimation(face_count=a.faces)
        except Exception as e:
            print(f"  decimate skipped ({e})")
    print(f"part: {out.extents.round(2)} mm, {len(out.faces):,} faces, watertight={out.is_watertight}")
    out.export(a.out)
    np.savetxt(a.out.rsplit(".", 1)[0] + "_merged.xyz", np.vstack([A, B])[::4], fmt="%.3f")
    print(f"wrote {a.out} (+ _merged.xyz to inspect the alignment)")


if __name__ == "__main__":
    main()
