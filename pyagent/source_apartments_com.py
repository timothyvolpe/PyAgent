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
import geopy
import re
import geopy.geocoders as gc
import time
from .cache import LocationCache

from .spider import ScrapySpider

logger = logging.getLogger(__name__)

# Turn off for quick testing
DO_MULTIPLE_PAGES = True
# Set the maximum number of apartment pages to check in one session
# Set to 0 for infinite
MAX_APARTMENT_SCRAPES = 0
# Must be greater than 1
NOMINATIM_REQUEST_DELAY = 1


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
        self._additional_tags = []
        self._locations = []
        self._addresses = []
        self._apartment_index = 0
        self._last_nom_reqest = 0

    def cleanup_garbage(self, dirty: str) -> str:
        """
        Clean up HTML garbage from tag text. Removes excess whitespace, leading and trailing whitespace, and some
        control characters
        :param dirty: The dirty string
        :return: Cleaner string
        """
        return ' '.join(dirty.split()).replace("\n", "").replace("\r", "").lstrip().rstrip()

    def simplify_address(self, addr: str) -> str:
        """
        Simplifies the housing address by removing things such as "Unit"
        :param addr: The verbose address
        :return: The simplified address
        """
        simplified = addr.replace("Unit", "")
        return ' '.join(simplified.split()).rstrip().lstrip()

    def parse_apartment(self, response):
        if self._apartment_index >= MAX_APARTMENT_SCRAPES and MAX_APARTMENT_SCRAPES != 0:
            return

        property_name = response.css(".propertyNameRow > .propertyName ::text").extract_first()
        # remove excess whitespace and control characters
        if property_name:
            property_name = self.cleanup_garbage(property_name)
        property_addr = response.css(".propertyAddressRow > .propertyAddress > h2").extract_first()
        if property_addr:
            property_addr = self.cleanup_garbage(property_addr.replace("<span>", "").replace("</span>", "") \
                .replace("<h2>", "").replace("</h2>", ""))
        property_neighborhood = response.css(".neighborhoodAddress > a.neighborhood ::text").extract_first()

        rent_str = response.css(".rentalGridRow > .rent ::text").extract_first()
        if rent_str:
            rent_str = self.cleanup_garbage(rent_str)
            try:
                rent_val = int(rent_str.replace("$", "").replace(",", ""))
                rent_str = str(rent_val)
            except ValueError:
                pass
        deposit_str = response.css(".rentalGridRow > .deposit ::text").extract_first()
        if deposit_str:
            deposit_str = self.cleanup_garbage(deposit_str)
            try:
                deposit_val = int(deposit_str.replace("$", "").replace(",", ""))
                deposit_str = str(deposit_val)
            except ValueError:
                pass
        sqft_str = response.css(".rentalGridRow > .sqft ::text").extract_first()
        if sqft_str:
            sqft_str = self.cleanup_garbage(sqft_str)
            try:
                sqft_val = int(sqft_str.replace(",", "").replace("Sq Ft", ""))
                sqft_str = str(sqft_val)
            except ValueError:
                pass

        beds_str = response.css(".rentalGridRow > .beds > .longText ::text").extract_first()
        if beds_str:
            beds_str = self.cleanup_garbage(beds_str)
            integers = re.search(r'\d+', beds_str)
            if integers:
                beds_val = int(integers.group())
                beds_str = str(beds_val)

        baths_str = response.css(".rentalGridRow > .baths > .longText ::text").extract_first()
        if baths_str:
            baths_str = self.cleanup_garbage(baths_str)
            integers = re.search(r'\d+', baths_str)
            if integers:
                baths_val = int(integers.group())
                baths_str = str(baths_val)

        location = self._locations[self._apartment_index]
        address = self._addresses[self._apartment_index]
        additional_tags = self._additional_tags[self._apartment_index]

        yield {
            "address": address,
            "neighborhood": property_neighborhood,
            "rent": rent_str,
            "deposit": deposit_str,
            "sqft": sqft_str,
            "beds": beds_str,
            "baths_str": baths_str,
            "coordinates": location,
            "additional": additional_tags,
            "link": response.request.url,
            "source": "apartments.com"
        }

        # Move to the next one
        if self._apartment_index+1 < len(self._apartment_urls):
            self._apartment_index += 1
            next_page_url = self._apartment_urls[self._apartment_index]
            request = scrapy.Request(url=next_page_url, callback=self.parse_apartment)
            yield request

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
                logger.error("Could not decipher page range, see source at {0}".format(response.request.url))
        else:
            logger.error("Could not find page range, see source at {0}".format(response.request.url))

        set_selector = 'div#placardContainer > ul > li.mortar-wrapper'
        for apt_placard in response.css(set_selector):
            availability_selector = '.property-information-wrapper > .availability ::text'
            price_selector = '.price-wrapper > .price-range ::text'
            link_selector = '.property-link ::attr(href)'

            availability = apt_placard.css(availability_selector).extract_first()
            if availability == "Unavailable":
                continue

            # Get the address
            addr_selector = '.property-title ::attr(title)'
            addr_title = apt_placard.css(addr_selector).extract_first()
            second_title = False
            additional_tags = []
            if "Condo for Rent" in addr_title:
                additional_tags.append("Condo")
                second_title = True
            elif "Townhome for Rent" in addr_title:
                additional_tags.append("Townhome")
                second_title = True
            if second_title:
                addr_sub_selector = '.property-address ::attr(title)'
                addr_title = apt_placard.css(addr_sub_selector).extract_first()

            # Check if address is in cache
            location = LocationCache.get_location(addr_title)
            # Make sure address is valid
            if location is None:
                time_since_last = (time.time() - self._last_nom_reqest)
                if time_since_last < NOMINATIM_REQUEST_DELAY:
                    time.sleep(NOMINATIM_REQUEST_DELAY - time_since_last)
                try:
                    geolocator = gc.Nominatim(user_agent="pyagent")
                    location_obj = geolocator.geocode(addr_title)
                except geopy.exc.ConfigurationError as e:
                    location_obj = None
                self._last_nom_reqest = time.time()
                if location_obj is None:
                    logger.error("Could not get geospatial coordinates of address '{0}', "
                                 "see source at {1}".format(addr_title, response.request.url))
                    continue
                location = (location_obj.latitude, location_obj.longitude)
                LocationCache.add_to_cache(addr_title, location)

            apartment_link = apt_placard.css(link_selector).extract_first()
            self._apartment_urls.append(apartment_link)
            self._additional_tags.append(additional_tags)
            self._locations.append(location)
            self._addresses.append(addr_title)

        # Go to next page if possible
        if page_current < page_count and DO_MULTIPLE_PAGES:
            next_page_url = self.start_urls[0] + "{0}/".format(page_current+1)
            request = scrapy.Request(url=next_page_url)
            yield request
        # Start parsing individual apartments
        else:
            self._apartment_index = 0
            next_page_url = self._apartment_urls[self._apartment_index]
            request = scrapy.Request(url=next_page_url, callback=self.parse_apartment)
            yield request

