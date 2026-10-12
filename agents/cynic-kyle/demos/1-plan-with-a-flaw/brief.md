# Plan: forecast error at station 102 on 2026-01-01

**Decision.** Compute the hourly forecast error at station 102 for 2026-01-01 and report its
mean as the model's warm or cold bias for the day.

**Method.** `obs.csv` and `model.csv` both cover 2026-01-01 hourly, 24 rows each, with
columns `time,t2m` in degC. Inner-join them on `time`, take model minus observation for each
hour, and report the mean and the RMSE.

**Evidence.** The two files in this folder. Both have 24 rows, the same `time` values, and
the same units, so the join matches every hour and no conversion is needed.
