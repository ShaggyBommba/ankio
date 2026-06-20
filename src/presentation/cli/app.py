from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import click

IMAGE = "ghcr.io/shaggybommba/ankio:latest"
CONTAINER = "ankio"
VOLUME = "ankio-data"
PORT = 8004
URL = f"http://localhost:{PORT}/mcp"

COMMANDS = {
    "claude": {
        "remove": ["claude", "mcp", "remove","--scope", "user", "ankio"],
        "add": ["claude", "mcp", "add", "--transport", "http", "--scope", "user", "ankio", URL],
    },
    "codex": {
        "remove": ["codex", "mcp", "remove", "ankio"],
        "add": ["codex", "mcp", "add", "ankio", "--url", URL],
    },
}


def boot(dry_run: bool) -> None:
    """Create the required volume and boot up the Ankio container."""
    click.echo("Configuring Docker runtime...")
    run(["docker", "volume", "create", VOLUME], dry_run)
    run(["docker", "rm", "-f", CONTAINER], dry_run, check=False)
    run(
        [
            "docker", "run", "-d",
            "--name", CONTAINER,
            "--restart", "unless-stopped",
            "-p", f"{PORT}:8004",
            "-v", f"{VOLUME}:/app/data",
            "-e", "APP_NAME=ankio",
            "-e", "APP_MCP_HOST=0.0.0.0",
            "-e", "APP_MCP_PORT=8004",
            "-e", "APP_DATABASE__PROVIDER=sqlite",
            "-e", "APP_DATABASE__DATABASE=data/app",
            IMAGE,
        ],
        dry_run,
    )


def copy(target: str, source: Path, dry_run: bool) -> None:
    """Copy skill directories to the target application's folder."""
    dest = Path.home() / f".{target}" / "skills" / "ankio"
    click.echo(f"Installing {target} skill to {dest}")

    if not dry_run:
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)


def register(target: str, dry_run: bool) -> None:
    """Register the MCP server with the specified target application."""
    click.echo(f"Registering {target} MCP server at {URL}")
    cmds = COMMANDS[target]
    
    run(cmds["remove"], dry_run, check=False)
    run(cmds["add"], dry_run)


def bundle() -> Path:
    """Locate the path to the assistant bundle."""
    local = Path.cwd() / "assistant"
    if local.exists():
        return local
    return Path(sys.prefix) / "share" / "ankio" / "assistant"


def run(cmd: list[str], dry_run: bool, check: bool = True) -> None:
    """Wrapper to execute shell commands with logging and dry-run support."""
    click.echo("+ " + " ".join(cmd))
    if dry_run:
        return

    result = subprocess.run(cmd, check=False)
    if check and result.returncode != 0:
        raise click.ClickException(f"Command failed: {' '.join(cmd)}")


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
def main(target: str, dry_run: bool) -> None:
    """Install Ankio's Docker runtime, skill, and MCP config."""
    path = bundle()
    source = path / "skills" / "ankio"
    targets = ("claude", "codex") if target == "all" else (target,)

    click.echo(f"Starting Ankio installation from {path}")

    boot(dry_run)

    for name in targets:
        copy(name, source, dry_run)
        register(name, dry_run)

    click.echo("Ankio install complete.")


if __name__ == "__main__":
    main()