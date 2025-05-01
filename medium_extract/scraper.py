# medium-extractor/medium_extract/scraper.py

import time
import logging
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- !!! IMPORTANT: UPDATE THIS SELECTOR !!! ---
# Inspect the Medium page in your browser's DevTools to find the
# CSS selector for the element that *only* contains the main article body,
# excluding related posts, footers, etc. It's often inside the <article> tag.
# Example selectors (you MUST verify): "section.section--body", "div.postArticle-content"
MAIN_CONTENT_SELECTOR = "section" # <--- TRY THIS FIRST, then refine if needed by inspecting

def extract_medium_headers(url: str, timeout: int = 20) -> Optional[List[Dict[str, Optional[str]]]]:
    """
    Extracts H2 and H3 headers and their IDs from a Medium article using Selenium.

    Args:
        url: The URL of the Medium article.
        timeout: Maximum time in seconds to wait for the page elements to load.

    Returns:
        A list of dictionaries, each containing 'tag', 'id', and 'text' for a header,
        or None if an error occurs during scraping.
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

        # Wait for the overall article container first
        logging.info(f"Waiting up to {timeout}s for article container (article tag)...")
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "article"))
        )

        # Now, specifically wait for the main content container *within* the article
        logging.info(f"Waiting up to {timeout}s for main content element ('{MAIN_CONTENT_SELECTOR}')...")
        try:
            # Use CSS_SELECTOR for flexibility
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f"article {MAIN_CONTENT_SELECTOR}"))
            )
            logging.info("Main content container found.")
        except TimeoutException:
            # Fallback if the specific container isn't found quickly after article tag
            logging.warning(f"Specific main content container ('{MAIN_CONTENT_SELECTOR}') not found within timeout after article appeared. Proceeding with <article> tag search, but results might include duplicates.")
            pass # Continue and search within the whole <article> tag as a fallback

        # Add a small fixed delay for safety
        time.sleep(2)

        logging.info("Getting page source...")
        rendered_html = driver.page_source

        logging.info("Parsing rendered HTML...")
        soup = BeautifulSoup(rendered_html, 'html.parser')

        # --- Find Headers within the main article content ---
        article_tag = soup.find('article')
        if not article_tag:
            logging.warning("Could not find the main <article> tag in the rendered HTML.")
            return []

        # Try to find the more specific content container
        content_container = article_tag.select_one(MAIN_CONTENT_SELECTOR)

        search_area = None
        if content_container:
            search_area = content_container
            logging.info(f"Searching for headers within the specific container: '{MAIN_CONTENT_SELECTOR}'")
        else:
            search_area = article_tag # Fallback to the whole article
            logging.warning(f"Could not find specific container '{MAIN_CONTENT_SELECTOR}'. Searching within the entire <article> tag (may cause duplicates).")


        potential_headers = search_area.find_all(['h2', 'h3']) # Search within the refined area

        logging.info(f"Found {len(potential_headers)} potential header tags within the search area.")

        for header in potential_headers:
            header_id = header.get('id')
            header_text = header.get_text(strip=True)

            if header_text:
                headers_with_ids.append({
                    'tag': header.name,
                    'id': header_id if header_id else None,
                    'text': header_text
                })

        logging.info(f"Successfully extracted {len(headers_with_ids)} headers.")
        return headers_with_ids

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
