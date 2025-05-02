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

app = typer.Typer(help="Extracts H1/H2/H3 headers and their IDs from Medium articles.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Modify this function to accept the override URL
def _create_html_content(
    headers: list,
    scraped_url: str, # Renamed for clarity
    link_base_url_override: Optional[str] # New parameter
) -> str:
    """Generates the HTML content string for the ToC."""
    logging.info(f"Generating HTML content for {len(headers)} headers...")

    # Determine the base URL to use for the links in the href attributes
    url_for_links = link_base_url_override if link_base_url_override else scraped_url
    base_link_href = url_for_links.split('?')[0] # Strip query params for href
    logging.info(f"Using base URL for href links: {base_link_href}")

    # Filter out headers that don't have an ID, as they can't be linked
    linkable_headers = [h for h in headers if h.get('id')]
    non_linkable_count = len(headers) - len(linkable_headers)
    if non_linkable_count > 0:
        logging.warning(f"Filtered out {non_linkable_count} headers without IDs.")

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
        .h1 {{ /* Style for H1 */ font-size: 1.2em; font-weight: bold; padding-left: 0; }}
        .h2 {{ /* Style for H2 */ font-weight: bold; padding-left: 10px; }}
        .h3 {{ /* Style for H3 */ padding-left: 25px; }} /* Indent H3 more */
        .info {{ font-size: 0.9em; color: #555; margin-top: 20px; }}
        .warning {{ color: #dc3545; font-style: italic; margin-top: 5px; }}
    </style>
</head>
<body>
    <h1>Table of Contents Links</h1>
    <p class="info">Generated from (scraped URL): <a href="{html.escape(scraped_url)}">{html.escape(scraped_url)}</a></p>
    <p class="info"><em>Select and copy the links below to paste into your Medium draft. Links point to base URL: {html.escape(base_link_href)}</em></p>
"""
    if not linkable_headers:
         html_content += '<p class="warning">No headers with IDs were found to create links.</p>'
    else:
        html_content += "<ul>\n"
        for header in linkable_headers:
            header_id = header['id']
            header_text = header['text']
            safe_header_text = html.escape(header_text)
            # Use the determined base_link_href
            link_url = f"{base_link_href}#{header_id}"
            css_class = header['tag'] # Use h1, h2, h3 as class names
            html_content += f'        <li class="{css_class}"><a href="{html.escape(link_url)}">{safe_header_text}</a></li>\n'
        html_content += "    </ul>\n"

    if non_linkable_count > 0:
        html_content += f'<p class="warning">Note: {non_linkable_count} header(s) found without IDs were omitted.</p>\n'


    html_content += """</body>
</html>
"""
    return html_content

# _write_to_file function remains the same
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
    url: str = typer.Argument(..., help="The URL of the Medium article to SCRAPE (can be friend link)."),
    link_base_url: Optional[str] = typer.Option(None, "--link-base-url", help="Optional: Use this URL as the base for generated links (e.g., the canonical URL). If omitted, the scraped URL is used."), # New Option
    timeout: int = typer.Option(20, "--timeout", "-t", help="Seconds to wait for page elements to load."),
    output_html: Optional[Path] = typer.Option(None, "--output-html", "-o", help="Path to save the ToC as a permanent HTML file.", writable=True, dir_okay=False),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output results as raw JSON (overrides HTML generation)."),
    save_source: Optional[Path] = typer.Option(None, "--save-source", help="Save the full rendered HTML source to this file for debugging.", writable=True, dir_okay=False)
):
    """
    Scrapes a Medium article URL (friend links OK). By default, generates a
    temporary HTML ToC file with links (using --link-base-url if provided,
    else scraped URL) and opens it in your browser.
    """
    rich_print(f"[bold blue]Starting extraction for (scrape URL):[/bold blue] {url}")
    if link_base_url:
        rich_print(f"[bold blue]Using base URL for generated links:[/bold blue] {link_base_url}")
    else:
        link_base_url = url
        rich_print(f"[bold blue]Using URL for generated links:[/bold blue] {url}")
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
        rich_print("[yellow]No H1/H2/H3 headers found within the main article content container (or filters removed all).[/yellow]")

    rich_print(f"\n[bold green]Extraction found {len(headers)} potential headers (before filtering).[/bold green]")

    # --- Output Logic ---
    if output_json:
        # ... (JSON output logic remains the same) ...
        if output_html or save_source or link_base_url:
             logging.warning("--json flag provided, ignoring --output-html, --save-source, and --link-base-url (source may still be saved by scraper).")
        rich_print("[bold blue]Outputting as JSON:[/bold blue]")
        print(json.dumps(headers, indent=2))

    elif output_html:
        # Save ToC to permanent file
        rich_print(f"[bold blue]Generating permanent ToC HTML output file:[/bold blue] {output_html}")
        # Pass both URLs to the generation function
        html_content = _create_html_content(headers, scraped_url=url, link_base_url_override=link_base_url)
        success = _write_to_file(html_content, output_html)
        if not success:
             raise typer.Exit(code=1)
        rich_print(f"[bold green]ToC HTML file saved to {output_html}[/bold green]")

    else:
        # Default: Generate temporary HTML and open in browser
        rich_print("[bold blue]Generating temporary ToC HTML file and opening in browser...[/bold blue]")
        # Pass both URLs to the generation function
        html_content = _create_html_content(headers, scraped_url=url, link_base_url_override=link_base_url)

        try:
            # ... (Temporary file creation and opening logic remains the same) ...
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix=".html", delete=False) as temp_file:
                temp_file.write(html_content)
                temp_file_path = temp_file.name
                logging.info(f"Temporary HTML content written to: {temp_file_path}")

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

    # Final message regardless of output type
    if save_source:
        rich_print(f"[bold yellow]Debug source HTML saved to:[/bold yellow] {save_source}")
    rich_print("\n[bold green]Processing complete.[/bold green]")


if __name__ == "__main__":
    app()
