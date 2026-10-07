# scidata-mcp (Python)

The Python implementation of the `scidata-mcp` server template. What the server is for, how
to connect it to your agent tool, and how to write an adapter for your own data are in
[the main README](../README.md).

## Run it

With [uv](https://docs.astral.sh/uv/), from this directory:

```
uv run scidata-mcp --data-root ../fixtures/data            # stdio
uv run scidata-mcp --data-root ../fixtures/data --http     # http://127.0.0.1:8000/mcp
```

Without uv, create a virtual environment, `pip install .`, and run `scidata-mcp` from it.

## Layout

| File | What it is |
|---|---|
| `src/scidata_mcp/server.py` | The protocol side: the tools, the resource, the prompt, limits, and transports. Shared by every adapter. |
| `src/scidata_mcp/adapter.py` | The interface an adapter implements. |
| `src/scidata_mcp/adapters/netcdf.py` | The local NetCDF adapter. |
| `src/scidata_mcp/models.py` | Result types, published as each tool's output schema. |
