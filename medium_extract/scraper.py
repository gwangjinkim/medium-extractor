# medium-extractor/medium_extract/scraper.py

import time
import logging
from typing import List, Dict, Optional
import re
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup, Tag

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Use the confirmed container selector
MAIN_CONTENT_SELECTOR = "article.meteredContent"

# Use a verified selector for link preview wrappers
LINK_PREVIEW_PARENT_SELECTOR = ".yl" # Class found wrapping the link previews

def extract_medium_headers(
    url: str,
    timeout: int = 20,
    save_source_path: Optional[Path] = None
) -> Optional[List[Dict[str, Optional[str]]]]:
    """
    Extracts H1, H2, H3 headers and their IDs from a Medium article's main body,
    using 'article.meteredContent' selector and filtering link previews based on '.yl' class.
    Checks parent elements for IDs if not found directly on the header tag.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    headers_with_ids = []
    rendered_html = None

    try:
        logging.info("Setting up ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout)

        logging.info(f"Loading URL: {url}")
        driver.get(url)

        logging.info(f"Waiting up to {timeout}s for main content element ('{MAIN_CONTENT_SELECTOR}')...")
        try:
            main_content_element_locator = (By.CSS_SELECTOR, MAIN_CONTENT_SELECTOR)
            # Ensure the element is not just present but also visible (might help with JS rendering)
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located(main_content_element_locator)
            )
            logging.info(f"Main content container found and visible: '{MAIN_CONTENT_SELECTOR}'")
            # Wait a bit longer AFTER finding the container and it being visible
            time.sleep(3) # Allow JS inside the container to potentially finish

        except TimeoutException:
            logging.error(f"Timeout occurred while waiting for '{MAIN_CONTENT_SELECTOR}'.")
            logging.warning("Attempting to get page source anyway for debugging...")
            try:
                rendered_html = driver.page_source
            except WebDriverException as e:
                 logging.error(f"Could not get page source after timeout: {e}")
            logging.error(f"CRITICAL: Could not find or ensure visibility of the main content container using selector '{MAIN_CONTENT_SELECTOR}' within the timeout.")
            return None

        logging.info("Getting page source...")
        rendered_html = driver.page_source

        if save_source_path and rendered_html:
            # ... (save source logic remains the same) ...
            logging.info(f"Saving rendered HTML source to: {save_source_path}")
            try:
                save_source_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_source_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_html)
                logging.info("HTML source saved successfully.")
            except IOError as e:
                logging.error(f"Failed to save HTML source to {save_source_path}: {e}")
        elif save_source_path:
             logging.warning(f"Save source requested, but page source could not be retrieved.")


        logging.info("Parsing rendered HTML...")
        soup = BeautifulSoup(rendered_html, 'html.parser')

        search_area = soup.select_one(MAIN_CONTENT_SELECTOR)
        if not search_area:
             logging.error(f"Could not select the main content container '{MAIN_CONTENT_SELECTOR}' using BeautifulSoup.")
             # Save source if possible before returning None
             if save_source_path and rendered_html and not Path(save_source_path).exists():
                 _save_source_in_finally(save_source_path, rendered_html) # Use a helper or repeat logic
             return None


        logging.info(f"Searching for H1, H2, H3 headers within: '{MAIN_CONTENT_SELECTOR}'")
        # --- Include H1 in the search ---
        potential_headers = search_area.find_all(['h1', 'h2', 'h3'], recursive=True)

        logging.info(f"Found {len(potential_headers)} potential header tags within the specific container.")

        for header in potential_headers:
            # --- Filter based on '.yl' parent class ---
            link_preview_class = LINK_PREVIEW_PARENT_SELECTOR.strip('.') # Remove leading dot
            if header.find_parent(lambda tag: tag.name and link_preview_class in tag.get('class', [])):
                 logging.debug(f"Skipping header inside link preview (.{link_preview_class}): '{header.get_text(strip=True)[:50]}...'")
                 continue

            # Get ID directly from header first
            header_id = header.get('id')
            header_text = header.get_text(strip=True)

            # Skip if no text content
            if not header_text:
                 logging.debug(f"Skipping empty header tag: {header.name}")
                 continue

            # Check parent for ID only if direct ID is missing (fallback)
            if not header_id and isinstance(header.parent, Tag):
                parent_id = header.parent.get('id')
                # Basic check: If parent_id looks like a possible Medium ID
                if parent_id and re.match(r'^[a-zA-Z0-9]{4,}$', parent_id):
                    header_id = parent_id
                    logging.info(f"Found ID '{header_id}' on PARENT of '{header.name}' tag: '{header_text[:50]}...'") # Log as INFO if found on parent

            headers_with_ids.append({
                'tag': header.name,
                'id': header_id if header_id else None,
                'text': header_text
            })

        logging.info(f"Successfully extracted {len(headers_with_ids)} headers (after filtering link previews).")
        return headers_with_ids

    # ... (Error handling and finally block, including final attempt to save source) ...
    except TimeoutException:
        logging.error(f"Timeout occurred while waiting for page elements or loading URL: {url}")
        if driver and not rendered_html: # Try to get source if timeout happened before getting it
             try: rendered_html = driver.page_source
             except: pass
        return None # Indicate failure
    except WebDriverException as e:
        logging.error(f"WebDriver error occurred: {e}")
        if driver and not rendered_html:
             try: rendered_html = driver.page_source
             except: pass
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {e}")
        if driver and not rendered_html:
             try: rendered_html = driver.page_source
             except: pass
        return None
    finally:
        # --- Save Source If Requested (in finally) ---
        _save_source_in_finally(save_source_path, rendered_html) # Use helper

        if driver:
            logging.info("Closing browser...")
            driver.quit()


# Helper function to avoid code duplication in finally
def _save_source_in_finally(save_path: Optional[Path], html_source: Optional[str]):
     if save_path and html_source:
        # Check existence to prevent overwriting if saved successfully earlier
        if not Path(save_path).exists():
            logging.info(f"Saving rendered HTML source to (from finally): {save_path}")
            try:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(html_source)
                logging.info("HTML source saved successfully (from finally).")
            except IOError as e:
                logging.error(f"Failed to save HTML source to {save_path} (from finally): {e}")
        else:
             logging.debug("Source file already exists (saved earlier). Skipping save in finally.")
     elif save_path:
         logging.warning(f"Save source requested, but page source was not available in finally block.")
