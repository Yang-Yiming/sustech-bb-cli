import click

from bb_cli.auth import ensure_authenticated
from bb_cli.client import BBClient
from bb_cli.formatting import extract, output_table

CONTENT_TYPE_NAMES = {
    "resource/x-bb-folder": "Folder",
    "resource/x-bb-file": "File",
    "resource/x-bb-document": "Document",
    "resource/x-bb-assignment": "Assignment",
    "resource/x-bb-blankpage": "Page",
    "resource/x-bb-externallink": "Link",
    "resource/x-bb-toollink": "Tool Link",
}


def _friendly_type(item: dict) -> str:
    raw = extract(item, "contentHandler.id") or ""
    return CONTENT_TYPE_NAMES.get(raw, raw)


@click.command()
@click.argument("course_id")
@click.option("--folder", "folder_id", default=None, help="Show contents of a specific folder.")
@click.option("--all", "show_all", is_flag=True, default=False, help="Include unavailable items.")
@click.pass_context
def contents(ctx, course_id, folder_id, show_all):
    """List course contents (top-level folders or a specific folder's children)."""
    cookies = ensure_authenticated()
    client = BBClient(cookies)

    if folder_id:
        items = client.get_paginated(f"/courses/{course_id}/contents/{folder_id}/children")
    else:
        items = client.get_paginated(f"/courses/{course_id}/contents")

    if not show_all:
        items = [i for i in items if extract(i, "availability.available") == "Yes"]

    if not items:
        click.echo("No contents found.")
        return

    json_flag = ctx.obj["json"]

    if json_flag:
        # Add typeName to each item for JSON output
        for item in items:
            item["typeName"] = _friendly_type(item)
        output_table(
            items,
            [
                ("ID", "id"),
                ("Title", "title"),
                ("Type", "contentHandler.id"),
                ("typeName", "typeName"),
                ("Available", "availability.available"),
            ],
            title="Course Contents",
            json_flag=True,
        )
    else:
        # Build table rows with friendly type names
        has_folders = any(extract(i, "contentHandler.id") == "resource/x-bb-folder" for i in items)

        # Inject friendly type for table display
        for item in items:
            item["_typeName"] = _friendly_type(item)

        output_table(
            items,
            [
                ("ID", "id"),
                ("Title", "title"),
                ("Type", "_typeName"),
                ("Available", "availability.available"),
            ],
            title="Course Contents",
            json_flag=False,
        )

        if has_folders and not folder_id:
            click.echo("\nTip: Use --folder <ID> to browse a subfolder")
