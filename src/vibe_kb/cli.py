"""CLI entry point for kb command."""
import click


@click.group()
@click.version_option()
def cli():
    """vibe-kb: LLM-powered knowledge base system."""
    pass


if __name__ == "__main__":
    cli()
