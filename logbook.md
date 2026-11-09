# Logbook

## Machine info
- **Mac:** Apple Silicon (arm64)
- **Cores (hw.ncpu):** 10
- **RAM (hw.memsize):** 25769803776 bytes = 24 GB
- **Free disk:** 258 GB of 460 GB
- **SU2**: 8.5.0 "Harrier"
- **SU2 parallel:** not linked to MPI (otool shows no libmpi); has -t/--threads (OpenMP) option
- **mpirun:** 5.0.11
- **gmsh:** 4.15.2
- **Python:** 3.9.6, **Git:** 2.39.5 (Apple Git-154)
- **ParaView:** 6.2.0 (brew cask); **OpenRocket:** 24.12 (brew cask)

## Entries

### Session 0: 2026-11-09 (Window, 2h)
- **Goal:** understand project workflow, setup workspace
- **Did:** setup Github repo, make a plan
- **Case/mesh/config:**
- **Files:** README, folder structure
- **Results:**
- **Problems:**
- **Running:**
- **Next:** first case (coarse Euler)

### Session 1: 2026-11-10 (iMac, 3h)
- **Goal:** first converged coarse Euler run, M=0.8, AoA=0
- **Did:** cloned repo, checked tools, ran SU2 tutorial, built coarse mesh
- **Files:** rocket_coarse_sw30.su2, rocket_euler.cfg, commit a1b2c3d
- **Results:** 137k cells, 0.4 s/iter on 4 cores, 3000 iter, residual -6.1, CD=0.xxx
- **Problems:** "Marker not found" -> mesh marker names did not match the config; fixed
- **Running:**
- **Next:** medium and fine meshes, mesh study
