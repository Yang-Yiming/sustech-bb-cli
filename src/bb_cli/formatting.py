from __future__ import annotations

import json as _json
from typing import Any, Sequence

import click
from rich.console import Console
from rich.table import Table


console = Console()


def extract(obj: dict, dotted_path: str) -> Any:
    """Extract a nested value via dotted key path (e.g. 'availability.available')."""
    val: Any = obj
    for key in dotted_path.split("."):
        if isinstance(val, dict):
            val = val.get(key)
        else:
            return None
    return val


def output_table(
    data: Sequence[dict],
    columns: list[tuple[str, str]],  # (header, dotted_path)
    title: str,
    json_flag: bool,
) -> None:
    """Print a list of records as a Rich table or JSON."""
    if json_flag:
        rows = [{header: extract(row, path) for header, path in columns} for row in data]
        click.echo(_json.dumps(rows, indent=2, ensure_ascii=False))
        return

    table = Table(title=title, show_lines=True)
    for header, _ in columns:
        table.add_column(header)
    for row in data:
        table.add_row(*(str(extract(row, path) or "") for _, path in columns))
    console.print(table)


def output_single(
    data: dict,
    fields: list[tuple[str, str]],  # (label, dotted_path)
    json_flag: bool,
) -> None:
    """Print a single record."""
    if json_flag:
        out = {label: extract(data, path) for label, path in fields}
        click.echo(_json.dumps(out, indent=2, ensure_ascii=False))
        return

    for label, path in fields:
        val = extract(data, path)
        console.print(f"[bold]{label}:[/bold] {val or ''}")
