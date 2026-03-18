import click

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.formatting import output_table


@click.command()
@click.argument("course_id")
@click.option("--folder", "folder_id", default=None, help="Show contents of a specific folder.")
@click.pass_context
def contents(ctx, course_id, folder_id):
    """List course contents (top-level folders or a specific folder's children)."""
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    if folder_id:
        items = client.get_paginated(f"/courses/{course_id}/contents/{folder_id}/children")
    else:
        items = client.get_paginated(f"/courses/{course_id}/contents")

    if not items:
        click.echo("No contents found.")
        return

    output_table(
        items,
        [
            ("ID", "id"),
            ("Title", "title"),
            ("Type", "contentHandler.id"),
            ("Available", "availability.available"),
        ],
        title="Course Contents",
        json_flag=ctx.obj["json"],
    )
