from __future__ import annotations

import logging
import shutil
from pathlib import Path

import click

from presentation.cli.common import URL, run, skills

NAME = "codex"
REMOVE = ["codex", "mcp", "remove", "ankio"]
ADD = ["codex", "mcp", "add", "ankio", "--url", URL]

logger = logging.getLogger(__name__)


def install(source: Path, dry_run: bool) -> None:
    """Copy a skill directory to Codex."""
    dest = Path.home() / ".codex" / "skills" / source.name
    logger.info(
        "Installing skill target=%s source=%s destination=%s dry_run=%s",
        NAME,
        source,
        dest,
        dry_run,
    )
    click.echo(f"Installing {NAME} skill to {dest}")

    if dry_run:
        return

    if dest.exists():
        logger.info("Removing existing skill directory target=%s path=%s", NAME, dest)
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest)
    logger.info("Skill directory installed target=%s path=%s", NAME, dest)


def remove(skill: str, dry_run: bool) -> None:
    """Remove a copied Codex skill directory."""
    dest = Path.home() / ".codex" / "skills" / skill
    logger.info("Removing skill target=%s path=%s dry_run=%s", NAME, dest, dry_run)
    click.echo(f"Removing {NAME} skill from {dest}")

    if dry_run:
        logger.info("Skipped skill removal because dry-run is enabled path=%s", dest)
        return

    if dest.exists():
        shutil.rmtree(dest)
        logger.info("Skill directory removed target=%s path=%s", NAME, dest)
    else:
        logger.info("Skill directory already absent target=%s path=%s", NAME, dest)


def register(dry_run: bool) -> None:
    """Register the Codex MCP server."""
    logger.info(
        "Registering MCP server target=%s url=%s dry_run=%s", NAME, URL, dry_run
    )
    click.echo(f"Registering {NAME} MCP server at {URL}")

    run(REMOVE, dry_run, check=False)
    run(ADD, dry_run)


def unregister(dry_run: bool) -> None:
    """Remove the Codex MCP server registration."""
    logger.info("Unregistering MCP server target=%s dry_run=%s", NAME, dry_run)
    click.echo(f"Removing {NAME} MCP server registration")
    run(REMOVE, dry_run, check=False)


def setup(path: Path, dry_run: bool) -> None:
    """Install Codex skills and MCP config."""
    for source in skills(path / "skills"):
        install(source, dry_run)
    register(dry_run)


def teardown(path: Path, dry_run: bool) -> None:
    """Remove Codex skills and MCP config."""
    unregister(dry_run)
    for source in skills(path / "skills"):
        remove(source.name, dry_run)
