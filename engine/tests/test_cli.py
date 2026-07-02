import json

from coord_engine import cli
from tests.test_reconcile import FakeTransport, _task


def test_cli_reconcile_then_status_and_board(capsys):
    t = FakeTransport()
    t.put("team/r/task/a.md", _task("Alpha", "active"))
    t.put("team/r/task/b.md", _task("Bravo", "waiting"))

    assert cli.main(["reconcile", "r"], transport=t) == 0
    assert "2 tasks" in capsys.readouterr().out

    assert cli.main(["status", "r", "--json"], transport=t) == 0
    counts = json.loads(capsys.readouterr().out)
    assert counts == {"active": 1, "waiting": 1}

    assert cli.main(["board", "r"], transport=t) == 0
    out = capsys.readouterr().out
    assert "ACTIVE (1)" in out and "Alpha" in out


def test_cli_needs_me(capsys):
    t = FakeTransport()
    t.put("team/r/task/a.md",
          "---\ntype: Task\ntitle: Mine\nstatus: active\nassignee: me\n---\n")
    cli.main(["reconcile", "r"], transport=t)
    capsys.readouterr()
    assert cli.main(["needs-me", "r", "--agent", "me"], transport=t) == 0
    assert "Mine" in capsys.readouterr().out


def test_cli_search(capsys):
    t = FakeTransport()
    t.put("team/r/task/a.md", _task("Widget fixer", "active"))
    cli.main(["reconcile", "r"], transport=t)
    capsys.readouterr()
    assert cli.main(["search", "r", "widget"], transport=t) == 0
    assert "Widget fixer" in capsys.readouterr().out


def test_cli_status_no_aggregate_hint(capsys):
    t = FakeTransport()
    assert cli.main(["status", "empty"], transport=t) == 0
    assert "run `reconcile` first" in capsys.readouterr().out


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def test_cli_roles_status_held(capsys):
    t = FakeTransport()
    t.put("team/r/roles/reviewer.md", "---\ntype: Role\npolicy: shared\nsla_hours: 24\n---\n")
    t.put("team/r/roles/reviewer/leases/ash.md",
          f"---\ntype: Lease\nagent: ash\ntimestamp: {_now_iso()}\n---\n")
    assert cli.main(["roles", "status", "r", "reviewer"], transport=t) == 0
    assert "HELD" in capsys.readouterr().out


def test_cli_roles_status_vacant_escalation_due(capsys):
    t = FakeTransport()
    t.put("team/r/roles/reviewer.md", "---\ntype: Role\nsla_hours: 24\n---\n")
    t.put("team/r/roles/reviewer/leases/ash.md",
          "---\ntype: Lease\nagent: ash\ntimestamp: 2020-01-01T00:00:00Z\n---\n")
    assert cli.main(["roles", "status", "r", "reviewer", "--json"], transport=t) == 0
    import json as _json
    res = _json.loads(capsys.readouterr().out)
    assert res["status"] == "VACANT"
    assert res["escalation_due"] is True


def test_cli_task_start_then_reconcile_shows_it(capsys):
    from coord_engine import okf
    t = FakeTransport()
    assert cli.main(["task", "start", "r", "Build the thing", "-w", "coord2",
                     "--status", "active", "-p", "P1"], transport=t) == 0
    assert "created" in capsys.readouterr().out
    fm = okf.parse_frontmatter(t.store["team/r/task/build-the-thing.md"])
    assert fm["type"] == "Task" and fm["status"] == "active" and fm["priority"] == "P1"
    cli.main(["reconcile", "r"], transport=t); capsys.readouterr()
    cli.main(["board", "r"], transport=t)
    assert "Build the thing" in capsys.readouterr().out


def test_cli_task_start_refuses_duplicate(capsys):
    t = FakeTransport()
    cli.main(["task", "start", "r", "Dup"], transport=t); capsys.readouterr()
    assert cli.main(["task", "start", "r", "Dup"], transport=t) == 1
    assert "already exists" in capsys.readouterr().err


def test_cli_task_illegal_transition_fails(capsys):
    t = FakeTransport()
    cli.main(["task", "start", "r", "T", "--status", "active"], transport=t)
    cli.main(["task", "done", "r", "t", "-e", "shipped"], transport=t)
    capsys.readouterr()
    assert cli.main(["task", "update", "r", "t", "--status", "active"], transport=t) == 1
    assert "illegal transition" in capsys.readouterr().err


def test_cli_task_update_done_needs_evidence(capsys):
    t = FakeTransport()
    cli.main(["task", "start", "r", "T", "--status", "active"], transport=t)
    capsys.readouterr()
    assert cli.main(["task", "update", "r", "t", "--status", "done"], transport=t) == 1
    assert "done requires evidence" in capsys.readouterr().err
    assert cli.main(["task", "update", "r", "t", "--status", "done", "-e", "ok"], transport=t) == 0


def test_cli_review_status(capsys):
    import json as _j
    t = FakeTransport()
    t.put("team/r/review/pr-9.md", "---\ntype: Review\nrequired: alice, bob\n---\n")
    t.put("team/r/review/pr-9/verdicts/alice.md",
          "---\ntype: Verdict\nreviewer: alice\nverdict: approve\n---\n")
    assert cli.main(["review", "status", "r", "pr-9", "--json"], transport=t) == 0
    res = _j.loads(capsys.readouterr().out)
    assert res["state"] == "PENDING" and res["pending_required"] == ["bob"]
    t.put("team/r/review/pr-9/verdicts/bob.md",
          "---\ntype: Verdict\nreviewer: bob\nverdict: changes\n---\n")
    cli.main(["review", "status", "r", "pr-9", "--json"], transport=t)
    assert _j.loads(capsys.readouterr().out)["state"] == "CHANGES"


def test_cli_review_keys_by_filename_not_frontmatter(capsys):
    # a file claiming someone else's reviewer name must NOT shadow their verdict
    import json as _j
    t = FakeTransport()
    t.put("team/r/review/pr-1.md", "---\ntype: Review\nrequired: alice\n---\n")
    t.put("team/r/review/pr-1/verdicts/alice.md",
          "---\ntype: Verdict\nreviewer: alice\nverdict: changes\n---\n")
    t.put("team/r/review/pr-1/verdicts/mallory.md",   # claims to be alice, approving
          "---\ntype: Verdict\nreviewer: alice\nverdict: approve\n---\n")
    cli.main(["review", "status", "r", "pr-1", "--json"], transport=t)
    res = _j.loads(capsys.readouterr().out)
    # alice's real changes still blocks; mallory counts as her own (approve) reviewer
    assert res["state"] == "CHANGES"
    assert "alice" in res["changes"] and "mallory" in res["approvals"]
