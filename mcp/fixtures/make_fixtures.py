# /// script
# requires-python = ">=3.11"
# dependencies = ["netCDF4>=1.6", "numpy>=1.26"]
# ///
"""Write the small NetCDF datasets the conformance tests and evaluations read.

Values come from simple formulas, not random numbers, so every answer in the evaluation
file can be worked out by hand. Each file carries something an agent could get wrong by
assuming: Celsius beside kelvin, a noleap calendar, packed values, fill values, units pint
doesn't know, and a variable with no units at all.

    uv run make_fixtures.py [OUTPUT_DIR]   (default: data/ beside this script)
"""

import sys
import warnings
from pathlib import Path

import netCDF4
import numpy as np

# netCDF4 1.7 sets an array's shape internally on every multi-dimensional write, which
# NumPy 2.5 deprecates. The data written is unaffected.
warnings.filterwarnings("ignore", message="Setting the shape on a NumPy array", category=DeprecationWarning)


def station_obs(path: Path) -> None:
    with netCDF4.Dataset(path, "w") as ds:
        ds.title = "Hourly observations at three stations"
        ds.Conventions = "CF-1.10"
        ds.createDimension("time", 24)
        ds.createDimension("station", 3)

        time = ds.createVariable("time", "f8", ("time",))
        time.units = "hours since 2026-01-01 00:00:00"
        time.calendar = "standard"
        time[:] = np.arange(24)

        station = ds.createVariable("station", "i4", ("station",))
        station.long_name = "station number"
        station[:] = [101, 102, 103]

        lat = ds.createVariable("lat", "f4", ("station",))
        lat.units = "degrees_north"
        lat[:] = [40.0, 39.5, 41.25]

        t2m = ds.createVariable("t2m", "f4", ("time", "station"))
        t2m.units = "degC"
        t2m.long_name = "air temperature at 2 m"
        t2m.standard_name = "air_temperature"
        hours = np.arange(24)[:, None]
        t2m[:] = -2.0 + 0.5 * hours + np.array([0.0, 1.0, 2.0])[None, :]

        wind = ds.createVariable("wind_speed", "f4", ("time", "station"))
        wind.units = "m s-1"
        wind[:] = 3.0 + np.zeros((24, 3)) + np.array([0.0, 0.5, 1.0])[None, :]

        precip = ds.createVariable("precip", "f4", ("time", "station"), fill_value=-999.0)
        precip.units = "mm"
        precip.long_name = "precipitation in the preceding hour"
        p = np.zeros((24, 3), dtype="f4")
        p[6:9, 0] = [0.2, 1.4, 0.6]
        data = np.ma.masked_array(p, mask=np.zeros_like(p, dtype=bool))
        data.mask[[3, 4, 17], 1] = True
        precip[:] = data

        rh = ds.createVariable("rh", "f4", ("time", "station"))
        rh.long_name = "relative humidity"
        rh[:] = 80.0 - np.arange(24)[:, None] + np.zeros((1, 3))


def model_grid(path: Path) -> None:
    with netCDF4.Dataset(path, "w") as ds:
        ds.title = "Daily model output on a small grid"
        ds.createDimension("time", 60)
        ds.createDimension("lat", 4)
        ds.createDimension("lon", 6)

        time = ds.createVariable("time", "f8", ("time",))
        time.units = "days since 2000-01-01"
        time.calendar = "noleap"
        time[:] = 365 * 26 + np.arange(60)

        lat = ds.createVariable("lat", "f4", ("lat",))
        lat.units = "degrees_north"
        lat[:] = [30.0, 35.0, 40.0, 45.0]
        lon = ds.createVariable("lon", "f4", ("lon",))
        lon.units = "degrees_east"
        lon[:] = [250.0, 255.0, 260.0, 265.0, 270.0, 275.0]

        t, y, x = np.meshgrid(np.arange(60), np.arange(4), np.arange(6), indexing="ij")

        tas = ds.createVariable("tas", "f4", ("time", "lat", "lon"))
        tas.units = "K"
        tas.standard_name = "air_temperature"
        tas[:] = 290.0 - 2.0 * y + 0.5 * x + 0.1 * t

        # Stored as int16 and unpacked on read: value = stored * 1e-6 (kg m-2 s-1).
        pr = ds.createVariable("pr", "i2", ("time", "lat", "lon"))
        pr.units = "kg m-2 s-1"
        pr.standard_name = "precipitation_flux"
        pr.scale_factor = 1e-6
        pr.add_offset = 0.0
        pr[:] = (10 * x + y + t) * 1e-6


def ocean_profile(path: Path) -> None:
    with netCDF4.Dataset(path, "w") as ds:
        ds.title = "One ocean temperature and salinity profile"
        ds.createDimension("depth", 8)

        depth = ds.createVariable("depth", "f4", ("depth",))
        depth.units = "m"
        depth.positive = "down"
        depth[:] = [0, 10, 20, 50, 100, 200, 500, 1000]

        temp = ds.createVariable("temp", "f4", ("depth",))
        temp.units = "Celsius"
        temp[:] = [18.0, 17.5, 16.0, 13.0, 10.0, 7.5, 5.0, 4.0]

        salt = ds.createVariable("salinity", "f4", ("depth",))
        salt.units = "psu"
        salt[:] = [34.0, 34.1, 34.3, 34.6, 34.8, 34.9, 34.95, 35.0]


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "data"
    (out / "profiles").mkdir(parents=True, exist_ok=True)
    station_obs(out / "station_obs.nc")
    model_grid(out / "model_grid.nc")
    ocean_profile(out / "profiles" / "ocean_profile.nc")
    print(f"wrote fixtures under {out}")


if __name__ == "__main__":
    main()
