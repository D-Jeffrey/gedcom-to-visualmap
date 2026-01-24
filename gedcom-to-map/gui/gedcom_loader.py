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
from gedcom_options import gvOptions
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
    """
    
    def __init__(self, panel: Any) -> None:
        """Initialize GEDCOM loader.
        
        Args:
            panel: Parent VisualMapPanel instance providing access to gOp and background_process
        """
        self.panel: Any = panel
    
    def ParseAndGPS(self, gOp: gvOptions, stage: int = 0) -> Optional[Dict[str, Person]]:
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
            gOp: Global options containing:
                 - GEDCOMinput: Path to GEDCOM file
                 - defaultCountry: Default country for ambiguous places
                 - UseGPS: If True, always attempt geocoding
                 - skip_file_alt_places: If False, use per-file alt places
            stage: Processing stage:
                   0 or 1: Clear people/lookup, set newload flag
                   1: Also perform geocoding
        
        Returns:
            Optional[Dict[str, Person]]: Dictionary of Person objects keyed by xref_id,
                                         or None if stage != 1.
        
        Side Effects:
            - Sets gOp.people to parsed Person objects
            - Sets gOp.lookup to GeolocatedGedcom instance
            - Sets gOp.gpsfile to cache file path
            - Sets gOp.Main to first person if not already set
            - Saves updated geocoding cache to disk
            - Sets gOp.newload=True and updategrid flag
        
        Raises:
            Logs errors if:
            - GEDCOM file cannot be read
            - Geocoding fails
            - Cache cannot be saved
        
        Example:
            loader = GedcomLoader(panel)
            people = loader.ParseAndGPS(gOp, stage=1)
            if people:
                print(f"Loaded {len(people)} people")
        
        Note:
            Geocoding requires internet connection and may take time for large files.
            Results are cached to avoid repeated API calls.
        """
        people: Optional[Dict[str, Person]] = None
        _log.info("Starting parsing of GEDCOM : %s (stage: %d)", gOp.GEDCOMinput, stage)
        
        if (stage == 0 or stage == 1):
            gOp.people = None  # Clear reference
            gOp.newload = True
            if hasattr(gOp, "UpdateBackgroundEvent") and hasattr(gOp.UpdateBackgroundEvent, "updategrid"):
                gOp.UpdateBackgroundEvent.updategrid = True

        if (stage == 1):
            gOp.lookup = None  # Clear reference
            _log.info("Starting Address to GPS resolution")
            gOp.step("Resolving addresses to GPS locations")
            input_path: Path = Path(gOp.GEDCOMinput)
            if not input_path.is_absolute():
                input_path = (Path.cwd() / input_path).resolve()
            base_file_name: str = input_path.stem
            
            cachefile: Path = input_path.parent / GLOBAL_GEO_CACHE_FILENAME
            gOp.gpsfile = cachefile
            alt_place_file_path: Path = input_path.parent / f"{base_file_name}{FILE_ALT_PLACE_FILENAME_SUFFIX}"
            file_geo_cache_path: Path = input_path.parent / f"{base_file_name}{FILE_GEOCACHE_FILENAME_SUFFIX}"
            geo_config_path: Path = gOp.geo_config_file
            defaultCountry: Optional[str] = gOp.get('defaultCountry') or None
            
            gOp.lookup = GeolocatedGedcom(
                gedcom_file=input_path.resolve(), 
                location_cache_file=cachefile,
                default_country=defaultCountry,
                always_geocode=gOp.UseGPS,
                cache_only=gOp.CacheOnly,
                alt_place_file_path=alt_place_file_path if not gOp.skip_file_alt_places else None,
                geo_config_path=geo_config_path,
                app_hooks=gOp.app_hooks,
                fuzz=True
            )
            _log.info("Completed Geocode")
            gOp.lookup.save_location_cache()
            gOp.people = gOp.lookup.people
            _log.info("Completed resolves")
            people = gOp.people
        
        if people and (not gOp.Main or not gOp.Main in list(people.keys())):
            gOp.set('Main', list(people.keys())[0])
            _log.info("Using starting person: %s (%s)", people[gOp.Main].name, gOp.Main)
        
        return people
    
    def updatestats(self) -> str:
        """Calculate and return statistics about geocoded data.
        
        Computes:
        - Unique addresses and hit rate (how many were successfully geocoded)
        - Unique surnames in dataset
        
        Returns:
            str: Formatted statistics string
        """
        count_of = ['arrivals', 'baptism', 'departures', 'marriages', 'military', 'residences']
        used = 0
        usedNone = 0
        totaladdr = 0
        my_gedcom: Optional[GeolocatedGedcom] = getattr(self.panel.gOp, "lookup", None)
        
        if hasattr(my_gedcom, 'address_book') and my_gedcom.address_book:
            for place, location in my_gedcom.address_book.addresses().items():
                if (getattr(location, 'used', 0) > 0): 
                    used += 1
                    totaladdr += getattr(location, 'used', 0)
                    if (location and location.latlon is None or location.latlon.isNone()) or location is None: 
                        usedNone += 1
        
        hit = 1 - (usedNone / used) if used > 0 else 0
        stats = f"Unique addresses: {used} with unresolvable: {usedNone}\nAddress hit rate {hit:.1%}\n" 
        
        people_list = getattr(self.panel.gOp, "people", None)
        if people_list:
            surname_list = list(person.surname.lower() for person in people_list.values() if person.surname)
            total_surname = len(set(surname_list))
            stats += f"Unique surnames: {total_surname}\n"
        
        return stats
