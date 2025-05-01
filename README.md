# Medium Header Extractor

A command-line tool to extract H2 and H3 headers and their associated IDs from Medium articles. It uses Selenium to render the page's JavaScript and BeautifulSoup to parse the result.

## Prerequisites

*   Python 3.8+
*   [uv](https://github.com/astral-sh/uv) (or pip)
*   Google Chrome browser installed

## Installation

1.  **Clone the repository (or create the files manually):**
    ```bash
    git clone https://github.com/yourusername/medium-extractor.git # Replace with your repo URL if applicable
    cd medium-extractor
    ```

2.  **Create and activate a virtual environment using uv:**
    ```bash
    uv venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3.  **Install the package using uv:**
    ```bash
    uv pip install -e .
    ```
    *(The `-e` flag installs it in editable mode, good for development.)*

    This command reads `pyproject.toml`, installs dependencies (like Selenium, Typer, etc.), and makes the `medium_extract` command available in your environment. `webdriver-manager` will automatically download the correct ChromeDriver the first time you run the script.

## Usage

Run the command followed by the Medium article URL:

```bash
medium_extract <url-to-medium-blog>
```

By default, this will extract the headers, generate a temporary HTML file containing the headers as links, and attempt to open this file in your default web browser. You can then copy the rendered links from the browser page.





**Example (Default Behavior):**

```bash
medium_extract "https://medium.com/towards-data-science/perplexity-ai-is-a-big-deal-and-google-should-be-worried-18706708f917"
```
(Your browser should open with the linked headers.)

**Output Options:**

*   **Save Permanent HTML File:** If you want to save the HTML file instead of opening 
    a temporary one, use `--output-html` or `-o` followed by a filename. 
    Headers without IDs will be omitted from the HTML file.
    ```bash
    medium_extract --output-html toc.html "YOUR_URL_HERE"
    medium_extract -o path/to/my_toc.html "YOUR_URL_HERE"
    ```

*   **JSON Output:** Use the `--json` or `-j` flag to get the output in JSON format.
    ```bash
    medium_extract --json "YOUR_URL_HERE"
    ```
*   **Timeout:** Adjust the waiting time (in seconds) for page elements using `--timeout` or `-t`. Default is 20 seconds.
    ```bash
    medium_extract --timeout 30 "YOUR_URL_HERE"
    ```

## Notes

*   Medium.com frequently changes its website structure. This scraper might break if they make significant changes to their HTML layout or class names.
*   Web scraping can be resource-intensive (running a headless browser).
*   Ensure you comply with Medium's Terms of Service regarding scraping. This tool is intended for personal, reasonable use.
