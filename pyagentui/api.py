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
import json
import os
from shutil import copyfile

logger = logging.getLogger(__name__)

WEB_DATA_DIR = "web/data"


class WebAPI:
    """
    Handles communication from JavaScript to Python
    """
    def __init__(self, char_file: str):
        """
        Constructor
        :param json_file: The path to the scraped data JSON file
        :param char_file: The path to the characterization data JSON file
        """
        self._char_file = char_file
        self._webview_window = None
        self._page_ready = False

        self._favorites = {}
        self._rejections = {}

    def reload_page(self) -> None:
        """
        Called when a new page is loaded, resets all page-specific parameters
        :return: Nothing
        """
        self._page_ready = False

    def ready(self) -> None:
        """
        Called from JavaScript, signifies the page is done loading
        :return: Nothing
        """
        self._page_ready = True
        logger.debug("Webpage ready!")

        # Copy the JSON data to the web directory
        found_char_file = False
        if self._char_file:
            copyfile(self._char_file, WEB_DATA_DIR + "/characterization.json")
            found_char_file = True

        # Tell javascript there is JSON data available
        if found_char_file:
            self._webview_window.evaluate_js(f"load_json(char_avail=true)")
        else:
            self._webview_window.evaluate_js(f"load_json(char_avail=false)")


    def add_to_favorites(self, hash_val, data) -> bool:
        """
        Adds a property to the favorite lists
        :param hash_val: The hash value of the entry
        :param data: The housing data of the entry
        :return: True if successfully added, false if otherwise
        """
        if hash_val not in self._favorites:
            logger.info("Adding {0} to favorites".format(hash_val))
            self._favorites[hash_val] = data
            return True
        else:
            return False

    def add_to_rejections(self, hash_val, data) -> bool:
        """
        Adds a property to the favorite lists
        :param hash_val: The hash value of the entry
        :param data: The housing data of the entry
        :return: True if successfully added, false if otherwise
        """
        if hash_val not in self._rejections:
            logger.info("Adding {0} to rejections".format(hash_val))
            self._rejections[hash_val] = data
            return True
        else:
            return False

    def remove_from_favorites(self, hash_val):
        """
        Tries to remove an item from the favorites
        :param hash_val: The hash value to remove
        :return: Nothing
        """
        if hash_val in self._favorites:
            logger.info("Removing {0} from favorites".format(hash_val))
            del self._favorites[hash_val]

    def remove_from_rejections(self, hash_val):
        """
        Tries to remove an item from the rejections
        :param hash_val: The hash value to remove
        :return: Nothing
        """
        if hash_val in self._rejections:
            logger.info("Removing {0} from rejections".format(hash_val))
            del self._rejections[hash_val]

    @property
    def window(self):
        return self._webview_window

    @window.setter
    def window(self, window):
        self._webview_window = window

    @property
    def is_ready(self) -> bool:
        return self._page_ready
