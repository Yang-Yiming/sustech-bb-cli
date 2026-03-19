import click

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.context import (
    cache_last_ls,
    clear_context,
    load_context,
    resolve_ref,
    save_context,
    set_course,
    set_folder,
)


@click.command("cd")
@click.argument("target", default=None, required=False)
@click.pass_context
def cd(ctx, target):
    """Change the current course or folder context.

    \b
    Examples:
      bb cd 3              # enter course #3 (from bb ls)
      bb cd "Lecture Notes" # enter folder by name
      bb cd 1/2            # nested navigation
      bb cd ..             # go up one level
      bb cd /              # back to course root
      bb cd                # clear context entirely
    """
    # bb cd (no arg) → clear context
    if target is None:
        clear_context()
        click.echo("Context cleared.")
        return

    nav_ctx = load_context()
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    if target == "..":
        _cd_up(nav_ctx)
        return

    if target == "/":
        _cd_root(nav_ctx)
        return

    if not nav_ctx.get("course_id"):
        # No course selected → resolve target as a course
        _cd_into_course(client, nav_ctx, target)
    else:
        # Inside a course → resolve target as folder(s)
        _cd_into_folder(client, nav_ctx, target)


def _cd_up(nav_ctx: dict):
    """Go up one level: pop last path entry, or leave course if at root."""
    if nav_ctx.get("path"):
        nav_ctx["path"].pop()
        if nav_ctx["path"]:
            nav_ctx["folder_id"] = nav_ctx["path"][-1]["id"]
        else:
            nav_ctx["folder_id"] = None
        nav_ctx["last_ls"] = []
        save_context(nav_ctx)
        _print_location(nav_ctx)
    elif nav_ctx.get("course_id"):
        # At course root → leave course
        clear_context()
        click.echo("Left course. Context cleared.")
    else:
        click.echo("Already at top level.")


def _cd_root(nav_ctx: dict):
    """Go back to course root (keep course, clear folder)."""
    if not nav_ctx.get("course_id"):
        click.echo("No course selected.")
        return
    nav_ctx["folder_id"] = None
    nav_ctx["path"] = []
    nav_ctx["last_ls"] = []
    save_context(nav_ctx)
    _print_location(nav_ctx)


def _cd_into_course(client, nav_ctx: dict, target: str):
    """Resolve target as a course reference and set it."""
    cached = nav_ctx.get("last_ls", [])
    if not cached:
        # Need to fetch courses
        from bb_cli.commands.courses import fetch_courses
        course_list = fetch_courses(client)
        if not course_list:
            raise click.ClickException("No courses found.")
        # Build items for resolution
        cached = [
            {"id": c["id"], "title": c.get("name", ""), "type": "course"}
            for c in course_list
        ]
        cache_last_ls([
            {"id": c["id"], "title": c.get("name", ""), "contentHandler": {"id": "course"}}
            for c in course_list
        ])

    resolved = resolve_ref(target, cached)
    set_course(resolved["id"], resolved["title"])
    click.echo(f"/{resolved['title']}")


def _cd_into_folder(client, nav_ctx: dict, target: str):
    """Resolve /-separated target as folder navigation within a course."""
    from bb_cli.commands.contents import fetch_items, _is_folder

    segments = [s for s in target.split("/") if s]
    course_id = nav_ctx["course_id"]
    path = list(nav_ctx.get("path", []))
    current_folder_id = nav_ctx.get("folder_id")

    for seg in segments:
        # Try cached items first, otherwise fetch
        cached = nav_ctx.get("last_ls", [])
        if cached:
            resolved = resolve_ref(seg, cached)
            # Fetch full item if we only have a cache stub
            if "contentHandler" not in resolved:
                full = client.get(f"/courses/{course_id}/contents/{resolved['id']}")
                resolved = full
        else:
            items = fetch_items(client, course_id, current_folder_id)
            resolved = resolve_ref(seg, items)

        if not _is_folder(resolved):
            from bb_cli.commands.contents import _friendly_type
            typename = _friendly_type(resolved)
            raise click.ClickException(
                f"'{resolved.get('title', '')}' is a {typename}, not a folder"
            )

        path.append({"name": resolved.get("title", ""), "id": resolved["id"]})
        current_folder_id = resolved["id"]
        # Clear cache so next segment fetches fresh
        nav_ctx["last_ls"] = []
        nav_ctx["folder_id"] = current_folder_id

    set_folder(current_folder_id, path)
    _print_location(load_context())


def _print_location(nav_ctx: dict):
    """Print the current location path."""
    click.echo(_format_location(nav_ctx))


def _format_location(nav_ctx: dict) -> str:
    """Format the current location as a path string."""
    if not nav_ctx.get("course_id"):
        return "/"
    parts = [nav_ctx.get("course_name") or nav_ctx["course_id"]]
    for entry in nav_ctx.get("path", []):
        parts.append(entry["name"])
    return "/" + "/".join(parts)


@click.command("pwd")
def pwd():
    """Show the current course/folder context."""
    nav_ctx = load_context()
    click.echo(_format_location(nav_ctx))
