#!/usr/bin/env python3
"""
Post-process SU2 sweep results.

Reads  results.csv      (from sweep.py: mach, aoa, CD, CL, CMy, ...)
Writes cd_vs_mach.png, cl_cm_vs_aoa.png, stability.csv
Optional mesh study:  python postprocess.py --mesh-study mesh_study.csv
    mesh_study.csv columns: level,cells,CD    (coarse, medium, fine)

Usage:
    python postprocess.py --cg 0.72 --lref 0.1
"""
import argparse
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plots_and_stability(path, xcg, lref):
    df = pd.read_csv(path).sort_values(["aoa", "mach"])

    # CD vs Mach (alpha = 0 only)
    d0 = df[df.aoa == 0]
    if not d0.empty:
        plt.figure(figsize=(6, 4))
        plt.plot(d0.mach, d0.CD, "o-")
        plt.xlabel("Mach number")
        plt.ylabel("$C_D$")
        plt.title("Drag coefficient vs Mach (AoA = 0)")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig("cd_vs_mach.png", dpi=200)
        plt.close()

    # CL and CMy vs AoA, one line per Mach
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for m, g in df.groupby("mach"):
        g = g.sort_values("aoa")
        ax[0].plot(g.aoa, g.CL, "o-", label=f"M={m:g}")
        ax[1].plot(g.aoa, g.CMy, "o-", label=f"M={m:g}")
    ax[0].set_xlabel("AoA (deg)"); ax[0].set_ylabel("$C_L$")
    ax[1].set_xlabel("AoA (deg)"); ax[1].set_ylabel("$C_{m,y}$ (about CG)")
    for a in ax:
        a.grid(alpha=0.3); a.legend()
    plt.tight_layout()
    plt.savefig("cl_cm_vs_aoa.png", dpi=200)
    plt.close()

    # Stability from the smallest nonzero AoA at each Mach.
    # Sign convention: SU2 body-axis CMy is nose-up positive. For a statically stable
    # rocket dCm/dalpha < 0 and x_CP is aft of x_CG. CHECK this against OpenRocket
    # on your first stable case; if x_CP comes out forward of CG, flip the sign.
    rows = []
    for m, g in df.groupby("mach"):
        base = g[g.aoa == 0]
        pos = g[g.aoa > 0].sort_values("aoa")
        if base.empty or pos.empty:
            continue
        a = pos.iloc[0]
        da = math.radians(a.aoa)
        cl_a = (a.CL - base.iloc[0].CL) / da
        cm_a = (a.CMy - base.iloc[0].CMy) / da
        cn_a = cl_a            # small-angle approximation (CN ~ CL)
        xcp = xcg - cm_a / cn_a * lref if cn_a != 0 else float("nan")
        rows.append(dict(mach=m, aoa_used=a.aoa, CLalpha_per_rad=cl_a, Cmalpha_per_rad=cm_a,
                         x_cp=xcp, static_margin_cal=(xcp - xcg) / lref))
    out = pd.DataFrame(rows)
    out.to_csv("stability.csv", index=False)
    print(out.to_string(index=False) if not out.empty else "No AoA > 0 cases yet for stability.")


def mesh_study(path):
    df = pd.read_csv(path)
    order = {"coarse": 0, "medium": 1, "fine": 2}
    df = df.sort_values("level", key=lambda s: s.map(order)).reset_index(drop=True)
    cd = df.CD.tolist()
    n = df.cells.tolist()
    print(df.to_string(index=False))
    if len(df) == 3:
        # effective refinement ratio in 3D: r = (N_fine / N_coarse)^(1/3) per step
        r21 = (n[1] / n[0]) ** (1 / 3)
        r32 = (n[2] / n[1]) ** (1 / 3)
        e21, e32 = cd[1] - cd[0], cd[2] - cd[1]
        print(f"\nchange coarse->medium: {e21:+.5f} ({e21 / cd[1] * 100:+.2f}%)")
        print(f"change medium->fine  : {e32:+.5f} ({e32 / cd[2] * 100:+.2f}%)")
        if e21 * e32 > 0 and abs(e32) > 0 and abs(e21 / e32) > 1 and abs(r21 - r32) < 0.2:
            p = math.log(abs(e21 / e32)) / math.log((r21 + r32) / 2)
            cd_ext = cd[2] + e32 / (((r21 + r32) / 2) ** p - 1)
            print(f"observed order p = {p:.2f}, Richardson-extrapolated CD = {cd_ext:.5f}")
        else:
            print("Not monotonic or inconsistent ratios: report the changes, skip Richardson.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results.csv")
    ap.add_argument("--cg", type=float, default=0.72)
    ap.add_argument("--lref", type=float, default=0.1)
    ap.add_argument("--mesh-study", default=None)
    args = ap.parse_args()
    try:
        plots_and_stability(args.results, args.cg, args.lref)
    except FileNotFoundError:
        print(f"{args.results} not found yet; run sweep.py first.")
    if args.mesh_study:
        mesh_study(args.mesh_study)


if __name__ == "__main__":
    main()
