---
name: fulcra-agent-roles
description: "Add durable roles to a fulcra-agent-teams space: agents claim leases on named roles (reviewer, maintainer, on-call), liveness is tracked, and a role left vacant past its SLA escalates to its maintainer."
homepage: "https://github.com/ashfulcra/coord2"
license: "MIT"
user-invocable: true
metadata: { "openclaw": { "emoji": "🎓" } }
---

# Fulcra Agent Roles

Enhances the [`fulcra-agent-teams`](https://github.com/fulcradynamics/agent-skills) skill. A team's
`member/<agent>/role.md` says what a *member* does, but teams has no notion of a **durable role** that
outlives any one session — "who is the reviewer right now?", "is anyone on-call?", "this role has been
unattended too long." This skill adds that, as a pure OKF-markdown convention over the team namespace
(no new tools — just `fulcra-api file` and the OKF standard).

## Concepts
- **Role** — a named, durable function in the team (e.g. `reviewer`, `maintainer`, `on-call`). Defined
  once; sessions come and go.
- **Lease** — an agent's claim on a role, refreshed to prove liveness. A role is *held* while a fresh
  lease exists.
- **Policy** — `shared` (many holders allowed) or `exclusive` (one holder; a second fresh lease is a
  contention signal).
- **SLA / escalation** — if a role sits vacant longer than `sla_hours`, its `maintainer` is notified.

## Layout (under `team/<team>/roles/`)
- **`roles/<name>.md`** — the role registry doc. OKF `type: Role`. Created once when the role is
  established. Frontmatter carries the policy and SLA:
  ```yaml
  ---
  type: Role
  title: Reviewer
  description: Adversarial code/plan review for the team's PRs.
  policy: shared            # shared | exclusive
  sla_hours: 24             # vacancy longer than this escalates
  maintainer: ash           # who gets the escalation (an agent or member name)
  ---
  # Duties
  - Pick up review requests from the team inbox…
  ```
- **`roles/<name>/leases/<agent-name>.md`** — one lease per holder. OKF `type: Lease`. The
  `timestamp` is the liveness signal — **refresh it** (re-upload) each time you act in the role:
  ```yaml
  ---
  type: Lease
  title: reviewer lease — treecle
  agent: treecle
  timestamp: 2026-07-01T18:00:00Z
  ---
  Holding the reviewer role. Next: drain the review inbox.
  ```
- **`roles/<name>/escalations/<YYYY-MM-DD>.md`** — a first-writer-wins daily marker so a vacant role
  escalates at most once per day (avoids spamming the maintainer).

## Lifecycle

### Establish a role (once)
Write `roles/<name>.md` with `type: Role` + policy/SLA/maintainer, and list it in the team `roles/index.md`.

### Claim / hold
Upload a lease `roles/<name>/leases/<your-agent-name>.md` with a current `timestamp`. **Refresh it**
(re-upload with a new `timestamp`) whenever you do work in the role — this is what keeps the role "held".
The Fulcra File Store versions every write, so the lease's history is an audit trail of your tenure.

### Release
Delete your lease file `roles/<name>/leases/<your-agent-name>.md`. (Delete is not undoable via the CLI,
which is correct here — releasing is intentional.)

### Determine role status (the fold)
List `roles/<name>/leases/` and read each lease's `timestamp`:
- **HELD** — at least one lease refreshed within the freshness window (default: 24h, or `sla_hours`).
- **VACANT** — no fresh lease.
- **CONTESTED** — policy is `exclusive` and two or more leases are fresh. Resolve by having all but one
  holder release.

### Escalate a vacancy
When you observe a role is **VACANT** longer than its `sla_hours` and today's
`roles/<name>/escalations/<date>.md` marker does not yet exist:
1. Write the marker (first-writer-wins — if the upload races, that's fine; the marker just dedupes).
2. Drop a message into the maintainer's inbox
   (`team/<team>/member/<maintainer>/inbox/<YYYYMMDD-HHMMSS>_<you>_role-vacant-<name>.md`) per the
   `fulcra-agent-teams` inbox lifecycle, stating which role is vacant and for how long.

## When to use
- Establishing "someone owns X" in a team without pinning it to one session.
- Routing work by role ("the reviewer") instead of by name.
- Making sure a critical function (on-call, maintainer) is never silently unattended.

## Efficiency (per the teams OKF directive)
List roles in `roles/index.md`, but do **not** index every lease or escalation marker — describe the
`leases/` and `escalations/` directories as a whole. Keep the team `log.md` for role *creation* and
*handoff* milestones, not every lease refresh.

See [`references/roles-cli.md`](references/roles-cli.md) for exact `fulcra-api file` commands.
