# Conventions

Five rules every `scidata-mcp` server and adapter follows. Each has a test in
[`conformance/`](conformance/), so a server that breaks one fails the suite rather than relying
on a reviewer to notice.

These rules exist because an agent will use whatever a server allows. A tool description
saying "read-only" doesn't stop anything; code that has no way to write does.

## 1. Read-only by construction

No tool creates, changes, or deletes anything. The adapter interface has no write
operation, so there is nothing to call.

*Test:* run every tool, then compare a hash of every file under the data root with the hash
from before.

## 2. Narrow questions, not shells

Each tool answers one specific question with typed, bounded inputs. No tool takes a
command, code, a query language, a URL, or a file path. Datasets are named by the ids
`scidata_list` returns, and a read is an index range on named dimensions.

*Test:* walk every tool's input schema; fail on inputs named like `command`, `code`, `url`,
`path`, or `query`, and on any string without a maximum length.

## 3. Provenance on every response

Every result says where it came from: the source (a dataset id, or the request URL for an
API), a SHA-256 of the file read, the adapter, the server name and version, and when the
source was read. The server stamps these. The agent never supplies them, so a value it
reports can be traced to the bytes it came from.

*Test:* every tool's output schema requires `provenance`, and every response has the fields
filled, with a hash that matches the file.

## 4. Annotations declared and accurate

Every tool sets all four annotations: `readOnlyHint` true, `destructiveHint` false,
`idempotentHint` true, and `openWorldHint` true only for an adapter that reaches outside the
machine. Clients use these to decide what to ask you before a call. They are hints, not
guarantees, which is why rule 1 is enforced in code and the annotation only reports it.

*Test:* every tool's annotations have these values, with `openWorldHint` matching the
adapter.

## 5. Confined

A file adapter serves one data root and nothing outside it. An id is looked up in the
listing of that root, never joined onto a path, and a symbolic link pointing out of the root
is not listed. An API adapter calls only the hosts on its allowlist. The HTTP transport binds
to this machine only.

*Test:* ids such as `../outside.nc`, absolute paths, and a symbolic link out of the root are
all refused, as is a resource URI that tries to climb out; a request with a foreign `Host`
header is refused; and the server won't start on a non-loopback address. The host
allowlist gets its test with the first API adapter.
