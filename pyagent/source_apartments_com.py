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

    def __init__(self, *a, **kw):
        super(ApartmentsComSpiderWorker, self).__init__(*a, **kw)
        self._apartment_urls = []
        self._apartment_index = 0

    def parse_apartment(self, response):
        pass

    def parse(self, response):
        # Get number of pages
        page_range_selector = ".searchResults > .pageRange ::text"
        page_range = response.css(page_range_selector).extract_first()
        page_current = 1
        page_count = 1
        if page_range:
            page_range_tokens = page_range.split(' ')
            try:
                page_current = int(page_range_tokens[1])
                page_count = int(page_range_tokens[3])
            except ValueError:
                logger.error("Could not decipher page range")
        else:
            logger.error("Could not find page range")

        set_selector = 'div#placardContainer > ul > li.mortar-wrapper'
        for apt_placard in response.css(set_selector):
            availability_selector = '.property-information-wrapper > .availability ::text'
            addr_selector = '.property-title ::attr(title)'
            price_selector = '.price-wrapper > .price-range ::text'
            phone_selector = '.phone-wrapper > .phone-link ::attr(href)'
            link_selector = '.property-link ::attr(href)'
            additional_tags = []

            availability = apt_placard.css(availability_selector).extract_first()
            if availability == "Unavailable":
                continue

            addr_title = apt_placard.css(addr_selector).extract_first()
            second_title = False
            if "Condo for Rent" in addr_title:
                additional_tags.append("Condo")
                second_title = True
            elif "Townhome for Rent" in addr_title:
                additional_tags.append("Townhome")
                second_title = True
            if second_title:
                addr_sub_selector = '.property-address ::attr(title)'
                addr_title = apt_placard.css(addr_sub_selector).extract_first()

            phone_link = apt_placard.css(phone_selector).extract_first()
            phone_number = None
            if phone_link:
                phone_number = phone_link.replace("tel:", "")
            apartment_link = apt_placard.css(link_selector).extract_first()
            self._apartment_urls.append(apartment_link)
            yield {
                "address": addr_title,
                "price": apt_placard.css(price_selector).extract_first(),
                "phone": phone_number,
                "availability": availability,
                "additional_tags": additional_tags,
                "link": apartment_link,
                "page": page_current
            }

        # Go to next page if possible
        if page_current < page_count:
            next_page_url = self.start_urls[0] + "{0}/".format(page_current+1)
            request = scrapy.Request(url=next_page_url)
            yield request
        # Start parsing individual apartments
        else:
            self._apartment_index = 0
            next_page_url = self._apartment_urls[self._apartment_index]
            request = scrapy.Request(url=next_page_url, callback=self.parse_apartment)
            yield request

