import click

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.formatting import output_table


@click.command()
@click.argument("course_id")
@click.pass_context
def grades(ctx, course_id):
    """Show grades for a course."""
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    # Get current user
    user = client.get("/users/me")
    user_id = user["id"]

    # Get grade columns
    columns = client.get_paginated(f"/courses/{course_id}/gradebook/columns")
    if not columns:
        click.echo("No grade columns found.")
        return

    # Fetch the user's grade for each column
    grade_rows = []
    for col in columns:
        col_id = col["id"]
        try:
            grade = client.get(
                f"/courses/{course_id}/gradebook/columns/{col_id}/users/{user_id}"
            )
        except click.ClickException:
            grade = {}
        grade_rows.append({
            "column_id": col_id,
            "name": col.get("name", ""),
            "score": grade.get("score"),
            "text": grade.get("text", ""),
            "notes": grade.get("notes", ""),
        })

    output_table(
        grade_rows,
        [
            ("Column", "name"),
            ("Score", "score"),
            ("Text", "text"),
            ("Notes", "notes"),
        ],
        title="Grades",
        json_flag=ctx.obj["json"],
    )
