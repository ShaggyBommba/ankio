from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import click

IMAGE = "ghcr.io/shaggybommba/ankio:latest"
CONTAINER = "ankio"
VOLUME = "ankio-data"
MCP_PORT = 8035
HTMX_PORT = 8034
HOST = "127.0.0.1"
URL = f"http://{HOST}:{MCP_PORT}/mcp"
HTMX_URL = f"http://{HOST}:{HTMX_PORT}"

logger = logging.getLogger(__name__)


def runtime(dry_run: bool) -> None:
    """Create the required volume and boot up the Ankio container."""
    logger.info(
        "Configuring Docker runtime image=%s container=%s volume=%s mcp_port=%s htmx_port=%s dry_run=%s",
        IMAGE,
        CONTAINER,
        VOLUME,
        MCP_PORT,
        HTMX_PORT,
        dry_run,
    )
    click.echo("Configuring Docker runtime...")
    run(["docker", "volume", "create", VOLUME], dry_run)
    run(["docker", "rm", "-f", CONTAINER], dry_run, check=False)
    run(
        [
            "docker",
            "run",
            "-d",
            "--platform",
            "linux/amd64",
            "--name",
            CONTAINER,
            "--restart",
            "unless-stopped",
            "-p",
            f"{HOST}:{HTMX_PORT}:{HTMX_PORT}",
            "-p",
            f"{HOST}:{MCP_PORT}:{MCP_PORT}",
            "-v",
            f"{VOLUME}:/app/data",
            "-e",
            "APP_NAME=ankio",
            "-e",
            "APP_HTMX_HOST=0.0.0.0",
            "-e",
            f"APP_HTMX_PORT={HTMX_PORT}",
            "-e",
            "APP_MCP_HOST=0.0.0.0",
            "-e",
            f"APP_MCP_PORT={MCP_PORT}",
            "-e",
            "APP_DATABASE__PROVIDER=sqlite",
            "-e",
            "APP_DATABASE__DATABASE=data/app",
            IMAGE,
            "app",
        ],
        dry_run,
    )
    click.echo(f"HTMX UI: {HTMX_URL}")
    click.echo(f"MCP endpoint: {URL}")


def skills(skills_dir: Path) -> tuple[Path, ...]:
    """Return bundled skill directories that contain a skill manifest."""
    return tuple(
        sorted(
            (
                path
                for path in skills_dir.iterdir()
                if path.is_dir() and (path / "SKILL.md").is_file()
            ),
            key=lambda path: path.name,
        )
    )


def rmruntime(dry_run: bool) -> None:
    """Remove Docker runtime resources created by the installer."""
    logger.info(
        "Removing Docker runtime image=%s container=%s volume=%s dry_run=%s",
        IMAGE,
        CONTAINER,
        VOLUME,
        dry_run,
    )
    click.echo("Removing Docker runtime...")
    run(["docker", "rm", "-f", CONTAINER], dry_run, check=False)
    run(["docker", "volume", "rm", VOLUME], dry_run, check=False)
    run(["docker", "image", "rm", IMAGE], dry_run, check=False)


def bundle() -> Path:
    """Locate the path to the assistant bundle."""
    local = Path.cwd() / "assistant"
    if local.exists():
        logger.debug("Using local assistant bundle path=%s", local)
        return local

    installed = Path(sys.prefix) / "share" / "ankio" / "assistant"
    logger.debug("Using installed assistant bundle path=%s", installed)
    return installed


def run(cmd: list[str], dry_run: bool, check: bool = True) -> None:
    """Wrapper to execute shell commands with logging and dry-run support."""
    command = " ".join(cmd)
    logger.info("Running command cmd=%s dry_run=%s check=%s", command, dry_run, check)
    click.echo("+ " + " ".join(cmd))
    if dry_run:
        logger.info("Skipped command because dry-run is enabled cmd=%s", command)
        return

    result = subprocess.run(cmd, check=False)
    logger.info(
        "Command finished cmd=%s returncode=%s check=%s",
        command,
        result.returncode,
        check,
    )
    if check and result.returncode != 0:
        logger.error("Command failed cmd=%s returncode=%s", command, result.returncode)
        raise click.ClickException(
            f"Command failed with exit status {result.returncode}: {command}"
        )
