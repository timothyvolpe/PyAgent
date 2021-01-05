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

import haversine
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ResultFormat(Enum):
    Generic = 1,
    Currency = 2,
    SquareFoot = 3,
    Bedrooms = 4,
    Bathrooms = 5,
    Miles = 6


class Criterion:
    """
    Base housing characterization criterion
    """

    train_data = []

    @staticmethod
    def format_result(result_format: ResultFormat, info: str):
        """
        Formats result info
        :param result_format: The format to use
        :param info: The result info string
        :return: Formatted result info string
        """
        if result_format == ResultFormat.Generic:
            return info
        elif result_format == ResultFormat.Currency:
            return "${0}".format(info)
        elif result_format == ResultFormat.SquareFoot:
            return "{0} sqft".format(info)
        elif result_format == ResultFormat.Bedrooms:
            return "{0} Bedrooms".format(info)
        elif result_format == ResultFormat.Bathrooms:
            return "{0} Bath".format(info)
        elif result_format == ResultFormat.Miles:
            return "{0} mi".format(info)
        else:
            logger.warning("Invalid result format passed to criterion: {0}!".format(result_format))
            return info

    def __init__(self, name: str, key: str, weight: int, result_format: ResultFormat = ResultFormat.Generic,
                 required: bool = False):
        """
        Constructor
        :param name: The user-facing name of the criterion
        :param key: The key from the scrape data to evaluate
        :param weight: The weight of the criterion in points, ex. 100 means it will contribute at most 100 points
        :param result_format: How to format the result info string
        :param required: If the criterion is required. If required, when it cannot be evaluated the housing will be
        discarded. When false, if the criterion cannot be evaluated, then it simply will not be considered.
        """
        self._name = name
        self._key = key
        self._weight = weight
        self._required = required
        self._result_format = result_format
        self._result_info = None

    def evaluate(self, data) -> float:
        pass

    @staticmethod
    def map_to_range(value, lower, upper, rating_max):
        """
        Maps an integer to the score range
        :param value: The integer value to map
        :param lower: The lower bounds of the range
        :param upper: The upper bounds of the  range
        :param rating_max: The maximum rating (minimum is always 0)
        :return:
        """
        if value < lower:
            return 0
        if value > upper:
            return rating_max
        scale_factor = rating_max / (upper-lower)
        return (value - lower)*scale_factor

    @property
    def name(self) -> str:
        return self._name

    @property
    def key(self) -> str:
        """
        Returns the requested scrape data key
        :return: Requested scrape data key
        """
        return self._key

    @property
    def weight(self) -> int:
        return self._weight

    @property
    def result_info(self):
        """
        Returns info about the result, such as the value that was used for the evaluation
        :return: Info about result
        """
        return self._result_info


class CriterionGreater(Criterion):
    """
    Housing characterization criterion where greater is better
    """
    def __init__(self, name: str, key: str, weight: int, lower: int, upper: int,
                 result_format: ResultFormat = ResultFormat.Generic, required: bool = False, maximum=None):
        """
        :param name: The user-facing name of the criterion
        :param key: The key from the scrape data to evaluate, must be integer
        :param weight: The weight of the criterion in points, ex. 100 means it will contribute at most 100 points
        :param lower: The lower bounds to map the rating range
        :param upper: The upper bounds to map the rating range
        :param result_format: How to format the result info string
        :param required: If the criterion is required. If required, when it cannot be evaluated the housing will be
        discarded. When false, if the criterion cannot be evaluated, then it simply will not be considered.
        :param maximum: The maximum value for the criterion, above which it is not considered. None means no max
        """
        Criterion.__init__(self, name, key, weight, result_format, required)
        self._maximum = maximum
        self._lower = lower
        self._upper = upper

    def evaluate(self, data) -> float:
        if data is not None:
            try:
                value = float(data)
                self._result_info = Criterion.format_result(self._result_format, value)
                if self._maximum is not None and value > self._maximum:
                    return -1
                return Criterion.map_to_range(value, self._lower, self._upper, self._weight)
            except ValueError:
                self._result_info = data
                return -1
        else:
            return -1


class CriterionLesser(Criterion):
    """
    Housing characterization criterion where lesser is better
    """
    def __init__(self, name: str, key: str, weight: int, lower: int, upper: int,
                 result_format: ResultFormat = ResultFormat.Generic, required: bool = False, minimum=None):
        """
        :param name: The user-facing name of the criterion
        :param key: The key from the scrape data to evaluate, must be integer
        :param weight: The weight of the criterion in points, ex. 100 means it will contribute at most 100 points
        :param lower: The lower bounds to map the rating range
        :param upper: The upper bounds to map the rating range
        :param result_format: How to format the result info string
        :param required: If the criterion is required. If required, when it cannot be evaluated the housing will be
        discarded. When false, if the criterion cannot be evaluated, then it simply will not be considered.
        :param minimum: The minimum value for the criterion, below which it is not considered. None means no min
        """
        Criterion.__init__(self, name, key, weight, result_format, required)
        self._minimum = minimum
        self._lower = lower
        self._upper = upper

    def evaluate(self, data) -> float:
        if data is not None:
            try:
                value = float(data)
                self._result_info = Criterion.format_result(self._result_format, value)
                if self._minimum is not None and value < self._minimum:
                    return -1
                return self._weight - Criterion.map_to_range(value, self._lower, self._upper, self._weight)
            except ValueError:
                self._result_info = data
                return -1
        else:
            return -1


class CriterionSqFt(CriterionGreater):
    """
    Housing criterion for square footage, but filters out fake values.
    """
    def evaluate(self, data) -> float:
        if data == "999" or data == "9999":
            return 0
        result = CriterionGreater.evaluate(self, data)
        return result


class CriterionBeds(CriterionLesser):
    """
    Housing criterion for number of beds. Factors in "Studio" etc.
    """
    def evaluate(self, data) -> float:
        result = CriterionLesser.evaluate(self, data)
        if data == "Studio":
            self._result_info = "Studio"
            return 5
        return result


class CriterionTrain(Criterion):
    """
    Housing criterion for determining closeness to trains
    """
    def __init__(self, name: str, key: str, weight: int, max_distance: float,
                 result_format: ResultFormat = ResultFormat.Generic, required: bool = False):
        """
        Constructor
        :param name: The user-facing name of the criterion
        :param key: The key from the scrape data to evaluate
        :param weight: The weight of the criterion in points, ex. 100 means it will contribute at most 100 points
        :param result_format: How to format the result info string
        :param required: If the criterion is required. If required, when it cannot be evaluated the housing will be
        discarded. When false, if the criterion cannot be evaluated, then it simply will not be considered.
        """
        Criterion.__init__(self, name, key, weight, result_format, required)
        self._name = name
        self._key = key
        self._weight = weight
        self._max_distance = max_distance
        self._required = required

    def evaluate(self, data) -> float:
        """
        Determine how close to trains we are
        :param data: Should be housing coords
        :return:
        """
        # Find closest train
        closest_station = []
        closest_distance = None
        if not data:
            return -1
        for station in Criterion.train_data:
            distance = haversine.haversine(station["coords"], data, unit=haversine.Unit.MILES)
            if closest_distance is None:
                closest_distance = distance
                closest_station = station
                continue
            elif distance < closest_distance:
                closest_distance = distance
                closest_station = station

        if closest_distance is not None:
            self._result_info = Criterion.format_result(self._result_format, "{0:2.2f}".format(closest_distance))
            return self._weight - Criterion.map_to_range(closest_distance, 0, self._max_distance, self._weight)
        return 0

