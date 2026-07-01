# L1 `coord-reconcile` — implementable design

The linchpin package of the teams-as-substrate architecture: give a `fulcra-agent-teams` space
**queryable, self-healing views** by scanning the OKF markdown and (re)generating its indexes + a
fast-path aggregate — without a shadow store. Grounded in OKF v0.1 (`type` required; producers MAY add
keys; consumers MUST preserve/not-reject unknown keys; `index.md`/`log.md` formats per §6/§7; §3 blesses
"synthesize an index by scanning frontmatter").

## 0. Goal & non-goals
- **Goal:** one command (`coord-reconcile <team>`) that scans a team namespace, heals `task/index.md` +
  `task/log.md`, and writes a `_coord/summaries.json` aggregate that the query verbs read in one download.
- **Non-goals:** no typed lifecycle enforcement (that's L2), no writing concept docs (agents/L2 do that),
  no roles/review (L4/L5). L1 only *reads* concept docs and *owns* the derived index/log/aggregate.

## 1. The OKF Task concept contract (what L1 reads)
A task is an OKF concept doc `team/<team>/task/<name>.md`:
```yaml
---
type: Task                         # OKF required
title: Fix summaries orphan leak   # OKF recommended (display)
description: prune stale orphans on the authoritative merge   # OKF recommended (index/search snippet)
timestamp: 2026-06-26T14:14:54Z    # OKF recommended (last meaningful change)
tags: [workstream:fulcra-coord, kind:bug]                     # OKF recommended
# --- coord extensions (OKF-legal producer keys) ---
id: TASK-20260626-fix-summaries-2ee6e720
status: done                       # proposed|active|waiting|blocked|done|abandoned
priority: P1                       # P0|P1|P2|P3
owner: claude-code:Ashs-MBP-Work:fulcra-tools
assignee: null
blocked_on: null
due: null
not_before: null
next_action: null
---
<body: human prose + appended state-change notes>
```
All coord fields are OKF-legal (extensions). `description`/`title`/`timestamp`/`tags` reuse OKF-recommended
keys so bare-teams tooling renders them correctly.

## 2. Parse rules (defensive, never-raise)
For each `task/<name>.md`:
1. Split frontmatter (`---`…`---`) and body. **No frontmatter or unparseable YAML → do not drop:** keep
   the file's *prior* aggregate row (if any), emit a warning to `_coord/reconcile.log`, continue. (Never
   lose a task to a malformed edit — a hand-edit is a teams feature.)
2. `type` missing or ≠ `Task` → treat as non-task, skip (not an error).
3. Missing coord extensions → **backfill defaults** (`status: proposed`, `priority: P2`,
   `owner: <derived from path/frontmatter>`, `assignee: null`) so bare-teams-authored tasks (which lack
   them) are first-class. This is C6 (mixed-fleet) tolerance.
4. Row = `{id (or filename slug if absent), name, path, title, description, status, priority, owner,
   assignee, tags, timestamp, blocked_on, due, not_before}`.

## 3. Heal algorithm (one pass)
```
rows        = []
warnings    = []
prior       = load(_coord/summaries.json)            # {} on miss/corrupt → full rebuild
listing     = fulcra-api file list team/<t>/task/    # 1 remote op
for f in listing where f endswith .md and f != index.md and f != log.md:
    if f.mtime <= prior.rows[f].mtime:  rows += prior.rows[f]        # INCREMENTAL: skip unchanged
    else:                               rows += parse(download(f))    # only changed files re-downloaded
# --- derived artifacts, all ENGINE-OWNED (single-writer LWW) ---
write task/index.md      = render_index(rows)        # OKF §6, grouped by status
append task/log.md       = diff(prior, rows)         # OKF §7, date-grouped transitions since last pass
write _coord/summaries.json = {schema, generated_at, rows, warnings}
```
**Orphan-proof by construction:** `index.md` + the aggregate are rebuilt from the *live listing* each
pass, never unioned with stale state — so the coord summaries-orphan bug class (1142 stale rows) cannot
recur here. A deleted `task/<name>.md` simply vanishes from the next index. (Terminal-task archival, if
wanted, is an explicit move to `task/archive/`, mirroring coord retention — optional add-on.)

### 3.1 `render_index(rows)` → `task/index.md` (OKF §6, no frontmatter)
```markdown
# Active
* [Fix summaries orphan leak](fix-summaries.md) - prune stale orphans on the authoritative merge

# Waiting
...
# Blocked
...
# Proposed
...
# Recently Done (last 7d)
...
```
Sections in fixed order; within a section, sort by priority then timestamp. Bullet =
`* [<title>](<name>.md) - <description>` (OKF: entries SHOULD carry the concept's `description`).

### 3.2 `log.md` append (OKF §7)
Diff prior vs new rows; for each status transition or new/removed task, append under today's
`## YYYY-MM-DD` heading (newest first): `* **Update**: [<title>](<name>.md) active → done.` /
`* **Creation**: …` / `* **Deprecation**: … abandoned.`

## 4. Aggregate sidecar — `team/<team>/_coord/summaries.json`
Non-OKF operational file in a clearly-marked `_coord/` subtree (precedent: OKF `references/` mirrors +
teams' non-indexed `inbox/`/`archive/`). `_coord/` is listed once in the root `index.md` with a
high-level description; its contents are not individually indexed.
```json
{ "schema": "coord.teams.summaries.v1",
  "team": "<team>",
  "generated_at": "2026-06-26T18:00:00Z",
  "reconcile_host": "claude-code:Ashs-MBP-Work:fulcra-tools",
  "rows": [ { "id": "...", "name": "fix-summaries", "path": "task/fix-summaries.md",
              "title": "...", "description": "...", "status": "done", "priority": "P1",
              "owner": "...", "assignee": null, "tags": [...], "timestamp": "...",
              "mtime": "...", "blocked_on": null, "due": null, "not_before": null } ],
  "warnings": [ "task/foo.md: unparseable frontmatter, kept prior row" ] }
```

## 5. Query verbs (read the aggregate — one download each)
- `coord status <team>` — counts by status/priority/workstream.
- `coord board <team>` — active / waiting / blocked / proposed groupings.
- `coord needs-me <team> --agent <a>` — rows where `assignee == a` or `blocked_on` names `a`, gated on
  `not_before`.
- `coord search <team> <q>` — substring over title/description/tags (from the aggregate; no per-file reads).
All read `_coord/summaries.json` only. If absent/stale (older than a TTL), run §3 first.

## 6. Concurrency & ownership (resolves C2/C4)
- **Concept docs** `task/*.md` are multi-writer but each is a *distinct file* → no clobber; agents (or L2)
  create/edit freely. L1 never writes them.
- **Derived artifacts** (`task/index.md`, `task/log.md`, `_coord/summaries.json`) are **engine-owned,
  single-writer LWW**. Governance rule (C2): once L1 is installed, humans/agents stop hand-editing
  `task/index.md`; they edit task *content*, reconcile owns the index. Run reconcile from one scheduled
  host (or accept LWW — output is deterministic from the listing, so concurrent reconciles converge).
- **No shadow store** (C4): the aggregate is a *cache of the concept docs*, never authoritative. Deleting
  `_coord/` and re-running reproduces it exactly.

## 7. Performance (against the ~1s/op, ~15–18-concurrent Fulcra transport)
- **Reads: O(1)** — one aggregate download, not N. (The whole reason the sidecar exists — C3.)
- **Reconcile: O(changed)** — 1 list + only re-download task files whose `mtime` advanced past the
  aggregate (§3 incremental). First run is O(N); steady state is O(delta).
- Deadline-gated + bounded concurrency (reuse coord's `_PhaseTimer` + worker-pool discipline). If a pass
  can't finish, it writes what it has and defers the tail (coord's proven pattern).

## 8. Degraded handling
- Bad frontmatter → keep prior row + warn (never drop). Missing/corrupt aggregate → full rebuild.
- Listing fails (transport) → abort the pass, leave prior derived artifacts intact (never write a
  truncated index — mirrors coord's degraded-load early-return).

## 9. Open questions to close before coding
- **`fulcra-api file` guarantees:** atomic-ish upload + reliable `stat`-after-write + a usable `mtime`
  (or version id) in `file list` output — the §3 incremental + §6 LWW assume last-writer-wins with no
  partial reads. Verify.
- **Reconcile trigger:** L7 launchd heartbeat vs a designated host; how to prevent two hosts both owning
  the index (or confirm convergence is enough).
- **Archival policy:** do we move terminal tasks to `task/archive/` on a window (coord retention), or
  leave them (index just grows a "Recently Done" tail)? Recommend optional archival add-on.
- Exact `_coord/` naming + whether to hide it from bare-teams `index.md` entirely.
