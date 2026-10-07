"""Result types for every tool and resource.

The server returns these as structured content, and the MCP SDK publishes each one's JSON
schema as the tool's output schema, so a client knows the shape before it calls.
"""

from typing import Any

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    """Where a response came from. Stamped by the server, never supplied by the agent."""

    source: str = Field(description="The dataset's location: a path under the data root, or a request URL.")
    sha256: str | None = Field(default=None, description="Hash of the file read, when the source is a file.")
    adapter: str = Field(description="The adapter that read the source.")
    server: str = Field(description="Server name and version.")
    retrieved_at: str = Field(description="When the server read the source, in UTC (ISO 8601).")
    attribution: str | None = Field(default=None, description="Credit the source requires, if any.")


class DatasetSummary(BaseModel):
    id: str = Field(description="Pass this to scidata_describe and scidata_read.")
    title: str | None = Field(default=None, description="The dataset's own title attribute, if it has one.")
    variable_count: int


class ListResult(BaseModel):
    datasets: list[DatasetSummary]
    total: int
    offset: int
    has_more: bool
    next_offset: int | None = Field(default=None, description="Pass as offset to get the next page.")
    provenance: Provenance


class VariableInfo(BaseModel):
    name: str
    dims: list[str]
    shape: list[int]
    dtype: str
    units: str | None = Field(description="The units attribute exactly as declared; null if there is none.")
    long_name: str | None = None
    standard_name: str | None = None
    calendar: str | None = Field(default=None, description="Declared calendar, for time variables.")
    is_coordinate: bool
    packed: bool = Field(
        description="True if stored values are scaled (scale_factor or add_offset). Values returned "
        "are unpacked."
    )
    scale_factor: float | None = Field(default=None, description="Declared scale_factor, if packed.")
    add_offset: float | None = Field(default=None, description="Declared add_offset, if packed.")
    fill_value: float | None = Field(
        default=None, description="Declared _FillValue or missing_value; returned values show these as null."
    )
    attributes: dict[str, str] = Field(description="All other attributes, as strings.")


class DescribeResult(BaseModel):
    dataset: str
    dimensions: dict[str, int]
    variables: list[VariableInfo]
    global_attributes: dict[str, str]
    provenance: Provenance


class Coordinate(BaseModel):
    values: list[Any]
    units: str | None


class ReadResult(BaseModel):
    dataset: str
    variable: str
    units: str | None = Field(description="The units attribute exactly as declared; null if there is none.")
    dims: list[str]
    shape: list[int] = Field(description="Shape of the selection returned.")
    selection: dict[str, list[int]] = Field(
        description="Index range [start, stop) read along each dimension."
    )
    values: Any = Field(description="Nested lists in dimension order. Missing values are null.")
    missing_count: int
    coordinates: dict[str, Coordinate] = Field(
        description="Coordinate values for the selection, as stored, with their declared units."
    )
    provenance: Provenance
