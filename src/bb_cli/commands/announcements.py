import click

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.formatting import output_table


@click.command()
@click.option("--course", "course_id", default=None, help="Filter by course ID.")
@click.pass_context
def announcements(ctx, course_id):
    """List announcements (system-wide or per-course)."""
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    if course_id:
        items = client.get_paginated(f"/courses/{course_id}/announcements")
    else:
        items = client.get_paginated("/announcements")

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
