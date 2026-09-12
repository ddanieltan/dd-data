"""Command Line Interface for dd-data."""

import json
from pathlib import Path
from typing import Optional
import typer
from rich.table import Table

from dd_data.core.base import registry
from dd_data.core.git import commit_and_push, write_target_file
from dd_data.core.logger import console, error_console, log_error, log_info, log_success
# Ensure scrapers are registered
import dd_data.scrapers  # noqa: F401

app = typer.Typer(
    name="dd-data",
    help="Centralized Git-Scraping Engine with Pydantic Schema Guards.",
    add_completion=False,
)


@app.command(name="list")
def list_scrapers() -> None:
    """List all registered scrapers and their target repositories."""
    table = Table(title="Registered Git-Scrapers in dd-data")
    table.add_column("Scraper Name", style="bold cyan")
    table.add_column("Target Repository", style="green")
    table.add_column("Target File", style="yellow")
    table.add_column("Description")

    for name, scraper in sorted(registry.all().items()):
        table.add_row(name, scraper.target_repo, scraper.target_path, scraper.description)

    console.print(table)


@app.command(name="validate")
def validate_file(
    scraper_name: str = typer.Argument(..., help="Name of the scraper/schema to test against"),
    file_path: Path = typer.Argument(..., help="Path to JSON file to validate", exists=True),
) -> None:
    """Validate an existing JSON file against a scraper's Pydantic schema guard."""
    scraper = registry.get(scraper_name)
    try:
        raw_json = json.loads(file_path.read_text(encoding="utf-8"))
        scraper.validate_payload(raw_json)
        log_success(f"File '{file_path}' successfully passed '{scraper_name}' schema validation!")
    except Exception as e:
        log_error(f"Validation failed for '{file_path}' against '{scraper_name}': {e}")
        raise typer.Exit(code=1)


@app.command(name="scrape")
def scrape(
    scraper_name: str = typer.Argument(..., help="Name of the scraper to run"),
    target_dir: Optional[Path] = typer.Option(
        None,
        "--target-dir",
        "-d",
        help="Root directory of the checked-out target repository",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output-file",
        "-o",
        help="Optional destination file path (overrides target_dir / target_path)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Fetch and validate only, without committing or pushing",
    ),
    commit: bool = typer.Option(
        True,
        "--commit/--no-commit",
        help="Commit and push changes if git changes exist in target-dir",
    ),
    branch: str = typer.Option(
        "main",
        "--branch",
        "-b",
        help="Git branch to push to",
    ),
) -> None:
    """Run a scraper, validate the schema guard, and update the target repository."""
    try:
        scraper = registry.get(scraper_name)
    except KeyError as e:
        log_error(str(e))
        raise typer.Exit(code=1)

    log_info(f"Starting execution for scraper: [bold]{scraper.name}[/bold]")

    try:
        formatted_content = scraper.execute()
    except Exception as e:
        log_error(f"Scrape failed during fetch or validation: {e}")
        raise typer.Exit(code=1)

    # Dry-run mode
    if dry_run:
        log_success(f"Dry run complete for '{scraper.name}'. Validated output preview:")
        preview_lines = formatted_content.splitlines()[:15]
        console.print("\n".join(preview_lines))
        if len(preview_lines) < len(formatted_content.splitlines()):
            console.print(f"... ({len(formatted_content.splitlines()) - 15} more lines)")
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(formatted_content, encoding="utf-8")
            log_info(f"Wrote dry-run output to {output_file}")
        return

    # Normal execution: require target directory or output file
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(formatted_content, encoding="utf-8")
        log_success(f"Wrote validated data to {output_file}")
        return

    if not target_dir:
        log_error(
            "Neither --target-dir nor --output-file was provided. "
            "Pass --target-dir to update a git repo, --output-file, or --dry-run."
        )
        raise typer.Exit(code=1)

    target_file = write_target_file(target_dir, scraper.target_path, formatted_content)

    if commit:
        log_info(f"Checking for git changes in {target_dir}...")
        try:
            pushed = commit_and_push(
                repo_dir=target_dir,
                rel_path=scraper.target_path,
                branch=branch,
            )
            if pushed:
                log_success(f"Successfully scraped and pushed update for '{scraper.name}'.")
            else:
                log_info(f"Target file {scraper.target_path} is identical to latest commit. Done.")
        except Exception as e:
            log_error(f"Git commit/push failed: {e}")
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
