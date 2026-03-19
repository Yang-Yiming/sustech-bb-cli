import click

from bb_cli.commands.login import login
from bb_cli.commands.courses import courses
from bb_cli.commands.announcements import announcements
from bb_cli.commands.contents import ls
from bb_cli.commands.download import download
from bb_cli.commands.grades import grades


@click.group()
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON instead of a table.")
@click.pass_context
def cli(ctx, json_flag):
    """SUSTech Blackboard CLI."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_flag


cli.add_command(login)
cli.add_command(courses)
cli.add_command(announcements)
cli.add_command(ls)
cli.add_command(ls, name="contents")  # backward-compat alias
cli.add_command(download)
cli.add_command(grades)
