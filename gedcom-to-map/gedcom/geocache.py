"""
geocache.py - Geocoded location cache utilities for GEDCOM mapping.

Handles reading and saving geocoded location cache as CSV.

Author: @colin0brass
"""

import os
import csv
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from models.location import Location

logger = logging.getLogger(__name__)

class GeoCache:
    """
    Manages reading and writing of geocoded location cache data for GEDCOM mapping.

    Loads cached geocoding results from a CSV file, normalizes fields,
    and provides methods to save updated cache data back to disk. Ensures
    consistent handling of fields such as 'found_country' and tracks usage counts.

    Attributes:
        location_cache_file (str): Path to the cache CSV file.
        always_geocode (bool): If True, ignore cache and always geocode.
        geo_cache (Dict[str, dict]): Dictionary mapping place names to cached geocode data.
        alt_addr_cache (Dict[str, dict]): Dictionary mapping place names to alternative address data.
    """

    def __init__(
        self,
        cache_file: str,
        always_geocode: bool,
        alt_addr_file: Optional[Path] = None
    ):
        """
        Initialize the GeoCache object.

        Args:
            cache_file (str): Path to the cache CSV file.
            always_geocode (bool): If True, ignore cache and always geocode.
            alt_addr_file (Optional[Path]): Path to alternative address file.
        """
        self.location_cache_file = cache_file
        self.always_geocode = always_geocode
        self.geo_cache: Dict[str, dict] = {}
        self.alt_addr_cache: Dict[str, dict] = {}

        self.read_geo_cache()
        if alt_addr_file:
            self.read_alt_addr_file(alt_addr_file)
            self.add_alt_addr_to_cache()

    def read_geo_cache(self) -> None:
        """
        Read geocoded location cache from the CSV file.

        Loads cached geocoding results into self.geo_cache.
        Normalizes the 'found_country' field to boolean.
        If always_geocode is True or the cache file does not exist, skips loading.
        """
        self.geo_cache = {}
        if self.always_geocode:
            logger.info('Configured to ignore cache')
            return
        if not self.location_cache_file or not os.path.exists(self.location_cache_file):
            logger.info(f'No location cache file found: {self.location_cache_file}')
            return
        try:
            with open(self.location_cache_file, newline='', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f, dialect='excel')
                for line in csv_reader:
                    key = line.get('address', '').lower()
                    line['used'] = 0
                    # Normalize found_country to boolean
                    found_country_val = line.get('found_country', '')
                    if isinstance(found_country_val, str):
                        line['found_country'] = found_country_val.lower() in ('true', '1')
                    else:
                        line['found_country'] = bool(found_country_val)
                    self.geo_cache[key] = line
        except FileNotFoundError as e:
            logger.warning(f'Location cache file not found: {e}')
        except csv.Error as e:
            logger.error(f'CSV error reading location cache file {self.location_cache_file}: {e}')
        except Exception as e:
            logger.error(f'Error reading location cache file {self.location_cache_file}: {e}')

    def save_geo_cache(self) -> None:
        """
        Save geocoded location cache to the CSV file.

        Writes all cached geocoding results from self.geo_cache to disk.
        Ensures the 'found_country' field is saved as a 'True' or 'False' string.
        """
        if not self.geo_cache:
            logger.info('No geocoded location cache to save')
            return
        try:
            # Collect all fieldnames from all cache entries
            all_fieldnames = set()
            for entry in self.geo_cache.values():
                all_fieldnames.update(entry.keys())
            fieldnames = list(all_fieldnames)
            if not fieldnames:
                logger.info('Geocoded location cache is empty, nothing to save.')
                return
            with open(self.location_cache_file, 'w', newline='', encoding='utf-8') as f:
                csv_writer = csv.DictWriter(f, fieldnames=fieldnames, dialect='excel')
                csv_writer.writeheader()
                for line in self.geo_cache.values():
                    # Ensure 'found_country' is saved as 'True' or 'False' string
                    if 'found_country' in line:
                        line['found_country'] = 'True' if bool(line['found_country']) else 'False'
                    csv_writer.writerow(line)
            logger.info(f'Saved geocoded location cache to: {self.location_cache_file}')
        except FileNotFoundError as e:
            logger.warning(f'Location cache file not found for saving: {e}')
        except csv.Error as e:
            logger.error(f'CSV error saving geocoded location cache: {e}')
        except Exception as e:
            logger.error(f'Error saving geocoded location cache: {e}')

    def read_alt_addr_file(self, alt_addr_file: Optional[Path]) -> None:
        """
        Read alternative address names from a CSV file.

        Args:
            alt_addr_file (Optional[Path]): Path to alternative address file.
        """
        if not alt_addr_file or not os.path.exists(alt_addr_file):
            logger.info(f'No alternative address file found: {alt_addr_file}')
            return
        try:
            with open(alt_addr_file, newline='', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f, dialect='excel')
                for line in csv_reader:
                    key = line.get('address', '').lower()
                    self.alt_addr_cache[key] = line
        except FileNotFoundError as e:
            logger.warning(f'Alternative address file not found: {e}')
        except csv.Error as e:
            logger.error(f'CSV error reading alternative address file {alt_addr_file}: {e}')
        except Exception as e:
            logger.error(f'Error reading alternative address file {alt_addr_file}: {e}')

    def lookup_geo_cache_entry(self, address: str) -> Tuple[str, Optional[dict]]:
        """
        Look up an address in the geocoded cache or alternative address names.

        Args:
            address (str): The address string to look up.

        Returns:
            Tuple[str, Optional[dict]]: (possibly substituted address, cached geocode data if found, else None)
        """
        address_lower = address.lower()
        alt_addr_data = None
        alt_addr_name = None

        if address_lower in self.alt_addr_cache:
            alt_addr_data = self.alt_addr_cache[address_lower]
            alt_addr_name = alt_addr_data.get('alt_addr')

        use_addr_name = alt_addr_name if alt_addr_name else address

        if address_lower in self.geo_cache:
            if alt_addr_name is not None:
                logger.info(f"Adding alternative address name for cache entry: {address} : {alt_addr_name}")
                self.geo_cache[address_lower]['alt_addr'] = alt_addr_name
                if alt_addr_data.get('latitude') and alt_addr_data.get('longitude'):
                    self.geo_cache[address_lower]['latitude'] = alt_addr_data.get('latitude')
                    self.geo_cache[address_lower]['longitude'] = alt_addr_data.get('longitude')

            return use_addr_name, self.geo_cache[address_lower]

        return use_addr_name, None

    def add_geo_cache_entry(self, address: str, location: Location) -> None:
        """
        Add a new entry to the geocoded location cache.

        Args:
            address (str): The address string.
            location (Location): The geocoded location object.
        """
        self.geo_cache[address] = {
            'address': address,
            'alt_addr': getattr(location, 'alt_addr', ''),
            'latitude': getattr(location.latlon, 'lat', ''),
            'longitude': getattr(location.latlon, 'lon', ''),
            'country_code': location.country_code,
            'country_name': location.country_name,
            'continent': location.continent,
            'found_country': 'True' if location.found_country else 'False',
            'used': 1  # Initialize usage count to 1
        }

    def add_alt_addr_to_cache(self) -> None:
        """
        Add alternative address names to the cache.

        Iterates through alt_addr_cache and adds entries to geo_cache if not already present.
        """
        for address, data in self.alt_addr_cache.items():
            if address.lower() not in self.geo_cache:
                logger.info(f"Adding alternative address to cache: {address} : {data.get('alt_addr')}")
                self.geo_cache[address.lower()] = {
                    'address': address,
                    'alt_addr': data.get('alt_addr', ''),
                    'latitude': data.get('latitude', ''),
                    'longitude': data.get('longitude', ''),
                    'country_code': data.get('country_code', ''),
                    'country_name': data.get('country_name', ''),
                    'continent': data.get('continent', ''),
                    'found_country': 'False',
                    'used': 0
                }