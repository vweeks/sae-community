# Plan: forecast error at station 102 on 2026-01-01

**Decision.** Compute the hourly forecast error at station 102 for 2026-01-01, as a check
that the scoring pipeline works before running it on the full month. This is not a verdict
on the model.

**Method.** `obs.csv` and `model.csv` are hourly, in degC, with times in UTC (each file's
header says so). Inner-join them on `time`. One observation (15:00) is blank, which the
header defines as missing; drop that hour rather than filling it. Take model minus
observation for the remaining 23 hours and report the mean error and the RMSE, with n = 23.

**Evidence.** The two files in this folder.
