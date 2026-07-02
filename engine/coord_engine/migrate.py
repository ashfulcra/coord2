"""One-shot exporter: incumbent fulcra-coord JSON tasks -> coord2 task docs.

The migration plan's approach C (docs 06): deterministic field mapping, idempotent
(re-runs skip already-migrated work), one-way, and **marked** — after a verified
coord2 write the incumbent task gains a ``migrated:coord2`` tag so a task lives in
exactly one active system. Never deletes anything on the incumbent.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from . import okf
from .model import VALID_PRIORITIES, VALID_STATUSES
from .tasks import agent_key, slugify
from .transport import TransportError

MIGRATED_TAG = "migrated:coord2"


def map_task(t: dict[str, Any], *, now: str) -> tuple[str, dict[str, Any], str]:
    """Deterministic incumbent-task -> (slug, frontmatter, body) mapping."""
    title = str(t.get("title") or t.get("id") or "untitled")
    slug = slugify(title)
    status = t.get("status") if t.get("status") in VALID_STATUSES else "proposed"
    priority = t.get("priority") if t.get("priority") in VALID_PRIORITIES else "P2"
    tags: list[str] = []
    if t.get("workstream"):
        tags.append(f"workstream:{t['workstream']}")
    if t.get("kind"):
        tags.append(f"kind:{t['kind']}")
    for tag in t.get("tags") or []:
        s = str(tag)
        # drop the incumbent's denormalized dupes; keep real labels
        if not s.startswith(("agent:", "status:", "priority:", "workstream:", "kind:")):
            tags.append(s)
    fm = {
        "type": "Task", "title": title,
        "description": t.get("current_summary") or "",
        "timestamp": t.get("updated_at") or t.get("created_at") or now,
        "tags": tags, "id": slug,
        "status": status, "priority": priority,
        "owner": t.get("owner_agent"), "assignee": t.get("assignee"),
        "next_action": t.get("next_action"), "blocked_on": t.get("blocked_on"),
        "not_before": t.get("not_before"), "due": t.get("due"),
        "checkpoint_ref": t.get("checkpoint_ref"),
        "migrated_from": t.get("id"),
    }
    body = (f"\n# {title}\n\n"
            f"- Migrated from fulcra-coord task `{t.get('id')}` on {now}.\n")
    return slug, fm, body


def migrate(
    transport: Any,
    team: str,
    *,
    now: str,
    source: str = "/coordination",
    dry_run: bool = False,
    mark: bool = True,
    include_terminal: bool = False,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    """One pass. Returns {planned:[…], migrated, skipped, marked, errors:[…]}."""
    planned: list[str] = []
    errors: list[str] = []
    migrated = skipped = marked = 0
    try:
        entries = transport.list_dir(f"{source}/tasks/")
    except TransportError as e:
        return {"planned": [], "migrated": 0, "skipped": 0, "marked": 0,
                "errors": [f"source unreadable: {e}"]}
    # existing migrated_from ids in the team (idempotence)
    existing_from: dict[str, str] = {}
    existing_slugs: set = set()
    try:
        for e in transport.list_dir(f"team/{team}/task/"):
            n = e.get("name") or ""
            if e.get("is_dir") or not n.endswith(".md") or n in ("index.md", "log.md"):
                continue
            fm = okf.parse_frontmatter(transport.read(f"team/{team}/task/{n}")) or {}
            existing_slugs.add(n[:-3])
            if fm.get("migrated_from"):
                existing_from[str(fm["migrated_from"])] = n[:-3]
    except TransportError:
        pass
    for e in entries:
        n = e.get("name") or ""
        if e.get("is_dir") or not n.endswith(".json"):
            continue
        raw = transport.read(f"{source}/tasks/{n}")
        try:
            t = json.loads(raw) if raw else None
        except Exception:
            t = None
        if not isinstance(t, dict) or not t.get("id"):
            continue
        if MIGRATED_TAG in (t.get("tags") or []):
            skipped += 1
            continue
        if not include_terminal and t.get("status") in ("done", "abandoned"):
            continue
        if str(t.get("id")) in existing_from:
            skipped += 1
            continue
        if limit is not None and migrated + len(planned) >= limit and dry_run:
            break
        if limit is not None and migrated >= limit and not dry_run:
            break
        slug, fm, body = map_task(t, now=now)
        if slug in existing_slugs:  # collision with a non-migrated doc: disambiguate
            slug = f"{slug}-{agent_key(str(t['id']))[-6:]}"
            fm["id"] = slug
        if dry_run:
            planned.append(f"{t['id']} -> task/{slug}.md [{fm['status']}/{fm['priority']}]")
            continue
        dst = f"team/{team}/task/{slug}.md"
        if not transport.write(dst, okf.render_frontmatter(fm) + body):
            errors.append(f"{t['id']}: coord2 write failed; incumbent untouched")
            continue
        if transport.read(dst) is None:  # verify before marking (one-active-system)
            errors.append(f"{t['id']}: coord2 write not readable back; incumbent untouched")
            continue
        migrated += 1
        existing_slugs.add(slug)
        if mark:
            t.setdefault("tags", []).append(MIGRATED_TAG)
            if transport.write(f"{source}/tasks/{n}", json.dumps(t, indent=1)):
                marked += 1
            else:
                errors.append(f"{t['id']}: migrated but MARK FAILED — re-run may duplicate "
                              f"(idempotence via migrated_from still guards)")
    return {"planned": planned, "migrated": migrated, "skipped": skipped,
            "marked": marked, "errors": errors}
