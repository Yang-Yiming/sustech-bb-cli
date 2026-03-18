from pathlib import Path

import click
from rich.progress import Progress

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.config import BB_BASE_URL


@click.command()
@click.argument("course_id")
@click.argument("content_id")
@click.option("-o", "--output-dir", default=".", help="Directory to save files to.")
@click.pass_context
def download(ctx, course_id, content_id, output_dir):
    """Download attachments for a content item."""
    cookies = ensure_authenticated()
    client = BBClient(cookies)

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
        task = progress.add_task("Downloading…", total=len(attachments))
        for att in attachments:
            filename = att.get("fileName", "unknown")
            att_id = att["id"]
            url = f"/courses/{course_id}/contents/{content_id}/attachments/{att_id}/download"
            dest = dest_dir / filename
            progress.update(task, description=f"Downloading {filename}")
            client.download_file(url, dest)
            progress.advance(task)

    click.echo(f"Downloaded {len(attachments)} file(s) to {dest_dir.resolve()}")
