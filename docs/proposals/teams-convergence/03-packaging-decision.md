# Packaging decision — how coord2's layers ship

**Question:** should coord2's layers be Python **packages**, pure-prose **skills**, or a **hybrid**?

## Options

### A — Packages (pip monorepo)
Each layer is an installable package (`coord-reconcile`, `coord-tasks`, …) with a CLI/library.
- **+** deterministic, testable, versioned, strong separation, reusable as libraries.
- **−** heavyweight distribution: pip install + **version-sync across a fleet** — the exact pain that has
  dominated the coord maintainer workstream (stale hosts, version skew, the summaries-orphan leak needing
  a deploy to fix, wake-auth drift). Not agent-native. Doesn't compose with the agent-skills ecosystem.
  Not upstreamable to `fulcradynamics/agent-skills`.

### B — Pure-prose skills
Each layer is a `SKILL.md` of instructions over `fulcra-api file` + OKF, like `fulcra-agent-teams` itself.
- **+** agent-native (invocable, discoverable), zero-install, composes with teams + the whole skills
  ecosystem, upstreamable, portable across runtimes (Claude Code, OpenClaw, Codex).
- **−** **prose conventions drift.** Asking an agent to hand-maintain `index.md`, eyeball lease
  timestamps for an SLA fold, or keep the aggregate consistent is *the exact failure coord exists to
  eliminate* (teams' `index.md` upkeep → coord's reconcile; the 1142-orphan leak came from a *union* bug
  even with code — prose would be worse). No determinism, no tests, no self-healing.

### C — Skills that bundle one shared, tested engine  ← RECOMMENDED
Each capability is a **skill** (agent-facing interface + genuinely-conventional prose), and the
consistency-critical logic lives in **one shared stdlib-only engine** the skills invoke.
- The **skill** is distribution + discovery + the conventional parts (*how* to write a task doc, *when*
  to claim a role, the inbox lifecycle) — capturing B's adoption/composition/upstream wins.
- The **engine** is the deterministic parts (reconcile/heal, the role HELD/VACANT/CONTESTED fold, SLA
  vacancy timing, OKF parse/render, the aggregate) — capturing A's determinism/testability/self-healing.
- **One engine, many thin skills** — not N duplicated tools. The engine ships *with* the skills (pulled
  together, versioned together), so there's no separate fleet pip-sync.

**Decision rule:** *prose for what an agent does reliably by hand; code for what must be deterministic
(state folds, healing, timing, parsing).*

## Why C over B for the stateful layers
The failure coord is built around is **drift of derived/aggregate state**. Any layer that computes a
*fold over multiple files* (reconcile's index, roles' lease-status, review's verdict tally, retention's
archival window) must be deterministic or it silently rots. Those folds are exactly what a tool does well
and prose does badly. Conversely, *single-file, single-writer* actions (write a task doc, drop an inbox
message, refresh your own lease) are reliable as prose — so those stay in the SKILL.md.

## Concrete shape
```
coord2/
  engine/            # one stdlib-only package: OKF parse/render, transport, reconcile,
                     # role-fold, task-lifecycle, ... exposed as `coord <verb>` subcommands. Tested.
  skills/
    fulcra-agent-reconcile/   SKILL.md + references + (invokes engine `reconcile`/`board`/…)
    fulcra-agent-roles/       SKILL.md + references + (invokes engine `roles status`/`roles escalate`)
    fulcra-agent-tasks/       SKILL.md + references + (invokes engine `task start/update/done`)
    fulcra-agent-review/      SKILL.md (mostly convention; engine tallies verdicts)
    fulcra-agent-continuity/  SKILL.md + schema (engine writes/reads structured snapshots)
    fulcra-agent-automation/  SKILL.md + install scripts (heartbeat/wake)
  docs/…
```
(Open question for review: one `engine/` package wrapped by all skills, vs. each skill bundling the
engine under its own `scripts/`. Shared-engine is DRY but couples the skills' release; per-skill bundling
is independently installable but duplicates. Leaning shared-engine with each skill pinning an engine
version.)

## What this changes vs. the current tree
L1 `coord-reconcile` (already built + tested + live-verified) becomes the seed of `engine/`, wrapped by
the `fulcra-agent-reconcile` skill. The first-draft `fulcra-agent-roles` SKILL.md must gain a bundled
`roles status`/`roles escalate` engine command for the fold + SLA (it is currently too prose-only).

## Recommendation
**Approach C.** Skills for interface + adoption + upstream; one shared tested engine for every stateful
fold. Build order: seed `engine/` from reconcile → `fulcra-agent-reconcile` skill → `fulcra-agent-roles`
(with the fold as an engine command) → tasks → review → continuity → automation, each PR reviewed on the
bus (Codex) + an independent pass.
