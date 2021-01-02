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
from .spider import BaseSpider

logger = logging.getLogger(__name__)


class ApartmentsComSpider(BaseSpider):
    """
    scrapy spider class for scraping apartments.com search page
    """
    name = "apartments_crawler"
    start_urls = "https://www.apartments.com/"

    def init(self, config) -> None:
        """
        Assign config options
        :param config: List of config options
        :return:
        """
        self.start_urls = self.start_urls + config["search_url"]

    def parse(self, response):
        pass
