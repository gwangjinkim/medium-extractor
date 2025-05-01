# Medium Header Extractor

A command-line tool to extract H2 and H3 headers and their associated IDs from Medium articles. It uses Selenium to render the page's JavaScript and BeautifulSoup to parse the result.

## Prerequisites

*   Python 3.8+
*   [uv](https://github.com/astral-sh/uv) (or pip)
*   Google Chrome browser installed

## Installation

1.  **Clone the repository (or create the files manually):**
    ```bash
    git clone https://github.com/gwangjinkim/medium-extractor.git # Replace with your repo URL if applicable
    cd medium-extractor
    ```

2.  **Create and activate a virtual environment using uv:**
    
    If you don't have `uv`, then first, install `uv`:
    ```bash
    # macos/linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # windows (either use WSL2 ubuntu linux - command above) or Powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

    When uv installed, you can `sync`:
    ```bash
    uv sync
    ```
    This installs all dependencies listed in `pyproject.toml`.

3.  **Install the package using uv:**
    ```bash
    uv pip install -e .
    ```
    *(The `-e` flag installs it in editable mode, good for development.)*

    This command reads `pyproject.toml`, installs dependencies (like Selenium, Typer, etc.), and makes the `medium_extract` command available in your environment. `webdriver-manager` will automatically download the correct ChromeDriver the first time you run the script.


## Usage

-Run the command followed by the Medium article URL:
+Run the command followed by the Medium article URL you want to **scrape** (this can be a friend link to bypass paywalls):

```bash
-medium_extract <url-to-medium-blog>
+medium_extract <scrape-url> [OPTIONS]
```

By default, this will extract the headers, generate a temporary HTML file containing the headers as links, and attempt to open this file in your default web browser. You can then copy the rendered links from the browser page.





**Example (Default Behavior):**

```bash
medium_extract "https://medium.com/towards-data-science/perplexity-ai-is-a-big-deal-and-google-should-be-worried-18706708f917"
```
(Your browser should open with the linked headers pointing to https://medium.com/some-article-slug#header-id)


**Output Options:**

*   **Specify Link Base URL:** Use `--link-base-url` to provide a different URL 
    (e.g., the clean, canonical URL) that should be used when constructing the `href` 
    attributes in the generated ToC HTML. 
    If omitted, the scraped URL (with query parameters stripped) is used.
    ```bash
    # Scrape using friend link, but generate links using the canonical URL
    uv run medium_extract "https://medium.com/article-slug-friendlink" --link-base-url "https://medium.com/article-slug"
    ```
*   **Save Permanent HTML File:** If you want to save the HTML file instead of opening a temporary one, use `--output-html` or `-o` followed by a filename. Headers without IDs will be omitted from the HTML file.
    ```bash
    uv run medium_extract --output-html toc.html "YOUR_URL_HERE"
    uv run medium_extract -o path/to/my_toc.html "YOUR_URL_HERE"
    ```
*   **JSON Output:** Use the `--json` or `-j` flag to get the output in raw JSON format. *Note: This overrides HTML generation/opening.*
    ```bash
    uv run medium_extract --json "YOUR_URL_HERE"
    ```
*   **Save Full Source HTML:** Use `--save-source` followed by a filename to save the complete HTML source code retrieved by Selenium *after* waiting for the page to load. This is useful for debugging selectors if extraction fails.
    ```bash
    uv run medium_extract --save-source debug_source.html "YOUR_URL_HERE"
    ```
*   **Timeout:** Adjust the waiting time (in seconds) for page elements using `--timeout` or `-t`. Default is 20 seconds.
    ```bash
    uv run medium_extract --timeout 30 "YOUR_URL_HERE"
    ```

**How it Works:**

1.  **New CLI Option:** `cli.py` now has a `--link-base-url` option (type `Optional[str]`).
2.  **Argument Passed:** The value of `--link-base-url` (which is `None` if the option isn't used) is passed from the `main` function to the `_create_html_content` function.
3.  **URL Choice in HTML Gen:** `_create_html_content` checks if `link_base_url_override` was provided.
    *   If yes, it uses that URL as the base for creating the `href` links (after stripping query parameters).
    *   If no (it's `None`), it falls back to using the original `scraped_url` (after stripping query parameters).
4.  **Clarity in Output:** The generated HTML now explicitly states which URL was scraped and which base URL was used for the links within it.

Now you can use the friend link for easy access by the script and still generate clean, canonical links for your final ToC.



## Notes

*   Medium.com frequently changes its website structure. This scraper might break if they make significant changes to their HTML layout or class names.
*   Web scraping can be resource-intensive (running a headless browser).
*   Ensure you comply with Medium's Terms of Service regarding scraping. This tool is intended for personal, reasonable use.


