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


class Criterion:
    """
    Base housing characterization criterion
    """
    def __init__(self, name: str, key: str, weight: int, required: bool = False):
        """
        Constructor
        :param name: The user-facing name of the criterion
        :param key: The key from the scrape data to evaluate
        :param weight: The weight of the criterion in points, ex. 100 means it will contribute at most 100 points
        :param required: If the criterion is required. If required, when it cannot be evaluated the housing will be
        discarded. When false, if the criterion cannot be evaluated, then it simply will not be considered.
        """
        self._name = name
        self._key = key
        self._weight = weight
        self._required = required

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


class CriterionGreater(Criterion):
    """
    Housing characterization criterion where greater is better
    """
    def __init__(self, name: str, key: str, weight: int, lower: int, upper: int, required: bool = False, maximum=None):
        """
        :param name: The user-facing name of the criterion
        :param key: The key from the scrape data to evaluate, must be integer
        :param weight: The weight of the criterion in points, ex. 100 means it will contribute at most 100 points
        :param lower: The lower bounds to map the rating range
        :param upper: The upper bounds to map the rating range
        :param required: If the criterion is required. If required, when it cannot be evaluated the housing will be
        discarded. When false, if the criterion cannot be evaluated, then it simply will not be considered.
        :param maximum: The maximum value for the criterion, above which it is not considered. None means no max
        """
        Criterion.__init__(self, name, key, weight, required)
        self._maximum = maximum
        self._lower = lower
        self._upper = upper

    def evaluate(self, data) -> float:
        if data is not None:
            try:
                value = int(data)
                if self._maximum is not None and value > self._maximum:
                    return -1
                return Criterion.map_to_range(value, self._lower, self._upper, self._weight)
            except ValueError:
                return 0
        return 0


class CriterionLesser(Criterion):
    """
    Housing characterization criterion where lesser is better
    """
    def __init__(self, name: str, key: str, weight: int, lower: int, upper: int, required: bool = False, minimum=None):
        """
        :param name: The user-facing name of the criterion
        :param key: The key from the scrape data to evaluate, must be integer
        :param weight: The weight of the criterion in points, ex. 100 means it will contribute at most 100 points
        :param lower: The lower bounds to map the rating range
        :param upper: The upper bounds to map the rating range
        :param required: If the criterion is required. If required, when it cannot be evaluated the housing will be
        discarded. When false, if the criterion cannot be evaluated, then it simply will not be considered.
        :param minimum: The minimum value for the criterion, below which it is not considered. None means no min
        """
        Criterion.__init__(self, name, key, weight, required)
        self._minimum = minimum
        self._lower = lower
        self._upper = upper

    def evaluate(self, data) -> float:
        if data is not None:
            try:
                value = int(data)
                if self._minimum is not None and value < self._minimum:
                    return -1
                return self._weight - Criterion.map_to_range(value, self._lower, self._upper, self._weight)
            except ValueError:
                return 0
        return 0


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
            return 5
        return result
