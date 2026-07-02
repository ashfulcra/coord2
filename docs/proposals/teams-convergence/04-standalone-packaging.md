# Standalone packaging — how coord2 installs on its own (pre-upstream)

**Goal (this phase):** make coord2 usable **standalone** — an agent/user installs it and gets the
`coord-engine` tool + the 6 `fulcra-agent-*` skills working over a `fulcra-agent-teams` space — **without
publishing anything externally**. Sequence set by the operator: *standalone now → migrate off the
incumbent `fulcra-tools-coord` → contribute upstream to `fulcradynamics/agent-skills` when happy.* So
external publishing (PyPI / plugin registry) is deliberately **deferred to the upstream phase**.

## What "standalone" needs
1. **Engine installable without a local checkout.** ✅ Verified: `uv tool install
   "git+https://github.com/ashfulcra/coord2.git#subdirectory=engine"` installs `coord-engine` 0.4.0 from
   the public repo (no PyPI). All subcommands present.
2. **Skills discoverable by the agent.** The 6 skills live in `skills/`; an agent (Claude Code / OpenClaw)
   must find them — either copied into its skills dir or added as a plugin.
3. **A one-command setup** that does both (with consent), + a quickstart.
4. **A pinned version** so installs are reproducible (`uv tool install git+…@<tag>`).

## Two approaches

### A — Git-installable + a setup script (NO external publishing)  ← recommended for this phase
- Engine: `uv tool install "git+…/coord2#subdirectory=engine"` (optionally `@<tag>`).
- Skills: a top-level `scripts/coord2-setup.sh` that installs the engine and **links the 6 skills into the
  agent's skills location** (detect `~/.claude/skills/` and/or OpenClaw's skills dir; symlink or copy;
  consent-gated), then runs a self-test (`coord-engine --help`).
- Quickstart in the README; tag `v0.4.0`.
- **+** nothing published (reversible, private-friendly, no name-squat on PyPI before upstreaming); matches
  the sequence; a symlink install means `git pull` updates skills in place.
- **−** requires `uv` + git; skills-dir wiring is agent-specific; a symlink couples to the checkout.

### B — Publish now (PyPI `coord-engine` + a Claude Code plugin)
- Publish the engine to PyPI (`uv tool install coord-engine`) and register the skills as a plugin.
- **+** cleanest end-user install; versioned artifacts.
- **−** **premature**: publishing is hard to reverse; the eventual home is `agent-skills` (upstream), so a
  standalone PyPI `coord-engine` may duplicate/þconflict with whatever the upstream contribution becomes;
  and you'd be publishing before you're "happy." Violates the stated sequence.

## Recommendation
**A.** Git-installable engine + a consent-gated setup script that wires the skills into the agent, pinned
to a `v0.4.0` tag, with a README quickstart. Publishing (B) is the *upstream phase's* job, not now.

## Open questions for review (Codex + independent)
1. A vs B for this phase — is deferring all publishing correct, or is there a reason to publish the engine
   now?
2. Skills install mechanism: **symlink** the repo's `skills/<name>/` into `~/.claude/skills/` (live-updates
   on `git pull`, but couples to the checkout) vs **copy** (self-contained, but stale until re-run) vs
   package as a **plugin** (a `plugin.json` + skills). Which fits Claude Code / OpenClaw skill discovery?
3. Should the setup script pin the engine to a git **tag** (reproducible) or track `main` (auto-update)?
4. Migration-phase compatibility: does anything here make the later "migrate off `fulcra-tools-coord`" or
   "upstream to agent-skills" steps harder? (E.g. skill names, the `_coord/` sidecar, the `team/` layout.)

## Build (approach A), once feedback is in
- `scripts/coord2-setup.sh [--claude|--openclaw] [--copy|--symlink] [--yes]` — install engine from git,
  wire skills, self-test. Validated inputs, consent-gated (same discipline as `install-heartbeat.sh`).
- README "Install (standalone)" quickstart.
- Tag `v0.4.0`.
- Live-verify: fresh install → `coord-engine reconcile` + a skill is discoverable.
