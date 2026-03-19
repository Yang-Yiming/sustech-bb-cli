import click

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.context import load_context
from bb_cli.formatting import output_table


def fetch_announcements(client: BBClient, course_id: str | None = None) -> list[dict]:
    """Fetch announcements, optionally filtered to a course. Reusable helper."""
    if course_id:
        return client.get_paginated(f"/courses/{course_id}/announcements")
    return client.get_paginated("/announcements")


@click.command()
@click.option("--course", "course_id", default=None, help="Filter by course ID.")
@click.pass_context
def announcements(ctx, course_id):
    """List announcements (system-wide or per-course).

    Defaults to the current course context if --course is not provided.
    """
    # Fall back to context course if no explicit --course
    if course_id is None:
        nav_ctx = load_context()
        course_id = nav_ctx.get("course_id")  # may still be None → system-wide

    cookies = ensure_authenticated()
    client = BBClient(cookies)

    items = fetch_announcements(client, course_id)

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
        json_flag=ctx.obj["json"],
    )
