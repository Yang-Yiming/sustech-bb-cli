import click
import httpx

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.formatting import extract, output_table

CONTENT_TYPE_NAMES = {
    "resource/x-bb-folder": "Folder",
    "resource/x-bb-file": "File",
    "resource/x-bb-document": "Document",
    "resource/x-bb-assignment": "Assignment",
    "resource/x-bb-blankpage": "Page",
    "resource/x-bb-externallink": "Link",
    "resource/x-bb-toollink": "Tool Link",
}


def _friendly_type(item: dict) -> str:
    raw = extract(item, "contentHandler.id") or ""
    return CONTENT_TYPE_NAMES.get(raw, raw)


def _is_folder(item: dict) -> bool:
    return extract(item, "contentHandler.id") == "resource/x-bb-folder"


def _resolve_segment(segment: str, items: list[dict]) -> dict:
    """Match a single path segment against a list of content items.

    Tries in order: exact title (case-insensitive), 1-based row index,
    unique substring match.
    """
    # 1. Exact title match (case-insensitive)
    for item in items:
        if item.get("title", "").lower() == segment.lower():
            return item

    # 2. Integer index (1-based)
    try:
        idx = int(segment)
        if 1 <= idx <= len(items):
            return items[idx - 1]
        raise click.ClickException(
            f"Row {idx} is out of range (1-{len(items)})"
        )
    except ValueError:
        pass

    # 3. Unique substring match (case-insensitive)
    matches = [i for i in items if segment.lower() in i.get("title", "").lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        titles = "\n".join(f"  {n+1}. {m.get('title', '')}" for n, m in enumerate(matches))
        raise click.ClickException(
            f"Ambiguous match for '{segment}'. Did you mean one of:\n{titles}"
        )

    # No match — show available items
    available = "\n".join(f"  {n+1}. {i.get('title', '')}" for n, i in enumerate(items))
    raise click.ClickException(
        f"No match for '{segment}'. Available items:\n{available}"
    )


def _resolve_path(client: BBClient, course_id: str, path: str, show_all: bool):
    """Walk a /-separated path from root, returning (items, breadcrumbs).

    Returns the *children* of the final resolved folder (or root items if path is empty).
    breadcrumbs is a list of (title, id) tuples for the resolved folders.
    """
    breadcrumbs = []
    segments = [s for s in path.split("/") if s]

    # Start at root
    items = _fetch_items(client, course_id, None, show_all)

    for i, seg in enumerate(segments):
        resolved = _resolve_segment(seg, items)
        is_last = i == len(segments) - 1

        if not _is_folder(resolved):
            if is_last:
                # Last segment resolves to a non-folder — show it as a single-item list
                breadcrumbs.append((resolved.get("title", ""), resolved.get("id", "")))
                return [resolved], breadcrumbs
            typename = _friendly_type(resolved)
            raise click.ClickException(
                f"'{resolved.get('title', '')}' is a {typename}, not a folder"
            )

        breadcrumbs.append((resolved.get("title", ""), resolved.get("id", "")))
        items = _fetch_items(client, course_id, resolved["id"], show_all)

    return items, breadcrumbs


def _fetch_items(client: BBClient, course_id: str, folder_id: str | None, show_all: bool):
    """Fetch contents for a folder (or root if folder_id is None), applying availability filter."""
    try:
        if folder_id:
            items = client.get_paginated(f"/courses/{course_id}/contents/{folder_id}/children")
        else:
            items = client.get_paginated(f"/courses/{course_id}/contents")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            raise click.ClickException("Access denied to this folder. You may not have permission.")
        raise

    if not show_all:
        items = [i for i in items if extract(i, "availability.available") == "Yes"]

    return items


def _print_breadcrumb(course_id: str, breadcrumbs: list[tuple[str, str]]):
    parts = [course_id] + [title for title, _ in breadcrumbs]
    click.echo(f"📁 {' > '.join(parts)}\n")


def _print_nav_hint(course_id: str, items: list[dict], breadcrumbs: list[tuple[str, str]]):
    has_folders = any(_is_folder(i) for i in items)
    if not has_folders:
        return
    path_prefix = "/".join(title for title, _ in breadcrumbs)
    if path_prefix:
        example = f'bb ls {course_id} "{path_prefix}/1"'
    else:
        example = f"bb ls {course_id} 1"
    click.echo(f"\nTip: Navigate into a folder with {example}")


@click.command("ls")
@click.argument("course_id")
@click.argument("path", default="")
@click.option("--id", "folder_id", default=None, help="Browse a folder by its Blackboard ID.")
@click.option("--folder", "folder_id_compat", default=None, hidden=True, help="Alias for --id (backward compat).")
@click.option("--all", "show_all", is_flag=True, default=False, help="Include unavailable items.")
@click.pass_context
def ls(ctx, course_id, path, folder_id, folder_id_compat, show_all):
    """List course contents with filesystem-like navigation.

    Navigate by name, row number, or slash-separated path.

    \b
    Examples:
      bb ls CS101                        # root contents
      bb ls CS101 "Lecture Notes"        # by folder name
      bb ls CS101 1                      # by row number
      bb ls CS101 "Lecture Notes/Week 1" # nested path
      bb ls CS101 --id _12345_1          # by Blackboard ID
    """
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    # --folder (hidden compat) takes precedence if --id not given
    effective_folder_id = folder_id or folder_id_compat

    json_flag = ctx.obj["json"]

    if effective_folder_id:
        # Direct ID access (escape hatch / backward compat)
        items = _fetch_items(client, course_id, effective_folder_id, show_all)
        breadcrumbs = []
        # Try to get folder name for breadcrumb
        try:
            folder_info = client.get(f"/courses/{course_id}/contents/{effective_folder_id}")
            breadcrumbs = [(folder_info.get("title", effective_folder_id), effective_folder_id)]
        except Exception:
            breadcrumbs = [(effective_folder_id, effective_folder_id)]
    elif path:
        items, breadcrumbs = _resolve_path(client, course_id, path, show_all)
    else:
        items = _fetch_items(client, course_id, None, show_all)
        breadcrumbs = []

    if not items:
        click.echo("No contents found.")
        return

    if json_flag:
        for item in items:
            item["typeName"] = _friendly_type(item)
        output_table(
            items,
            [
                ("ID", "id"),
                ("Title", "title"),
                ("Type", "contentHandler.id"),
                ("typeName", "typeName"),
                ("Available", "availability.available"),
            ],
            title="Course Contents",
            json_flag=True,
        )
    else:
        _print_breadcrumb(course_id, breadcrumbs)

        # Inject row number and friendly type
        for idx, item in enumerate(items, 1):
            item["_row"] = str(idx)
            item["_typeName"] = _friendly_type(item)

        output_table(
            items,
            [
                ("#", "_row"),
                ("Title", "title"),
                ("Type", "_typeName"),
                ("Available", "availability.available"),
            ],
            title="Course Contents",
            json_flag=False,
        )

        _print_nav_hint(course_id, items, breadcrumbs)
