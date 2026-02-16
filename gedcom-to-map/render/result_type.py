"""Result type enumeration for output formats.

Defines the ResultType enum that specifies which output format to generate:
HTML, KML, KML2, or SUM (summary/statistics).
"""

import re
import logging
from enum import Enum

_log = logging.getLogger(__name__)


class ResultType(Enum):
    """Output format types for genealogical visualizations."""

    HTML = "HTML"
    KML = "KML"
    KML2 = "KML2"
    SUM = "SUM"

    @staticmethod
    def ResultTypeEnforce(value) -> "ResultType":
        """Coerce a value to a ResultType.

        Accepts an existing ResultType or a string (case-insensitive).

        Args:
            value: ResultType instance or string like "HTML" or "ResultType.HTML"

        Returns:
            ResultType instance

        Raises:
            ValueError: If string value is not a valid ResultType
            TypeError: If value cannot be converted to ResultType
        """
        if isinstance(value, ResultType):
            return value
        if isinstance(value, str):
            # handle ResultType like "ResultType.HTML"
            m = re.match(r"^\s*ResultType\.([A-Za-z_][A-Za-z0-9_]*)\s*$", value)
            if m:
                value = m.group(1)
            try:
                return ResultType[value.upper()]
            except Exception:
                raise ValueError(f"Invalid ResultType string: {value}")
        raise TypeError(f"Cannot convert {type(value)} to ResultType")

    def __str__(self) -> str:
        """Return the value as a string."""
        return self.value

    def long_name(self) -> str:
        """Return the long form name (e.g., 'ResultType.HTML')."""
        try:
            name_attr = getattr(self, "name")
            if callable(name_attr):
                name_str = name_attr()
            else:
                name_str = name_attr
        except Exception:
            name_str = str(self.value)
        return f"ResultType.{name_str}"

    def index(self) -> int:
        """Return the index of this ResultType in the enum list."""
        rt = ResultType.ResultTypeEnforce(self)
        return list(ResultType).index(rt)

    @staticmethod
    def file_extension(result_type: "ResultType") -> str:
        """Return the standard file extension for a given ResultType.

        Args:
            result_type: The ResultType to get extension for

        Returns:
            File extension string without leading dot (e.g., "html", "kml", "txt")
        """
        rt = ResultType.ResultTypeEnforce(result_type)
        if rt == ResultType.HTML:
            return "html"
        elif rt == ResultType.KML or rt == ResultType.KML2:
            return "kml"
        elif rt == ResultType.SUM:
            return "txt"  # Changed from "md" to match old behavior
        else:
            return "html"

    @staticmethod
    def for_file_extension(file_extension: str) -> "ResultType":
        """Return the appropriate ResultType for a given file extension.

        Args:
            file_extension: File extension with or without leading dot

        Returns:
            Corresponding ResultType (defaults to HTML if unrecognized)
        """
        ext = file_extension.lower().lstrip(".")
        if ext == "html":
            return ResultType.HTML
        elif ext == "kml":
            return ResultType.KML
        elif ext in ("txt", "md"):  # Support both txt and md
            return ResultType.SUM
        else:
            _log.warning("Unsupported file extension for ResultType: %s; reverting to HTML", file_extension)
            return ResultType.HTML

    @staticmethod
    def list_values():
        """Return a list of all ResultType values as strings."""
        return [rt.value for rt in ResultType]
