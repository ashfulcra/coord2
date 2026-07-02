---
name: fulcra-agent-roles-cli
description: "Exact fulcra-api file commands for establishing roles, claiming/refreshing/releasing leases, and escalating vacancies."
---

# Fulcra Agent Roles — CLI reference

All operations are `fulcra-api file` calls against the team namespace (needs `fulcra-api auth login`).
Write markdown locally, then upload. Every upload is versioned by the Fulcra File Store.

## Establish a role
```bash
# roles/<name>.md — type: Role, with policy / sla_hours / maintainer in frontmatter
uv tool run fulcra-api file upload /tmp/reviewer.md "team/<team>/roles/reviewer.md"
# add it to the roles index
uv tool run fulcra-api file upload /tmp/roles-index.md "team/<team>/roles/index.md"
```

## Claim / refresh a lease
```bash
# leases/<your-agent>.md — type: Lease, timestamp = now (UTC). Re-run to REFRESH (new timestamp) each
# time you act in the role; this is the liveness signal.
uv tool run fulcra-api file upload /tmp/my-lease.md "team/<team>/roles/reviewer/leases/<your-agent>.md"
```

## Read role status (the fold) — deterministic, via coord-engine
Do NOT classify by eyeballing timestamps. The engine folds policy + lease freshness:
```bash
uv tool run coord-engine roles status "<team>" "reviewer" --json
# -> {status: HELD|VACANT|CONTESTED|UNKNOWN, policy, sla_hours, holders, fresh_holders, escalation_due}
```

## Release
```bash
uv tool run fulcra-api file delete "team/<team>/roles/reviewer/leases/<your-agent>.md"
```

## Escalate a vacancy (at most once per day)
```bash
# 1. first-writer-wins daily marker (dedupe)
uv tool run fulcra-api file upload /tmp/escalation.md \
  "team/<team>/roles/reviewer/escalations/$(date -u +%Y-%m-%d).md"
# 2. notify the maintainer via the teams inbox lifecycle
uv tool run fulcra-api file upload /tmp/notice.md \
  "team/<team>/member/<maintainer>/inbox/$(date -u +%Y%m%d-%H%M%S)_<you>_role-vacant-reviewer.md"
```

## Freshness window
Treat a lease as fresh if its `timestamp` is within the role's `sla_hours` (default 24h). A role with no
fresh lease is VACANT; an `exclusive` role with two or more fresh leases is CONTESTED.
