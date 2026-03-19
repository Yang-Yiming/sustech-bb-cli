import click

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.context import load_context, require_course, resolve_ref
from bb_cli.formatting import output_single, output_table


@click.command("show")
@click.argument("target")
@click.pass_context
def show(ctx, target):
    """Show details for a content item, grades, or announcements.

    \b
    Examples:
      bb show 3              # show item #3 from last bb ls
      bb show grades         # grades for current course
      bb show announcements  # announcements for current course
    """
    json_flag = ctx.obj["json"]

    if target.lower() == "grades":
        _show_grades(json_flag)
        return

    if target.lower() in ("announcements", "ann"):
        _show_announcements(json_flag)
        return

    # Resolve as content item
    _show_item(target, json_flag)


def _show_grades(json_flag: bool):
    nav_ctx = require_course()
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    from bb_cli.commands.grades import fetch_grades
    grade_rows = fetch_grades(client, nav_ctx["course_id"])

    if not grade_rows:
        click.echo("No grade columns found.")
        return

    output_table(
        grade_rows,
        [
            ("Column", "name"),
            ("Score", "score"),
            ("Text", "text"),
            ("Notes", "notes"),
        ],
        title="Grades",
        json_flag=json_flag,
    )


def _show_announcements(json_flag: bool):
    nav_ctx = require_course()
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    from bb_cli.commands.announcements import fetch_announcements
    items = fetch_announcements(client, nav_ctx["course_id"])

    if not items:
        click.echo("No announcements found.")
        return

    output_table(
        items,
        [
            ("ID", "id"),
            ("Title", "title"),
            ("Created", "created"),
        ],
        title="Announcements",
        json_flag=json_flag,
    )


def _show_item(target: str, json_flag: bool):
    nav_ctx = require_course()
    cached = nav_ctx.get("last_ls", [])
    if not cached:
        raise click.ClickException(
            "No cached listing. Run 'bb ls' first, then 'bb show <row#>'."
        )

    resolved = resolve_ref(target, cached)
    content_id = resolved["id"]
    course_id = nav_ctx["course_id"]

    cookies = ensure_authenticated()
    client = BBClient(cookies)

    content = client.get(f"/courses/{course_id}/contents/{content_id}")

    output_single(
        content,
        [
            ("Title", "title"),
            ("Type", "contentHandler.id"),
            ("Description", "description"),
            ("Available", "availability.available"),
            ("Created", "created"),
            ("Modified", "modified"),
        ],
        json_flag=json_flag,
    )
