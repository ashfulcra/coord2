# coord-reconcile (L1)

The linchpin layer of coord2. Gives a `fulcra-agent-teams` namespace **queryable, self-healing views**
by scanning the OKF markdown and regenerating its indexes + a fast-path aggregate — no shadow store.

- **Reads:** `team/<team>/task/*.md` (OKF `type: Task` concept docs).
- **Owns (single-writer):** `task/index.md` (OKF §6), `task/log.md` (§7), `_coord/summaries.json` (aggregate).
- **Serves:** `status` / `board` / `needs-me` / `search` — one aggregate download each.
- **Property:** rebuilt from the live listing each pass, so the orphan-leak bug class cannot recur.

Full design: [`../../docs/proposals/teams-convergence/02-L1-coord-reconcile.md`](../../docs/proposals/teams-convergence/02-L1-coord-reconcile.md).

**Status:** skeleton. Implementation gated on verifying `fulcra-api file` last-writer-wins + `stat`/`mtime`
guarantees (design §9).

## Dev
```
uv run --extra dev pytest
```
