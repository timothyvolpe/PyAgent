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
import re

logger = logging.getLogger(__name__)


class BaseSpider:
    """
    Base source spider class
    """
    name = "apartments_crawler"
    start_urls = ""

    NOMINATIM_REQUEST_DELAY = 1

    @staticmethod
    def cleanup_garbage(dirty: str) -> str:
        """
        Clean up HTML garbage from tag text. Removes excess whitespace, leading and trailing whitespace, and some
        control characters
        :param dirty: The dirty string
        :return: Cleaner string
        """
        cleanr = re.compile('<.*?>')
        dirty_notags = re.sub(cleanr, '', dirty)
        return ' '.join(dirty_notags.split()).replace("\n", "").replace("\r", "").lstrip().rstrip()

    @staticmethod
    def simplify_address(addr: str) -> str:
        """
        Simplifies the housing address by removing things such as "Unit"
        :param addr: The verbose address
        :return: The simplified address
        """
        # Find pound sign and remove word
        idx = addr.find('#')
        while idx > -1:
            for i in range(idx, len(addr)):
                if addr[i] == ' ' or addr[i] == ',':
                    # Remove that part of string
                    if idx > 0:
                        addr = addr[:idx-1] + addr[i:]
                    else:
                        addr = addr[:idx] + addr[i:]
                    break
            idx = addr.find('#')

        def remove_excess_word(word, addr) -> str:
            # Find word and remove
            idx = addr.find(word)
            first_space = False
            while idx > -1:
                for i in range(idx, len(addr)):

                    if addr[i] == ' ' or addr[i] == ',':
                        if not first_space and not addr[i] == ',':
                            first_space = True
                            continue
                        else:
                            # Remove that part of string
                            if idx > 0:
                                addr = addr[:idx - 1] + addr[i:]
                            else:
                                addr = addr[:idx] + addr[i:]
                            break
                idx = addr.find(word)
            return addr

        addr = remove_excess_word("APT", addr)
        addr = remove_excess_word("FLOOR", addr)

        return ' '.join(addr.split()).rstrip().lstrip()

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
