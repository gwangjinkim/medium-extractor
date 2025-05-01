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
    chrome_options.add_argument("--headless")  # Run headless (no visible browser window)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
    chrome_options.add_argument("--window-size=1920,1080") # Sometimes needed for headless
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    headers_with_ids = []

    try:
        logging.info("Setting up ChromeDriver...")
        # Use webdriver-manager to automatically handle driver download/updates
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout) # Timeout for initial page load

        logging.info(f"Loading URL: {url}")
        driver.get(url)

        # --- Wait for the main article content to likely be present ---
        # We wait for the <article> tag, which usually wraps the main content.
        logging.info(f"Waiting up to {timeout}s for article content to load...")
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "article"))
        )
        # Add a small fixed delay just in case some elements render slightly after the article tag appears
        time.sleep(2)

        logging.info("Article container found. Getting page source...")
        rendered_html = driver.page_source

        logging.info("Parsing rendered HTML...")
        soup = BeautifulSoup(rendered_html, 'html.parser')

        # --- Find Headers within the main article ---
        article_tag = soup.find('article')
        if not article_tag:
            logging.warning("Could not find the main <article> tag in the rendered HTML.")
            return [] # Return empty list if no article tag found

        # Find H2 and H3 tags specifically within the article tag
        potential_headers = article_tag.find_all(['h2', 'h3'])

        logging.info(f"Found {len(potential_headers)} potential header tags within <article>.")

        for header in potential_headers:
            header_id = header.get('id')
            header_text = header.get_text(strip=True)

            # Basic check: ensure header has text content
            if header_text:
                headers_with_ids.append({
                    'tag': header.name,
                    'id': header_id if header_id else None, # Store None if no ID
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
