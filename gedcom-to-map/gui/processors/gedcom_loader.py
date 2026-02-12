"""
GEDCOM parsing and geocoding operations.

This module handles loading GEDCOM files and resolving addresses to GPS coordinates.
Extracted from visual_map_actions.py for better separation of concerns.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

from geo_gedcom.person import Person
from geo_gedcom.geolocated_gedcom import GeolocatedGedcom
from services.interfaces import IConfig, IState, IProgressTracker
from const import GLOBAL_GEO_CACHE_FILENAME, FILE_ALT_PLACE_FILENAME_SUFFIX, FILE_GEOCACHE_FILENAME_SUFFIX

_log = logging.getLogger(__name__.lower())


class GedcomLoader:
    """Handles GEDCOM file parsing and geocoding operations.

    Responsibilities:
    - Parse GEDCOM files
    - Geocode place names to GPS coordinates
    - Manage geocoding cache
    - Validate cache paths

    Attributes:
        panel: Reference to parent VisualMapPanel for UI updates
        svc_state: Runtime state service for accessing lookup and people data
    """

    def __init__(self, panel: Any, svc_state: Optional["IState"] = None) -> None:
        """Initialize GEDCOM loader.

        Args:
            panel: Parent VisualMapPanel instance for UI access.
            svc_state: Optional runtime state service (defaults to panel.svc_state if not provided).
        """
        self.panel: Any = panel
        self.svc_state: Optional["IState"] = svc_state or getattr(panel, "svc_state", None)

    def ParseAndGPS(
        self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker, stage: int = 0
    ) -> Optional[Dict[str, Person]]:
        """Parse GEDCOM file and resolve addresses to GPS coordinates.

        Two-stage process controlled by stage parameter:
        - Stage 0/1: Parse GEDCOM and clear cached data
        - Stage 1: Additionally geocode all places

        Creates GeolocatedGedcom instance that:
        - Parses GEDCOM file structure
        - Corrects common GEDCOM errors
        - Geocodes place names to lat/lon coordinates
        - Loads/saves global and per-file geocoding caches
        - Optionally uses alternative place name mappings

        Args:
            svc_config: Configuration service
            svc_state: Runtime state service
            svc_progress: Progress tracking service
            stage: Processing stage:
                   0 or 1: Clear people/lookup, set newload flag
                   1: Also perform geocoding

        Returns:
            Optional[Dict[str, Person]]: Dictionary of Person objects keyed by xref_id,
                                         or None if stage != 1.

        Side Effects:
            - Sets svc_state.people to parsed Person objects
            - Sets svc_state.lookup to GeolocatedGedcom instance
            - Sets svc_config gpsfile to cache file path
            - Sets svc_config Main to first person if not already set
            - Saves updated geocoding cache to disk
            - Sets newload flag

        Raises:
            Logs errors if:
            - GEDCOM file cannot be read
            - Geocoding fails
            - Cache cannot be saved

        Example:
            loader = GedcomLoader(panel)
            people = loader.ParseAndGPS(svc_config, svc_state, svc_progress, stage=1)
            if people:
                print(f"Loaded {len(people)} people")

        Note:
            Geocoding requires internet connection and may take time for large files.
            Results are cached to avoid repeated API calls.
        """
        people: Optional[Dict[str, Person]] = None
        gedcom_input = svc_config.get("GEDCOMinput")
        _log.info("Starting parsing of GEDCOM : %s (stage: %d)", gedcom_input, stage)

        if stage == 0 or stage == 1:
            svc_state.people = None  # Clear reference
            svc_state.newload = True
            if hasattr(svc_state, "UpdateBackgroundEvent") and hasattr(svc_state.UpdateBackgroundEvent, "updategrid"):
                svc_state.UpdateBackgroundEvent.updategrid = True

        if stage == 1:
            svc_state.lookup = None  # Clear reference
            _log.info("Starting Address to GPS resolution")
            svc_progress.step("Resolving addresses to GPS locations")
            input_path: Path = Path(gedcom_input)
            if not input_path.is_absolute():
                input_path = (Path.cwd() / input_path).resolve()
            base_file_name: str = input_path.stem

            cachefile: Path = input_path.parent / GLOBAL_GEO_CACHE_FILENAME
            svc_config.set("gpsfile", cachefile)
            alt_place_file_path: Path = input_path.parent / f"{base_file_name}{FILE_ALT_PLACE_FILENAME_SUFFIX}"
            file_geo_cache_path: Path = input_path.parent / f"{base_file_name}{FILE_GEOCACHE_FILENAME_SUFFIX}"
            geo_config_path: Path = svc_config.get("geo_config_file")

            geo_config_updates = svc_config.get("geo_config_overrides")
            geo_coding_options = svc_config.get("geocoding_options", {})
            if geo_coding_options:
                geo_config_updates["default_country"] = geo_coding_options.get("defaultCountry")
                geo_config_updates["always_geocode"] = geo_coding_options.get("geocode_only", False)
                geo_config_updates["cache_only"] = geo_coding_options.get("cache_only", False)
                geo_config_updates["days_between_retrying_failed_lookups"] = geo_coding_options.get(
                    "days_between_retrying_failed_lookups", 7
                )
            try:
                svc_state.lookup = GeolocatedGedcom(
                    gedcom_file=input_path.resolve(),
                    location_cache_file=cachefile,
                    alt_place_file_path=alt_place_file_path if not svc_config.get("skip_file_alt_places") else None,
                    geo_config_path=geo_config_path,
                    geo_config_updates=geo_config_updates,
                    app_hooks=svc_config.get("app_hooks"),
                    fuzz=True,
                )

                svc_state.lookup.save_location_cache()
                svc_state.people = svc_state.lookup.people
                people = svc_state.people
                _log.info("Completed geocoding with %d people", len(people) if people else 0)

            except Exception as e:
                _log.exception("Error during GEDCOM geocoding: %s", e)
                raise

        main_person_id = svc_config.get("Main")
        if people and (not main_person_id or main_person_id not in people):
            svc_config.set("Main", list(people.keys())[0])
            _log.info("Using starting person: %s (%s)", people[svc_config.get("Main")].name, svc_config.get("Main"))

        # Update state with the main person
        if people and svc_config.get("Main"):
            svc_state.setMain(svc_config.get("Main"))
            _log.debug("Set main person in state: %s", svc_config.get("Main"))

        return people

    def updatestats(self) -> str:
        """Calculate and return statistics about geocoded data.

        Computes:
        - Unique addresses and hit rate (how many were successfully geocoded)
        - Unique surnames in dataset

        Returns:
            str: Formatted statistics string
        """
        count_of = ["arrivals", "baptism", "departures", "marriages", "military", "residences"]
        used = 0
        usedNone = 0
        totaladdr = 0
        my_gedcom: Optional[GeolocatedGedcom] = getattr(self.svc_state, "lookup", None) if self.svc_state else None

        if hasattr(my_gedcom, "address_book") and my_gedcom.address_book:
            for place, location in my_gedcom.address_book.addresses().items():
                if getattr(location, "used", 0) > 0:
                    used += 1
                    totaladdr += getattr(location, "used", 0)
                    if (location and location.latlon is None or location.latlon.isNone()) or location is None:
                        usedNone += 1

        hit = 1 - (usedNone / used) if used > 0 else 0
        stats = f"Unique addresses: {used} with unresolvable: {usedNone}\nAddress hit rate {hit:.1%}\n"

        people_list = getattr(self.svc_state, "people", None) if self.svc_state else None
        if people_list:
            surname_list = list(person.surname.lower() for person in people_list.values() if person.surname)
            total_surname = len(set(surname_list))
            stats += f"Unique surnames: {total_surname}\n"

        return stats
