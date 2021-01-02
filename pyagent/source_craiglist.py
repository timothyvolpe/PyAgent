"""
    PyAgent - Python program for aggregating housing info
    Copyright (C) 2021 Timothy Volpe

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import scrapy
from .spider import ScrapySpider

logger = logging.getLogger(__name__)


class CraigslistSpider(ScrapySpider):
    """
    Scrapy spider for scraping craigslist
    """

    def __init__(self):
        ScrapySpider.__init__(self, CraigslistSpiderWorker)

    def init(self, config) -> None:
        self._spider.name = "craiglist_spider"
        start_urls = "https://" + config["subdomain"] + ".craigslist.com"
        self._spider.start_urls.append(start_urls)


class CraigslistSpiderWorker(scrapy.Spider):
    """
    scrapy spider class for scraping craigslist.com search page
    """
    allowed_domains = ["craigslist.com"]
    start_urls = []

    def parse(self, response):
        pass
