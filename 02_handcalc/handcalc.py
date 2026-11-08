#!/usr/bin/env python3
"""
Hand calculations for the sounding-rocket CFD project (no SU2 needed).

1. Freestream table at sea-level ISA for each Mach number
2. Isentropic stagnation ratios and normal-shock relations (M > 1)
3. Barrowman CP and static margin for the baseline geometry
   (compare with OpenRocket; this is an approximate, low-AoA subsonic method)

Usage:
    python handcalc.py                       # defaults
    python handcalc.py --cg 0.72 --sweep 40  # other CG / fin sweep
Outputs a console report and handcalc_freestream.csv in the current folder.
"""
import argparse
import csv
import math

GAMMA = 1.4
R_AIR = 287.058
P0 = 101325.0
T0 = 288.15
MU_REF, T_REF, S_SUTH = 1.716e-5, 273.15, 110.4   # Sutherland (air)

# ---- baseline geometry (keep in sync with make_mesh.py) ----
D = 0.10
L = 1.20
L_NOSE = 0.30
FIN_ROOT, FIN_TIP, FIN_SPAN = 0.15, 0.05, 0.10
N_FINS = 4
XCG_DEFAULT = 0.72


def freestream(mach, p=P0, t=T0):
    a = math.sqrt(GAMMA * R_AIR * t)
    v = mach * a
    rho = p / (R_AIR * t)
    q = 0.5 * rho * v * v
    mu = MU_REF * (t / T_REF) ** 1.5 * (T_REF + S_SUTH) / (t + S_SUTH)
    return dict(a=a, V=v, rho=rho, q=q, mu=mu, Re_L=rho * v * L / mu, Re_D=rho * v * D / mu)


def isentropic_ratios(m):
    f = 1.0 + 0.5 * (GAMMA - 1.0) * m * m
    return dict(T0_T=f, p0_p=f ** (GAMMA / (GAMMA - 1.0)), rho0_rho=f ** (1.0 / (GAMMA - 1.0)))


def normal_shock(m1):
    g = GAMMA
    m2 = math.sqrt((1 + 0.5 * (g - 1) * m1**2) / (g * m1**2 - 0.5 * (g - 1)))
    p2_p1 = 1 + 2 * g / (g + 1) * (m1**2 - 1)
    rho2_rho1 = (g + 1) * m1**2 / ((g - 1) * m1**2 + 2)
    t2_t1 = p2_p1 / rho2_rho1
    p02_p01 = (rho2_rho1 ** (g / (g - 1))) * \
        ((g + 1) / (2 * g * m1**2 - (g - 1))) ** (1 / (g - 1))
    return dict(M2=m2, p2_p1=p2_p1, rho2_rho1=rho2_rho1, T2_T1=t2_t1, p02_p01=p02_p01)


def barrowman(sweep_deg, xcg, nose_cp_frac=0.466):
    """Barrowman: nose + fins (constant-diameter body adds no normal force).
    All CN_alpha are per radian, referenced to pi*D^2/4.
    nose_cp_frac = 0.466 is the tangent-ogive value, used here as an approximation
    for the von Karman nose."""
    r = D / 2.0
    # nose
    cn_nose = 2.0
    x_nose = nose_cp_frac * L_NOSE
    # fins
    xm = FIN_SPAN * math.tan(math.radians(sweep_deg))       # LE root -> LE tip, axial
    lf = math.sqrt(FIN_SPAN**2 + (xm + (FIN_TIP - FIN_ROOT) / 2.0) ** 2)  # mid-chord length
    k_fb = 1.0 + r / (FIN_SPAN + r)
    cn_fin = k_fb * (4.0 * N_FINS * (FIN_SPAN / D) ** 2) / \
        (1.0 + math.sqrt(1.0 + (2.0 * lf / (FIN_ROOT + FIN_TIP)) ** 2))
    x_root_le = L - FIN_ROOT
    x_fin = x_root_le + xm / 3.0 * (FIN_ROOT + 2 * FIN_TIP) / (FIN_ROOT + FIN_TIP) \
        + (1.0 / 6.0) * ((FIN_ROOT + FIN_TIP) - FIN_ROOT * FIN_TIP / (FIN_ROOT + FIN_TIP))
    cn_total = cn_nose + cn_fin
    xcp = (cn_nose * x_nose + cn_fin * x_fin) / cn_total
    return dict(cn_nose=cn_nose, cn_fin=cn_fin, cn_total=cn_total, x_fin=x_fin,
                xcp=xcp, margin_cal=(xcp - xcg) / D)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mach", type=float, nargs="+", default=[0.3, 0.8, 0.95, 1.05, 1.5, 2.0])
    ap.add_argument("--cg", type=float, default=XCG_DEFAULT, help="CG from nose tip (m)")
    ap.add_argument("--sweep", type=float, nargs="+", default=[20, 30, 40, 50])
    args = ap.parse_args()

    a_ref = math.pi * D**2 / 4.0
    print(f"Sea-level ISA: p={P0:.0f} Pa, T={T0} K | D={D} m, L={L} m, A_ref={a_ref:.6f} m^2\n")

    print(f"{'M':>5} {'V m/s':>8} {'q Pa':>10} {'Re_L':>10} {'p0/p':>7} "
          f"{'q*Aref N':>9}  shock (M>1): M2  p2/p1  p02/p01")
    rows = []
    for m in args.mach:
        fs = freestream(m)
        iso = isentropic_ratios(m)
        extra = ""
        if m > 1:
            s = normal_shock(m)
            extra = f"  {s['M2']:.3f}  {s['p2_p1']:.3f}  {s['p02_p01']:.3f}"
        print(f"{m:5.2f} {fs['V']:8.1f} {fs['q']:10.0f} {fs['Re_L']:10.2e} {iso['p0_p']:7.3f} "
              f"{fs['q'] * a_ref:9.1f}{extra}")
        rows.append([m, fs["a"], fs["V"], fs["rho"], fs["q"], fs["Re_L"], fs["Re_D"], iso["p0_p"],
                     fs["q"] * a_ref])
    print("\n(q*Aref converts a drag coefficient into newtons: D = CD * q * Aref)\n")

    print(f"Barrowman (x_CG = {args.cg} m from nose, static margin in calibers of D):")
    print(f"{'sweep':>6} {'CNa_nose':>9} {'CNa_fins':>9} {'x_CP m':>8} {'SM cal':>7}")
    for sw in args.sweep:
        b = barrowman(sw, args.cg)
        print(f"{sw:6.0f} {b['cn_nose']:9.2f} {b['cn_fin']:9.2f} {b['xcp']:8.3f} {b['margin_cal']:7.2f}")
    print("\nNote: a 4-fin X-configuration and the von Karman nose are approximated; "
          "compare with OpenRocket and report the difference.")

    with open("handcalc_freestream.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mach", "a_ms", "V_ms", "rho", "q_Pa", "Re_L", "Re_D", "p0_over_p", "q_Aref_N"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
