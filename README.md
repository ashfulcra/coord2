# coord2

**Agent coordination as optional layers on top of [`fulcra-agent-teams`](https://github.com/fulcradynamics/agent-skills).**

coord2 is a ground-up rebuild of `fulcra-coord` + `fulcra-continuity` as a set of **optional packages**
that layer structured-coordination power onto Fulcra's official (alpha) `fulcra-agent-teams` skill —
rather than running as a parallel system with its own store and CLI.

Bare `fulcra-agent-teams` is a lightweight OKF-markdown convention over the Fulcra File Store
(per-agent inboxes, `progress.md` continuity, consent-gated automation). coord2 keeps that as the
**base tier** and adds, à la carte, the machinery that a convention structurally lacks: typed task
lifecycle, self-healing queryable views, roles + leases, a review handshake, a VCS bridge, structured
resumable continuity, and OS-level wake automation.

## Why
The incumbent [`fulcra-tools-coord`](https://github.com/ashfulcra/fulcra-tools) (v0.15.x) is a powerful
but heavyweight parallel system — a dedicated CLI + JSON store + reconcile engine that must be kept
version-synced across a fleet. coord2's thesis: make the **official skill the substrate** and coord the
opt-in **"pro tier."** Bare-teams agents interoperate by reading the same markdown; power agents opt into
the layers they want. OKF v0.1 explicitly permits the typed frontmatter and synthesized views this needs.

## Architecture (optional layers)
| Layer | Package | Adds |
|---|---|---|
| L0 | `fulcra-agent-teams` (external, base) | OKF-markdown team spaces, inboxes, continuity files |
| **L1** | **`coord-reconcile`** | scan the team namespace → heal `task/index.md`/`log.md` → emit `_coord/summaries.json` aggregate → query verbs (`status`/`board`/`needs-me`/`search`) |
| L2 | `coord-tasks` | typed status/priority/assignee lifecycle in frontmatter |
| L3 | `coord-directives` | priority + ack + re-notify on the inbox |
| L4 | `coord-roles` | roles + leases + SLA vacancy escalation |
| L5 | `coord-review` / `coord-forge` | review handshake + GitHub bridge |
| L6 | `coord-continuity` | structured resumable snapshots |
| L7 | `coord-automation` | heartbeat / listener / wake / digest installers |

L1 is the linchpin (queryability + self-healing). L4–L7 are additive/independent.

## Status
**Design + scaffold.** See [`docs/proposals/teams-convergence/`](docs/proposals/teams-convergence/) for the
full analysis, architecture, and the implementable L1 spec. No layer is implemented yet.

**Before coding L1**, one assumption must be verified empirically (see doc `02` §9): does `fulcra-api file`
give last-writer-wins semantics + a reliable `stat`/`mtime` in `list` output? The incremental reconcile
and single-writer index ownership depend on it.

## Layout
- `docs/proposals/teams-convergence/` — the design set (start at its `README.md`).
- `packages/coord-reconcile/` — L1 package (skeleton; implementation gated on the probe above).

## Conventions
Python, **stdlib-only** in the coordination packages (inherited from coord — the transport is a
CLI-subprocess-per-file call to `fulcra-api`, so no heavy deps). Best-effort / never-raise on the
reconcile path. TDD.

## License
MIT © 2026 Fulcra Dynamics
