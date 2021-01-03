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


class BaseSpider:
    """
    Base source spider class
    """
    name = "apartments_crawler"
    start_urls = ""

    def __init__(self):
        pass

    def init(self, config) -> None:
        """
        Assign config options
        :param config: List of config options
        :return:
        """
        pass


class ScrapySpider(BaseSpider):
    """
    A scrapy spider source class
    """

    def __init__(self, spider: scrapy.Spider):
        self._spider = spider

    def init(self, config) -> None:
        pass

    @property
    def scrapy_spider(self) -> scrapy.Spider:
        """
        Get the scrapy spider object
        :return: Scrapy spider object
        """
        return self._spider
