"""Console logging and styling for dd-data."""

from rich.console import Console

console = Console()
error_console = Console(stderr=True)


def log_info(msg: str) -> None:
    console.print(f"[bold cyan]INFO[/bold cyan]  {msg}")


def log_success(msg: str) -> None:
    console.print(f"[bold green]SUCCESS[/bold green] {msg}")


def log_warning(msg: str) -> None:
    console.print(f"[bold yellow]WARN[/bold yellow]  {msg}")


def log_error(msg: str) -> None:
    error_console.print(f"[bold red]ERROR[/bold red] {msg}")
