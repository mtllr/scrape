import click
from .topic import run as topic


@click.group(name="github", help="Scrape source https://github.com")
def cli():
    pass


cli.add_command(topic)
