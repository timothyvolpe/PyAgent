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

logger = logging.getLogger(__name__)


class BaseSpider(scrapy.Spider):
    """
    Base scrapy class
    """
    name = "apartments_crawler"
    start_urls = ""

    def init(self, config) -> None:
        """
        Assign config options
        :param config: List of config options
        :return:
        """
        pass

    def parse(self, response):
        pass