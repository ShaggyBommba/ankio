from __future__ import annotations

import logging
import shutil
from pathlib import Path

import click

from presentation.cli.common import run, skills

NAME = "claude"
MARKETPLACE = "ankio"
PLUGIN = f"ankio@{MARKETPLACE}"
REMOVE = ["claude", "mcp", "remove", "--scope", "user", "ankio"]

logger = logging.getLogger(__name__)


def marketplace(path: Path) -> Path:
    """Return the root that contains the Claude plugin marketplace."""
    root = path.parent
    required = (
        root / ".claude-plugin" / "marketplace.json",
        path / ".claude-plugin" / "plugin.json",
        path / ".mcp.json",
    )

    missing = [entry for entry in required if not entry.is_file()]
    if missing:
        joined = ", ".join(str(entry) for entry in missing)
        raise click.ClickException(f"Missing Claude plugin metadata: {joined}")

    return root


def install(path: Path, dry_run: bool) -> None:
    """Install the Claude Code plugin through a local marketplace."""
    root = marketplace(path)
    logger.info(
        "Installing Claude plugin marketplace=%s plugin=%s source=%s dry_run=%s",
        MARKETPLACE,
        PLUGIN,
        root,
        dry_run,
    )
    click.echo(f"Installing Claude plugin {PLUGIN} from {root}")

    run(
        ["claude", "plugin", "uninstall", "--scope", "user", PLUGIN],
        dry_run,
        check=False,
    )
    run(
        ["claude", "plugin", "marketplace", "remove", MARKETPLACE],
        dry_run,
        check=False,
    )
    run(
        ["claude", "plugin", "marketplace", "add", "--scope", "user", str(root)],
        dry_run,
    )
    run(["claude", "plugin", "install", "--scope", "user", PLUGIN], dry_run)


def uninstall(dry_run: bool) -> None:
    """Remove the Claude Code plugin and local marketplace."""
    logger.info(
        "Uninstalling Claude plugin marketplace=%s plugin=%s dry_run=%s",
        MARKETPLACE,
        PLUGIN,
        dry_run,
    )
    click.echo(f"Removing Claude plugin {PLUGIN}")

    run(
        ["claude", "plugin", "uninstall", "--scope", "user", PLUGIN],
        dry_run,
        check=False,
    )
    run(
        ["claude", "plugin", "marketplace", "remove", MARKETPLACE],
        dry_run,
        check=False,
    )


def unregister(dry_run: bool) -> None:
    """Remove the legacy direct Claude MCP registration."""
    logger.info("Unregistering MCP server target=%s dry_run=%s", NAME, dry_run)
    click.echo(f"Removing {NAME} MCP server registration")
    run(REMOVE, dry_run, check=False)


def remove(skill: str, dry_run: bool) -> None:
    """Remove a legacy loose Claude skill directory."""
    dest = Path.home() / ".claude" / "skills" / skill
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


def setup(path: Path, dry_run: bool) -> None:
    """Install Claude plugin config and remove legacy loose config."""
    install(path, dry_run)
    unregister(dry_run)
    for source in skills(path / "skills"):
        remove(source.name, dry_run)


def teardown(path: Path, dry_run: bool) -> None:
    """Remove Claude plugin config and legacy loose config."""
    uninstall(dry_run)
    unregister(dry_run)
    for source in skills(path / "skills"):
        remove(source.name, dry_run)
