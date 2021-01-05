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
from typing import Optional
from .data_source import Source
from .spider import ScrapySpider
from .source_apartments_com import ApartmentsComSpider
from .source_craiglist import CraigslistSpider
from .source_zillow import ZillowSpider
from .cache import LocationCache
from .criteria import (Criterion,
                       CriterionLesser,
                       CriterionGreater,
                       CriterionBeds,
                       CriterionSqFt,
                       CriterionTrain,
                       ResultFormat)

logger = logging.getLogger(__name__)

# Initialize default sources
_source_list = [Source("apartments_com", "apartments.com", required_conf=["search_url"],
                       spider=ApartmentsComSpider()),
                Source("craigslist_bos", "boston.craigslist.com", required_conf=["subdomain"],
                       spider=CraigslistSpider()),
                Source("zillow", "zillow.com", required_conf=["search_url"],
                       spider=ZillowSpider())]


def get_source(key) -> Optional[Source]:
    """
    Gets a valid source from the supported list of sources
    :param key: Unique identifier representing source
    :return: Source object if found, none if invalid key
    """
    for item in _source_list:
        if item.key == key:
            return item
    return None


def init_sources() -> None:
    """
    Initialize all the sources after config data is loaded
    :return: None
    """
    logger.debug("Initializing sources...")
    for item in _source_list:
        item.init()


def get_source_list() -> list:
    """
    Gets the list of housing sources
    :return: List of housing sources
    """
    return _source_list


def set_train_data(data) -> None:
    """
    Sets the train data loaded from json
    :param data: Train data loaded from json
    :return: Nothing
    """
    Criterion.train_data = data
