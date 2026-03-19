import click

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.formatting import output_table


def fetch_courses(client: BBClient, term: str | None = None) -> list[dict]:
    """Fetch enrolled courses, optionally filtered by term. Reusable helper."""
    user = client.get("/users/me")
    user_id = user["id"]

    memberships = client.get_paginated(f"/users/{user_id}/courses")

    course_list = []
    for m in memberships:
        course_id = m.get("courseId")
        if not course_id:
            continue
        try:
            course = client.get(f"/courses/{course_id}")
        except click.ClickException:
            continue
        course["_role"] = m.get("courseRoleId", "")
        course_list.append(course)

    if term:
        course_list = [
            c for c in course_list
            if term.lower() in (c.get("termId") or "").lower()
            or term.lower() in (c.get("name") or "").lower()
        ]

    return course_list


@click.command()
@click.option("--term", default=None, help="Filter by term name (substring match).")
@click.pass_context
def courses(ctx, term):
    """List enrolled courses."""
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    course_list = fetch_courses(client, term)

    if not course_list:
        click.echo("No courses found.")
        return

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
        json_flag=ctx.obj["json"],
    )
