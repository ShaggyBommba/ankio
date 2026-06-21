from __future__ import annotations

import logging

import click

from infrastructure.config import get_settings
from infrastructure.observability.logger import LoggingService
from presentation.cli import claude, codex
from presentation.cli.common import bundle, rmruntime, runtime

TARGETS = {
    "claude": claude,
    "codex": codex,
}

logger = logging.getLogger(__name__)


def names(target: str) -> tuple[str, ...]:
    """Return the target names selected by a CLI option."""
    if target == "all":
        return ("claude", "codex")
    return (target,)


@click.command()
@click.option(
    "--target",
    type=click.Choice(["claude", "codex", "all"]),
    default="all",
    show_default=True,
    help="Harness to configure.",
)
@click.option(
    "--dry-run", is_flag=True, help="Print commands without changing anything."
)
def setup(target: str, dry_run: bool) -> None:
    """Set up Ankio's Docker runtime, skill, and MCP config."""
    settings = get_settings()
    LoggingService.setup(settings.logging)

    try:
        path = bundle()
        selected = names(target)

        logger.info(
            "Starting Ankio setup target=%s dry_run=%s bundle=%s",
            target,
            dry_run,
            path,
        )
        click.echo(f"Starting Ankio setup from {path}")

        runtime(dry_run)

        for name in selected:
            TARGETS[name].setup(path, dry_run)

        logger.info("Ankio setup complete target=%s dry_run=%s", target, dry_run)
        click.echo("Ankio setup complete.")
    except click.ClickException:
        logger.error("Ankio setup failed target=%s dry_run=%s", target, dry_run)
        raise
    except Exception:
        logger.exception("Ankio setup failed target=%s dry_run=%s", target, dry_run)
        raise


@click.command()
@click.option(
    "--target",
    type=click.Choice(["claude", "codex", "all"]),
    default="all",
    show_default=True,
    help="Harness to remove configuration from.",
)
@click.option(
    "--dry-run", is_flag=True, help="Print commands without changing anything."
)
def teardown(target: str, dry_run: bool) -> None:
    """Remove Ankio's Docker runtime, skill, and MCP config."""
    settings = get_settings()
    LoggingService.setup(settings.logging)

    try:
        path = bundle()
        selected = names(target)

        logger.info("Starting Ankio teardown target=%s dry_run=%s", target, dry_run)
        click.echo("Starting Ankio teardown")

        for name in selected:
            TARGETS[name].teardown(path, dry_run)

        rmruntime(dry_run)

        logger.info("Ankio teardown complete target=%s dry_run=%s", target, dry_run)
        click.echo("Ankio teardown complete.")
    except click.ClickException:
        logger.error("Ankio teardown failed target=%s dry_run=%s", target, dry_run)
        raise
    except Exception:
        logger.exception("Ankio teardown failed target=%s dry_run=%s", target, dry_run)
        raise


if __name__ == "__main__":
    setup()
