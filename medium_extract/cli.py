# medium-extractor/medium_extract/cli.py

import typer
import json
from rich import print # Use rich print for better formatting

from .scraper import extract_medium_headers

app = typer.Typer(help="Extracts H2/H3 headers and their IDs from Medium articles.")

@app.command()
def main(
    url: str = typer.Argument(..., help="The URL of the Medium article to scrape."),
    timeout: int = typer.Option(20, "--timeout", "-t", help="Seconds to wait for page elements to load."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output results as JSON.")
):
    """
    Scrapes a Medium article URL and prints its H2/H3 headers and IDs.
    """
    print(f"[bold blue]Starting extraction for:[/bold blue] {url}")

    headers = extract_medium_headers(url, timeout)

    if headers is None:
        print("[bold red]Error:[/bold red] Extraction failed. Check logs for details.")
        raise typer.Exit(code=1)

    if not headers:
        print("[yellow]No H2 or H3 headers found within the main article content.[/yellow]")
        raise typer.Exit()

    print(f"\n[bold green]Extracted Headers ({len(headers)}):[/bold green]")

    if output_json:
        print(json.dumps(headers, indent=2))
    else:
        for header in headers:
            id_str = f" (ID: [cyan]{header['id']}[/cyan])" if header['id'] else ""
            print(f"- [bold]{header['tag'].upper()}[/bold]: {header['text']}{id_str}")

    print("\n[bold green]Extraction complete.[/bold green]")


if __name__ == "__main__":
    app() # Allows running `python -m medium_extract.cli <url>`
