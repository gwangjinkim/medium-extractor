# medium-extractor/medium_extract/cli.py

import typer
import json
import logging # Add logging import
import html # Import html module for escaping
from pathlib import Path # To handle file paths
from rich import print as rich_print # Use rich print for better formatting

from .scraper import extract_medium_headers

app = typer.Typer(help="Extracts H2/H3 headers and their IDs from Medium articles.")

# Setup basic logging for the CLI part too
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_html_toc(headers: list, original_url: str, filename: Path):
    """Generates an HTML file with linked headers."""
    logging.info(f"Generating HTML ToC for {len(headers)} headers...")

    # Filter out headers that don't have an ID, as they can't be linked
    linkable_headers = [h for h in headers if h.get('id')]
    if len(linkable_headers) != len(headers):
        logging.warning(f"Filtered out {len(headers) - len(linkable_headers)} headers without IDs.")

    if not linkable_headers:
        logging.error("No linkable headers (headers with IDs) found.")
        rich_print(f"[bold red]Error:[/bold red] No headers with IDs found to create links.")
        return False # Indicate failure

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Medium Article ToC Links</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; padding: 20px; }}
        h1 {{ border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
        ul {{ list-style: none; padding-left: 0; }}
        li {{ margin-bottom: 10px; }}
        a {{ text-decoration: none; color: #0d6efd; }}
        a:hover {{ text-decoration: underline; }}
        .h2 {{ padding-left: 0; font-weight: bold; }}
        .h3 {{ padding-left: 20px; }} /* Indent H3 */
    </style>
</head>
<body>
    <h1>Table of Contents Links</h1>
    <p>Generated from: <a href="{html.escape(original_url)}">{html.escape(original_url)}</a></p>
    <ul>
"""
    # --- Build list items ---
    for header in linkable_headers:
        header_id = header['id']
        header_text = header['text']
        # Escape header text to prevent HTML injection issues if text contains < or >
        safe_header_text = html.escape(header_text)
        link_url = f"{original_url.split('?')[0]}#{header_id}" # Use URL without query params for cleaner link
        # Use tag name to apply different styles/indentation
        css_class = header['tag'] # e.g., 'h2' or 'h3'
        html_content += f'        <li class="{css_class}"><a href="{html.escape(link_url)}">{safe_header_text}</a></li>\n'

    # --- Close tags ---
    html_content += """    </ul>
</body>
</html>
"""
    # --- Write to file ---
    try:
        filename.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"HTML file successfully saved to: {filename}")
        return True # Indicate success
    except IOError as e:
        logging.error(f"Failed to write HTML file {filename}: {e}")
        rich_print(f"[bold red]Error:[/bold red] Could not write to file {filename}.")
        return False # Indicate failure


@app.command()
def main(
    url: str = typer.Argument(..., help="The URL of the Medium article to scrape."),
    timeout: int = typer.Option(20, "--timeout", "-t", help="Seconds to wait for page elements to load."),
    output_html: Optional[Path] = typer.Option(None, "--output-html", "-o", help="Path to save the output as an HTML file.", writable=True, dir_okay=False),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output results as raw JSON (overrides HTML output).")
):
    """
    Scrapes a Medium article URL and prints its H2/H3 headers and IDs,
    or generates an HTML file with linked headers.
    """
    rich_print(f"[bold blue]Starting extraction for:[/bold blue] {url}")

    headers = extract_medium_headers(url, timeout)

    if headers is None:
        rich_print("[bold red]Error:[/bold red] Extraction failed. Check logs for details.")
        raise typer.Exit(code=1)

    if not headers:
        rich_print("[yellow]No H2 or H3 headers found within the main article content.[/yellow]")
        raise typer.Exit()

    rich_print(f"\n[bold green]Extraction found {len(headers)} headers.[/bold green]")

    # --- Output Logic ---
    if output_json:
        # JSON output takes precedence if both json and html flags are set
        if output_html:
             logging.warning("--json flag provided, ignoring --output-html flag.")
        rich_print("[bold blue]Outputting as JSON:[/bold blue]")
        print(json.dumps(headers, indent=2)) # Use standard print for clean JSON

    elif output_html:
        rich_print(f"[bold blue]Generating HTML output file:[/bold blue] {output_html}")
        success = generate_html_toc(headers, url, output_html)
        if not success:
             raise typer.Exit(code=1) # Exit with error if HTML generation failed
        rich_print(f"[bold green]HTML file saved to {output_html}[/bold green]")

    else:
        # Default: Print formatted text to console
        rich_print("[bold blue]Extracted Headers (Console Output):[/bold blue]")
        linkable_count = 0
        for header in headers:
            id_str = f" (ID: [cyan]{header['id']}[/cyan])" if header['id'] else " (No ID)"
            if header['id']:
                linkable_count += 1
            # Basic indentation for console readability
            indent = "  " if header['tag'] == 'h3' else ""
            rich_print(f"- {indent}[bold]{header['tag'].upper()}[/bold]: {html.escape(header['text'])}{id_str}") # Escape text for console too

        if linkable_count < len(headers):
             rich_print(f"\n[yellow]Note:[/yellow] {len(headers) - linkable_count} headers do not have IDs and cannot be directly linked in the ToC.")


    rich_print("\n[bold green]Processing complete.[/bold green]")


if __name__ == "__main__":
    app()
