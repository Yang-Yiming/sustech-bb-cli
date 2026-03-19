from __future__ import annotations

import json as _json

import click

from bb_cli.config import CONFIG_DIR, CONTEXT_FILE

_EMPTY = {
    "course_id": None,
    "course_name": None,
    "folder_id": None,
    "path": [],
    "last_ls": [],
}


def load_context() -> dict:
    """Read context from disk, returning defaults if missing."""
    if not CONTEXT_FILE.exists():
        return dict(_EMPTY)
    try:
        data = _json.loads(CONTEXT_FILE.read_text())
        # Merge with defaults so new keys are always present
        return {**_EMPTY, **data}
    except (_json.JSONDecodeError, OSError):
        return dict(_EMPTY)


def save_context(ctx: dict) -> None:
    """Write context to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONTEXT_FILE.write_text(_json.dumps(ctx, indent=2))


def clear_context() -> None:
    """Reset context to empty defaults."""
    save_context(dict(_EMPTY))


def require_course() -> dict:
    """Load context and raise if no course is set."""
    ctx = load_context()
    if not ctx.get("course_id"):
        raise click.ClickException(
            "No course selected. Use 'bb cd <course>' first, or pass COURSE_ID directly."
        )
    return ctx


def set_course(course_id: str, course_name: str) -> dict:
    """Set the active course, clearing folder/path/cache."""
    ctx = load_context()
    ctx["course_id"] = course_id
    ctx["course_name"] = course_name
    ctx["folder_id"] = None
    ctx["path"] = []
    ctx["last_ls"] = []
    save_context(ctx)
    return ctx


def set_folder(folder_id: str | None, path: list[dict]) -> dict:
    """Update current folder and path within the active course."""
    ctx = load_context()
    ctx["folder_id"] = folder_id
    ctx["path"] = path
    ctx["last_ls"] = []
    save_context(ctx)
    return ctx


def cache_last_ls(items: list[dict]) -> None:
    """Cache lightweight item summaries from the last ls."""
    ctx = load_context()
    ctx["last_ls"] = [
        {"id": i.get("id", ""), "title": i.get("title", ""), "type": _item_type(i)}
        for i in items
    ]
    save_context(ctx)


def _item_type(item: dict) -> str:
    """Extract a short type string from a content item."""
    handler = item.get("contentHandler", {})
    if isinstance(handler, dict):
        return handler.get("id", "")
    return ""


def resolve_ref(ref: str, items: list[dict], title_key: str = "title") -> dict:
    """Resolve a reference to an item: exact title -> 1-based index -> unique substring.

    Works with both full API items and cached last_ls summaries.
    """
    # 1. Exact title match (case-insensitive)
    for item in items:
        if item.get(title_key, "").lower() == ref.lower():
            return item

    # 2. Integer index (1-based)
    try:
        idx = int(ref)
        if 1 <= idx <= len(items):
            return items[idx - 1]
        raise click.ClickException(
            f"Row {idx} is out of range (1-{len(items)})"
        )
    except ValueError:
        pass

    # 3. Unique substring match (case-insensitive)
    matches = [i for i in items if ref.lower() in i.get(title_key, "").lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        titles = "\n".join(
            f"  {n+1}. {m.get(title_key, '')}" for n, m in enumerate(matches)
        )
        raise click.ClickException(
            f"Ambiguous match for '{ref}'. Did you mean one of:\n{titles}"
        )

    # No match
    available = "\n".join(
        f"  {n+1}. {i.get(title_key, '')}" for n, i in enumerate(items)
    )
    raise click.ClickException(
        f"No match for '{ref}'. Available items:\n{available}"
    )
