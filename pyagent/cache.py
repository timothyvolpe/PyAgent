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
import os
import json
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_DIR = "cache"
LOCATION_CACHE = "location.json"
LOCATION_CACHE_REVERSE = "location_reverse.json"

import hashlib
from base64 import b64encode


class LocationCache:
    """
    Stores address location data
    """
    location_data = None
    location_reverse_data = None
    cache_path = CACHE_DIR + "\\" + LOCATION_CACHE
    cache_path_rev = CACHE_DIR + "\\" + LOCATION_CACHE_REVERSE

    @staticmethod
    def init_cache() -> None:
        logger.debug("Reading location cache from disk")
        # Check if cache folder exists, create if needed
        if not os.path.isdir(CACHE_DIR):
            os.mkdir(CACHE_DIR)

        # Read the cache into memory
        if os.path.isfile(LocationCache.cache_path):
            try:
                with open(LocationCache.cache_path) as json_file:
                    LocationCache.location_data = json.load(json_file)
            except OSError as e:
                logger.critical("Failed to read cache from disk: {0}".format(e))
        else:
            LocationCache.location_data = {}
        # Read reverse cache into memory
        if os.path.isfile(LocationCache.cache_path_rev):
            try:
                with open(LocationCache.cache_path_rev) as json_file:
                    LocationCache.location_reverse_data = json.load(json_file)
            except OSError as e:
                logger.critical("Failed to read cache from disk: {0}".format(e))
        else:
            LocationCache.location_reverse_data = {}

    @staticmethod
    def save_cache() -> None:
        """
        Save the cache to disk
        :return: Nothing
        """
        try:
            with open(LocationCache.cache_path, 'w') as outfile:
                outfile.seek(0)
                json.dump(LocationCache.location_data, outfile)
                outfile.truncate()
                logger.info("Saving location cache...")
            with open(LocationCache.cache_path_rev, 'w') as outfile:
                outfile.seek(0)
                json.dump(LocationCache.location_reverse_data, outfile)
                outfile.truncate()
                logger.info("Saving location reverse cache...")
        except OSError as e:
            logger.critical("Failed to write cache to disk: {0}".format(e))

    @staticmethod
    def get_address(coords: list) -> Optional[dict]:
        """
        Retrieves an approximate address from the given set of coordinates
        :param coords: Coordinates as 2 floats, [lat, long]
        :return: Address dict if in cache, None otherwise
        """
        uid = hashlib.sha256(str(coords[0]).encode() + str(coords[1]).encode()).hexdigest()
        if uid in LocationCache.location_reverse_data:
            return LocationCache.location_reverse_data[uid]
        return None

    @staticmethod
    def get_location(addr: str):
        """
        Retrieves a location from the cache if it exists
        :param addr: The address string
        :return: Coordinates (lat, log) if in cache, None otherwise
        """
        if addr in LocationCache.location_data:
            return LocationCache.location_data[addr]
        return None

    @staticmethod
    def entry_present(addr: str) -> bool:
        """
        Checks if there is an entry in the cache for the given address
        :param addr: The address to look up
        :returns: True if an entry was found, False if otherwise
        """
        return addr in LocationCache.location_data

    @staticmethod
    def entry_present_reverse(coords: list) -> bool:
        """
         Checks if there is an entry in the cache for the given coords
        :param coords: The coords to look up
        :return: True if an entry was found, False if otherwise
        """
        uid = hashlib.sha256(str(coords[0]).encode() + str(coords[1]).encode()).hexdigest()
        return uid in LocationCache.location_reverse_data

    @staticmethod
    def add_to_cache(addr: str, location: (float, float)) -> None:
        """
        Adds a location to the cache
        :param addr: The address string
        :param location: The coordinates, (lat, long)
        :return: Nothing
        """
        LocationCache.location_data[addr] = location

    @staticmethod
    def add_to_reverse_cache(coords: list, addr: str) -> None:
        """
        Adds coordinates to the cache
        :param coords: The coordinates
        :param addr: The address near the coordinates
        :return: Nothing
        """
        uid = hashlib.sha256(str(coords[0]).encode() + str(coords[1]).encode()).hexdigest()
        LocationCache.location_reverse_data[uid] = addr
