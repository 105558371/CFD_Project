# Aerodynamic analysis of a sounding rocket (SU2)

| Folder | Contents |
|---|---|
| 01_notes | notes, session plan, email drafts |
| 02_handcalc | `handcalc.py`: freestream, shock relations, Barrowman CP |
| 03_geometry | `make_mesh.py`: Gmsh half-model, fins in X layout |
| 04_mesh | generated `.su2` meshes (git-ignored) |
| 05_cases | `rocket_euler.cfg`, `sweep.py`, `runs/` (git-ignored) |
| 06_results | `postprocess.py`, `run_matrix.xlsx`, `results*.csv`, figures |
| 07_report | report |

Quick start (from the repo root):
```
python3 02_handcalc/handcalc.py
python3 03_geometry/make_mesh.py --level coarse
cd 05_cases
python3 sweep.py --mesh ../04_mesh/rocket_coarse_sw30.su2 --tag coarse --mach 0.8 --aoa 0 --threads 8 --dry-run
```
