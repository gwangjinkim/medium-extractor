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

# --- !!! USING SELECTOR SUGGESTED BY CHROMIUM AI !!! ---
# This selector might be fragile and could change if Medium updates its site.
# If this stops working, you will need to re-inspect the page and find a more
# stable selector for the main article body content container.
MAIN_CONTENT_SELECTOR = ".eu.bg.ev.ew.ex.ey" # <--- Updated based on AI suggestion

# Selector for filtering out link previews (update if needed)
LINK_PREVIEW_PARENT_SELECTOR = ".graf--miro" # Or your verified selector for previews

def extract_medium_headers(url: str, timeout: int = 20) -> Optional[List[Dict[str, Optional[str]]]]:
    """
    Extracts H2 and H3 headers and their IDs from a Medium article's main body,
    using a specific selector for the content area and filtering link previews.
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

    try:
        logging.info("Setting up ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout)

        logging.info(f"Loading URL: {url}")
        driver.get(url)

        # Wait for the overall article container first (optional but safe)
        # logging.info(f"Waiting up to {timeout}s for article container (article tag)...")
        # WebDriverWait(driver, timeout).until(
        #     EC.presence_of_element_located((By.TAG_NAME, "article"))
        # )

        # Now, specifically wait for the *precise* main content container
        # We assume the suggested selector is unique enough on the page,
        # If not, we might need to scope it like "article .eu.bg..."
        logging.info(f"Waiting up to {timeout}s for main content element ('{MAIN_CONTENT_SELECTOR}')...")
        try:
            # Try finding the element directly on the page first
            main_content_element_locator = (By.CSS_SELECTOR, MAIN_CONTENT_SELECTOR)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(main_content_element_locator)
            )
            logging.info(f"Precise main content container found using selector: '{MAIN_CONTENT_SELECTOR}'")
        except TimeoutException:
            logging.error(f"CRITICAL: Could not find the specific main content container using selector '{MAIN_CONTENT_SELECTOR}' within the timeout. Scraping cannot proceed accurately.")
            logging.error("Please re-inspect the page HTML and update MAIN_CONTENT_SELECTOR in scraper.py, or the selector might be invalid/changed.")
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
             # This might happen if the selector worked for Selenium's wait but BS4 can't find it (less likely)
             logging.error(f"Could not select the main content container '{MAIN_CONTENT_SELECTOR}' using BeautifulSoup after page load. HTML structure might be inconsistent or selector incorrect.")
             return None


        logging.info(f"Searching for headers within the specific container: '{MAIN_CONTENT_SELECTOR}'")
        potential_headers = search_area.find_all(['h2', 'h3'], recursive=True)

        logging.info(f"Found {len(potential_headers)} potential header tags within the specific container.")
        if len(potential_headers) == 0:
             logging.warning(f"No H2 or H3 tags found inside the specified main content container ('{MAIN_CONTENT_SELECTOR}'). Check the selector and page structure.")


        for header in potential_headers:
            # Filter out headers inside link previews
            # Check class using lambda (adjust selector if needed)
            if header.find_parent(lambda tag: tag.name and LINK_PREVIEW_PARENT_SELECTOR.strip('.') in tag.get('class', [])):
                 logging.debug(f"Skipping header inside link preview ('{LINK_PREVIEW_PARENT_SELECTOR}'): '{header.get_text(strip=True)[:30]}...'")
                 continue
            # You might need a different check if LINK_PREVIEW_PARENT_SELECTOR isn't just a class

            header_id = header.get('id')
            header_text = header.get_text(strip=True)

            if not header_text:
                 logging.debug(f"Skipping empty header tag: {header.name}")
                 continue

            # Check parent for ID if needed
            if not header_id and isinstance(header.parent, Tag):
                parent_id = header.parent.get('id')
                if parent_id and re.match(r'^[a-zA-Z0-9]{4,}$', parent_id): # Check if it looks like a Medium ID
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
