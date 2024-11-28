import click


@click.group(name="github", help="Scrape source https://github.com")
def cli():
    pass


from .topic import run as topic

cli.add_command(topic)
