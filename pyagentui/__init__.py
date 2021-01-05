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

from .ui import WebUI


def open_gui(json_file: str, char_file: str) -> None:
    """
    Opens PyAgent gui
    :param json_file: The path to the JSON file
    :param char_file: The path to the characterization data JSON file
    :return: Nothing
    """
    ui = WebUI()
    ui.open_webview(json_file=json_file, char_file=char_file)
