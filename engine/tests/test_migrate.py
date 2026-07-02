import json

from coord_engine import cli, migrate, okf
from tests.test_reconcile import FakeTransport

NOW = "2026-07-02T16:00:00Z"


def _incumbent(id, title, status="active", **over):
    t = {"id": id, "title": title, "status": status, "priority": "P1",
         "workstream": "fulcra-coord", "kind": "bug", "owner_agent": "claude-code:mb:x",
         "assignee": "codex:h:r", "current_summary": "the summary",
         "next_action": "do next", "blocked_on": None, "not_before": None,
         "due": "2026-08-01T00:00:00Z", "updated_at": "2026-06-30T10:00:00Z",
         "tags": ["agent:claude-code:mb:x", "status:active", "extra:label"]}
    t.update(over)
    return t


def test_map_task_field_fidelity():
    slug, fm, body = migrate.map_task(_incumbent("TASK-X-1", "Fix the widget"), now=NOW)
    assert slug == "fix-the-widget"
    assert fm["status"] == "active" and fm["priority"] == "P1"
    assert fm["owner"] == "claude-code:mb:x" and fm["assignee"] == "codex:h:r"
    assert fm["description"] == "the summary" and fm["next_action"] == "do next"
    assert fm["timestamp"] == "2026-06-30T10:00:00Z" and fm["due"] == "2026-08-01T00:00:00Z"
    assert fm["migrated_from"] == "TASK-X-1"
    assert "workstream:fulcra-coord" in fm["tags"] and "kind:bug" in fm["tags"]
    assert "extra:label" in fm["tags"]                       # real labels kept
    assert not any(t.startswith(("agent:", "status:")) for t in fm["tags"])  # dupes dropped
    assert "Migrated from fulcra-coord task `TASK-X-1`" in body


def test_map_task_sanitizes_bad_enums_and_sentinels():
    slug, fm, _ = migrate.map_task(_incumbent("T2", "Odd", status="weird", priority="P9",
                                              assignee="*"), now=NOW)
    assert fm["status"] == "proposed" and fm["priority"] == "P2"
    assert fm["assignee"] == "*"                             # broadcast sentinel preserved


def test_migrate_end_to_end_idempotent_and_marked():
    t = FakeTransport()
    t.put("/coordination/tasks/TASK-X-1.json", json.dumps(_incumbent("TASK-X-1", "Fix the widget")))
    t.put("/coordination/tasks/TASK-X-2.json", json.dumps(_incumbent("TASK-X-2", "Done thing", status="done")))
    res = migrate.migrate(t, "fulcra", now=NOW)
    assert res["migrated"] == 1 and res["errors"] == []       # terminal excluded
    doc = t.store["team/fulcra/task/fix-the-widget.md"]
    assert okf.parse_frontmatter(doc)["migrated_from"] == "TASK-X-1"
    # incumbent marked
    marked = json.loads(t.store["/coordination/tasks/TASK-X-1.json"])
    assert migrate.MIGRATED_TAG in marked["tags"]
    # second run: skip via the tag (and via migrated_from even if tag missing)
    res2 = migrate.migrate(t, "fulcra", now=NOW)
    assert res2["migrated"] == 0 and res2["skipped"] >= 1


def test_migrate_dry_run_writes_nothing():
    t = FakeTransport()
    t.put("/coordination/tasks/TASK-X-1.json", json.dumps(_incumbent("TASK-X-1", "Fix it")))
    before = dict(t.store)
    res = migrate.migrate(t, "fulcra", now=NOW, dry_run=True)
    assert len(res["planned"]) == 1 and t.store == before


def test_migrate_slug_collision_disambiguates():
    t = FakeTransport()
    t.put("team/fulcra/task/fix-it.md", "---\ntype: Task\ntitle: Fix it\nstatus: active\n---\n")
    t.put("/coordination/tasks/TASK-X-9.json", json.dumps(_incumbent("TASK-X-9", "Fix it")))
    res = migrate.migrate(t, "fulcra", now=NOW)
    assert res["migrated"] == 1
    news = [p for p in t.store if p.startswith("team/fulcra/task/fix-it-")]
    assert len(news) == 1                                     # suffixed, original untouched


def test_migrate_mark_failure_reports_but_keeps_coord2_doc():
    t = FakeTransport()
    t.put("/coordination/tasks/TASK-X-1.json", json.dumps(_incumbent("TASK-X-1", "Fix it")))
    orig = t.write
    t.write = lambda p, c: False if p.startswith("/coordination/") else orig(p, c)
    res = migrate.migrate(t, "fulcra", now=NOW)
    assert res["migrated"] == 1 and any("MARK FAILED" in e for e in res["errors"])
    assert "team/fulcra/task/fix-it.md" in t.store


def test_cli_migrate_dry_run(capsys):
    t = FakeTransport()
    t.put("/coordination/tasks/TASK-X-1.json", json.dumps(_incumbent("TASK-X-1", "Fix it")))
    assert cli.main(["migrate", "fulcra", "--dry-run"], transport=t) == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "TASK-X-1 -> task/fix-it.md" in out
