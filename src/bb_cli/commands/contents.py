import click
import httpx

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.context import cache_last_ls, load_context, resolve_ref
from bb_cli.commands.courses import fetch_courses
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


def _resolve_path(client: BBClient, course_id: str, path: str, show_all: bool):
    """Walk a /-separated path from root, returning (items, breadcrumbs)."""
    breadcrumbs = []
    segments = [s for s in path.split("/") if s]

    items = fetch_items(client, course_id, None, show_all)

    for i, seg in enumerate(segments):
        resolved = resolve_ref(seg, items)
        is_last = i == len(segments) - 1

        if not _is_folder(resolved):
            if is_last:
                breadcrumbs.append((resolved.get("title", ""), resolved.get("id", "")))
                return [resolved], breadcrumbs
            typename = _friendly_type(resolved)
            raise click.ClickException(
                f"'{resolved.get('title', '')}' is a {typename}, not a folder"
            )

        breadcrumbs.append((resolved.get("title", ""), resolved.get("id", "")))
        items = fetch_items(client, course_id, resolved["id"], show_all)

    return items, breadcrumbs


def fetch_items(client: BBClient, course_id: str, folder_id: str | None, show_all: bool = False):
    """Fetch contents for a folder (or root if folder_id is None)."""
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


def _print_breadcrumb(label: str, breadcrumbs: list[tuple[str, str]]):
    parts = [label] + [title for title, _ in breadcrumbs]
    click.echo(f"/{'/'.join(parts)}\n")


def _print_nav_hint(items: list[dict]):
    has_folders = any(_is_folder(i) for i in items)
    if not has_folders:
        return
    click.echo("\nTip: Navigate into a folder with bb cd <row#>")


def _display_courses(client: BBClient, json_flag: bool):
    """Show courses list and cache for cd resolution."""
    course_list = fetch_courses(client)
    if not course_list:
        click.echo("No courses found.")
        return

    # Cache for cd resolution
    cache_last_ls([
        {"id": c["id"], "title": c.get("name", ""), "contentHandler": {"id": "course"}}
        for c in course_list
    ])

    if json_flag:
        output_table(
            course_list,
            [
                ("ID", "id"),
                ("Course ID", "courseId"),
                ("Name", "name"),
                ("Role", "_role"),
                ("Available", "availability.available"),
            ],
            title="Enrolled Courses",
            json_flag=True,
        )
    else:
        for idx, c in enumerate(course_list, 1):
            c["_row"] = str(idx)
        output_table(
            course_list,
            [
                ("#", "_row"),
                ("Name", "name"),
                ("Course ID", "courseId"),
                ("Available", "availability.available"),
            ],
            title="Courses",
            json_flag=False,
        )
        click.echo("\nTip: Enter a course with bb cd <row#>")


@click.command("ls")
@click.argument("course_id", default=None, required=False)
@click.argument("path", default="")
@click.option("--id", "folder_id", default=None, help="Browse a folder by its Blackboard ID.")
@click.option("--folder", "folder_id_compat", default=None, hidden=True, help="Alias for --id (backward compat).")
@click.option("--all", "show_all", is_flag=True, default=False, help="Include unavailable items.")
@click.pass_context
def ls(ctx, course_id, path, folder_id, folder_id_compat, show_all):
    """List course contents (or courses if no context).

    Without a course context, shows enrolled courses.
    With a course context, shows folder contents.

    \b
    Examples:
      bb ls                              # list courses (or current folder)
      bb cd 3                            # enter course #3
      bb ls                              # list course root contents
      bb ls CS101                        # explicit course root
      bb ls CS101 "Lecture Notes/Week 1" # explicit path
    """
    cookies = ensure_authenticated()
    client = BBClient(cookies)
    json_flag = ctx.obj["json"]

    # If no course_id argument, try context
    if course_id is None:
        nav_ctx = load_context()
        if nav_ctx.get("course_id"):
            course_id = nav_ctx["course_id"]
            folder_id = folder_id or folder_id_compat or nav_ctx.get("folder_id")
        else:
            # No context, no arg → show courses
            _display_courses(client, json_flag)
            return

    effective_folder_id = folder_id or folder_id_compat

    if effective_folder_id and not path:
        # Direct ID access
        items = fetch_items(client, course_id, effective_folder_id, show_all)
        breadcrumbs = []
        try:
            folder_info = client.get(f"/courses/{course_id}/contents/{effective_folder_id}")
            breadcrumbs = [(folder_info.get("title", effective_folder_id), effective_folder_id)]
        except Exception:
            breadcrumbs = [(effective_folder_id, effective_folder_id)]
    elif path:
        items, breadcrumbs = _resolve_path(client, course_id, path, show_all)
    else:
        items = fetch_items(client, course_id, None, show_all)
        breadcrumbs = []

    if not items:
        click.echo("No contents found.")
        return

    # Cache items for cd/download resolution
    cache_last_ls(items)

    # Build breadcrumb label from context
    nav_ctx = load_context()
    label = nav_ctx.get("course_name") or course_id
    if nav_ctx.get("path"):
        breadcrumbs = [(p["name"], p["id"]) for p in nav_ctx["path"]] + breadcrumbs

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
        _print_breadcrumb(label, breadcrumbs)

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

        _print_nav_hint(items)
