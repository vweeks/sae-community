# Time encodings

CF-style time variables store numbers counted from a reference date, with units such as
`hours since 1970-01-01 00:00:00`. `unit_check.py` treats any units string containing
`since` as a time encoding.

## What is checked

- **Form:** `<unit> since <date>`, where the date looks like `1970-01-01`, optionally
  followed by a time (`00:00`, `00:00:00`, `00:00:00.0`, with a space or `T`) and a zone
  (`Z`, `UTC`, `GMT`, `+05:30`, `-06`). A missing zone is read as UTC, as CF specifies.
- **Fixed-length unit:** days, hours, minutes, seconds, milliseconds, microseconds.
  `months` and `years` are reported as `time-malformed`, because their length depends on
  the calendar and CF advises against them.
- **Field ranges:** month 1–12, day 1–31, hour 0–23, minute 0–59, second 0–60.
- **Against an expected encoding** (`require`, or `scan --expect`): the unit, the reference
  date, and the zone must all match. A different reference date is `wrong-unit`.
- **Calendar:** `scan` reports a variable's `calendar` attribute when there is one
  (`noleap`, `360_day`, and so on) but doesn't judge it.

## What isn't checked

Whether the reference date is the one the data's producer actually used, and whether the
code's date handling respects a non-standard calendar. A well-formed encoding with the
wrong epoch passes. If results depend on absolute times, compare one decoded timestamp
against a source you trust.
