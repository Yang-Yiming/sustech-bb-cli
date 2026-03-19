import click

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.context import require_course
from bb_cli.formatting import output_table


def fetch_grades(client: BBClient, course_id: str) -> list[dict]:
    """Fetch grades for a course. Reusable helper."""
    user = client.get("/users/me")
    user_id = user["id"]

    columns = client.get_paginated(f"/courses/{course_id}/gradebook/columns")
    if not columns:
        return []

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

    return grade_rows


@click.command()
@click.argument("course_id", default=None, required=False)
@click.pass_context
def grades(ctx, course_id):
    """Show grades for a course.

    Uses the current course context if COURSE_ID is not provided.
    """
    if course_id is None:
        nav_ctx = require_course()
        course_id = nav_ctx["course_id"]

    cookies = ensure_authenticated()
    client = BBClient(cookies)

    grade_rows = fetch_grades(client, course_id)

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
        json_flag=ctx.obj["json"],
    )
