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
import time
import geopy
import geopy.geocoders as gc
from .cache import LocationCache
from .spider import ScrapySpider, BaseSpider

logger = logging.getLogger(__name__)

# Set the maximum number of apartment pages to check in one session
# Set to 0 for infinite
MAX_HOUSING_SCRAPES = 10

class CraigslistSpider(ScrapySpider):
    """
    Scrapy spider for scraping craigslist
    """

    def __init__(self):
        ScrapySpider.__init__(self, CraigslistSpiderWorker)

    def init(self, config) -> None:
        self._spider.name = "craiglist_spider"

        start_urls = "https://" + config["subdomain"] + ".craigslist.org/" + config["search_url"]
        self._spider.start_urls.append(start_urls)


class CraigslistSpiderWorker(scrapy.Spider):
    """
    scrapy spider class for scraping craigslist.com search page
    """
    allowed_domains = ["craigslist.org"]
    start_urls = []

    def __init__(self, *a, **kw):
        super(CraigslistSpiderWorker, self).__init__(*a, **kw)

        self._last_nom_reqest = 0

        self._housing_index = 0
        self._housing_link_list = []

    def parse_housing(self, response):
        housing_data = self._housing_link_list[self._housing_index]
        latitude = response.css("#map ::attr(data-latitude)").extract_first()
        longitude = response.css("#map ::attr(data-longitude)").extract_first()
        coordinates = None
        if latitude and longitude:
            try:
                coordinates = [float(latitude), float(longitude)]
            except ValueError:
                logger.error("Invalid floating-point coordinates ({0}, {1})".format(latitude, longitude))

        # Check if coords are in cache
        address = LocationCache.get_address(coordinates)
        if address is None and not LocationCache.entry_present_reverse(coordinates):
            time_since_last = (time.time() - self._last_nom_reqest)
            if time_since_last < BaseSpider.NOMINATIM_REQUEST_DELAY:
                time.sleep(BaseSpider.NOMINATIM_REQUEST_DELAY - time_since_last)
            try:
                geolocator = gc.Nominatim(user_agent="pyagent")
                address_obj = geolocator.reverse(query=geopy.point.Point(coordinates[0], coordinates[1]), exactly_one=True)
            except geopy.exc.ConfigurationError as e:
                address_obj = None

            if address_obj is None:
                logger.error("Could not get nearby address of coordinates '({0}, {1})', "
                             "see source at {1}".format(coordinates[0], coordinates[1]))
                LocationCache.add_to_reverse_cache(coordinates, None)
                address = None
            found_address = address_obj.address
            # Format address (remove housing number, make more brief)
            address_tokens = found_address.split(',')
            if len(address_tokens) >= 4:
                address_tokens = address_tokens[0:4]
                found_address = ', '.join(address_tokens).rstrip().lstrip()
            found_address = "Near " + found_address
            LocationCache.add_to_reverse_cache(coordinates, found_address)
            address = found_address

            self._last_nom_reqest = time.time()

        # Get post ID
        post_infos = response.css("p.postinginfo ::text").extract()
        post_id = None
        for info in post_infos:
            if "post id:" in info:
                info = info.replace("post id: ", "").lstrip().rstrip()
                try:
                    post_id = int(info)
                except ValueError:
                    logger.error("Invalid post id '{0}'".format(post_id))

        # Yield info
        yield {
            "uid": BaseSpider.get_next_uid(),
            "address": address,
            "neighborhood": housing_data["hood"],
            "rent": housing_data["price"],
            "deposit": None,
            "sqft": None,
            "beds": None,
            "baths_str": None,
            "unit": post_id,
            "coordinates": coordinates,
            "additional": None,
            "link": response.request.url,
            "source": "craigslist.com"
        }
        # Go to next
        if self._housing_index+1 < len(self._housing_link_list):
            if self._housing_index+1 >= MAX_HOUSING_SCRAPES and MAX_HOUSING_SCRAPES != 0:
                return
            self._housing_index += 1
            next_page_url = self._housing_link_list[self._housing_index]["link"]
            request = scrapy.Request(url=next_page_url, callback=self.parse_housing,
                                     meta={'dont_merge_cookies': True})
            yield request

    def parse(self, response):
        # Try to get result rows
        result_rows = response.css(".rows > .result-row")
        if not result_rows:
            logger.error("No results found on page")
            return

        # Find each house
        price_text = None
        hood_text = None
        for row in result_rows:
            price_text = row.css("span.result-price ::text").extract_first()
            if price_text:
                price_text = price_text.replace("$", "").replace(",", "")
            hood_text = row.css("span.result-hood ::text").extract_first()
            if hood_text:
                hood_text = hood_text.lstrip().rstrip()
            post_link = row.css(".result-heading > a.result-title ::attr(href)").extract_first()

            if post_link:
                housing_data = {
                    "link": post_link,
                    "price": price_text,
                    "hood": hood_text
                }
                self._housing_link_list.append(housing_data)

        # Start parsing housing
        if self._housing_link_list:
            self._housing_index = 0
            next_page_url = self._housing_link_list[self._housing_index]["link"]
            request = scrapy.Request(url=next_page_url, callback=self.parse_housing,
                                     meta={'dont_merge_cookies': True})
            yield request
