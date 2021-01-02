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


class Source:
    """
    A housing data source definition
    """
    def __init__(self, key: str, name: str, required_conf: [str], spider: BaseSpider):
        """
        Initialize the data source
        :param key: A unique key that represents this source, used in options.ini
        :param name: A user-friendly name of this source
        :param required_conf: A list of required config keys
        :param spider: The spider object for scraping data
        """
        self._key = key
        self._name = name
        self._required_conf = required_conf
        self._spider = spider
        self._config = {}

    def add_config(self, name: str, value: str = "") -> None:
        """
        Add a config option
        :param name: The config option name
        :param value: The config option value
        :return: None
        """
        if name not in self._required_conf:
            logger.warning("Unexpected config option {0} pass to {1}".format(name, self._key))
        self._config[name] = value

    def verify_config(self) -> bool:
        """
        Checks to make sure all the expected config options are present
        :return: True if config is valid, false if otherwise
        """
        for key in self._required_conf:
            if key not in self._config:
                logger.error("Missing {0} option".format(key))
                return False

        return True

    def init(self) -> None:
        """
        Called after config loaded but before scrape
        :return: Nothing
        """
        self._spider.init(config=self._config)

    @property
    def key(self) -> str:
        return self._key

    @property
    def name(self) -> str:
        return self._name

    @property
    def spider(self) -> BaseSpider:
        return self._spider
