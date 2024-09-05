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
import re

class MaxlinearNewsSpider(scrapy.Spider):
    name = "maxlinear_news"
    start_urls = ["https://www.maxlinear.com/news"]

    custom_settings = {
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
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()

        self.images_dir = 'images'
        self.articles_dir = 'articles'
        for directory in [self.images_dir, self.articles_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def start_requests(self):
        yield SeleniumRequest(url=self.start_urls[0], callback=self.parse, wait_time=10)

    def parse(self, response):
        self.logger.info("Starting to parse the main page...")
        self.driver.get(response.url)

        last_height = 0

        while True:
            self.driver.execute_script('window.scrollBy(0, 5000)')
            time.sleep(3)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            self.logger.info(f"New height: {new_height}, Last height: {last_height}")

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

            if stop_scroll or new_height == last_height:
                break
            else:
                last_height = new_height

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

        if formatted_date and '2020' <= formatted_date[:4] <= '2024':
            content_paragraphs = response.css('.news-content .content p::text, .news-content .content ul li::text')
            content = "\n".join(content_paragraphs.getall()).strip()

            image_metadata = []

            og_image = response.css('meta[property="og:image"]::attr(content)').get()
            if og_image:
                og_image_url = response.urljoin(og_image)
                image_info = self.download_image(og_image_url)
                if image_info:
                    image_metadata.append(image_info)

            images = response.css('.news-content img::attr(src)').getall()
            for img_url in images:
                img_url = response.urljoin(img_url)
                image_info = self.download_image(img_url)
                if image_info:
                    image_metadata.append(image_info)

            self.logger.info(f"Scraping article - Title: {title}, Date: {formatted_date}, URL: {response.url}")

            self.save_article({
                'title': title,
                'date': formatted_date,
                'content': content,
                'url': response.url,
                'images': image_metadata
            })
        else:
            self.logger.info(f"Skipping article - Date {formatted_date} not in range 2020 to 2024.")

    def download_image(self, img_url):
        img_filename = os.path.basename(img_url.split("?")[0])
        img_filepath = os.path.join(self.images_dir, img_filename)
        self.logger.info(f"Downloading image {img_url} to {img_filepath}")
        try:
            response = requests.get(img_url, timeout=10)
            response.raise_for_status()
            with open(img_filepath, 'wb') as img_file:
                img_file.write(response.content)
            return {
                'url': img_url,
                'filename': img_filename,
                'filepath': img_filepath,
                'size': len(response.content)
            }
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

    def save_article(self, article):
        # Create a valid filename from the article title
        filename = re.sub(r'[^\w\-_\. ]', '_', article['title'])
        filename = f"{article['date']}_{filename[:50]}.txt"  # Limit filename length
        filepath = os.path.join(self.articles_dir, filename)
        print(f"Saving article to {filepath}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Title: {article['title']}\n")
            f.write(f"Date: {article['date']}\n")
            f.write(f"URL: {article['url']}\n")
            f.write("Content:\n")
            f.write(f"{article['content']}\n\n")
            f.write("Images:\n")
            for image in article['images']:
                f.write(f"  - URL: {image['url']}\n")
                f.write(f"    Filename: {image['filename']}\n")
                f.write(f"    Filepath: {image['filepath']}\n")
                f.write(f"    Size: {image['size']} bytes\n")

        self.logger.info(f"Saved article to {filepath}")

    def closed(self, reason):
        self.logger.info("Closing the driver...")
        self.driver.quit()

# Run the spider
if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(MaxlinearNewsSpider)
    process.start()