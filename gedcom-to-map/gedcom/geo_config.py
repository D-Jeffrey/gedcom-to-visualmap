"""
geo_config.py - Geographic configuration and country/continent utilities for GEDCOM mapping.

Provides GeoConfig for loading continent mappings, country substitutions, and related
geographic settings from a YAML configuration file.

Author: @colin0brass
"""

import os
import csv
import yaml
import logging
from pathlib import Path
from typing import Dict, Optional, Union, Tuple

import pycountry
import pycountry_convert as pc

logger = logging.getLogger(__name__)

class GeoConfig:
    """
    GeoConfig manages loading of geographic configuration data from a YAML file.

    Loads continent mappings, country substitutions, and other geographic settings
    for use in geocoding and location processing tasks.

    Attributes:
        geo_config_path (Optional[Path]): Path to the configuration YAML file.
        countrynames (List[str]): List of country names.
        countrynames_lower (List[str]): List of country names in lowercase.
        country_name_to_code_dict (Dict[str, str]): Mapping of country names to ISO codes.
        country_code_to_name_dict (Dict[str, str]): Mapping of ISO codes to country names.
        country_code_to_continent_dict (Dict[str, str]): Mapping of ISO codes to continent names.
        country_substitutions (Dict[str, str]): Substitution mapping for country names.
        country_substitutions_lower (Dict[str, str]): Lowercase-keyed substitution mapping.
        countrynames_dict_lower (Dict[str, str]): Lowercase-keyed country name mapping.
        default_country (str): Default country name.
        fallback_continent_map (Dict[str, str]): Fallback continent mapping for country codes.
    """

    def __init__(self, geo_config_path: Optional[Path] = None):
        """
        Initialize GeoConfig with country data from pycountry and optional config file.

        Args:
            geo_config_path (Optional[Path]): Path to the configuration YAML file.
        """
        self.geo_config_path = geo_config_path
        self.countrynames = []
        self.countrynames_lower = []
        self.country_name_to_code_dict = {}
        self.country_code_to_continent_dict = {}
        self.country_code_to_name_dict = {}
        self.country_code_to_continent_dict = {}
        self.country_substitutions = {}
        self.default_country = None
        self.fallback_continent_map = {}

        self.__geo_config_path = geo_config_path

        if geo_config_path:
            self.load_geo_config()

    def load_geo_config(self) -> None:
        """
        Load geographic configuration from the YAML file.

        Populates country substitutions, default country, continent mappings,
        and additional country codes from the config file.
        """
        if self.__geo_config_path and self.__geo_config_path.exists():
            try:
                with open(self.__geo_config_path, 'r', encoding='utf-8') as f:
                    self.__geo_config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load geo config from {self.__geo_config_path}: {e}")
                self.__geo_config = {}
        else:
            self.__geo_config = {}

        self.country_substitutions = self.__geo_config.get('country_substitutions', {})
        self.default_country = self.__geo_config.get('default_country', '')
        additional_countries_codes_dict_to_add = self.__geo_config.get('additional_countries_codes_dict_to_add', {})
        self.fallback_continent_map = self.__geo_config.get('fallback_continent_map', {})

        additional_countries_to_add = list(additional_countries_codes_dict_to_add.keys())
        self.countrynames = [country.name for country in pycountry.countries]
        self.countrynames.extend(additional_countries_to_add)

        self.countrynames_lower = [name.lower() for name in self.countrynames]

        self.country_name_to_code_dict = {country.name: country.alpha_2 for country in pycountry.countries}
        self.country_name_to_code_dict.update(additional_countries_codes_dict_to_add)

        self.country_code_to_name_dict = {v: k for k, v in self.country_name_to_code_dict.items()}
        self.country_code_to_continent_dict = {code: self.country_code_to_name_dict.get(code) for code in self.country_code_to_name_dict.keys()}

        self.country_substitutions_lower = {k.lower(): v for k, v in self.country_substitutions.items()}
        self.countrynames_dict_lower = {name.lower(): name for name in self.countrynames}

    def get_continent_for_country_code(self, country_code: str) -> Optional[str]:
        """
        Get the continent name for a given ISO alpha-2 country code.

        Args:
            country_code (str): The ISO alpha-2 country code.

        Returns:
            Optional[str]: The continent name if found, else None.
        """
        if not country_code:
            return None
        try:
            continent_code = pc.country_alpha2_to_continent_code(country_code)
            continent_name = pc.convert_continent_code_to_continent_name(continent_code)
            return continent_name
        except KeyError:
            # If pycountry_convert does not have the mapping, check fallback map
            return self.fallback_continent_map.get(country_code)
        except Exception as e:
            logger.error(f"Error getting continent for country code {country_code}: {e}")
            return None
        
    def substitute_country_name(self, country_name: str) -> Tuple[str, bool]:
        """
        Substitute a country name using the config's substitution mapping.

        Args:
            country_name (str): The original country name.

        Returns:
            Tuple[str, bool]: (Substituted country name, True if substituted, False otherwise)
        """
        if not country_name:
            return country_name, False
        substituted = self.country_substitutions.get(country_name)
        if substituted:
            return substituted, True
        substituted = self.country_substitutions_lower.get(country_name.lower())
        if substituted:
            return substituted, True
        return country_name, False
    
    def get_country_name(self, country_name: str) -> Tuple[Optional[str], bool]:
        """
        Get the canonical country name for a given country name.

        Args:
            country_name (str): The country name.

        Returns:
            Tuple[Optional[str], bool]: (Canonical country name if found, True if found, else None and False)
        """
        if country_name.lower() in self.countrynames_dict_lower:
            return self.countrynames_dict_lower[country_name.lower()], True
        else:
            return None, False
        
    def get_country_code(self, country_name: str) -> Optional[str]:
        """
        Get the ISO alpha-2 country code for a given country name.

        Args:
            country_name (str): The country name.

        Returns:
            Optional[str]: The ISO alpha-2 country code if found, else None.
        """
        return self.country_name_to_code_dict.get(country_name)
    
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

        country_name, found_sub = self.substitute_country_name(last_place_element)
        if found_sub:
            logger.info(f"Substituting country '{last_place_element}' with '{country_name}' in place '{place}'")
            place_lower = place_lower.replace(last_place_element, country_name)
            found = True

        country_name, found_country = self.get_country_name(last_place_element)
        if found_country:
            logger.info(f"Found country '{country_name}' for place '{place}'")
            found = True

        if not found and self.default_country.lower() != 'none':
            logger.info(f"Adding default country '{self.default_country}' to place '{place}'")
            place_lower = place_lower + ', ' + self.default_country
            country_name = self.default_country

        country_code = self.get_country_code(country_name) if country_name else 'none'
        
        return (place_lower, country_code, country_name, found)