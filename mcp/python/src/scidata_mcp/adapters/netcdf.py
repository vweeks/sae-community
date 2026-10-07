"""Local NetCDF files under one data root.

Confinement: a dataset id is only ever looked up in the listing of the data root, never
turned into a path directly, so no id can name a file outside it. Files reached through a
symbolic link that points outside the root are left out of the listing.

Values are read with xarray. Packed values (scale_factor, add_offset) are unpacked and fill
values become missing. Times are not decoded: they are returned as stored, with their
declared units and calendar, so nothing is interpreted on the agent's behalf.
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import xarray as xr

from scidata_mcp import __version__
from scidata_mcp.adapter import Adapter, AdapterError, BadSelection, NotFound, json_values
from scidata_mcp.models import Coordinate, DatasetSummary, Provenance, VariableInfo

SUFFIXES = (".nc", ".nc4", ".netcdf")
NAMED_ATTRS = ("units", "long_name", "standard_name", "calendar")


class NetCDFAdapter(Adapter):
    name = "netcdf"
    open_world = False

    def __init__(self, data_root: str | Path):
        root = Path(data_root).expanduser()
        if not root.is_dir():
            raise ValueError(f"data root {root} is not a directory")
        self.root = root.resolve()
        self._hashes: dict[tuple[Path, int, int], str] = {}

    # -- the three questions ------------------------------------------------------------

    def list_datasets(self) -> list[DatasetSummary]:
        summaries = []
        for dataset_id, path in self._index().items():
            try:
                with self._open(path) as ds:
                    title = ds.attrs.get("title")
                    summaries.append(
                        DatasetSummary(
                            id=dataset_id,
                            title=str(title) if title is not None else None,
                            variable_count=len(ds.variables),
                        )
                    )
            except AdapterError:
                # Listed, so the agent can see it exists; describing it reports the problem.
                summaries.append(DatasetSummary(id=dataset_id, title=None, variable_count=0))
        return summaries

    def describe(self, dataset):
        with self._open(self._path(dataset)) as ds:
            variables = [
                self._variable_info(name, var, name in ds.coords) for name, var in ds.variables.items()
            ]
            dims = {str(k): int(v) for k, v in ds.sizes.items()}
            return dims, variables, _attrs(ds.attrs)

    def shape(self, dataset, variable):
        with self._open(self._path(dataset)) as ds:
            var = _variable(ds, dataset, variable)
            return {str(d): int(n) for d, n in zip(var.dims, var.shape)}

    def read(self, dataset, variable, selection):
        with self._open(self._path(dataset)) as ds:
            var = _variable(ds, dataset, variable)
            if not np.issubdtype(var.dtype, np.number):
                raise BadSelection(
                    f"Variable {variable!r} holds {var.dtype} data, not numbers. "
                    "scidata_describe shows its attributes; this server reads numeric variables only."
                )
            slices = {dim: slice(start, stop) for dim, (start, stop) in selection.items()}
            values = np.asarray(var.isel(slices).values)
            if not np.issubdtype(values.dtype, np.floating):
                values = values.astype(float)  # so missing values can be NaN
            coords = {}
            for dim in var.dims:
                if dim in ds.variables and dim != variable:
                    coord = ds[dim].isel({dim: slices.get(dim, slice(None))})
                    coords[str(dim)] = Coordinate(
                        values=json_values(coord.values), units=coord.attrs.get("units")
                    )
            return [str(d) for d in var.dims], var.attrs.get("units"), values, coords

    def provenance(self, dataset):
        now = datetime.now(UTC).isoformat(timespec="seconds")
        server = f"scidata_mcp {__version__}"
        if dataset is None:
            return Provenance(source="data root", adapter=self.name, server=server, retrieved_at=now)
        path = self._path(dataset)
        return Provenance(
            source=dataset, sha256=self._sha256(path), adapter=self.name, server=server, retrieved_at=now
        )

    # -- confinement --------------------------------------------------------------------

    def _index(self) -> dict[str, Path]:
        found = {}
        for path in sorted(self.root.rglob("*")):
            if path.suffix.lower() not in SUFFIXES or not path.is_file():
                continue
            if not path.resolve().is_relative_to(self.root):
                continue
            found[path.relative_to(self.root).as_posix()] = path
        return found

    def _path(self, dataset: str) -> Path:
        path = self._index().get(dataset)
        if path is None:
            raise NotFound(f"No dataset {dataset!r}. Call scidata_list for the available ids.")
        return path

    # -- reading ------------------------------------------------------------------------

    def _open(self, path: Path) -> xr.Dataset:
        try:
            return xr.open_dataset(path, engine="netcdf4", decode_times=False, mask_and_scale=True)
        except (OSError, ValueError) as exc:
            name = path.relative_to(self.root).as_posix()
            raise AdapterError(
                f"Could not read {name!r} as NetCDF ({exc}). Try another dataset, "
                "and tell the user this file may be damaged."
            ) from exc

    def _variable_info(self, name, var, is_coordinate) -> VariableInfo:
        enc = var.encoding
        return VariableInfo(
            name=str(name),
            dims=[str(d) for d in var.dims],
            shape=[int(n) for n in var.shape],
            dtype=str(enc.get("dtype", var.dtype)),
            units=_str_or_none(var.attrs.get("units")),
            long_name=_str_or_none(var.attrs.get("long_name")),
            standard_name=_str_or_none(var.attrs.get("standard_name")),
            calendar=_str_or_none(var.attrs.get("calendar")),
            is_coordinate=is_coordinate,
            packed="scale_factor" in enc or "add_offset" in enc,
            scale_factor=_float_or_none(enc.get("scale_factor")),
            add_offset=_float_or_none(enc.get("add_offset")),
            fill_value=_float_or_none(enc.get("_FillValue", enc.get("missing_value"))),
            attributes=_attrs({k: v for k, v in var.attrs.items() if k not in NAMED_ATTRS}),
        )

    def _sha256(self, path: Path) -> str:
        stat = path.stat()
        key = (path, stat.st_mtime_ns, stat.st_size)
        if key not in self._hashes:
            digest = hashlib.sha256()
            with path.open("rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    digest.update(block)
            self._hashes[key] = digest.hexdigest()
        return self._hashes[key]


def _variable(ds: xr.Dataset, dataset: str, variable: str) -> xr.Variable:
    if variable not in ds.variables:
        raise NotFound(
            f"No variable {variable!r} in {dataset!r}. Call scidata_describe({dataset!r}) for its variables."
        )
    return ds.variables[variable]


def _attrs(attrs) -> dict[str, str]:
    return {str(k): _to_str(v) for k, v in attrs.items()}


def _to_str(value) -> str:
    if isinstance(value, np.ndarray):
        return str(value.tolist())
    return str(value)


def _float_or_none(value) -> float | None:
    if value is None:
        return None
    value = float(np.asarray(value).ravel()[0])
    return None if np.isnan(value) else value


def _str_or_none(value) -> str | None:
    return None if value is None else _to_str(value)
