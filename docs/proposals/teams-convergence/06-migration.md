# Migration — moving off `fulcra-tools-coord` onto coord2

**Goal:** migrate real coordination from the incumbent (`/coordination/` JSON bus, fulcra-coord v0.15.16,
launchd fleet) to coord2 (`team/<t>/` markdown + coord-engine), and test on a real team.

## Constraints that shape the choice
- **The fleet is machine-gated.** ArcBot / Mac / Workbook / codex hosts run incumbent listeners,
  heartbeats, and the review workbook — they can only be migrated when someone touches those machines.
  Any plan requiring simultaneous fleet cutover is dead on arrival.
- **Same physical store.** Both systems live on the one Fulcra File Store (`/coordination/` vs `team/`),
  so "migration" is a data mapping + habit change, not a platform move.
- **Doc 01's C4 rule:** no long-lived shadow store / dual-truth. Any bridge must be short-lived or absent.
- History: the incumbent holds ~350 task records (~140 open), full event/audit history, review loops.

## Approaches compared

### A — Hard cutover
Freeze the incumbent (broadcast), export open tasks → coord2 team, retire incumbent automation, point
everyone at coord2.
- **+** one truth immediately; no bridge code; cleanest end state.
- **−** requires the whole fleet at once (machine-gated → impossible today); breaks the live Codex review
  workbook flow mid-flight; no rollback once incumbent automation is retired; big-bang risk on a
  system that coordinates the very agents doing the migration.

### B — Gradual bridge (dual-run + mirror)
coord2 primary for new work; a bridge job mirrors incumbent directives/inbox into the coord2 team (and/or
back) while hosts migrate one by one.
- **+** nothing goes dark; per-host migration.
- **−** exactly the "two systems bridged" failure doc 01 forbids: dual truth, drift, ack/status divergence
  between mirrored copies, and the bridge is throwaway code needing its own reviews. The incumbent's own
  history (summaries-orphan leak) shows what mirrored derived state does over time.

### C — Phased adoption with a one-shot exporter (RECOMMENDED)
No mirror. Three phases, each independently safe:
1. **Adopt (test on a real team):** create the real team space (`team/fulcra/`), migrate **open** tasks
   once via a deterministic exporter (`coord-engine migrate` — incumbent JSON → coord2 task docs,
   idempotent, `--dry-run` first), install coord2 heartbeat+listener on THIS host, and run real work on
   it (this epic's own follow-ups live there). The incumbent keeps running untouched for the fleet.
2. **Per-host adoption:** as each fleet machine is touched (operator-gated), run `coord2-setup.sh`,
   `install-heartbeat`/`install-listener` for the team, and retire that host's incumbent launchd jobs.
   New work goes to coord2; an agent still on the incumbent simply isn't reachable by coord2 directives
   yet (visible in `presence`/`agents` — no silent loss).
3. **Retire:** when `coord-engine health` shows every active host reconciling coord2 and the incumbent
   board is empty of open work, freeze the incumbent (final broadcast + read-only), keep `/coordination/`
   as cold history (no data deleted), remove remaining launchd jobs.
- **+** no bridge code, no dual-truth window per task (a task lives in exactly one system: unmigrated =
  incumbent, migrated = coord2; the exporter marks migrated tasks on the incumbent side), rollback at
  every phase, fleet migrates at its own pace, real-world test is phase 1 itself.
- **−** during phase 2 the OPERATOR watches two digests (bounded, explicit); incumbent history is not
  ported (deliberate — it stays queryable read-only forever; coord2 starts with open work only).

## The exporter (`coord-engine migrate`) — deterministic mapping
- Source: `/coordination/tasks/*.json` via the same transport. Filter: non-terminal only (default).
- Field map: `title→title`, `status→status` (identical vocab), `priority→priority`, `workstream→tags
  workstream:<ws>` , `kind→tags kind:<k>`, `owner_agent→owner`, `assignee→assignee` (incl `*`/@backlog),
  `current_summary→description`, `next_action→next_action`, `blocked_on→blocked_on`,
  `not_before/due→same`, `updated_at→timestamp`, `id→body provenance line` (slug from title; original id
  preserved in frontmatter `migrated_from`).
- **Idempotent:** skip if a doc with the same `migrated_from` already exists in the team (or same slug).
- **One-way + marked:** after a successful verified write, append a `migrated` event/tag on the incumbent
  task (`tags += migrated:coord2`) so incumbent boards/digests can filter them out — the task now lives in
  exactly one active system. `--dry-run` prints the plan without writing. `--no-mark` for rehearsal.
- Never deletes anything on the incumbent.

## Test plan (phase 1 acceptance)
On `team/fulcra` with real migrated tasks: reconcile heals index/aggregate at real scale (~140 docs —
first full reconcile ~2-3 min at ~1s/op, then incremental); board/needs-me/digest match the incumbent's
view for the migrated set (spot-check N=10); directives round-trip (tell→inbox→ack→respond); briefing +
park/checkpoint; health fresh; heartbeat + listener installed and self-tested on this host. Rollback
rehearsal: `--dry-run` + `--no-mark` first on a scratch team.
