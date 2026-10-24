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

    def get_top_reviews(self,product_url,count=2):
        """Get the top reviews for a product.
        """
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = uc.Chrome(options=options,use_subprocess=True,version_main=155)

        if not product_url.startswith("http"):
            driver.quit()
            return "No reviews found"

        try:
            # driver.get(product_url)
            # time.sleep(4)
            driver.get(product_url)
            time.sleep(5)

            print("Review page title:", driver.title)
            print("Review page URL:", driver.current_url)

            driver.save_screenshot("review_debug.png")

            with open("review_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            print("Saved review_debug.png and review_debug.html")



            
            # try:
            #     driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
            #     time.sleep(1)
            # except Exception as e:
            #     print(f"Error occurred while closing popup: {e}")

            try:
                driver.find_element(
                    By.XPATH, "//button[contains(text(), '✕')]"
                ).click()
            except Exception:
                pass

            for _ in range(4):
                ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1.5)


                
            soup = BeautifulSoup(driver.page_source, "html.parser")

            seen = set()
            reviews = []

            def add_review(text):
                text = " ".join(text.split()).strip()
                text = text.replace("Read full review", "").strip()

                if text and text not in seen:
                    seen.add(text)
                    reviews.append(text)

            # First: extract reviews from JSON-LD structured data
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

                        # Handle nested objects and lists
                        for value in obj.values():
                            if isinstance(value, (dict, list)):
                                stack.append(value)

                    elif isinstance(obj, list):
                        stack.extend(obj)

            # Fallback: extract review text from HTML elements
            if not reviews:
                for block in soup.select("div.sXs98a"):
                    review_element = block.select_one(".G4PxIA")

                    if review_element:
                        add_review(
                            review_element.get_text(" ", strip=True)
                        )

                    if len(reviews) >= count:
                        break

            reviews = reviews[:count]
            

####
        #     soup = BeautifulSoup(driver.page_source, "html.parser")
        #     review_blocks = soup.select("div._27M-vq, div.col.EPCmJX, div._6K-7Co")
        #     seen = set()
        #     reviews = []

        #     for block in review_blocks:
        #         text = block.get_text(separator=" ", strip=True)
        #         if text and text not in seen:
        #             reviews.append(text)
        #             seen.add(text)
        #         if len(reviews) >= count:
        #             break
        # except Exception:
        #     reviews = []

            driver.quit()
            return " || ".join(reviews) if reviews else "No reviews found"
    
    def scrape_flipkart_products(self, query, max_products=1, review_count=2):
        """Scrape Flipkart products based on a search query.
        """
        options = uc.ChromeOptions()
        driver = uc.Chrome(
          options=options,
          use_subprocess=True,
          version_main=155
          )
        search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(4)


        print("Page title:", driver.title)
        print("Current URL:", driver.current_url)

        print(
            "Elements with data-id:",
            len(driver.find_elements(By.CSS_SELECTOR, "div[data-id]"))
        )

        # Save what Chrome actually received
        driver.save_screenshot("flipkart_debug.png")

        with open("flipkart_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        print("Saved flipkart_debug.png and flipkart_debug.html")

        # try:
        #     driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
        # except Exception as e:
        #     print(f"Error occurred while closing popup: {e}")

        try:
            driver.find_element(
                By.XPATH, "//button[contains(text(), '✕')]"
            ).click()
        except Exception:
            pass

        time.sleep(2)
        products = []
        items = driver.find_elements(
            By.CSS_SELECTOR, "div[data-id]"
        )[:max_products]

        for item in items:
            try:
                # Extract product title
                title = item.find_element(
                    By.CSS_SELECTOR, "div.RG5Slk"
                ).text.strip()

                # Extract product price
                price = item.find_element(
                    By.CSS_SELECTOR, "div.hZ3P6w"
                ).text.strip()

                # Extract rating (optional)
                rating_elements = item.find_elements(
                    By.CSS_SELECTOR, "div.MKiFS6"
                )
                rating = (
                    rating_elements[0].text.strip()
                    if rating_elements else "N/A"
                )

                # Extract review count (optional)
                review_elements = item.find_elements(
                    By.CSS_SELECTOR, "span.PvbNMB"
                )
                reviews_text = (
                    review_elements[0].text.strip()
                    if review_elements else ""
                )

                match = re.search(
                    r"([\d,]+)(?=\s+Reviews)",
                    reviews_text
                )
                total_reviews = match.group(1) if match else "N/A"

                # Extract product URL
                link_el = item.find_element(
                    By.CSS_SELECTOR, "a[href*='/p/']"
                )
                href = link_el.get_attribute("href")

                if not href:
                    raise ValueError("Product URL not found")

                product_link = (
                    href if href.startswith("http")
                    else "https://www.flipkart.com" + href
                )

                # Extract product ID
                match = re.findall(
                    r"/p/(itm[0-9A-Za-z]+)", href
                )
                product_id = match[0] if match else "N/A"

            except Exception as e:
                print(f"Error occurred while processing item: {e}")
                continue

            # Scrape top reviews
            top_reviews = (
                self.get_top_reviews(product_link, count=review_count)
                if "flipkart.com" in product_link
                else "Invalid product URL"
            )

            # Preserve your existing output format
            products.append([
                product_id,
                title,
                rating,
                total_reviews,
                price,
                top_reviews
            ])

        driver.quit()
        return products
        # items = driver.find_elements(By.CSS_SELECTOR, "div[data-id]")[:max_products]
        # for item in items:
        #     try:
        #         title = item.find_element(By.CSS_SELECTOR,  "div.RG5Slk").text.strip()
        #         price = item.find_element(By.CSS_SELECTOR, "div.hZ3P6w").text.strip()
        #         rating = item.find_element(By.CSS_SELECTOR, "div.MKiFS6").text.strip()
        #         reviews_text = item.find_element(By.CSS_SELECTOR, "span.Wphh3N").text.strip()
        #         match = re.search(r"\d+(,\d+)?(?=\s+Reviews)", reviews_text)
        #         total_reviews = match.group(0) if match else "N/A"

        #         link_el = item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
        #         href = link_el.get_attribute("href")
        #         product_link = href if href.startswith("http") else "https://www.flipkart.com" + href
        #         match = re.findall(r"/p/(itm[0-9A-Za-z]+)", href)
        #         product_id = match[0] if match else "N/A"
        #     except Exception as e:
        #         print(f"Error occurred while processing item: {e}")
        #         continue

        #     top_reviews = self.get_top_reviews(product_link, count=review_count) if "flipkart.com" in product_link else "Invalid product URL"
        #     products.append([product_id, title, rating, total_reviews, price, top_reviews])

        # driver.quit()
        # return products
    
    def save_to_csv(self, data, filename="product_reviews.csv"):
        """Save the scraped product reviews to a CSV file."""
        if os.path.isabs(filename):
            path = filename
        elif os.path.dirname(filename):  # filename includes subfolder like 'data/product_reviews.csv'
            path = filename
            os.makedirs(os.path.dirname(path), exist_ok=True)
        else:
            # plain filename like 'output.csv'
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"])
            writer.writerows(data)
        