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
import time
import geopy
import geopy.geocoders as gc
from typing import Optional
from .cache import LocationCache

logger = logging.getLogger(__name__)

NOMINATIM_REQUEST_DELAY = 1

us_state_abbrev = {
    'Alabama': 'AL',
    'Alaska': 'AK',
    'American Samoa': 'AS',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'District of Columbia': 'DC',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Guam': 'GU',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Northern Mariana Islands':'MP',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Pennsylvania': 'PA',
    'Puerto Rico': 'PR',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virgin Islands': 'VI',
    'Virginia': 'VA',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY'
}


class AddressLookup:
    """
    Static class for looking up address and interacting with the cache
    Uses Nominatim
    """

    last_nom_request = 0

    @staticmethod
    def extract_address_dict(location) -> dict:
        house_number = ""
        if "house_number" in location.raw["address"]:
            house_number = location.raw["address"]["house_number"]
        road = ""
        if "road" in location.raw["address"]:
            road = location.raw["address"]["road"]
        neighborhood = ""
        if "neighbourhood" in location.raw["address"]:
            neighborhood = location.raw["address"]["neighbourhood"]
        suburb = ""
        if "suburb" in location.raw["address"]:
            suburb = location.raw["address"]["suburb"]
        elif "hamlet" in location.raw["address"]:
            suburb = location.raw["address"]["hamlet"]
        city = ""
        if "city" in location.raw["address"]:
            city = location.raw["address"]["city"]
        elif "town" in location.raw["address"]:
            city = location.raw["address"]["town"]
        state = ""
        if "state" in location.raw["address"]:
            state = location.raw["address"]["state"]
            if state in us_state_abbrev:
                state = us_state_abbrev[state]
            else:
                state = ""

        loc_dict = {
            "lat": location.latitude,
            "long": location.longitude,
            "house_number": house_number,
            "road": road,
            "neighborhood": neighborhood,
            "suburb": suburb,
            "city": city,
            "state": state,
        }

        return loc_dict

    @staticmethod
    def lookup_coordinates(coordinates) -> Optional[dict]:
        """
        Looks up the address of the given coordinates. Uses cache for cached coordinates. This will block until
        NOMINATIM_REQUEST_DELAY passes since last request
        :param coordinates: The coordinates to lookup
        """
        location = LocationCache.get_address(coordinates)
        if location is None:
            # Sleep if necessary
            time_since_last = (time.time() - AddressLookup.last_nom_request)
            if time_since_last < NOMINATIM_REQUEST_DELAY:
                time.sleep(NOMINATIM_REQUEST_DELAY - time_since_last)

            address_obj = None
            try:
                geolocator = gc.Nominatim(user_agent="pyagent")
                address_obj = geolocator.reverse(query=geopy.point.Point(coordinates[0], coordinates[1]),
                                                 exactly_one=True)
            except geopy.exc.ConfigurationError as e:
                logger.error("Geocoder error looking up coordinates {0}: {1}".format(coordinates, e))
                address_obj = None
            except geopy.exc.GeocoderTimedOut as e:
                logger.error("Geocoder timed out for address {0}: {1}".format(coordinates, e))
                address_obj = None
            AddressLookup.last_nom_request = time.time()

            if address_obj:
                location = AddressLookup.extract_address_dict(address_obj)
            else:
                return None
            LocationCache.add_to_reverse_cache(coordinates, location)
            return location
        else:
            return location

    @staticmethod
    def lookup_address(address) -> Optional[dict]:
        """
        Looks up the coordinates of a given address. Uses cache for cached addresses. This will block until
        NOMINATIM_REQUEST_DELAY passes since last request
        :param address: The address to lookup
        """
        location = LocationCache.get_location(address)
        if location is None:
            # Sleep if necessary
            time_since_last = (time.time() - AddressLookup.last_nom_request)
            if time_since_last < NOMINATIM_REQUEST_DELAY:
                time.sleep(NOMINATIM_REQUEST_DELAY - time_since_last)

            # Try to retrieve the address from Nominatim
            location_obj = None
            try:
                geolocator = gc.Nominatim(user_agent="pyagent")
                location_obj = geolocator.geocode(address, addressdetails=True)
            except geopy.exc.ConfigurationError as e:
                logger.error("Geocoder error looking up address {0}: {1}".format(address, e))
                location_obj = None
            except geopy.exc.GeocoderTimedOut as e:
                logger.error("Geocoder timed out for address {0}: {1}".format(address, e))
                location_obj = None
            AddressLookup.last_nom_request = time.time()

            if location_obj:
                location = AddressLookup.extract_address_dict(location_obj)
            else:
                location = {}
            LocationCache.add_to_cache(address, location)
            if not location and location is not None:
                return None
            return location
        else:
            if not location and location is not None:
                logger.warning("Address {0} is in cache as invalid, you may need"
                               " to clear the location.json cache if this is a valid address".format(address))
                return None
            return location

    @staticmethod
    def construct_address(location) -> str:
        components = []
        road_part = ""
        if location["house_number"]:
            road_part = location["house_number"]
        if location["road"]:
            if road_part:
                road_part += " " + location["road"]
            else:
                road_part = location["road"]
            components.append(road_part)
        if location["neighborhood"]:
            components.append(location["neighborhood"])
        if location["suburb"]:
            components.append(location["suburb"])
        if location["city"]:
            components.append(location["city"])
        if location["state"]:
            components.append(location["state"])

        return ", ".join(components)
