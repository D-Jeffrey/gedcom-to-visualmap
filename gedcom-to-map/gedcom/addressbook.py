"""
addressbook.py - FuzzyAddressBook for GEDCOM mapping.

Provides a class for storing, managing, and fuzzy-matching geocoded addresses.

Author: @colin0brass
"""

import logging
from typing import Any, Dict, Optional, Union, List
from rapidfuzz import process, fuzz

from models.location import Location
from models.LatLon import LatLon

logger = logging.getLogger(__name__)

class FuzzyAddressBook:
    def __init__(self):
        self.__addresses : Dict[str, Location] = {}

    def __add_address(self, key: str, location: Location):
        self.__addresses[key] = location

    def get_address(self, key: str) -> Optional[Location]:
        return self.__addresses.get(key)

    def addresses(self) -> Dict[str, Location]:
        """
        Returns the addresses in the address book.

        Returns:
            Dict[str, Location]: Dictionary of addresses.
        """
        return self.__addresses

    def len(self) -> int:
        """
        Returns the number of addresses in the address book.

        Returns:
            int: Number of addresses.
        """
        return len(self.__addresses)

    def fuzzy_lookup_address(self, address: str, threshold: int = 90) -> Optional[str]:
        """
        Find the best fuzzy match for an address in the address book.

        Args:
            address (str): The address to match.
            threshold (int): Minimum similarity score (0-100) to accept a match.

        Returns:
            str: The best matching address key, or None if no good match found.
        """
        choices = list(self.__addresses.keys())
        if choices:
            match, score, _ = process.extractOne(address, choices, scorer=fuzz.token_sort_ratio)
            if score >= threshold:
                return match
        return None

    def fuzzy_add_address(self, address: str, location: Union[Location, None]):
        """
        Add a new address to the address book, using fuzzy matching to find
        the best existing address if there's a close match, and use same alt_addr.

        Args:
            address (str): The address to add.
            location (Location): The location data associated with the address.
        """
        existing_key = self.fuzzy_lookup_address(address)
        if location is None:
            location = Location(address=address)
        if existing_key is not None:
            # If a similar (or identical) address exists, create or update the entry with the same alt_addr
            if existing_key == address:
                location.used = self.__addresses[existing_key].used + 1
            alt_addr = self.__addresses[existing_key].alt_addr
            if alt_addr is not None:
                location.alt_addr = alt_addr
            self.__addresses[existing_key] = location
        else:
            # If no similar address exists, add it as a new entry.
            self.__add_address(address, location)