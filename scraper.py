"""
Web Scraping Script.

Attributes:
    BASE_URL (str): Base URL of the website to scrape.
    PRODUCT_CSV (str): Filename for saving the extracted product data.

Functions:
    get_random_user_agent(): Returns a randomly chosen user-agent.
    safe_scrape_page(url, headers): Fetch and parse the page content.
    is_product_page(url): Check if the URL is a product page.
    extract_product_data(soup, current_url): Extract data from a soup object.
    save_to_dataframe(products, filename): Save products to a CSV file.
"""

import argparse
import time
import queue
import logging
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from faker import Faker
from requests.exceptions import RequestException



# Setup logging
logging.basicConfig(filename='scrape_errors.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Constants
BASE_URL = 'https://scrapeme.live/shop/'
PRODUCT_CSV = 'products.csv'

def get_random_user_agent():
    """Returns a random user agent string."""
    fake = Faker()
    return fake.user_agent()

def safe_scrape_page(url, headers, timeout=10):
    """Attempts to scrape the page and handles network errors."""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()  # Will raise an HTTPError for bad responses
        soup = BeautifulSoup(response.content, "html.parser")
        return soup
    except RequestException as error:
        logging.error("Network error fetching %s: %s", url, error)
        return None
    except Exception as error:
        logging.error("Unexpected error fetching %s: %s", url, error)
        return None


def is_product_page(url):
    """Check if the URL is a product page based on a specific pattern."""
    return re.match(r"^https://scrapeme\.live/shop/page/\d+/?$", url)

def extract_product_data(soup, current_url):
    """Extract and return product data from a BeautifulSoup object."""
    try:
        product = {"url": current_url}
        product_image = soup.select_one(".wp-post-image")
        product["image"] = product_image["src"] if product_image else "No image found"
        product_title = soup.select_one(".woocommerce-loop-product__title")
        product["name"] = product_title.text.strip() if product_title else "No title found"
        product_price = soup.select_one(".price")
        product["price"] = product_price.text.strip() if product_price else "No price found"
        return product
    except Exception as error:
        logging.error("Error extracting product data: %s", error)
        return None

def save_to_dataframe(products, products_file):
    """Save a list of product dictionaries to a CSV file using a pandas DataFrame."""
    # Convert the list of dictionaries to a DataFrame
    p_dataframe = pd.DataFrame(products)

    # Save the DataFrame to a CSV file
    p_dataframe.to_csv(products_file, index=False)


def get_args():
    """Set up a CLI and retrieve agruments from it"""
    parser = argparse.ArgumentParser(
        description="Scrape a website for product data with optional time and page limits."
        )
    parser.add_argument(
        '--time-limit', type=int, default=None,
        help='Optional: Time limit for the scraping session in minutes'
        )
    parser.add_argument(
        '--page-limit', type=int, default=None,
        help='Optional: Maximum number of pages to scrape'
        )
    args = parser.parse_args()
    return args


def main():
    """
    Main function to control the web scraping process.

    This function handles the setup and execution of a web scraping session.
    It uses command line arguments to determine the time limit and page limit for the scraping.
    It manages the URL queue, fetches and processes pages, and handles data extraction and saving.

    - Initializes command line parsing for runtime parameters.
    - Manages a queue of URLs to be scraped.
    - Loops over the queue, scraping each page within the provided time and page limits.
    - Extracts product data from each page and accumulates results.
    - Saves the accumulated data to a CSV file once scraping is complete.
    """
    args = get_args()
    time_limit = args.time_limit * 60 if args.time_limit else None
    # Convert minutes to seconds only if time limit is not None
    page_limit = args.page_limit

    start_time = time.time()
    products = []
    urls = queue.PriorityQueue()
    urls.put((0.5, BASE_URL))
    visited_urls = []
    pages_scraped = 0

    while not urls.empty() and (time_limit is None or (time.time() - start_time) < time_limit) and (page_limit is None or pages_scraped < page_limit):
        _, current_url = urls.get()
        headers_ua = {'User-Agent': get_random_user_agent()}
        soup = safe_scrape_page(current_url, headers_ua)

        if soup:
            visited_urls.append(current_url)
            pages_scraped += 1
            link_elements = soup.select("a[href]")

            for link_element in link_elements:
                url = link_element['href']
                if re.match(r"https://(?:.*\.)?scrapeme.live", url):
                    if url not in visited_urls and url not in [item[1] for item in urls.queue]:
                        priority_score = 1
                        if is_product_page(url):
                            priority_score = 0.5
                        urls.put((priority_score, url))

            if is_product_page(current_url):
                product = extract_product_data(soup, current_url)
                products.append(product)
        else:
            logging.error("Skipping %s due to errors.", current_url)

    save_to_dataframe(products, PRODUCT_CSV)
    end_time = time.time()
    print(f'The script ran for {round((end_time - start_time) / 60, 2)} minutes and processed {pages_scraped} pages.')

if __name__ == "__main__":
    main()
