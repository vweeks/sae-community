"""The adapter interface: the part you write for your own data.

The server (server.py) owns the protocol, the limits, the error messages, and provenance.
An adapter only answers three narrow questions about one kind of source: what datasets are
there, what is in one of them, and what values are in a bounded selection. Everything an
adapter returns is read from the source; it never computes, converts, or fills in.
"""

from abc import ABC, abstractmethod

import numpy as np

from scidata_mcp.models import Coordinate, DatasetSummary, Provenance, VariableInfo


def json_values(array: np.ndarray) -> list:
    """Nested lists for JSON: NaN becomes null, and a float32 becomes its shortest decimal
    (0.2, not 0.20000000298023224), so the agent sees the value stored, not artifacts of
    widening it to a Python float."""
    array = np.asarray(array)
    if array.dtype == np.float32:
        array = array.astype(str).astype(float)
    if np.issubdtype(array.dtype, np.floating):
        return np.where(np.isnan(array), None, array).tolist()
    return array.tolist()


class AdapterError(Exception):
    """A failure the agent can act on. The message must say what to do next."""


class NotFound(AdapterError):
    """No dataset or variable with that name."""


class BadSelection(AdapterError):
    """A selection names an unknown dimension or falls outside the data."""


class Adapter(ABC):
    #: Short name, reported in provenance.
    name: str
    #: True if the adapter reaches outside the machine (an API); sets openWorldHint.
    open_world: bool
    #: Credit the source requires in anything built from it, or None.
    attribution: str | None = None

    @abstractmethod
    def list_datasets(self) -> list[DatasetSummary]:
        """Every dataset this adapter can serve, in a stable order."""

    @abstractmethod
    def describe(self, dataset: str) -> tuple[dict[str, int], list[VariableInfo], dict[str, str]]:
        """Dimensions, variables, and global attributes. Raise NotFound for an unknown id."""

    @abstractmethod
    def read(
        self, dataset: str, variable: str, selection: dict[str, tuple[int, int]]
    ) -> tuple[list[str], str | None, np.ndarray, dict[str, Coordinate]]:
        """Read one variable over index ranges [start, stop) per dimension.

        Return (dims, units, values as a numpy array with NaN for missing, coordinates).
        The server has already checked the selection's size against its limit.
        """

    @abstractmethod
    def shape(self, dataset: str, variable: str) -> dict[str, int]:
        """Dimension sizes of one variable, so the server can bound a read before it happens."""

    @abstractmethod
    def provenance(self, dataset: str | None) -> Provenance:
        """Where the data comes from. For None, describe the collection as a whole."""
