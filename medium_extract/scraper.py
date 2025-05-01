# medium-extractor/medium_extract/scraper.py

import time
import logging
from typing import List, Dict, Optional
import re
from pathlib import Path # Import Path

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

# Keep the selector you want to test
MAIN_CONTENT_SELECTOR = "article.meteredContent" # Or your current best guess
LINK_PREVIEW_PARENT_SELECTOR = ".graf--miro" # Or your verified selector for previews

def extract_medium_headers(
    url: str,
    timeout: int = 20,
    save_source_path: Optional[Path] = None # New parameter
) -> Optional[List[Dict[str, Optional[str]]]]:
    """
    Extracts H2 and H3 headers and their IDs from a Medium article's main body.
    Optionally saves the full rendered HTML source for debugging.
    """
    # ... (webdriver setup code remains the same) ...
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    headers_with_ids = []
    rendered_html = None # Define outside try block

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
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(main_content_element_locator)
            )
            logging.info(f"Main content container found using selector: '{MAIN_CONTENT_SELECTOR}'")
            # Wait a bit longer AFTER finding the container
            time.sleep(5) # Increased sleep *after* finding element

        except TimeoutException:
            logging.error(f"Timeout occurred while waiting for '{MAIN_CONTENT_SELECTOR}'.")
            logging.warning("Attempting to get page source anyway for debugging...")
            # Try to get source even on timeout, before quitting
            try:
                rendered_html = driver.page_source
                logging.info("Grabbed page source after timeout.")
            except WebDriverException as e:
                 logging.error(f"Could not get page source after timeout: {e}")
            # Now re-raise or handle the original timeout
            logging.error(f"CRITICAL: Could not find the main content container using selector '{MAIN_CONTENT_SELECTOR}' within the timeout.")
            logging.error("Selector might be incorrect, page structure changed, or loading took too long.")
            # We return None below, after the finally block saves the source if requested/possible
            return None # Indicate failure to find element

        # --- Get Page Source ---
        logging.info("Getting page source...")
        rendered_html = driver.page_source # Get source after successful wait & sleep

        # --- Save Source If Requested ---
        # Do this *before* parsing, so we save the raw source
        if save_source_path and rendered_html:
            logging.info(f"Saving rendered HTML source to: {save_source_path}")
            try:
                save_source_path.parent.mkdir(parents=True, exist_ok=True) # Ensure dir exists
                with open(save_source_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_html)
                logging.info("HTML source saved successfully.")
            except IOError as e:
                logging.error(f"Failed to save HTML source to {save_source_path}: {e}")
        elif save_source_path:
             logging.warning(f"Save source requested, but page source could not be retrieved.")


        # --- Proceed with Parsing ---
        logging.info("Parsing rendered HTML...")
        soup = BeautifulSoup(rendered_html, 'html.parser')

        search_area = soup.select_one(MAIN_CONTENT_SELECTOR)
        if not search_area:
             # If selector worked for wait but not BS4, log it, but don't necessarily fail extraction yet
             logging.warning(f"Could not select '{MAIN_CONTENT_SELECTOR}' using BeautifulSoup, though Selenium wait succeeded. Searching entire page.")
             search_area = soup # Fallback: search entire soup object

        # ... (rest of the header finding and filtering logic remains the same) ...
        logging.info(f"Searching for headers within the specific container: '{MAIN_CONTENT_SELECTOR}' (or fallback area)")
        potential_headers = search_area.find_all(['h2', 'h3'], recursive=True)

        logging.info(f"Found {len(potential_headers)} potential header tags within the search area.")
        # ... (loop, filtering, ID checking, appending) ...

        for header in potential_headers:
            # Filter out headers inside link previews
            preview_class = LINK_PREVIEW_PARENT_SELECTOR.strip('.')
            if header.find_parent(lambda tag: tag.name and preview_class in tag.get('class', [])):
                 logging.debug(f"Skipping header inside link preview ('{LINK_PREVIEW_PARENT_SELECTOR}'): '{header.get_text(strip=True)[:30]}...'")
                 continue

            header_id = header.get('id')
            header_text = header.get_text(strip=True)

            if not header_text:
                 logging.debug(f"Skipping empty header tag: {header.name}")
                 continue

            if not header_id and isinstance(header.parent, Tag):
                parent_id = header.parent.get('id')
                if parent_id and re.match(r'^[a-zA-Z0-9]{4,}$', parent_id):
                    header_id = parent_id
                    logging.debug(f"Found ID '{header_id}' on parent of header: '{header_text[:30]}...'")

            headers_with_ids.append({
                'tag': header.name,
                'id': header_id if header_id else None,
                'text': header_text
            })


        logging.info(f"Successfully extracted {len(headers_with_ids)} headers (after filtering link previews).")
        return headers_with_ids

    except WebDriverException as e:
        # Catch webdriver errors that might happen before getting source
        logging.error(f"WebDriver error occurred: {e}")
        # Try to get source in finally block
        if driver:
            try:
                rendered_html = driver.page_source # Try again
            except: pass # Ignore error here, focus on original one
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {e}")
        # Try to get source in finally block
        if driver:
            try:
                rendered_html = driver.page_source # Try again
            except: pass
        return None
    finally:
        # --- Save Source If Requested (in finally) ---
        # This attempts to save even if an exception occurred after getting the source
        if save_source_path and rendered_html:
            if not Path(save_source_path).exists(): # Avoid writing twice if saved earlier
                logging.info(f"Saving rendered HTML source to (from finally): {save_source_path}")
                try:
                    save_source_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(save_source_path, 'w', encoding='utf-8') as f:
                        f.write(rendered_html)
                    logging.info("HTML source saved successfully (from finally).")
                except IOError as e:
                    logging.error(f"Failed to save HTML source to {save_source_path} (from finally): {e}")
        elif save_source_path:
            logging.warning(f"Save source requested, but page source was not available in finally block.")

        if driver:
            logging.info("Closing browser...")
            driver.quit()
