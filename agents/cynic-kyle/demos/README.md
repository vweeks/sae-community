# Demonstrations

Three briefs, each with the files it cites. Install the agent (see the
[agent README](../README.md)), start your agent tool in one demo folder, and ask:

> Have cynic-kyle review the plan in brief.md.

Then compare its report with the notes below. The model writes a different report each
run, so judge whether it found the problem, not whether the wording matches.

## 1. A plan with a flaw

Joins hourly observations to a model forecast on the `time` column. The files have the same
timestamps and the same units, and the brief says so. But `obs.csv` is in local standard
time (UTC-7) and `model.csv` is in UTC, as each file's header says. The join pairs readings
seven hours apart, and nothing raises an error.

A good review returns "material problems found" and calls the alignment **wrong**, citing
the two headers. The cheapest check is reading them. The fix is to shift one file by seven
hours before joining, which leaves 17 overlapping hours, not 24.

## 2. A sound plan

The same task, done carefully. Both files are in UTC, the one missing observation is
dropped and counted (n = 23), and the brief limits its claim to a check of the pipeline.

A good review returns the clean verdict, "I tried to break this and couldn't find a
material problem". It lists what it tried (time zones, units, missing values, the size of
the claim), with at most a few notes, such as that one day says nothing about the model's
bias. Inventing a material problem here is the failure to watch for.

## 3. A result written up too broadly

A draft conclusion recommends a bias correction "across the network in all seasons". The
evidence is one station, in one month, and the correction was fitted to that same month,
so the forecasts were scored on the data they were corrected with.

A good review returns "material problems found". The network-wide, all-seasons claim is
**not shown**: there is one station and one month. The improvement is in-sample: scored on
the data the correction was fitted to. The cheapest check is fitting on one month and
scoring on another, or on another station.
