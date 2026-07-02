---
name: fulcra-agent-reconcile-cli
description: "Exact commands to run the coord-reconcile tool over a fulcra-agent-teams namespace."
---

# Fulcra Agent Reconcile — CLI reference

The tool is a stdlib-only Python package bundled in this skill
(`skills/fulcra-agent-reconcile/`). It shells out to `fulcra-api file` for all storage I/O, so
`fulcra-api` must be authenticated (`fulcra-api auth login`).

## Run

From the coord2 repo root:
```bash
uv run --project skills/fulcra-agent-reconcile coord-reconcile <command> ...
```
Or install it once and call `coord-reconcile` directly:
```bash
uv tool install --force skills/fulcra-agent-reconcile
coord-reconcile reconcile <team>
```

## Commands
```bash
# Scan team/<team>/task/*.md -> heal task/index.md + task/log.md -> write _coord/summaries.json
coord-reconcile reconcile <team>

# Read views (one aggregate download each; run reconcile first):
coord-reconcile status   <team> [--json]           # counts by status
coord-reconcile board    <team> [--json]           # open work grouped active/waiting/blocked/proposed
coord-reconcile needs-me <team> --agent <id> [--json]  # assigned-to / blocking <id>, gated on not_before
coord-reconcile search   <team> <query> [--json]   # substring over id/title/description/tags
```

## Environment
- `FULCRA_CLI_COMMAND` — override the storage CLI (default `fulcra-api`). E.g. `uv tool run fulcra-api`.
- `FULCRA_COORD_AGENT` — identity recorded as `reconcile_host` in the aggregate (default `coord-reconcile:<hostname>`).
- `COORD_LOG_LEVEL` — `debug|info|warn|error` (structured JSON logs to stderr; default `info`).

## Behavior notes
- **Incremental:** a task file is re-read only when its `fulcra-api file list` timestamp differs from the
  last aggregate. That timestamp is minute-granular, so two edits within one minute of the prior pass are
  re-scanned on the next run (conservative, never stale).
- **Degraded:** if `file list` fails, the pass aborts and writes nothing (prior index/log/aggregate stay).
- **Concurrency:** run reconcile from one scheduled host, or accept convergence — the output is
  deterministic from the listing, so concurrent passes converge (Fulcra File Store is last-writer-wins
  and versions every write).

## Tests
```bash
cd skills/fulcra-agent-reconcile && uv run --extra dev pytest -q
```
