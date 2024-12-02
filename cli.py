import click
from core import LazyGroup


include_list = ["data", "github"]


@click.group(
    cls=LazyGroup,
    lazy_subcommands={key: f"sources.{key}.cli" for key in include_list},
    help="scrape main CLI command",
)
def cli(): ...
