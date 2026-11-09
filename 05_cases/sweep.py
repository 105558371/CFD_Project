#!/usr/bin/env python3
"""
Mach / AoA sweep driver for SU2.

Usage (from 05_cases/; meshes live in ../04_mesh/):
    python sweep.py --mesh ../04_mesh/rocket_medium_sw30.su2 --tag medium --mach 0.3 0.8 1.05 2.0 --aoa 0 4 --threads 8
    python sweep.py --mach 0.8 --aoa 0 --threads 8 --dry-run      # just write configs
    python sweep.py ... --chain                              # restart from previous case

Each case runs in runs/M<mach>_a<aoa>/ and results go to results.csv.
Finished cases (already in results.csv) are skipped, so you can re-run safely.
"""
import argparse
import csv
import re
import shutil
import subprocess
from pathlib import Path

BASE_CFG = "rocket_euler.cfg"
MESH = "rocket.su2"
RESULTS = Path("results.csv")


def set_option(text, key, value):
    """Replace 'KEY= old' with 'KEY= value' (first match, line-anchored)."""
    pattern = re.compile(rf"^{key}\s*=.*$", re.MULTILINE)
    if not pattern.search(text):
        raise KeyError(f"{key} not found in base config")
    return pattern.sub(f"{key}= {value}", text, count=1)


def case_name(mach, aoa):
    return f"M{mach:g}_a{aoa:g}"


def read_last_row(history_path):
    """Return dict of the last row of history.csv with cleaned column names."""
    with open(history_path, newline="") as f:
        reader = csv.reader(f)
        header = [h.strip().strip('"') for h in next(reader)]
        last = None
        for row in reader:
            if row:
                last = row
    if last is None:
        raise RuntimeError("history.csv has no data rows")
    return {h: v.strip() for h, v in zip(header, last)}


def find(row, *names):
    """Case-insensitive column lookup; returns float or None."""
    lower = {k.lower(): v for k, v in row.items()}
    for n in names:
        if n.lower() in lower:
            return float(lower[n.lower()])
    return None


def done_cases():
    if not RESULTS.exists():
        return set()
    with open(RESULTS, newline="") as f:
        return {(float(r["mach"]), float(r["aoa"])) for r in csv.DictReader(f)}


def append_result(mach, aoa, row):
    new = not RESULTS.exists()
    with open(RESULTS, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["mach", "aoa", "CD", "CL", "CMy", "final_iter", "rms_density"])
        w.writerow([
            mach, aoa,
            find(row, "CD"), find(row, "CL"), find(row, "CMy"),
            find(row, "Inner_Iter", "Cur_Iter", "Time_Iter"),
            find(row, "rms[Rho]", "rms[rho]"),
        ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mach", type=float, nargs="+", required=True)
    ap.add_argument("--aoa", type=float, nargs="+", default=[0.0])
    ap.add_argument("--mesh", default=MESH, help="mesh file to use (copied in as rocket.su2)")
    ap.add_argument("--cfg", default=BASE_CFG, help="base config file")
    ap.add_argument("--tag", default="", help="suffix for run folders / results, e.g. medium")
    ap.add_argument("--np", type=int, default=1, help="MPI processes (needs an MPI build of SU2)")
    ap.add_argument("--threads", type=int, default=1, help="OpenMP threads (SU2_CFD -t N)")
    ap.add_argument("--su2", default="SU2_CFD", help="path/name of SU2_CFD")
    ap.add_argument("--mpi", default="mpirun", help="MPI launcher")
    ap.add_argument("--chain", action="store_true",
                    help="restart each case from the previous one (helps transonic)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    global RESULTS
    if args.tag:
        RESULTS = Path(f"results_{args.tag}.csv")
    base = Path(args.cfg).read_text()
    mesh = Path(args.mesh)
    if not mesh.exists():
        raise SystemExit(f"{args.mesh} not found")

    finished = done_cases()
    prev_restart = None

    for aoa in args.aoa:
        for mach in sorted(args.mach):
            if (mach, aoa) in finished:
                print(f"skip {case_name(mach, aoa)} (already in results.csv)")
                continue

            d = Path("runs") / (case_name(mach, aoa) + (f"_{args.tag}" if args.tag else ""))
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy(mesh, d / MESH)

            cfg = set_option(base, "MACH_NUMBER", mach)
            cfg = set_option(cfg, "AOA", aoa)
            if args.chain and prev_restart and prev_restart.exists():
                shutil.copy(prev_restart, d / "solution_flow.dat")
                cfg = set_option(cfg, "RESTART_SOL", "YES")
            (d / "config.cfg").write_text(cfg)

            if args.dry_run:
                print(f"wrote {d}/config.cfg")
                continue

            cmd = [args.su2] + (["-t", str(args.threads)] if args.threads > 1 else []) + ["config.cfg"]
            if args.np > 1:
                cmd = [args.mpi, "-n", str(args.np)] + cmd
            print(f"running {case_name(mach, aoa)}: {' '.join(cmd)}")
            with open(d / "log.txt", "w") as log:
                rc = subprocess.run(cmd, cwd=d, stdout=log, stderr=subprocess.STDOUT).returncode
            if rc != 0:
                print(f"  SU2 exited with code {rc}; see {d}/log.txt")
                continue

            try:
                row = read_last_row(d / "history.csv")
                append_result(mach, aoa, row)
                print(f"  CD={find(row, 'CD')}  CL={find(row, 'CL')}  CMy={find(row, 'CMy')}")
            except Exception as e:
                print(f"  could not read history.csv: {e}")
            prev_restart = d / "restart_flow.dat"

    if RESULTS.exists():
        print(f"\nResults in {RESULTS}")


if __name__ == "__main__":
    main()
