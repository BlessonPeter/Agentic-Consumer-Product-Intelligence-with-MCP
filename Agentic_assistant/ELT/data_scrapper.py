import csv
import time
import re
import json
import os

from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


class FlipkartScraper:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def get_top_reviews(self, product_url, count=2):
        """Get up to `count` review texts for a Flipkart product."""
        if not product_url or not product_url.startswith("http"):
            return "No reviews found"

        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = None
        reviews = []

        try:
            driver = uc.Chrome(
                options=options,
                use_subprocess=True,
                version_main=155,
            )
            driver.get(product_url)
            time.sleep(5)

            print("Review page title:", driver.title)
            print("Review page URL:", driver.current_url)

            # Save the rendered page for debugging.
            # driver.save_screenshot("review_debug.png")
            # with open("review_debug.html", "w", encoding="utf-8") as file:
            #     file.write(driver.page_source)
            # print("Saved review_debug.png and review_debug.html")

            # The close button is optional.
            try:
                driver.find_element(
                    By.XPATH, "//button[contains(text(), '✕')]"
                ).click()
                time.sleep(1)
            except Exception:
                pass

            # Scroll to allow review sections to load.
            for _ in range(4):
                ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1.5)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            seen = set()

            def add_review(review_text):
                review_text = " ".join(review_text.split()).strip()
                review_text = review_text.replace("Read full review", "").strip()

                if review_text and review_text not in seen:
                    seen.add(review_text)
                    reviews.append(review_text)

            # First, inspect JSON-LD structured product data.
            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    data = json.loads(script.string or script.get_text())
                except (json.JSONDecodeError, TypeError):
                    continue

                stack = [data]
                while stack and len(reviews) < count:
                    obj = stack.pop()

                    if isinstance(obj, dict):
                        review_data = obj.get("review", [])

                        if isinstance(review_data, dict):
                            review_data = [review_data]

                        if isinstance(review_data, list):
                            for review in review_data:
                                if isinstance(review, dict):
                                    body = review.get("reviewBody", "")
                                    if body:
                                        add_review(body)
                                    if len(reviews) >= count:
                                        break

                        for value in obj.values():
                            if isinstance(value, (dict, list)):
                                stack.append(value)

                    elif isinstance(obj, list):
                        stack.extend(obj)

            # Fallback to review blocks found in the saved Flipkart HTML.
            if len(reviews) < count:
                for block in soup.select("div.sXs98a"):
                    review_element = block.select_one(".G4PxIA")
                    if review_element:
                        add_review(review_element.get_text(" ", strip=True))

                    if len(reviews) >= count:
                        break

            return " || ".join(reviews[:count]) if reviews else "No reviews found"

        except Exception as exc:
            print(f"Error while scraping product reviews: {exc}")
            return "No reviews found"

        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

    def scrape_flipkart_products(self, query, max_products=1, review_count=2):
        """Scrape Flipkart products based on a search query."""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = None
        products = []

        try:
            driver = uc.Chrome(
                options=options,
                use_subprocess=True,
                version_main=155,
            )

            search_url = (
                "https://www.flipkart.com/search?q="
                + query.replace(" ", "+")
            )
            driver.get(search_url)
            time.sleep(4)

            print("Page title:", driver.title)
            print("Current URL:", driver.current_url)
            print(
                "Elements with data-id:",
                len(driver.find_elements(By.CSS_SELECTOR, "div[data-id]")),
            )

            # # Save the rendered search page for debugging.
            # driver.save_screenshot("flipkart_debug.png")
            # with open("flipkart_debug.html", "w", encoding="utf-8") as file:
            #     file.write(driver.page_source)
            # print("Saved flipkart_debug.png and flipkart_debug.html")

            # The close button is optional.
            try:
                driver.find_element(
                    By.XPATH, "//button[contains(text(), '✕')]"
                ).click()
                time.sleep(1)
            except Exception:
                pass

            items = driver.find_elements(
                By.CSS_SELECTOR, "div[data-id]"
            )[:max_products]

            for item in items:
                try:
                    # Product title
                    title_elements = item.find_elements(
                        By.CSS_SELECTOR, "div.RG5Slk"
                    )
                    title = (
                        title_elements[0].text.strip()
                        if title_elements
                        else "0"
                    )

                    # Product price
                    price_elements = item.find_elements(
                        By.CSS_SELECTOR, "div.hZ3P6w"
                    )
                    price = (
                        price_elements[0].text.strip()
                        if price_elements
                        else "0"
                    )

                    # Product rating
                    rating_elements = item.find_elements(
                        By.CSS_SELECTOR, "div.MKiFS6"
                    )
                    rating = (
                        rating_elements[0].text.strip()
                        if rating_elements
                        else "0"
                    )

                    # Rating and review counts may share a combined element.
                    review_elements = item.find_elements(
                        By.CSS_SELECTOR,
                        "span.EZaE0Q, span.PvbNMB, span.Wphh3N",
                    )
                    reviews_text = " ".join(
                        element.text.strip() for element in review_elements
                    )

                    match = re.search(
                        r"([\d,]+)\s+Reviews\b",
                        reviews_text,
                        flags=re.IGNORECASE,
                    )
                    total_reviews = match.group(1) if match else "0"

                    # Product URL
                    link_elements = item.find_elements(
                        By.CSS_SELECTOR, "a[href*='/p/']"
                    )
                    if not link_elements:
                        raise ValueError("Product URL not found")

                    href = link_elements[0].get_attribute("href")
                    if not href:
                        raise ValueError("Product URL is empty")

                    product_link = (
                        href
                        if href.startswith("http")
                        else "https://www.flipkart.com" + href
                    )

                    # Product ID
                    match = re.search(r"/p/(itm[0-9A-Za-z]+)", href)
                    product_id = match.group(1) if match else "N/A"

                except Exception as exc:
                    print(f"Error occurred while processing item: {exc}")
                    continue

                top_reviews = self.get_top_reviews(
                    product_link,
                    count=review_count,
                )

                products.append(
                    [
                        product_id,
                        title,
                        rating,
                        total_reviews,
                        price,
                        top_reviews,
                    ]
                )

            return products

        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

    def save_to_csv(self, data, filename="product_reviews.csv"):
        """Save scraped product information and reviews to a CSV file."""
        if os.path.isabs(filename):
            path = filename
        elif os.path.dirname(filename):
            path = filename
            os.makedirs(os.path.dirname(path), exist_ok=True)
        else:
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "product_id",
                    "product_title",
                    "rating",
                    "total_reviews",
                    "price",
                    "top_reviews",
                ]
            )
            writer.writerows(data)

        print(f"Saved {len(data)} products to: {path}")
