from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

import click

from infrastructure.config import get_settings
from infrastructure.observability.logger import LoggingService

IMAGE = "ghcr.io/shaggybommba/ankio:latest"
CONTAINER = "ankio"
VOLUME = "ankio-data"
MCP_PORT = 8035
HTMX_PORT = 8034
HOST = "127.0.0.1"
URL = f"http://{HOST}:{MCP_PORT}/mcp"
HTMX_URL = f"http://{HOST}:{HTMX_PORT}"

logger = logging.getLogger(__name__)

COMMANDS = {
    "claude": {
        "remove": ["claude", "mcp", "remove", "--scope", "user", "ankio"],
        "add": [
            "claude",
            "mcp",
            "add",
            "--transport",
            "http",
            "--scope",
            "user",
            "ankio",
            URL,
        ],
    },
    "codex": {
        "remove": ["codex", "mcp", "remove", "ankio"],
        "add": ["codex", "mcp", "add", "ankio", "--url", URL],
    },
}


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


def install(target: str, source: Path, dry_run: bool) -> None:
    """Copy skill directories to the target application's folder."""
    dest = Path.home() / f".{target}" / "skills" / source.name
    logger.info(
        "Installing skill target=%s source=%s destination=%s dry_run=%s",
        target,
        source,
        dest,
        dry_run,
    )
    click.echo(f"Installing {target} skill to {dest}")

    if not dry_run:
        if dest.exists():
            logger.info(
                "Removing existing skill directory target=%s path=%s", target, dest
            )
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)
        logger.info("Skill directory installed target=%s path=%s", target, dest)


def register(target: str, dry_run: bool) -> None:
    """Register the MCP server with the specified target application."""
    logger.info(
        "Registering MCP server target=%s url=%s dry_run=%s", target, URL, dry_run
    )
    click.echo(f"Registering {target} MCP server at {URL}")
    cmds = COMMANDS[target]

    run(cmds["remove"], dry_run, check=False)
    run(cmds["add"], dry_run)


def unregister(target: str, dry_run: bool) -> None:
    """Remove the MCP server registration for the specified target application."""
    logger.info("Unregistering MCP server target=%s dry_run=%s", target, dry_run)
    click.echo(f"Removing {target} MCP server registration")
    run(COMMANDS[target]["remove"], dry_run, check=False)


def rmskill(target: str, skill_name: str, dry_run: bool) -> None:
    """Remove the copied skill directory from the target application's folder."""
    dest = Path.home() / f".{target}" / "skills" / skill_name
    logger.info("Removing skill target=%s path=%s dry_run=%s", target, dest, dry_run)
    click.echo(f"Removing {target} skill from {dest}")

    if dry_run:
        logger.info("Skipped skill removal because dry-run is enabled path=%s", dest)
        return

    if dest.exists():
        shutil.rmtree(dest)
        logger.info("Skill directory removed target=%s path=%s", target, dest)
    else:
        logger.info("Skill directory already absent target=%s path=%s", target, dest)


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
        sources = skills(path / "skills")
        if target == "all":
            targets = ("claude", "codex")
        else:
            targets = (target,)

        logger.info(
            "Starting Ankio setup target=%s dry_run=%s bundle=%s",
            target,
            dry_run,
            path,
        )
        click.echo(f"Starting Ankio setup from {path}")

        runtime(dry_run)

        for name in targets:
            for source in sources:
                install(name, source, dry_run)
            register(name, dry_run)

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
        skill_names = tuple(source.name for source in skills(path / "skills"))
        if target == "all":
            targets = ("claude", "codex")
        else:
            targets = (target,)

        logger.info("Starting Ankio teardown target=%s dry_run=%s", target, dry_run)
        click.echo("Starting Ankio teardown")

        for name in targets:
            unregister(name, dry_run)
            for skill_name in skill_names:
                rmskill(name, skill_name, dry_run)

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
