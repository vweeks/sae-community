# Units spellings

`unit_check.py` parses units with pint and accepts the shorthand common in scientific data.

## Accepted

- **pint syntax:** `m/s`, `kg/m**2/s`, `W/m^2`, `degC`, `°C`, `hPa`, `%`, `1`.
- **udunits shorthand:** names separated by spaces or `.`, each with an optional integer
  exponent: `m s-1`, `kg m-2 s-1`, `W m-2`, `m.s-1`, `m2 s-2`.
- **Added names:** `degrees_north`, `degrees_east` (and the CF variants such as
  `degree_N`), and `Celsius`.

Two spellings count as the same unit if pint resolves them to the same unit, or if one
converts to the other with a factor of exactly 1 and neither has an offset (`hPa` and
`mbar` match; `degC` and `K` don't).

## Known limits

- **Angles and ratios are both dimensionless in pint.** `degree` against `%` comes back as
  `wrong-unit`, not `wrong-dimension`. Treat any dimensionless mismatch as a question to
  settle, not a conversion to write.
- **Scale factors inside the units string** (`10^3 m`, `1e-3 kg`) are reported as
  `unparseable`. Ask what the producer meant.
- **Units pint doesn't define** (`psu`, `dB` with a reference level, local or project-specific
  names) are reported as `unparseable`. If the project defines them, check them by hand and
  say so in your report.
