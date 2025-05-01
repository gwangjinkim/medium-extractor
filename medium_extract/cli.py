# medium-extractor/medium_extract/cli.py

import typer
import json
import logging
import html
from pathlib import Path
import tempfile
import webbrowser
import os
from typing import Optional

from rich import print as rich_print

from .scraper import extract_medium_headers

app = typer.Typer(help="Extracts H2/H3 headers and their IDs from Medium articles.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ... (_create_html_content and _write_to_file functions remain the same) ...
def _create_html_content(headers: list, original_url: str) -> str:
    """Generates the HTML content string for the ToC."""
    logging.info(f"Generating HTML content for {len(headers)} headers...")
    linkable_headers = [h for h in headers if h.get('id')]
    if len(linkable_headers) != len(headers):
        logging.warning(f"Filtered out {len(headers) - len(linkable_headers)} headers without IDs.")
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Medium Article ToC Links</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: auto; }}
        h1 {{ border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
        ul {{ list-style: none; padding-left: 0; }}
        li {{ margin-bottom: 10px; }}
        a {{ text-decoration: none; color: #0d6efd; }}
        a:hover {{ text-decoration: underline; }}
        .h2 {{ padding-left: 0; font-weight: bold; }}
        .h3 {{ padding-left: 20px; }} /* Indent H3 */
        .warning {{ color: #dc3545; font-style: italic; margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>Table of Contents Links</h1>
    <p>Generated from: <a href="{html.escape(original_url)}">{html.escape(original_url)}</a></p>
    <p><em>Select and copy the links below to paste into your Medium draft.</em></p>
"""
    if not linkable_headers:
         html_content += '<p class="warning">No headers with IDs were found to create links.</p>'
    else:
        html_content += "<ul>\n"
        for header in linkable_headers:
            header_id = header['id']
            header_text = header['text']
            safe_header_text = html.escape(header_text)
            link_url = f"{original_url.split('?')[0]}#{header_id}"
            css_class = header['tag']
            html_content += f'        <li class="{css_class}"><a href="{html.escape(link_url)}">{safe_header_text}</a></li>\n'
        html_content += "    </ul>\n"
    html_content += """</body>
</html>
"""
    return html_content

def _write_to_file(html_content: str, filename: Path) -> bool:
    """Writes HTML content to a specified file."""
    try:
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"HTML file successfully saved to: {filename}")
        return True
    except IOError as e:
        logging.error(f"Failed to write HTML file {filename}: {e}")
        rich_print(f"[bold red]Error:[/bold red] Could not write to file {filename}.")
        return False


@app.command()
def main(
    url: str = typer.Argument(..., help="The URL of the Medium article to scrape."),
    timeout: int = typer.Option(20, "--timeout", "-t", help="Seconds to wait for page elements to load."),
    output_html: Optional[Path] = typer.Option(None, "--output-html", "-o", help="Path to save the output as a permanent HTML file.", writable=True, dir_okay=False),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output results as raw JSON (overrides HTML generation)."),
    save_source: Optional[Path] = typer.Option(None, "--save-source", help="Save the full rendered HTML source to this file for debugging.", writable=True, dir_okay=False) # New option
):
    """
    Scrapes a Medium article URL. By default, generates a temporary HTML
    file with linked headers and opens it in your browser. Use flags for
    JSON output, saving a permanent HTML file, or saving the raw source HTML.
    """
    rich_print(f"[bold blue]Starting extraction for:[/bold blue] {url}")
    if save_source:
        rich_print(f"[bold yellow]Will save full HTML source to:[/bold yellow] {save_source}")

    # Pass the save_source path to the scraper function
    headers = extract_medium_headers(url, timeout, save_source_path=save_source)

    # --- Processing after scraping attempt ---

    if headers is None:
        rich_print("[bold red]Error:[/bold red] Header extraction failed. Check logs for details.")
        if save_source:
            rich_print(f"[bold yellow]Check the saved source file for clues:[/bold yellow] {save_source}")
        raise typer.Exit(code=1)

    if not headers:
        rich_print("[yellow]No H2 or H3 headers found within the main article content container (or filters removed all).[/yellow]")
        # Decide if you want to proceed with empty HTML or exit
        # Let's allow proceeding to generate potentially empty HTML for consistency

    rich_print(f"\n[bold green]Extraction found {len(headers)} potential headers (before filtering).[/bold green]")


    # --- Output Logic ---
    if output_json:
        if output_html or save_source: # Check against save_source too now
             logging.warning("--json flag provided, ignoring --output-html and --save-source (source may still be saved by scraper).")
        rich_print("[bold blue]Outputting as JSON:[/bold blue]")
        print(json.dumps(headers, indent=2))

    elif output_html:
        # Save ToC to permanent file
        rich_print(f"[bold blue]Generating permanent ToC HTML output file:[/bold blue] {output_html}")
        html_content = _create_html_content(headers, url)
        success = _write_to_file(html_content, output_html)
        if not success:
             raise typer.Exit(code=1)
        rich_print(f"[bold green]ToC HTML file saved to {output_html}[/bold green]")

    else:
        # Default: Generate temporary HTML and open in browser
        rich_print("[bold blue]Generating temporary ToC HTML file and opening in browser...[/bold blue]")
        html_content = _create_html_content(headers, url)

        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix=".html", delete=False) as temp_file:
                temp_file.write(html_content)
                temp_file_path = temp_file.name

            file_url = Path(temp_file_path).absolute().as_uri()

            rich_print(f"Attempting to open ToC: {file_url}")
            opened = webbrowser.open(file_url)

            if opened:
                 rich_print("[bold green]Temporary ToC HTML file opened in your default browser.[/bold green]")
                 rich_print(f"[cyan]ToC file: {temp_file_path}[/cyan]")
            else:
                 rich_print("[bold red]Error:[/bold red] Could not automatically open the browser for ToC.")
                 rich_print(f"You can manually open the temporary ToC file:")
                 rich_print(f"[cyan]{temp_file_path}[/cyan]")

        except Exception as e:
            logging.error(f"Failed to create/open temporary ToC HTML file: {e}")
            rich_print(f"[bold red]Error:[/bold red] Failed to create or open the temporary ToC HTML file: {e}")
            # Don't exit if only browser opening failed

    # Final message regardless of output type
    if save_source:
        rich_print(f"[bold yellow]Debug source HTML saved to:[/bold yellow] {save_source}")
    rich_print("\n[bold green]Processing complete.[/bold green]")


if __name__ == "__main__":
    app()

