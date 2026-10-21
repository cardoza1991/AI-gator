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

from flatbase import drop_strays, load_points, unit_scale


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


def make_watertight(m):
    """Fix the rare marching-cubes pinch (edge shared by 4 faces): cut it out, keep the
    main body, patch the tiny hole."""
    m.merge_vertices()
    if m.is_watertight:
        return m
    u, inv, cnt = np.unique(m.edges_sorted, axis=0, return_inverse=True, return_counts=True)
    bad_v = np.unique(u[cnt != 2])
    m.update_faces(~np.isin(m.faces, bad_v).any(1))
    m.remove_unreferenced_vertices()
    parts = m.split(only_watertight=False)
    m = max(parts, key=lambda p: len(p.faces))
    # cap each small hole with a fan from its centre
    u, cnt = np.unique(m.edges_sorted, axis=0, return_counts=True)
    open_e = u[cnt == 1]
    if len(open_e):
        import networkx as nx

        verts = [m.vertices]
        faces = [m.faces]
        nv = len(m.vertices)
        for loop in nx.cycle_basis(nx.Graph(open_e.tolist())):
            verts.append(m.vertices[loop].mean(0)[None])
            faces.append(np.array([[loop[i], loop[(i + 1) % len(loop)], nv] for i in range(len(loop))]))
            nv += 1
        m = trimesh.Trimesh(np.vstack(verts), np.vstack(faces))
    m.fix_normals()
    return m


def voxel_shell(clouds, voxel, smooth, close, offset=0.0):
    """Rasterize surface points, close gaps, fill inside, blur, re-surface. Always watertight."""
    pad = (2 * close + 4 * smooth + 6) * voxel + offset
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
    surface = grid
    # thicken skin so gaps <= 2*k voxels seal, fill inside, shrink back.
    # If the shell still leaks (big scan gaps), seal harder rather than output scrap.
    for k in (close + 1, 2 * close + 2):
        shell = ndimage.binary_dilation(surface, ball, iterations=k)
        grid = ndimage.binary_fill_holes(shell)
        if grid.sum() > 1.5 * shell.sum():
            grid = ndimage.binary_erosion(grid, ball, iterations=k, border_value=0)
            break
        print(f"  shell leaks at {k * voxel:.1f} mm sealing, trying harder")
    else:
        # big gaps (usually side walls): fill each column between top and bottom skin.
        # Grid z is the part's thinnest direction (see main), so this is top-to-bottom.
        print("  big gaps: filling between top and bottom surfaces instead")
        k = close + 1
        skin = ndimage.binary_dilation(surface, ball, iterations=1)
        z = np.arange(skin.shape[2])
        first = np.where(skin.any(2), skin.argmax(2), -1)
        last = np.where(skin.any(2), skin.shape[2] - 1 - skin[:, :, ::-1].argmax(2), -2)
        grid = (z >= first[..., None]) & (z <= last[..., None])
        grid = ndimage.binary_closing(grid, ball, iterations=k)
        grid = ndimage.binary_erosion(grid, ball, iterations=1, border_value=0)  # undo skin growth
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
    return make_watertight(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scan", help="raw scan: mesh (stl/ply/obj) or points (asc/xyz/ply)")
    ap.add_argument("--ai", help="AI mesh made from photos (glb/obj/stl); fills scan holes")
    ap.add_argument("-o", "--out", default="smooth.stl")
    ap.add_argument("--voxel", type=float, default=0.5, help="grid size in scan units (mm). bigger = blobbier, faster")
    ap.add_argument("--smooth", type=float, default=1.5, help="blur in voxels. 0 = keep detail, 3+ = soap bar")
    ap.add_argument("--close", type=int, default=3, help="voxels of gap to seal in scan")
    ap.add_argument("--offset", type=float, default=0.0, help="grow surface outward by this many mm (clearance)")
    ap.add_argument("--faces", type=int, default=200000, help="target face count for slicer")
    ap.add_argument("--units", choices=["auto", "mm", "in"], default="auto", help="scan units; output is always mm")
    a = ap.parse_args()
    for f in [v for k, v in vars(a).items() if k in ("scan", "ai", "side_a", "side_b", "image") and v]:
        if f.lower().endswith(".wrp"):
            raise SystemExit(f"{f} is a Geomagic Wrap project, which can't be read outside Wrap.\n"
                             "  In Wrap: select the scans, File > Save As > .stl (mesh) or .asc (points), then use that file.")
        if not os.path.isfile(f):
            raise SystemExit(f"file not found: {f}\n  (run from the folder that has it, or give the full path, e.g. C:\\scans\\part.stl)")

    pts, scan = load_points(a.scan)
    k = unit_scale(pts, a.units)
    if scan is not None and len(scan.faces):
        scan.apply_scale(k)  # no size-based junk filter: real scans are many small passes
        cloud = drop_strays(surface_points(scan, a.voxel))
        print(f"scan: mesh, {len(scan.faces):,} faces, size {np.ptp(cloud, 0).round(2)} mm")
        meshes = [scan]
        clouds = [cloud]
    else:
        pts = drop_strays(pts * k)
        print(f"scan: points, {len(pts):,}, size {np.ptp(pts, 0).round(2)} mm")
        meshes = []
        clouds = [pts]
    if a.ai:
        if not meshes:
            raise SystemExit("--ai needs the scan as a mesh (stl/obj/ply with faces)")
        ai = drop_junk(load(a.ai))
        clouds.append(surface_points(align_ai_to_scan(ai, scan), a.voxel))

    # work in the part's own frame: longest axis x, thinnest axis z
    allp = np.vstack(clouds)
    c, vt = pca_frame(allp[:: max(1, len(allp) // 200000)])
    if np.linalg.det(vt) < 0:
        vt[2] *= -1
    clouds = [(p - c) @ vt.T for p in clouds]
    out = voxel_shell(clouds, a.voxel, a.smooth, a.close, a.offset)
    out.vertices = out.vertices @ vt + c
    if len(out.faces) > a.faces:
        try:
            dec = out.simplify_quadric_decimation(face_count=a.faces)
            if dec.is_watertight:
                out = dec
            else:
                print("  decimated mesh not watertight, keeping full resolution")
        except Exception as e:  # needs fast-simplification pkg
            print(f"  decimate skipped ({e})")
    print(f"out: {len(out.faces)} faces, size {out.extents.round(2)}, watertight={out.is_watertight}")
    out.export(a.out)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
