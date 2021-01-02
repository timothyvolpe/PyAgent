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


class ApartmentsComSpider(ScrapySpider):
    """
    Scrapy spider for scraping craigslist
    """

    def __init__(self):
        ScrapySpider.__init__(self, ApartmentsComSpiderWorker)

    def init(self, config) -> None:
        self._spider.name = "apartments_com_spider"
        start_urls = "https://www.apartments.com/" + config["search_url"]
        self._spider.start_urls.append(start_urls)


class ApartmentsComSpiderWorker(scrapy.Spider):
    """
    scrapy spider class for scraping apartments.com search page
    """
    allowed_domains = ["apartments.com"]
    start_urls = []

    def parse(self, response):
        set_selector = 'div#placardContainer > ul > li.mortar-wrapper'
        for apt_placard in response.css(set_selector):
            addr_selector = '.property-title ::attr(title)'
            price_selector = '.price-wrapper > .price-range ::text'
            yield {
                'address': apt_placard.css(addr_selector).extract_first(),
                'price': apt_placard.css(price_selector).extract_first()
            }
