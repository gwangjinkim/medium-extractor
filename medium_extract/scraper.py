# medium-extractor/medium_extract/scraper.py

import time
import logging
from typing import List, Dict, Optional
import re

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

# --- !!! USING SELECTOR BASED ON USER INSPECTION / AI FEEDBACK !!! ---
MAIN_CONTENT_SELECTOR = "article.meteredContent" # <--- Updated based on feedback

# Selector for filtering out link previews (update if needed)
LINK_PREVIEW_PARENT_SELECTOR = ".graf--miro" # Or your verified selector for previews

def extract_medium_headers(url: str, timeout: int = 20) -> Optional[List[Dict[str, Optional[str]]]]:
    """
    Extracts H2 and H3 headers and their IDs from a Medium article's main body,
    using the 'article.meteredContent' selector and filtering link previews.
    Checks parent elements for IDs if not found directly on the header tag.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Re-enable headless if you commented it out
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    headers_with_ids = []

    try:
        logging.info("Setting up ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout)

        logging.info(f"Loading URL: {url}")
        driver.get(url)

        # Wait directly for the specific 'article.meteredContent' element
        logging.info(f"Waiting up to {timeout}s for main content element ('{MAIN_CONTENT_SELECTOR}')...")
        try:
            main_content_element_locator = (By.CSS_SELECTOR, MAIN_CONTENT_SELECTOR)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(main_content_element_locator)
            )
            logging.info(f"Main content container found using selector: '{MAIN_CONTENT_SELECTOR}'")
        except TimeoutException:
            logging.error(f"CRITICAL: Could not find the main content container using selector '{MAIN_CONTENT_SELECTOR}' within the timeout.")
            logging.error("Selector might be incorrect, page structure changed, or loading took too long.")
            return None

        time.sleep(3) # Wait a bit longer after container found

        logging.info("Getting page source...")
        rendered_html = driver.page_source

        logging.info("Parsing rendered HTML...")
        soup = BeautifulSoup(rendered_html, 'html.parser')

        # --- Find Headers *only* within the precise main content container ---
        # Select the specific content container using BeautifulSoup
        search_area = soup.select_one(MAIN_CONTENT_SELECTOR)

        if not search_area:
             logging.error(f"Could not select the main content container '{MAIN_CONTENT_SELECTOR}' using BeautifulSoup after page load.")
             return None # Fail if the container isn't found in the parsed HTML


        logging.info(f"Searching for headers within the specific container: '{MAIN_CONTENT_SELECTOR}'")
        # Find headers that are direct children or descendants within the search area
        potential_headers = search_area.find_all(['h2', 'h3'], recursive=True)

        logging.info(f"Found {len(potential_headers)} potential header tags within the specific container.")
        if len(potential_headers) == 0:
             logging.warning(f"No H2 or H3 tags found inside the specified main content container ('{MAIN_CONTENT_SELECTOR}').")


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

            # Check parent for ID if needed
            if not header_id and isinstance(header.parent, Tag):
                parent_id = header.parent.get('id')
                # Check if parent_id looks like a typical Medium ID (e.g., 4+ alphanumeric chars)
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

    # ... (Error handling and finally block remain the same) ...
    except TimeoutException:
        logging.error(f"Timeout occurred while waiting for page elements or loading URL: {url}")
        return None
    except WebDriverException as e:
        logging.error(f"WebDriver error occurred: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {e}")
        return None
    finally:
        if driver:
            logging.info("Closing browser...")
            driver.quit()
