import scrapy
from scrapy_selenium import SeleniumRequest
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import os
import requests
from requests.exceptions import RequestException

class MaxlinearNewsSpider(scrapy.Spider):
    name = "maxlinear_news"
    start_urls = ["https://www.maxlinear.com/news"]

    custom_settings = {
        'FEEDS': {
            'maxlinear_news_combined.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 4,
                'overwrite': True,
            },
        },
        'FEED_EXPORT_ENCODING': 'utf-8',
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'SELENIUM_DRIVER_NAME': 'chrome',
        'SELENIUM_DRIVER_ARGUMENTS': ['--headless', '--no-sandbox', '--disable-dev-shm-usage'],
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_selenium.SeleniumMiddleware': 800,
        },
        'LOG_FILE': 'scrapy_log.txt',
        'LOG_LEVEL': 'INFO',
    }

    def __init__(self, *args, **kwargs):
        super(MaxlinearNewsSpider, self).__init__(*args, **kwargs)
        self.driver = webdriver.Chrome()  # Use Chrome() directly to find the path automatically
        self.driver.maximize_window()

        # Directory for saving images
        self.images_dir = 'images'
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)

    def start_requests(self):
        yield SeleniumRequest(url=self.start_urls[0], callback=self.parse, wait_time=10)

    def parse(self, response):
        self.logger.info("Starting to parse the main page...")
        self.driver.get(response.url)

        last_height = 0

        while True:
            # Scroll down by 5000 pixels
            self.driver.execute_script('window.scrollBy(0, 5000)')
            time.sleep(3)  # Allow time for new content to load

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            self.logger.info(f"New height: {new_height}, Last height: {last_height}")

            # Extract dates to check if we should stop scrolling
            visible_dates = self.driver.find_elements(By.CSS_SELECTOR, '.date-location .text')
            stop_scroll = False
            for date_elem in visible_dates:
                date_text = date_elem.text.strip()
                try:
                    news_date = datetime.strptime(date_text, "%B %d, %Y")
                    if news_date.year < 2020:
                        self.logger.info(f"Encountered a date before 2020 ({date_text}). Stopping scroll.")
                        stop_scroll = True
                        break
                except ValueError:
                    self.logger.error(f"Error parsing date: {date_text}")

            if stop_scroll:
                break  # Stop scrolling if we've encountered a date before 2020

            if new_height == last_height:
                self.logger.info("No new content loaded. Stopping scroll.")
                break
            else:
                last_height = new_height

        # After scrolling, proceed with extracting content
        response_html = scrapy.http.HtmlResponse(url=self.driver.current_url, body=self.driver.page_source, encoding='utf-8')
        link_extractor = LinkExtractor(restrict_css='.card.news .title a')
        links = link_extractor.extract_links(response_html)

        self.logger.info(f"Found {len(links)} news articles.")
        for link in links:
            self.logger.debug(f"Processing link: {link.url}")
            yield SeleniumRequest(url=link.url, callback=self.parse_article, meta={'title': link.text}, wait_time=5)

    def parse_article(self, response):
        title = response.meta.get('title') or response.css('h1::text').get()
        date = response.css('.date-location .text::text').get()
        formatted_date = self.format_date(date)

        # Only process articles from 2020 to 2024
        if formatted_date and '2020' <= formatted_date[:4] <= '2024':
            # Extract content from the article
            content_paragraphs = response.css('.news-content .content p::text, .news-content .content ul li::text')
            content = "\n".join(content_paragraphs.getall()).strip()

            # Extract and download images
            image_paths = []

            # Get og:image content
            og_image = response.css('meta[property="og:image"]::attr(content)').get()
            if og_image:
                og_image_url = response.urljoin(og_image)
                image_path = self.download_image(og_image_url)
                if image_path:
                    image_paths.append(image_path)

            # Get images from within the article content
            images = response.css('.news-content img::attr(src)').getall()
            for img_url in images:
                img_url = response.urljoin(img_url)  # Convert relative URLs to absolute URLs
                image_path = self.download_image(img_url)
                if image_path:
                    image_paths.append(image_path)

            self.logger.info(f"Scraping article - Title: {title}, Date: {formatted_date}, URL: {response.url}")

            yield {
                'title': title,
                'date': formatted_date,
                'content': content,
                'url': response.url,
                'images': image_paths  # Include the list of image paths in the output
            }
        else:
            self.logger.info(f"Skipping article - Date {formatted_date} not in range 2020 to 2024.")

    def download_image(self, img_url):
        img_filename = os.path.basename(img_url.split("?")[0])  # Get the filename without query parameters
        img_filepath = os.path.join(self.images_dir, img_filename)
        self.logger.info(f"Downloading image {img_url} to {img_filepath}")
        try:
            response = requests.get(img_url, timeout=10)
            response.raise_for_status()  # Raises an error for bad HTTP responses
            with open(img_filepath, 'wb') as img_file:
                img_file.write(response.content)
            return img_filepath
        except RequestException as e:
            self.logger.error(f"Failed to download image {img_url}: {e}")
            return None

    def format_date(self, date_str):
        if not date_str:
            return None
        try:
            formatted_date = datetime.strptime(date_str.strip(), "%B %d, %Y").strftime("%Y-%m-%d")
            return formatted_date
        except ValueError:
            self.logger.error(f"Date formatting error for: {date_str}")
            return date_str

    def closed(self, reason):
        self.logger.info("Closing the driver...")
        self.driver.quit()

# Run the spider
if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(MaxlinearNewsSpider)
    process.start()