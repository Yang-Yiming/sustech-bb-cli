from pathlib import Path

import click
from rich.progress import Progress

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.context import load_context, require_course, resolve_ref


@click.command()
@click.argument("target")
@click.argument("course_id", default=None, required=False)
@click.option("-o", "--output-dir", default=".", help="Directory to save files to.")
@click.pass_context
def download(ctx, target, course_id, output_dir):
    """Download attachments for a content item.

    TARGET can be a row number from the last 'bb ls', a name, or a Blackboard content ID.
    COURSE_ID is optional if you have a course context set via 'bb cd'.

    \b
    Examples:
      bb download 3              # download item #3 from last bb ls
      bb download "Week 1"       # download by name
      bb download _12345_1 _67890_1  # explicit content + course IDs
    """
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    # Resolve course_id
    if course_id is None:
        nav_ctx = require_course()
        course_id = nav_ctx["course_id"]
    else:
        nav_ctx = load_context()

    # Try to resolve target via cached last_ls
    content_id = _resolve_target(target, nav_ctx)

    # Get content item details
    content = client.get(f"/courses/{course_id}/contents/{content_id}")
    title = content.get("title", content_id)

    # Get attachments
    try:
        attachments = client.get_paginated(
            f"/courses/{course_id}/contents/{content_id}/attachments"
        )
    except click.ClickException:
        click.echo(f"No attachments found for '{title}'.")
        return

    if not attachments:
        click.echo(f"No attachments found for '{title}'.")
        return

    dest_dir = Path(output_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    with Progress() as progress:
        task = progress.add_task("Downloading...", total=len(attachments))
        for att in attachments:
            filename = att.get("fileName", "unknown")
            att_id = att["id"]
            url = f"/courses/{course_id}/contents/{content_id}/attachments/{att_id}/download"
            dest = dest_dir / filename
            progress.update(task, description=f"Downloading {filename}")
            client.download_file(url, dest)
            progress.advance(task)

    click.echo(f"Downloaded {len(attachments)} file(s) to {dest_dir.resolve()}")


def _resolve_target(target: str, nav_ctx: dict) -> str:
    """Resolve a target reference to a content ID."""
    cached = nav_ctx.get("last_ls", [])
    if cached:
        try:
            resolved = resolve_ref(target, cached)
            return resolved["id"]
        except click.ClickException:
            pass

    # If it looks like a BB ID (starts with _ and ends with _1), use directly
    if target.startswith("_") and "_" in target[1:]:
        return target

    raise click.ClickException(
        f"Cannot resolve '{target}'. Run 'bb ls' first, then use a row number or name."
    )
