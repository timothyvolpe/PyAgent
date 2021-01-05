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
    def __init__(self, json_file: str, char_file: str):
        """
        Constructor
        :param json_file: The path to the scraped data JSON file
        :param char_file: The path to the characterization data JSON file
        """
        self._json_file = json_file
        self._char_file = char_file
        self._webview_window = None
        self._page_ready = False

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
        if self._json_file:
            if not os.path.exists(WEB_DATA_DIR):
                os.mkdir(WEB_DATA_DIR)
            copyfile(self._json_file, WEB_DATA_DIR + "/scraped_data.json")
            # Copy the characterization JSON
            found_char_file = False
            if self._char_file:
                copyfile(self._char_file, WEB_DATA_DIR + "/characterization.json")
                found_char_file = True
            # Tell javascript there is JSON data available
            self._webview_window.evaluate_js(f"load_json(housing_avail=true, "
                                             f"char_avail={'true' if found_char_file else 'false'})")
        else:
            self._webview_window.evaluate_js(f"load_json(housing_avail=false, char_avail=false)")

    @property
    def window(self):
        return self._webview_window

    @window.setter
    def window(self, window):
        self._webview_window = window

    @property
    def is_ready(self) -> bool:
        return self._page_ready
