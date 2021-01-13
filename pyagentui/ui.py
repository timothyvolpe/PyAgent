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

import webview
from .api import WebAPI


class WebUI:
    def __init__(self):
        pass

    def open_webview(self, char_file: str):
        """
        Opens the pywebview window
        :param char_file: The path to the characterization data JSON file
        :return:
        """
        api = WebAPI(char_file)
        window = webview.create_window("PyAgent", "web/index.html", width=1600, height=900, js_api=api)
        api.window = window
        webview.start(debug=True, gui="edgechromium", http_server=True)
        api.save_lists()
