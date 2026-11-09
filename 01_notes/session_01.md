# First iMac session plan

**Goal for the day:** one converged coarse Euler run (M = 0.8, AoA = 0) with a readable log and a ParaView picture. Everything else is a bonus.

**How to read this plan:** each step has a *Why* (the theory), a *Where in code* line (where that theory lives in your files), and sometimes a *Predict first* prompt. Write your prediction in the logbook before you run the step, then compare. Being wrong is useful.

## Predictions to log before you start
1. At M = 0.8 with Euler (no viscosity), will your CD be higher or lower than a real rocket's at the same Mach? By roughly how much, and why?
2. At the nose tip, what pressure coefficient Cp do you expect? (Hint: step 3 gives you the number.)
3. If you shrink the surface element size from 12 mm to 8 mm, how many times more cells do you expect in 3D? (Hint: cells scale like (1/h)^3.)

## Before you leave home
- [ ] Unzip the workspace into your repo folder, then `git add .`, `git commit`, `git push`
- [ ] Bring a USB stick or have cloud access (meshes and results are git-ignored)

## 1. Arrive and set up (20 min)
```
git clone https://github.com/105558371/CFD_Project.git rocket-cfd
cd rocket-cfd
which SU2_CFD gmsh python3 mpirun git
SU2_CFD --help | head -n 3
sysctl -n hw.ncpu hw.memsize
df -h ~
python3 -m pip install --user numpy pandas matplotlib gmsh
```
- **Why:** CFD memory grows with the number of cells, and speed grows with the number of cores. These numbers tell you how big a mesh you can afford and what to pass to `SU2_CFD -t`.
- **Where in code:** `--threads` in `sweep.py`; the cell counts from `make_mesh.py` in step 5.
- Write the answers in `logbook.md` (machine info section).

## 2. Smoke test SU2 on a tutorial (30 min)
Run one small compressible Euler case from the SU2 tutorials. Goal: see residuals fall, find `history.csv`, open the result in ParaView. If this fails, fix it before anything else.
- **Why:** the Euler equations are conservation of mass, momentum and energy with no viscosity. SU2 solves them cell by cell and repeats until the imbalance (the *residual*) is small. A falling residual means the solution is approaching a state that satisfies those conservation laws.
- **Where in code:** the `rms[Rho]` column in `history.csv` is the density (mass-conservation) residual; `CONV_RESIDUAL_MINVAL= -8` in `rocket_euler.cfg` is the stopping target.
- **Predict first:** when residuals drop, will CD settle immediately or keep moving for a while? Watch and see.

## 3. Hand calculations (10 min)
```
python3 02_handcalc/handcalc.py
```
- **Why:** you need independent numbers to judge CFD against. The speed of sound is a = sqrt(gamma R T), velocity is V = M a, and dynamic pressure is q = 0.5 rho V^2. A coefficient times q times A_ref gives a force in newtons.
- **Where in code:** `freestream()` and `normal_shock()` in `handcalc.py`; `MACH_NUMBER` and `FREESTREAM_*` in the config.
- **Check:** the M = 2 line should read M2 = 0.577, p2/p1 = 4.5, p02/p01 = 0.721 (textbook values).
- **Predict first:** if CD = 0.3 at M = 0.8, what drag force is that in newtons? (Use the `q*Aref N` column.)
- **Also note:** the `p0/p` value at M = 0.8 (1.524). The stagnation pressure coefficient at the nose is Cp0 = (p0/p - 1) / (0.5 gamma M^2) = 0.524 / 0.448 = about 1.17. That is your prediction 2, and you will check it in step 7.

## 4. OpenRocket baseline (20 min)
Enter these so it matches the CFD model:
- Nose cone: von Karman, length 300 mm, diameter 100 mm
- Body tube: length 900 mm, diameter 100 mm
- Fin set: 4 fins, trapezoidal, root 150 mm, tip 50 mm, height 100 mm, sweep 57.7 mm (= 30 deg), thickness 3 mm, bottom of the body, rotation 45 deg so it matches the X layout
- Override CG to 720 mm from the nose tip (or add mass until CG is about 720 mm)
Record the CP, CG and static margin it reports.
- **Why:** a rocket is statically stable if the centre of pressure (CP) is behind the centre of gravity (CG). The margin is (x_CP - x_CG) / D, in calibers. Barrowman adds up normal-force contributions: the nose gives a slope of 2 per radian (slender-body theory) and the fins give most of the rest, then it takes the force-weighted average position.
- **Where in code:** `barrowman()` in `handcalc.py` (about 2.0 calibers at 30 deg); `REF_ORIGIN_MOMENT_X` in the config is your CG.
- **Predict first:** if you move the CG 0.1 m aft, does the margin go up or down, and by how many calibers? Test with `python3 02_handcalc/handcalc.py --cg 0.82`.
- Differences between OpenRocket and `handcalc.py` are normal; note them.

## 5. Build the coarse mesh (10 min)
```
python3 03_geometry/make_mesh.py --level coarse --no-mesh   # check the groups first
python3 03_geometry/make_mesh.py --level coarse
```
Expected: `surfaces: rocket=17 symmetry=2 farfield=3` and about 137,000 tetrahedra (counts from a test run on another machine; yours should match closely). Open the `.su2` or use `--gui` to see the model: half rocket, two fins, flat symmetry face.
- **Why:** the mesh decides how well the solver can resolve the nose, fins and shocks. Halving the element size gives about eight times as many cells in 3D, so refinement gets expensive quickly. The half-model uses the symmetry plane to halve the cost.
- **Where in code:** `LEVELS` (`h_wall`) and the size fields in `make_mesh.py`; marker names must match `MARKER_EULER`, `MARKER_SYM`, `MARKER_FAR` in the config.
- **Check prediction 3:** the three levels use h_wall = 12, 8 and 5 mm and give roughly 137k, 425k and 1.67M cells. Compare the ratios with (12/8)^3 = 3.4 and (8/5)^3 = 4.1.

## 6. First SU2 run (30 to 60 min)
```
cd 05_cases
cp ../04_mesh/rocket_coarse_sw30.su2 rocket.su2
sed -i '' 's/^ITER=.*/ITER= 300/' rocket_euler.cfg      # short sanity run first (macOS sed)
SU2_CFD rocket_euler.cfg                                   # serial, no MPI, to see the output
```
Check: no "Marker not found" error, residuals dropping, CD stays finite. Then restore `ITER= 3000` and run on several cores. Your SU2 build is not linked to MPI, so use OpenMP threads instead:
```
SU2_CFD -t 8 rocket_euler.cfg
```
While it runs, open a second Terminal window and run `top -o cpu`. If `SU2_CFD` shows roughly 600 to 800 % CPU, threading works. If it stays near 100 %, this build is single-core: tell me, and we will look at an MPI-enabled SU2 before the medium and fine meshes.
Note the time per iteration in the logbook (it sets your run budget).
- **Why, config block by block:**
  - `MARKER_EULER` is a slip wall: air cannot pass through the rocket but there is no friction, so no boundary layer and no skin-friction drag.
  - `MARKER_SYM` mirrors the flow across y = 0, which is why `REF_AREA` is halved.
  - `MARKER_FAR` is the freestream far away, set by `MACH_NUMBER`, `FREESTREAM_PRESSURE` and `FREESTREAM_TEMPERATURE`.
  - `CFL_NUMBER` is the pseudo-time step: bigger converges faster but can blow up.
  - `JST` adds a little artificial dissipation so shocks can be captured without wiggles.
- **Where in code:** all of these are in `rocket_euler.cfg`.
- **Predict first (prediction 1):** with no viscosity, there is no friction drag. Before you look at CD, decide whether it will be below or above a real rocket's. Then check the value in `history.csv`. (Euler has no skin-friction drag, but it still gives pressure drag on the nose, fins and base.)

## 7. Look at the result (20 min)
Open `flow.vtu` in ParaView, slice on y = 0, colour by Mach. For the surface, open `surface_flow.vtu` and colour by `Pressure_Coefficient`.
- **Why:** the pressure coefficient is Cp = (p - p_inf) / q_inf. At a stagnation point the flow stops and the pressure rises to p0. A smooth subsonic flow at M = 0.8 speeds up over the shoulder where the nose meets the body, so the local Mach number is highest there. If it exceeds 1 you have a small supersonic pocket, the start of transonic drag rise.
- **Where in code:** `OUTPUT_FILES` in the config writes these files; `p0/p` from `handcalc.py` gives the stagnation value.
- **Check prediction 2:** read the Cp at the nose tip and compare with about 1.17.
- **Look for:** the maximum Mach number on the body. Is it below or above 1?

## 8. If it converged: queue the mesh study (rest of the session or overnight)
```
python3 03_geometry/make_mesh.py --level medium
python3 03_geometry/make_mesh.py --level fine
cd 05_cases
nohup caffeinate -i python3 sweep.py --mesh ../04_mesh/rocket_medium_sw30.su2 --tag medium --mach 0.8 --aoa 0 --threads 8 > medium.log 2>&1 &
```
Then the same with `fine`. Fill `06_results/mesh_study.csv` (columns `level,cells,CD`) and run `postprocess.py --mesh-study mesh_study.csv`.
- **Why:** a converged solver only proves the equations were solved on that mesh, not that the mesh was good enough. If CD stops changing as the mesh is refined, the result is mesh-independent.
- **Where in code:** `mesh_study()` in `postprocess.py` computes the changes and a Richardson estimate.
- **Predict first:** will the change in CD from medium to fine be smaller than from coarse to medium? Roughly how much smaller?

## 9. Before you leave
- [ ] Logbook entry written (include your predictions and what actually happened)
- [ ] `git add -A && git commit -m "..." && git push`
- [ ] Copy `results*.csv` and any figures to cloud/USB
- [ ] Note what is still running and where

## If something goes wrong
| Symptom | Try |
|---|---|
| `Marker not found` / marker error | marker names in the config must match the mesh: rocket, symmetry, farfield |
| Residuals blow up or NaN | lower `CFL_NUMBER` (e.g. 1) and the CFL_ADAPT max (e.g. 20); check the mesh with `--gui` |
| Residuals stall around -3 to -4 | normal for transonic; judge by CD, CL, CMy flattening, and average the last few hundred iterations |
| CD oscillates at M = 1.05 | expected near M = 1; report the mean and the amplitude |
| `mpirun` not found | expected on this Mac: use `-t 8` (OpenMP threads) instead of `mpirun` |
| Gmsh volume or boolean error | send me the printed error and your `make_mesh.py` options |
| Python / pip permission error | use `--user` or a virtual environment (`python3 -m venv .venv`) |

## What was and was not tested
- Tested: `make_mesh.py` (builds, three marker groups, coarse/medium/fine meshes), `handcalc.py`, `postprocess.py` (on made-up data), `sweep.py` (dry run), `run_matrix.xlsx`.
- Not tested: SU2 itself and the `.cfg` options, because SU2 was not available when these were written. Expect to adjust option names if your SU2 version complains.
