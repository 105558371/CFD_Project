## Here is how the work so far maps to theory:

| Theory | Where you touch it | Quick exercise |
|---|---|---|
| Mach number, M = V/a | `MACH_NUMBER` in `rocket_euler.cfg`, `freestream()` in `handcalc.py` | Change T in `handcalc.py` and watch V change at fixed M |
| Dynamic pressure q = ½ρV² | the `q*Aref N` column in the `handcalc.py` output | Multiply a CD of 0.3 by that column to get drag in newtons |
| Normal shock relations | the shock columns in `handcalc.py` | Check that M2 at M = 2 matches a textbook table |
| Force coefficients | `REF_AREA`, `REF_LENGTH` in the config | Double `REF_AREA` and predict what happens to CD |
| Half-model symmetry | the halved `REF_AREA`, the `symmetry` marker | Predict CD if you forgot to halve it |
| Static margin, CP vs CG | `barrowman()` in `handcalc.py`, `REF_ORIGIN_MOMENT_X` | Move `--cg` and watch the margin change |
| Mesh resolution and independence | `h_wall` in `make_mesh.py`, `postprocess.py --mesh-study` | Compare cell counts for the three levels |
| Convergence | residuals and `history.csv` | Watch CD flatten while residuals fall |
