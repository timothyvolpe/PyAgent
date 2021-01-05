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
from .spider import ScrapySpider, BaseSpider
from .cache import LocationCache

logger = logging.getLogger(__name__)

# Maximum number of pages to scrape
MAX_SCRAPE_PAGES = 7


class ZillowSpider(ScrapySpider):
    """
    Scrapy spider for scraping zillow
    """

    def __init__(self):
        ScrapySpider.__init__(self, ZillowSpiderWorker)

    def init(self, config) -> None:
        self._spider.name = "zillow_spider"
        start_urls = "https://www.zillow.com/" + config["search_url"]
        self._spider.start_urls.append(start_urls)


class ZillowSpiderWorker(scrapy.Spider):
    """
    scrapy spider class for scraping craigslist.com search page
    """
    allowed_domains = ["zillow.com"]
    start_urls = []

    def __init__(self, *a, **kw):
        super(ZillowSpiderWorker, self).__init__(*a, **kw)
        self._last_nom_reqest = 0
        self._pages_scraped = 0
        self._first_search = ZillowSpiderWorker.start_urls[0]

        self.download_delay = 5

    def parse(self, response):
        housing_list = response.css("ul.photo-cards")
        if not housing_list:
            logger.error("Invalid zillow page")
        else:
            self._pages_scraped += 1
            list_cards = housing_list[0].css("article.list-card")
            # Check to make sure details are present
            details_item = housing_list[0].css(".list-card-details > li")
            if not details_item:
                logger.critical("Did not find any card details...")
                return
            for card in list_cards:
                address = card.css(".list-card-addr ::text").extract_first()
                # If theres a pipe in the middle, use the right side
                tokens = address.split('|')
                if len(tokens) > 1:
                    address = tokens[1]
                address = BaseSpider.simplify_address(BaseSpider.cleanup_garbage(address))

                # Check if address is in cache
                location = LocationCache.get_location(address)
                # Make sure address is valid
                if location is None and not LocationCache.entry_present(address):
                    time_since_last = (time.time() - self._last_nom_reqest)
                    if time_since_last < BaseSpider.NOMINATIM_REQUEST_DELAY:
                        time.sleep(BaseSpider.NOMINATIM_REQUEST_DELAY - time_since_last)
                    try:
                        geolocator = gc.Nominatim(user_agent="pyagent")
                        location_obj = geolocator.geocode(address)
                    except geopy.exc.ConfigurationError as e:
                        location_obj = None
                    self._last_nom_reqest = time.time()
                    if location_obj is None:
                        logger.error("Could not get geospatial coordinates of address '{0}', "
                                     "see source at {1}".format(address, response.request.url))
                        LocationCache.add_to_cache(address, None)
                        continue
                    location = (location_obj.latitude, location_obj.longitude)
                    LocationCache.add_to_cache(address, location)

                # Get the link to the address
                link = card.css(".list-card-link ::attr(href)").extract_first()
                if "/b/" in link:
                    link = "https://www.zillow.com" + link
                # Get the rent
                price_str = card.css(".list-card-price ::text").extract_first()
                price = None
                if not price_str:
                    logger.warning("Could not find rent for apartment (link: {0}), checking details".format(link))
                else:
                    price_str = price_str.replace("$", "").replace(",", "").replace("+", "").replace("/mo", "")
                    try:
                        price = int(price_str)
                    except ValueError:
                        pass

                # Get the apartment details
                details = card.css(".list-card-details > li")
                details_str = ""
                for detail in details:
                    if details_str != "":
                        details_str += " "
                    details_str += BaseSpider.cleanup_garbage(detail.extract())

                # Tokenize and extract info
                detail_tokens = details_str.split(' ')
                bed_count = None
                bath_count = None
                rent = None
                sqft = None
                for idx, label in enumerate(detail_tokens):
                    if len(label) <= 0:
                        continue
                    label = label.replace(",", "")
                    if label == "bds" and idx != 0:
                        try:
                            bed_count = int(detail_tokens[idx-1])
                        except ValueError:
                            logger.error("Found 'bds' label but integer did not preceeed it (link: {0})".format(link))
                            continue
                    elif label == "ba" and idx != 0:
                        try:
                            bath_count = float(detail_tokens[idx-1])
                        except ValueError:
                            logger.error("Found 'ba' label but integer did not preceeed it (link: {0})".format(link))
                            continue
                    elif label == "sqft" and idx != 0:
                        if detail_tokens[idx-1] != "--":
                            try:
                                sqft = int(detail_tokens[idx-1].replace(",", ""))
                            except ValueError:
                                logger.error("Found 'sqft' label but integer did not preceeed it (link: {0})".format(link))
                                continue
                    elif label[0] == "$":
                        rent_str = label.replace("$", "").replace(",", "").replace("+", "").replace("/mo", "")
                        try:
                            rent = int(rent_str)
                            continue
                        except ValueError:
                            logger.error("Found possible '{0}' rent but could not convert to integer (link: {1})"
                                         .format(label[0], link))
                            continue

                yield {
                    "address": address,
                    "neighborhood": None,
                    "rent": price if price else rent,
                    "deposit": None,
                    "sqft": sqft,
                    "beds": bed_count,
                    "baths_str": bath_count,
                    "unit": None,
                    "coordinates": location,
                    "additional": None,
                    "link": link,
                    "source": "zillow.com"
                }

            # Get the page links and move to next page
            if self._pages_scraped < MAX_SCRAPE_PAGES:
                pagination = response.css(".search-pagination > nav > ul > li")
                if pagination:
                    next_button = False
                    for page_item in pagination:
                        item_html = page_item.extract()
                        if "PaginationNumberItem" in item_html:
                            disabled = page_item.css("::attr(disabled)")
                            if disabled:
                                next_button = True
                                continue
                            elif next_button:
                                next_page = page_item.css("li > a ::text").extract_first()
                                if next_page:
                                    # Add pagination to search query
                                    if "/?searchQueryState" in response.request.url:
                                        pagination_query = '"pagination":{{"currentPage":{0}}},'.format(next_page)
                                        idx = self._first_search.find("/?searchQueryState={")+len("/?searchQueryState={")
                                        new_url = self._first_search[:idx] + pagination_query + self._first_search[idx:]
                                        request = scrapy.Request(url=new_url, headers=response.request.headers, meta={'dont_merge_cookies': True})
                                        yield request
                                        return
