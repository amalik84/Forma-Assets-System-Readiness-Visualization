"""Shared helpers for the fetch modules."""

import json

import config



def save(name, result, day=None):
    """Write data/raw/<projectId>/YYYY-MM-DD/<name>.json and return the path."""
    out = config.snapshot_dir(day or config.snapshot_day())
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.json"
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    return path


def done_statuses(env_value):
    """'closed, completed' -> {'closed', 'completed'} (lower case)."""
    return {s.strip().lower() for s in (env_value or "").split(",") if s.strip()}
