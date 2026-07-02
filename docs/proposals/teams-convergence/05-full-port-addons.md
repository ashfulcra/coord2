# Full port — coord/continuity parity as optional add-ons

**Goal (operator directive):** before migrating off `fulcra-tools-coord` and testing, port ALL remaining
coord + continuity functionality to coord2, structured as **optional add-ons** wherever that doesn't make
the functionality useless. Base tier stays `fulcra-agent-teams`; each add-on is a `fulcra-agent-*` skill
(pure prose) + `coord-engine` subcommands (every stateful fold deterministic + tested).

## Coverage matrix (every coord verb → status → where it lands)

| coord verb / feature | status | lands in |
|---|---|---|
| status / board / search | ✅ covered | reconcile |
| needs-me | ✅ covered | reconcile |
| start / update / done | ✅ covered | tasks |
| block / pause / abandon | 🟡 via generic `--status` | **A1 tasks-completion** (dedicated verbs + `blocked_on`/`not_before` semantics) |
| assign | ❌ | **A1** (`task assign`) |
| restore (un-archive) | ❌ | **A4 retention** |
| tell / broadcast / remind / later | ❌ | **A2 directives** |
| inbox (+ per-agent ack, re-notify) | ❌ (bare teams inbox only) | **A2 directives** |
| respond (close a loop) | ❌ | **A2 directives** |
| handoff (work + checkpoint ref) | ❌ | **A2 directives** (+ A6 continuity ref) |
| connect / workstream / presence / agents | ❌ | **A3 presence** |
| roles set / claim / release | 🟡 prose-only | **A3 presence** (engine `roles claim/release`; registry stays prose) |
| role vacancy auto-escalation | 🟡 agent-triggered | **A5 health** (heartbeat-run `escalate` sweep) |
| retention/archival of terminal tasks | ❌ | **A4 retention** (move-not-delete, window, throttle) |
| search --archived | ❌ | **A4** |
| health / doctor | ❌ | **A5 health** (`doctor` preflight + per-host health shards + fold) |
| digest (operator digest) | ❌ | **A5** (`digest` from the aggregate; timeline write optional) |
| request-review / review-done | ✅ covered (as review request/verdict) | review |
| forge-mirror (GitHub → evidence) | ❌ | **A7 forge** |
| announce-version / self-update | ❌ (deliberately dropped) | — versioning = git tag + setup script; skills+engine ship together. NOT ported. |
| capabilities | 🟡 | `coord-engine --help` suffices. NOT ported separately. |
| annotations (timeline writer) | ❌ | **A5** (digest → timeline via fulcra-api, optional flag) |
| identity / human | 🟡 env-based | **A3** (`FULCRA_COORD_AGENT`-style env + `identity` helper) |
| install-heartbeat | ✅ covered | automation |
| install-listener / notify-inbox / wake chain | ❌ | **A8 automation-completion** (listener tick + consent-gated wake, PATH/auth-hardened) |
| install-claude-code/codex/openclaw hooks | 🟡 | **A8** (session hooks optional; minimal: SessionEnd snapshot) |
| continuity snapshot / resume | ✅ covered | continuity |
| checkpoint (role resume point) | ❌ | **A6 continuity-completion** |
| park (session-exit checkpoint of held roles) | ❌ | **A6** |
| briefing (session-start bundle) | ❌ | **A6** (`briefing` = identity + status + inbox + needs-me in one call) |

## Add-on architecture (all OPTIONAL, each degrades gracefully)

Ordering by dependency + value. Each ships as engine subcommands + skill updates (or a new skill), its own
PR, opus + Codex review, tests, live verification.

- **A1 `tasks-completion`** (engine only; updates fulcra-agent-tasks skill): `task block/pause/abandon/assign`
  dedicated verbs (block sets `blocked_on`, `--on-user` assigns human + `needs:human` tag; pause requires
  `--next`). No new storage.
- **A2 `fulcra-agent-directives`** (new skill): a directive IS a task with `assignee` (coord's model) +
  **ack shards** `task/<slug>/_acks/<agent>.md` (append-only, one per agent — safe on LWW). Engine:
  `tell/broadcast/remind/later` (sugar over task start w/ assignee, `*` wildcard, `not_before` for remind),
  `inbox <team> --agent X [--ack <slug>]` (fold: open tasks assigned to X or `*`, minus acked, priority-sorted),
  `respond <slug> --outcome` (append response + close). Re-notify = unacked P1s surface in inbox/digest.
- **A3 `fulcra-agent-presence`** (new skill): presence shards `presence/<agent>.md` (frontmatter:
  workstreams, summary, timestamp) written by `presence beat`; folds `presence` (roster + live/idle/stale)
  and `agents` (cross-agent digest from aggregate + presence). `roles claim/release` = engine-written lease
  shards (replaces prose lease writing; registry doc stays prose).
- **A4 `retention`** (engine + reconcile flag): terminal tasks older than window (default 30d) moved to
  `task/archive/<YYYY-MM>/` during reconcile (move-not-delete, verified before delete, deadline-gated,
  daily marker throttle). `task restore <slug>`, `search --archived`. Index gets "Recently Done" only;
  archive keeps history. OPTIONAL: off unless `--retention-days` set on reconcile / env knob.
- **A5 `fulcra-agent-health`** (new skill): `doctor` (preflight: uv/fulcra-api/auth/store reachability),
  per-run health shard `_coord/health/<host>.json` written by reconcile, `health` fold (which hosts
  reconciled recently — the fleet-health fold the L7 review suggested), `digest` (blocked-on-you /
  upcoming / per-agent / stale from aggregate + presence; `--annotate` writes to the Fulcra timeline),
  role vacancy `escalate` sweep (engine decides + writes marker + inbox msg — automatable via heartbeat).
- **A6 `continuity-completion`** (engine + skill update): `continuity checkpoint --role <r> [--ref]` (role
  resume points in the role doc), `continuity park` (snapshot every held role/task at session exit),
  `briefing <team> --agent X` (one-call: presence + board + inbox + needs-me + latest snapshot).
- **A7 `fulcra-agent-forge`** (new skill): `forge mirror <team> --repo <r>` — poll GitHub (gh CLI) for
  merge/review signals on open review slugs, append evidence shards `review/<slug>/_evidence/<id>.md`,
  auto-verdict on merge. OPTIONAL: requires gh; degrades to no-op without it.
- **A8 `automation-completion`** (extends fulcra-agent-automation): `install-listener.sh` — scheduled
  `coord-engine inbox --agent X` tick; on NEW items → OS notification + optional consent-gated wake command
  (headless agent), with the PATH/HOME pinning + install self-test discipline from install-heartbeat (the
  parent wake-401 lesson: verify auth at install, log loudly). SessionEnd-snapshot hook optional.

**Deliberately not ported:** announce-version/self-update (git tags + setup script supersede), the ~35-view
apparatus + event/directive parity samplers (coord2's single-listing reconcile is orphan-proof by
construction — the parity machinery existed to detect drift that this architecture can't accrue),
NO-CAS sub-log transport layer (the File Store's native versioning + ack/evidence shards subsume it).

## Sequencing
A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8. A2 is the critical path (directives/ack is the biggest functional
gap); A1 first because it's trivial and A2 builds on task semantics. Each add-on: TDD → PR → opus review +
Codex bus request → fix → merge → live-verify. Bus task per add-on; tight loop to catch reviews.
