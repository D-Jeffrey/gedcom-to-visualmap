"""
geocode.py - Geocoding utilities for GEDCOM mapping.

Handles geocoding, country/continent lookup, and caching of location results.
Loads fallback continent mappings from geo_config.yaml.

Author: @colin0brass
"""

import time
import logging
import random
import re
from pathlib import Path
from typing import Optional, Tuple, Dict

import pycountry
import pycountry_convert as pc
import requests
import yaml  # Ensure PyYAML is installed
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable
from geopy.adapters import AdapterHTTPError

from const import GEOCODEUSERAGENT

from models.location import Location
from .addressbook import FuzzyAddressBook
from .geocache import GeoCache
from gedcomoptions import gvOptions

# Re-use higher-level logger (inherits configuration from main script)
logger = logging.getLogger(__name__)

def load_yaml_config(path: Path) -> dict:
    """
    Load YAML configuration from the given path.

    Args:
        path (Path): Path to the YAML file.

    Returns:
        dict: Parsed YAML configuration or empty dict if not found/error.
    """
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        logger.warning(f"Could not load geo_config.yaml: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading geo_config.yaml: {e}")
    return {}

class Geocode:
    """
    Handles geocoding and country/continent lookup for places.

    Attributes:
        always_geocode (bool): Ignore cache if True.
        location_cache_file (str): Path to cache file.
        default_country (str): Default country for geocoding.
        geo_cache (Dict[str, dict]): Cached addresses.
        geolocator (Nominatim): Geopy geocoder instance.
        fallback_continent_map (Dict[str, str]): Fallback continent mapping from YAML.
        ... (other config attributes)
    """
    __slots__ = [
        'always_geocode', 'location_cache_file', 'additional_countries_codes_dict_to_add',
        'additional_countries_to_add', 'country_substitutions', 'default_country', 'geo_cache',
        'geolocator', 'countrynames', 'countrynames_lower', 'country_name_to_code_dict',
        'country_code_to_name_dict', 'country_code_to_continent_dict', 'fallback_continent_map',
        'gOp', '_last_geocode_time'
    ]
    geocode_sleep_interval = 1  # Delay due to Nominatim request limit

    def __init__(
        self,
        cache_file: str,
        default_country: Optional[str] = None,
        always_geocode: bool = False,
        alt_place_file_path: Optional[Path] = None,
        gOp: Optional[gvOptions] = None
    ):
        """
        Initialize the Geocode object, loading country info and cache.

        Args:
            cache_file (str): Path to cache file.
            default_country (Optional[str]): Default country.
            always_geocode (bool): Ignore cache if True.
            alt_place_cache (Dict[str, dict]): Alternative place names cache.
            use_alt_places (bool): Whether to use alternative place names.
            alt_place_file_path (Optional[Path]): Alternative place names file path.
        """
        self.always_geocode = always_geocode
        logger.debug(f"Geocode always_geocode={self.always_geocode}")
        self.location_cache_file = cache_file
        
        geo_yaml_path = Path(__file__).parent / "geo_config.yaml"
        geo_config = load_yaml_config(geo_yaml_path)

        self.additional_countries_codes_dict_to_add = geo_config.get('additional_countries_codes_dict_to_add', {})
        self.additional_countries_to_add = list(self.additional_countries_codes_dict_to_add.keys())
        self.country_substitutions = geo_config.get('country_substitutions', {})
        self.default_country = default_country or geo_config.get('default_country', 'England')
        if default_country == 'None':
            default_country = None

        # Load fallback continent map from YAML if present, else use empty dict
        self.fallback_continent_map: Dict[str, str] = geo_config.get('fallback_continent_map', {})

        self.geo_cache = GeoCache(cache_file, always_geocode, alt_place_file_path)
        self.geolocator = Nominatim(user_agent=GEOCODEUSERAGENT)

        self.countrynames = [country.name for country in pycountry.countries]
        self.countrynames.extend(self.additional_countries_to_add)
        self.countrynames_lower = set(name.lower() for name in self.countrynames)

        self.country_name_to_code_dict = {country.name: country.alpha_2 for country in pycountry.countries}
        self.country_name_to_code_dict.update(self.additional_countries_codes_dict_to_add)
        self.country_code_to_name_dict = {v.upper(): k for k, v in self.country_name_to_code_dict.items()}
        self.country_code_to_continent_dict = {code: self.country_code_to_continent(code) for code in self.country_code_to_name_dict.keys()}

        self.gOp = gOp

        self._last_geocode_time = 0.0  # Timestamp of last geocode request

    def save_geo_cache(self) -> None:
        """
        Save address cache if applicable.
        """
        if self.geo_cache.location_cache_file:
            self.geo_cache.save_geo_cache()

    def country_code_to_continent(self, country_code: str) -> Optional[str]:
        """
        Convert country code to continent name.

        Args:
            country_code (str): Country code.

        Returns:
            Optional[str]: Continent name or None.
        """
        code = country_code.upper()
        # Use fallback mapping from YAML if present
        if code in self.fallback_continent_map:
            logger.debug(f"Using fallback continent map for code '{code}': {self.fallback_continent_map[code]}")
            return self.fallback_continent_map[code]
        try:
            continent_code = pc.country_alpha2_to_continent_code(code)
            continent_name = pc.convert_continent_code_to_continent_name(continent_code)
            return continent_name
        except Exception:
            logger.warning(f"Could not convert country code '{country_code}' to continent.")
            return "Unknown"

    def get_place_and_countrycode(self, place: str) -> Tuple[str, str, str, bool]:
        """
        Given a place string, return (place, country_code, country_name, found).

        Args:
            place (str): Place string.

        Returns:
            Tuple[str, str, str, bool]: (place, country_code, country_name, found)
        """
        found = False
        country_name = ''

        place_lower = place.lower()
        last_place_element = place_lower.split(',')[-1].strip()

        for key in self.country_substitutions:
            if last_place_element == key.lower():
                new_country = self.country_substitutions[key]
                logger.info(f"Substituting country '{last_place_element}' with '{new_country}' in place '{place}'")
                place_lower = place_lower.replace(last_place_element, new_country)
                country_name = new_country
                found = True
                break

        if last_place_element in self.countrynames_lower:
            found = True
            for name in self.countrynames:
                if name.lower() == last_place_element:
                    country_name = name
                    break

        if not found and self.default_country.lower() != 'none':
            logger.info(f"Adding default country '{self.default_country}' to place '{place}'")
            place_lower = place_lower + ', ' + self.default_country
            country_name = self.default_country

        country_code = self.country_name_to_code_dict.get(country_name, 'none')
        return (place_lower, country_code, country_name, found)

    def geocode_place(self, place: str, country_code: str, country_name: str, found_country: bool = False, address_depth: int = 0) -> Optional[Location]:
        """
        Geocode a place string and return a Location object.

        Args:
            place (str): Place string.
            country_code (str): Country code.
            country_name (str): Country name.
            found_country (bool): Whether country was found.
            address_depth (int): Recursion depth for less precise geocoding.

        Returns:
            Optional[Location]: Location object or None.
        """
        location = None

        if not place or (self.gOp and self.gOp.CacheOnly):
            return None

        max_retries = 3
        geo_location = None
        backoff_base = 0.5
        for attempt in range(1, max_retries + 1):
            # refresh last request timestamp each iteration
            last_ts = getattr(self, "_last_geocode_time", 0.0)
            now = time.time()
            to_wait = self.geocode_sleep_interval - (now - last_ts)
            if to_wait > 0:
                time.sleep(to_wait)
            try:
                # record request time for rate limiting (ensure we register the request even if it fails)
                self._last_geocode_time = time.time()
                ccodes = country_code if (country_code and country_code.lower() != 'none') else None
                logger.debug("Geocoding %r country=%r attempt=%d", place, ccodes, attempt)
                geo_location = self.geolocator.geocode(
                    place,
                    country_codes=ccodes,
                    timeout=10,
                    addressdetails=False,
                    exactly_one=True
                )

                # If geopy returned None (HTTP 200 but no match), do not retry — it's not a transient error.
                if geo_location is None:
                    logger.debug("No geocoding result for %r (not retrying)", place)
                    break

                # successful result
                break
            
            except (GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable, AdapterHTTPError, requests.RequestException) as e:
                # Determine HTTP status when available and treat 5xx as transient (retryable).
                status = None
                resp = getattr(e, "response", None)
                if resp is not None:
                    status = getattr(resp, "status_code", None)
                elif hasattr(e, "status"):
                    status = getattr(e, "status")
                else:
                    # best-effort parse of numeric HTTP code from message
                    m = re.search(r"\b(5\d{2}|4\d{2})\b", str(e))
                    if m:
                        try:
                            status = int(m.group(0))
                        except Exception:
                            status = None

                # retry for transient server errors (5xx) or timeouts/unavailable
                if status is not None and 500 <= status < 600:
                    logger.warning("Server error (status=%s) geocoding %r (attempt %d/%d): %s", status, place, attempt, max_retries, e)
                else:
                    # treat as transient if it's a known transient exception type
                    logger.warning("Transient geocoding exception for %r (attempt %d/%d): %s", place, attempt, max_retries, e)
            except Exception as e:
                logger.exception("Unexpected error geocoding %r (attempt %d/%d): %s", place, attempt, max_retries, e)

            # exponential backoff with small jitter before next attempt
            if attempt < max_retries:
                sleep_time = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.2)
                logger.info("Retrying geocode for %r (attempt %d/%d) after %.2fs", place, attempt + 1, max_retries, sleep_time)
                time.sleep(sleep_time)
            else:
                logger.error("Giving up on geocoding %r after %d attempts.", place, max_retries)
                # ensure we don't propagate the last exception to callers
                geo_location = None

        if geo_location:
            location = Location(
                used=1,
                latitude=geo_location.latitude,
                longitude=geo_location.longitude,
                country_code=country_code.upper(),
                country_name=country_name,
                continent=self.country_code_to_continent_dict.get(country_code.upper(), ''),
                found_country=bool(found_country),
                address=geo_location.address
            )

        if location is None and address_depth < 3:
            logger.info(f"Retrying geocode for {place} with less precision")
            parts = place.split(',')
            if len(parts) > 1:
                less_precise_address = ','.join(parts[1:]).strip()
                location = self.geocode_place(less_precise_address, country_code, country_name, address_depth + 1)
        return location

    def separate_cached_locations(self, address_book: FuzzyAddressBook) -> Tuple[FuzzyAddressBook, FuzzyAddressBook]:
        """
        Separate addresses into cached and non-cached.

        Args:
            address_book (FuzzyAddressBook): Address book containing full addresses.

        Returns:
            Tuple[Dict[str, dict], Dict[str, dict]]: (cached_places, non_cached_places)
        """
        cached_places = FuzzyAddressBook()
        non_cached_places = FuzzyAddressBook()
        for place, data in address_book.addresses().items():
            place_lower = place.lower()
            if not self.always_geocode and (place_lower in self.geo_cache.geo_cache):
                cached_places.fuzzy_add_address(place, data)
            else:
                non_cached_places.fuzzy_add_address(place, data)
        return (cached_places, non_cached_places)

    def lookup_location(self, place: str) -> Optional[Location]:
        """
        Lookup a place in the cache or geocode it.

        Args:
            place (str): Place string.

        Returns:
            Optional[Location]: Location object or None.
        """
        found_in_cache = False
        found_country = False
        location = None

        if not place:
            return None

        use_place_name = place
        cache_entry = None
        if not self.always_geocode:
            use_place_name, cache_entry = self.geo_cache.lookup_geo_cache_entry(place)

        if cache_entry and cache_entry.get("no_result"):
            logger.info(f"Place '{place}' marked as no_result in cache; skipping geocoding.")
            return None
        
        (place_with_country, country_code, country_name, found_country) = self.get_place_and_countrycode(use_place_name)

        if cache_entry and not self.always_geocode:
            if cache_entry.get('latitude') and cache_entry.get('longitude'):
                found_in_cache = True
                location = Location.from_dict(cache_entry)
                if cache_entry.get('found_country', False) == False or cache_entry.get('country_name', '') == '':
                    if found_country:
                        logger.info(f"Found country in cache for {use_place_name}, but it was not marked as found.")
                        location.found_country = True
                        location.country_code = country_code.upper()
                        location.country_name = country_name
                        location.continent = self.country_code_to_continent_dict.get(country_code.upper(), "Unknown")
                        self.geo_cache.add_geo_cache_entry(place, location)
                    else:
                        logger.info(f"Unable to add country from geo cache lookup for {use_place_name}")
                if not found_country:
                    logger.info(f"Country not found in cache for {use_place_name}, using default country: {self.default_country}")

        if not found_in_cache:
            location = self.geocode_place(place_with_country, country_code, country_name, found_country, address_depth=0)
            if location is not None:
                location.address = place
                self.geo_cache.add_geo_cache_entry(place, location)
                logger.info(f"Geocoded {place} to {location.latlon}")
            else: # record negative cache so we avoid re-trying repeatedly
                self.geo_cache.add_no_result_entry(place)
                logger.info(f"Geocoding couldn't find {place}, so marked as no_result to reduce fruitless attempts.")

        if location:
            continent = location.continent
            if not continent or continent.strip().lower() in ('', 'none'):
                location.continent = self.country_code_to_continent_dict.get(location.country_code, "Unknown")

        return location