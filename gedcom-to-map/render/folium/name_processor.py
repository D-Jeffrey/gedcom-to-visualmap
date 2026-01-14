"""
Utilities for processing and handling personal names.
"""
__all__ = ["NameProcessor"]

import unicodedata
import string
import re

class NameProcessor:
    """
    A class to handle various operations related to processing people's names.
    """
    def __init__(self, fullName: str) -> None:
        """
        Initialize the NameProcessor with a full name.
        Args:
            fullName (str): The full name of the person.
        """
        self.fullName: str = fullName
        self.firstName: str | None = None
        self.lastName: str | None = None
        self.middleNames: list[str] = []
        self._parse_name()

    def _parse_name(self) -> None:
        """
        Parse the full name into first name, last name, and middle names.
        """
        parts = self.fullName.split()
        if len(parts) > 0:
            self.firstName = parts[0]
        if len(parts) > 1:
            self.lastName = parts[-1]
        if len(parts) > 2:
            self.middleNames = parts[1:-1]

    def getInitials(self) -> str:
        """
        Get the initials of the person's name.
        Returns:
            str: The initials of the name.
        """
        initials = [name[0].upper() for name in [self.firstName] + self.middleNames + [self.lastName] if name]
        return ''.join(initials)

    def formatName(self) -> str:
        """
        Format the name in "Last, First Middle" format.
        Returns:
            str: The formatted name.
        """
        middle = ' '.join(self.middleNames)
        if middle:
            return f"{self.lastName}, {self.firstName} {middle}"
        return f"{self.lastName}, {self.firstName}"

    @staticmethod
    def isValidName(name: str) -> bool:
        """
        Check if a given name is valid (contains only alphabetic characters and spaces).

        Args:
            name (str): The name to validate.

        Returns:
            bool: True if the name is valid, False otherwise.
        """
        return all(part.isalpha() for part in name.split())

    @staticmethod
    def compareNames(name1: str, name2: str) -> bool:
        """
        Compare two names for equality, ignoring case and extra spaces.

        Args:
            name1 (str): The first name.
            name2 (str): The second name.

        Returns:
            bool: True if the names are equivalent, False otherwise.
        """
        return name1.strip().lower() == name2.strip().lower()

    @staticmethod
    def simplifyLastName(lastName: str) -> str:
        """
        Simplifies a last name by:
        - Removing punctuation
        - Removing accents
        - Stripping spaces
        - Converting to lowercase

        Args:
            lastName (str): The last name to simplify.

        Returns:
            str: The simplified last name.
        """
        # Normalize to remove accents
        normalized_name = unicodedata.normalize('NFD', lastName)
        noAccents = ''.join(c for c in normalized_name if unicodedata.category(c) != 'Mn')

        cleanedName = re.sub(r'\(.*?\)', '', noAccents)
        cleanedName = re.sub(r'\(born.*', '', cleanedName)

        # Remove punctuation and spaces
        simplifiedName = ''.join(c for c in cleanedName if c not in string.punctuation and not c.isspace())

        # Convert to lowercase
        return simplifiedName.lower()

    @staticmethod
    def soundex(lastName: str) -> str:
        """
        Computes the Soundex value for a given last name.
        Soundex is a phonetic algorithm for indexing names by sound.

        Args:
            lastName (str): The last name to encode.

        Returns:
            str: The Soundex code.
        """
        # Simplify the last name first
        lastName = NameProcessor.simplifyLastName(lastName)

        if not lastName:
            return ""

        # Soundex encoding rules
        soundex_mapping = {
            'b': '1', 'f': '1', 'p': '1', 'v': '1',
            'c': '2', 'g': '2', 'j': '2', 'k': '2', 'q': '2', 's': '2', 'x': '2', 'z': '2',
            'd': '3', 't': '3',
            'l': '4',
            'm': '5', 'n': '5',
            'r': '6'
        }

        # First letter is kept
        first_letter = lastName[0].upper()

        # Encode the remaining letters
        encoded_name = first_letter
        for char in lastName[1:]:
            code = soundex_mapping.get(char.lower(), '')
            # Avoid consecutive duplicates
            if code and (len(encoded_name) == 1 or code != encoded_name[-1]):
                encoded_name += code

        # Remove vowels and h/w except the first letter
        encoded_name = first_letter + ''.join(char for char in encoded_name[1:] if char not in "aeiouyhw")

        # Pad with zeros or truncate to ensure 4 characters
        return encoded_name[:4].ljust(4, '0')
