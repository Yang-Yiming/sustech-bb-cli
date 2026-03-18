import click

from bb_cli.auth import get_credentials, cas_login, save_cookies
from bb_cli.client import BBClient
from bb_cli.formatting import output_single


@click.command()
@click.pass_context
def login(ctx):
    """Force a fresh CAS login and display user info."""
    sid, password = get_credentials()
    cookies = cas_login(sid, password)
    save_cookies(cookies)
    click.echo("Login successful — cookies saved.")

    client = BBClient(cookies)
    user = client.get("/users/me")
    output_single(
        user,
        [
            ("User ID", "id"),
            ("Username", "userName"),
            ("Name", "name.given"),
            ("Family Name", "name.family"),
            ("Email", "contact.email"),
        ],
        json_flag=ctx.obj["json"],
    )
