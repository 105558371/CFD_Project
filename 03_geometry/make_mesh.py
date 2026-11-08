#!/usr/bin/env python3
"""
Half-model sounding rocket mesh for SU2 (Gmsh OpenCASCADE, tetrahedra).

Conventions (match rocket_euler.cfg):
  nose tip at x = 0, flow along +x, symmetry plane y = 0, model occupies y >= 0
  4 fins in an "X" arrangement (45 deg off the pitch plane), so the symmetry
  plane never cuts through a fin; the half-model holds 2 of the 4 fins.
Physical groups written to the .su2 file: rocket, symmetry, farfield

Usage:
    python make_mesh.py --level coarse               # -> ../04_mesh/rocket_coarse.su2
    python make_mesh.py --level medium --sweep 40    # 40 deg LE sweep fin
    python make_mesh.py --level coarse --no-mesh     # build geometry only (check groups)
    python make_mesh.py --level coarse --gui         # open Gmsh GUI afterwards
"""
import argparse
import math
import sys
from pathlib import Path

import gmsh

# ---------------- baseline geometry (metres) ----------------
D = 0.10            # body diameter
L = 1.20            # total length
L_NOSE = 0.30       # nose length (3 D)
FIN_ROOT = 0.15     # root chord
FIN_TIP = 0.05      # tip chord
FIN_SPAN = 0.10     # semi-span measured from the body surface
FIN_THK = 0.003     # fin thickness
FIN_EMBED = 0.01    # fin root penetrates the body this far so the fuse is clean
FIN_AZ = 45.0       # fin azimuth from the +y axis (X configuration)

# ---------------- mesh levels ----------------
# h_wall = surface element size on the rocket, h_far = farfield size
LEVELS = {
    "coarse": dict(h_wall=0.012, h_far=2.0, grow=0.35),
    "medium": dict(h_wall=0.008, h_far=2.0, grow=0.30),
    "fine":   dict(h_wall=0.005, h_far=2.0, grow=0.25),
}
FAR_UP = 10.0 * L       # upstream distance from nose
FAR_DOWN = 20.0 * L     # downstream distance from base
FAR_RAD = 10.0 * L      # farfield radius


def von_karman_radius(x, ln, r):
    """Von Karman (Haack, C=0) nose profile radius at axial station x."""
    theta = math.acos(1.0 - 2.0 * x / ln)
    return r / math.sqrt(math.pi) * math.sqrt(max(theta - math.sin(2.0 * theta) / 2.0, 0.0))


def revolve_half(face_tag):
    """Revolve a face (profile at -z side, in the x-z plane) by 180 deg about +x.
    Starting at -z and rotating about +x sweeps through +y, i.e. the y >= 0 half."""
    out = gmsh.model.occ.revolve([(2, face_tag)], 0, 0, 0, 1, 0, 0, math.pi)
    vols = [t for d, t in out if d == 3]
    return vols[0]


def build_body(occ):
    r = D / 2.0
    # profile points on the -z side
    n = 40
    pts = []
    for i in range(n + 1):
        # cosine spacing clusters points near the tip
        x = L_NOSE * 0.5 * (1.0 - math.cos(math.pi * i / n))
        rad = von_karman_radius(x, L_NOSE, r)
        pts.append(occ.addPoint(x, 0.0, -rad))
    p_aft_top = occ.addPoint(L, 0.0, -r)
    p_aft_axis = occ.addPoint(L, 0.0, 0.0)
    # first spline point (tip) lies on the axis
    nose = occ.addSpline(pts)
    side = occ.addLine(pts[-1], p_aft_top)
    base = occ.addLine(p_aft_top, p_aft_axis)
    axis = occ.addLine(p_aft_axis, pts[0])
    loop = occ.addCurveLoop([nose, side, base, axis])
    face = occ.addPlaneSurface([loop])
    return revolve_half(face)


def build_fin(occ, sweep_deg, az_deg):
    r = D / 2.0
    x_le_root = L - FIN_ROOT
    x_le_tip = x_le_root + FIN_SPAN * math.tan(math.radians(sweep_deg))
    x_te_tip = x_le_tip + FIN_TIP
    x_te_root = L
    if x_te_tip > L + 1e-9:
        print(f"WARNING: fin tip trailing edge ({x_te_tip:.3f} m) extends behind the "
              f"base (L = {L} m). Valid but check this is what you want.", file=sys.stderr)
    poly = [
        (x_le_root, r - FIN_EMBED),
        (x_le_root, r),
        (x_le_tip, r + FIN_SPAN),
        (x_te_tip, r + FIN_SPAN),
        (x_te_root, r),
        (x_te_root, r - FIN_EMBED),
    ]
    # drawn in the x-y plane (radial = +y), extruded in z, centred on z = 0
    p = [occ.addPoint(x, y, -FIN_THK / 2.0) for x, y in poly]
    lines = [occ.addLine(p[i], p[(i + 1) % len(p)]) for i in range(len(p))]
    loop = occ.addCurveLoop(lines)
    face = occ.addPlaneSurface([loop])
    out = occ.extrude([(2, face)], 0, 0, FIN_THK)
    vol = [t for d, t in out if d == 3][0]
    occ.rotate([(3, vol)], 0, 0, 0, 1, 0, 0, math.radians(az_deg))
    return vol


def build_farfield(occ):
    p1 = occ.addPoint(-FAR_UP, 0, 0)
    p2 = occ.addPoint(L + FAR_DOWN, 0, 0)
    p3 = occ.addPoint(L + FAR_DOWN, 0, -FAR_RAD)
    p4 = occ.addPoint(-FAR_UP, 0, -FAR_RAD)
    ls = [occ.addLine(p1, p2), occ.addLine(p2, p3), occ.addLine(p3, p4), occ.addLine(p4, p1)]
    loop = occ.addCurveLoop(ls)
    face = occ.addPlaneSurface([loop])
    return revolve_half(face)


def classify_surfaces(vol):
    """Split the domain boundary into symmetry / farfield / rocket by bounding box."""
    tol = 1e-6
    sym, far, rocket = [], [], []
    for dim, tag in gmsh.model.getBoundary([(3, vol)], oriented=False):
        x0, y0, z0, x1, y1, z1 = gmsh.model.getBoundingBox(dim, tag)
        if abs(y1) < tol and abs(y0) < tol:
            sym.append(tag)
        elif (abs(x1 - x0) < tol and (abs(x0 + FAR_UP) < 1e-3 or abs(x0 - (L + FAR_DOWN)) < 1e-3)) \
                or max(y1, abs(z0), abs(z1)) > 0.99 * FAR_RAD:
            far.append(tag)
        else:
            rocket.append(tag)
    return sym, far, rocket


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", choices=LEVELS, default="coarse")
    ap.add_argument("--sweep", type=float, default=30.0, help="fin leading-edge sweep (deg)")
    ap.add_argument("--out", default=None, help="output .su2 path")
    ap.add_argument("--no-mesh", action="store_true", help="build geometry/groups only")
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()

    cfg = LEVELS[args.level]
    out = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "04_mesh" / \
        f"rocket_{args.level}_sw{args.sweep:g}.su2"
    out.parent.mkdir(parents=True, exist_ok=True)

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add("rocket")
    occ = gmsh.model.occ

    body = build_body(occ)
    fins = [build_fin(occ, args.sweep, +FIN_AZ), build_fin(occ, args.sweep, -FIN_AZ)]
    occ.synchronize()
    fused, _ = occ.fuse([(3, body)], [(3, f) for f in fins])
    occ.synchronize()
    far = build_farfield(occ)
    occ.synchronize()
    cut, _ = occ.cut([(3, far)], fused)
    occ.synchronize()

    vols = [t for d, t in cut if d == 3]
    if len(vols) != 1:
        sys.exit(f"Expected 1 fluid volume, got {len(vols)}")
    vol = vols[0]

    sym, farf, rocket = classify_surfaces(vol)
    print(f"surfaces: rocket={len(rocket)} symmetry={len(sym)} farfield={len(farf)}")
    if not (sym and farf and rocket):
        sys.exit("Surface classification failed; open with --gui to inspect")

    gmsh.model.addPhysicalGroup(2, rocket, name="rocket")
    gmsh.model.addPhysicalGroup(2, sym, name="symmetry")
    gmsh.model.addPhysicalGroup(2, farf, name="farfield")
    gmsh.model.addPhysicalGroup(3, [vol], name="fluid")

    if not args.no_mesh:
        # size field: fine near the rocket, growing outward; extra refinement in the wake
        f_dist = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(f_dist, "SurfacesList", rocket)
        gmsh.model.mesh.field.setNumber(f_dist, "Sampling", 200)
        f_thr = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(f_thr, "InField", f_dist)
        gmsh.model.mesh.field.setNumber(f_thr, "SizeMin", cfg["h_wall"])
        gmsh.model.mesh.field.setNumber(f_thr, "SizeMax", cfg["h_far"])
        gmsh.model.mesh.field.setNumber(f_thr, "DistMin", 0.02)
        gmsh.model.mesh.field.setNumber(f_thr, "DistMax", cfg["h_far"] / cfg["grow"] * 0.25 + 0.3)
        f_box = gmsh.model.mesh.field.add("Box")
        gmsh.model.mesh.field.setNumber(f_box, "VIn", cfg["h_wall"] * 3.0)
        gmsh.model.mesh.field.setNumber(f_box, "VOut", cfg["h_far"])
        gmsh.model.mesh.field.setNumber(f_box, "XMin", -0.1)
        gmsh.model.mesh.field.setNumber(f_box, "XMax", L + 2.0)
        gmsh.model.mesh.field.setNumber(f_box, "YMin", 0.0)
        gmsh.model.mesh.field.setNumber(f_box, "YMax", 0.4)
        gmsh.model.mesh.field.setNumber(f_box, "ZMin", -0.4)
        gmsh.model.mesh.field.setNumber(f_box, "ZMax", 0.4)
        gmsh.model.mesh.field.setNumber(f_box, "Thickness", 0.8)
        f_min = gmsh.model.mesh.field.add("Min")
        gmsh.model.mesh.field.setNumbers(f_min, "FieldsList", [f_thr, f_box])
        gmsh.model.mesh.field.setAsBackgroundMesh(f_min)

        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.Algorithm", 6)       # Frontal-Delaunay (2D)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)     # Delaunay (3D)
        gmsh.option.setNumber("Mesh.Optimize", 1)

        gmsh.model.mesh.generate(3)
        n_tet = sum(len(t) for t in gmsh.model.mesh.getElementsByType(4)[:1])
        print(f"tetrahedra: {n_tet:,}")
        gmsh.write(str(out))
        print(f"wrote {out}")

    if args.gui:
        gmsh.fltk.run()
    gmsh.finalize()


if __name__ == "__main__":
    main()
