import os
import sys
import time
import subprocess
import webbrowser
import logging

from typing import Any, Optional, Dict, List, Tuple
from pathlib import Path

from models.creator import Creator, LifetimeCreator, CreatorTrace, Person
from render.folium.folium_exporter import foliumExporter
from render.kml1.kml_exporter import KmlExporter
from render.kml2 import KML_Life_Lines
from render.referenced import Referenced
from render.summary import SummaryReportConfig, generate_summary_reports

from gedcom_options import gvOptions, ResultType
from geo_gedcom.geolocated_gedcom import GeolocatedGedcom
from .do_actions_type import DoActionsType
from .file_operations import FileOpener

from const import GLOBAL_GEO_CACHE_FILENAME, FILE_ALT_PLACE_FILENAME_SUFFIX, FILE_GEOCACHE_FILENAME_SUFFIX, GEO_CONFIG_FILENAME

_log = logging.getLogger(__name__.lower())


class VisualMapActions:
    """Action handlers for genealogical visualization and file operations.
    
    This class encapsulates all major operations for the visual mapping application:
    - GEDCOM file parsing and geocoding
    - Map generation (HTML/Folium, KML)
    - Summary report generation
    - File opening with platform-specific handlers
    - Lineage tracing and relationship mapping
    
    All methods delegate to panel attributes (gOp, background_process, etc.) to maintain
    separation between UI lifecycle and business logic.
    
    Attributes:
        panel: Reference to parent VisualMapPanel containing gOp, background_process,
               and other UI components.
    
    Example:
        actions = VisualMapActions(visual_map_panel)
        actions.LoadGEDCOM()
        people = actions.ParseAndGPS(gOp, stage=1)
        actions.doHTML(gOp, people, fullresult=True)
    """

    def __init__(self, panel: Any) -> None:
        """Initialize action handler with reference to parent panel.
        
        Args:
            panel: Parent VisualMapPanel instance providing access to gOp (options),
                   background_process (threading), and UI components.
        """
        self.panel: Any = panel
        self.file_opener: Optional[FileOpener] = None

    def _get_file_opener(self) -> FileOpener:
        """Get or create FileOpener instance.
        
        Lazily initializes FileOpener with file_open_commands configuration
        from panel's gOp options on first access.
        
        Returns:
            FileOpener instance configured with current file_open_commands.
        """
        if self.file_opener is None:
            self.file_opener = FileOpener(self.panel.gOp.file_open_commands)
        return self.file_opener

    def LoadGEDCOM(self) -> None:
        """Trigger background parsing and loading of GEDCOM file.
        
        Initiates asynchronous GEDCOM parsing via background process. If background
        process is already running, sets stopping flag. Disables grid view and updates
        UI to show busy state.
        
        Side Effects:
            - Sets gOp.stopping=True if background process is active
            - Calls panel.OnBusyStart() to show progress UI
            - Disables grid view checkbox
            - Clears gOp.lookup if cache path differs from source path
            - Triggers background process with PARSE action
        
        Note:
            Actual parsing happens asynchronously in background thread.
        """
        bp = self.panel.background_process
        gOp = self.panel.gOp
        if getattr(bp, "IsTriggered", lambda: False)():
            gOp.stopping = True
        else:
            self.panel.OnBusyStart(-1)
            time.sleep(0.1)
            gOp.set('GridView', False)
            try:
                self.panel.id.CBGridView.SetValue(False)
            except Exception:
                pass

            cachepath, _ = os.path.split(gOp.get('GEDCOMinput'))
            if gOp.get('gpsfile'):
                sourcepath, _ = os.path.split(gOp.get('gpsfile'))
            else:
                sourcepath = None
            if getattr(gOp, "lookup", None) and cachepath != sourcepath:
                try:
                    del gOp.lookup
                except Exception:
                    gOp.lookup = None
            gOp.step('Loading GEDCOM')
            action: DoActionsType = DoActionsType.PARSE
            bp.Trigger(action)

    def DrawGEDCOM(self) -> None:
        """Trigger background generation of visualization output.
        
        Initiates asynchronous generation of HTML/KML/summary output via background
        process. Validates that output filename is configured before proceeding.
        
        Side Effects:
            - Shows error message if ResultFile is not set
            - Calls panel.OnBusyStart() to show progress UI
            - Triggers background process with GENERATE | REPARSE_IF_NEEDED actions
        
        Raises:
            Logs error and shows user message if gOp.ResultFile is empty.
        
        Note:
            Actual generation happens asynchronously in background thread.
        """
        if not self.panel.gOp.get('ResultFile'):
            _log.error("Error: Not output file name set")
            self.panel.background_process.SayErrorMessage("Error: Please set the Output file name")
        else:
            self.panel.OnBusyStart(-1)
            action: DoActionsType = DoActionsType.GENERATE | DoActionsType.REPARSE_IF_NEEDED
            self.panel.background_process.Trigger(action)

    def OpenCSV(self) -> None:
        """Open CSV GPS output file using configured command.
        
        Retrieves command for CSV file type from file_open_commands configuration
        and opens the GPS file (gOp.gpsfile) using that command.
        
        Side Effects:
            - Opens CSV file in external application via FileOpener
        """
        gps_file = str(self.panel.gOp.get('gpsfile'))
        self._get_file_opener().open_file('csv', gps_file)

    def LoadFile(self, file_type: str = 'html', datafile: str = '') -> None:
        """Open file using command configured for specified file type.
        
        Looks up command for file_type in file_open_commands configuration and
        opens datafile using that command. For HTML/KML file types, can force
        opening in web browser. Falls back to default browser for HTML/KML if
        no command is configured.
        
        Args:
            file_type: Type of file to open. Case-insensitive, uppercased for lookup.
                      Common types: 'html', 'kml', 'kml2', 'csv', 'trace'.
            datafile: Path to file to open.
        
        Example:
            # Open HTML in browser
            actions.LoadFile('html', '/path/to/map.html')
            
            # Open CSV in configured viewer
            actions.LoadFile('csv', '/path/to/data.csv')
        
        Note:
            If no command is configured for file_type and it's not HTML/KML,
            logs error and returns without opening file.
        """
        try:
            self._get_file_opener().open_file(file_type, datafile)
        except Exception as e:
            _log.exception("Failed to open file")
            bg = getattr(self.panel.gOp, "BackgroundProcess", None)
            if bg:
                bg.SayErrorMessage(f"Could not open {datafile}: {e}")

    def SaveTrace(self) -> None:
        """Generate and optionally open trace file listing all referenced people.
        
        Creates tab-delimited text file containing information about each person
        referenced in the visualization:
        - Person ID (xref_id)
        - Name
        - Reference year (birth or other significant date)
        - Location description
        - GPS coordinates
        - Relationship path from main person
        
        Trace file is saved as <resultfile_base>.trace.txt in the output directory.
        If gOp.SummaryOpen is True, attempts to open the trace file after creation.
        
        Side Effects:
            - Creates .trace.txt file in output directory
            - Shows info/error messages via background process
            - Opens trace file if configured
        
        Raises:
            Logs error if:
            - ResultFile or Referenced not available
            - lastlines not available (requires prior HTML generation)
            - File cannot be opened for writing
            - Individual person data write fails
        
        Note:
            Requires prior call to doHTML() to populate gOp.lastlines with path data.
        """
        gOp: gvOptions = self.panel.gOp
        bp = self.panel.background_process

        if gOp.ResultFile and getattr(gOp, "Referenced", None):
            if not getattr(gOp, "lastlines", None):
                _log.error("No lastline values in SaveTrace (do draw first using HTML Mode for this to work)")
                return

            tracepath: str = os.path.splitext(gOp.ResultFile)[0] + ".trace.txt"
            try:
                trace = open(tracepath, "w")
            except Exception as e:
                _log.error("Could not open trace file %s for writing %s", tracepath, e)
                bp.SayErrorMessage(f"Error: Could not open trace file {tracepath} for writing {e}")
                return

            trace.write("id\tName\tYear\tWhere\tGPS\tPath\n")
            people: Dict[str, Person] = bp.people or {}
            for h in people:
                try:
                    if gOp.Referenced.exists(people[h].xref_id):
                        ref_year, _ = people[h].ref_year()
                        (location, where) = people[h].bestlocation()
                        personpath: List[str] = gOp.lastlines[people[h].xref_id].path
                        trace.write(
                            f"{people[h].xref_id}\t{people[h].name}\t{ref_year}\t{where}\t{location}\t" + "\t".join(personpath) + "\n"
                        )
                except Exception:
                    _log.exception("SaveTrace: writing person %r failed", h)
            trace.close()
            _log.info("Trace file saved %s", tracepath)
            withall: str = "with all people" if gOp.get('AllEntities') else ""
            bp.SayInfoMessage(f"Trace file {withall} saved: {tracepath}", True)
            self.LoadFile('trace', tracepath)
        else:
            _log.error("SaveTrace: missing ResultFile or Referenced")

    def OpenBrowser(self) -> None:
        """Open most recently generated output file in appropriate viewer.
        
        Opens the file specified in gOp.ResultFile using the appropriate handler
        based on gOp.ResultType:
        - SUM: Opens CSV summary file with CSV viewer
        - KML/KML2: Opens KML file with configured KML viewer/Google Earth
        - Other: Falls back to opening KMLMAPSURL in browser
        
        Side Effects:
            - Opens file in external application via LoadFile()
        
        Note:
            File must exist at Path(gOp.resultpath) / gOp.ResultFile
        """
        gOp: gvOptions = self.panel.gOp
        result_type = gOp.get('ResultType', '')
        result_path: Path = Path(gOp.resultpath) / gOp.ResultFile
        result_path = result_path.resolve()
        if result_type and result_path.exists():
            if result_type == ResultType.SUM:
                self.LoadFile('csv', str(result_path))
            elif result_type in (ResultType.KML, ResultType.KML2):
                self.LoadFile('kml', str(result_path))
            else:
                self.LoadFile('default', getattr(__import__("const"), "KMLMAPSURL", "/"))

    def doHTML(self, gOp: gvOptions, people: Dict[str, Person], fullresult: bool) -> bool:
        """Generate interactive HTML map using Folium library.
        
        Creates lifetime lines for selected people (starting from gOp.Main) and
        exports to interactive HTML map with Folium. Optionally includes all people
        in dataset if gOp.AllEntities is True.
        
        Process:
        1. Create LifetimeCreator with people data
        2. Generate lifetime lines starting from main person
        3. Optionally add all other people
        4. Export to HTML using foliumExporter
        5. Optionally open in browser if fullresult=True
        
        Args:
            gOp: Global options containing:
                 - Main: xref_id of starting person
                 - MaxMissing: Maximum years gap to interpolate locations
                 - AllEntities: If True, include all people in map
                 - resultpath, ResultFile: Output location
            people: Dictionary of Person objects keyed by xref_id.
            fullresult: If True, opens generated HTML in browser after creation.
        
        Returns:
            bool: True if HTML generation succeeded, False if errors occurred.
        
        Side Effects:
            - Sets gOp.mainPerson to starting Person object
            - Sets gOp.totalpeople to count of people in output
            - Creates HTML file at gOp.resultpath/gOp.ResultFile
            - Opens browser if fullresult=True
        
        Raises:
            Logs error and returns False if:
            - No people provided
            - Starting person (gOp.Main) not found in people dict
            - Folium export fails
            - Result file not found after generation
        
        Example:
            success = actions.doHTML(gOp, people_dict, fullresult=True)
            if success:
                print("Map generated and opened in browser")
        """
        if (not people):
            _log.error("doHTML: no people provided")
            return False
        
        _log.debug  ("Creating Lifeline (fullresult:%s)", fullresult)
        lifeline: LifetimeCreator = LifetimeCreator(people, gOp.MaxMissing)    
        _log.debug  ("Creating People ")
        creator: list = lifeline.create(gOp.Main)    
        if gOp.Main not in people:
            _log.error ("Could not find your starting person: %s", gOp.Main)
            try:
                gOp.stopstep('Error could not find first person')
            except Exception:
                pass
            return False
        
        gOp.setMainPerson(people[gOp.Main])
        if gOp.AllEntities:
            gOp.step('Creating life line for everyone')
            lifeline.createothers(creator)
            _log.info ("Total of %i people & events.", len(creator))   
        gOp.totalpeople = len(creator)

        try:
            foliumExporter(gOp).export(people[gOp.Main], creator, fullresult)
        except Exception:
            _log.exception("doHTML: folium export failed")
            return False
        
        if (fullresult):
            result_path: Path = Path(gOp.resultpath) / gOp.ResultFile
            result_path = result_path.resolve()
            if result_path.exists():
                url: str = result_path.as_uri()
                opened: bool = webbrowser.open(url, new=0, autoraise=True)
                if not opened:
                    # platform fallbacks
                    if sys.platform == "darwin":
                        subprocess.run(["open", str(result_path)])
                    elif os.name == "posix":
                        subprocess.run(["xdg-open", str(result_path)])
                    elif os.name == "nt":
                        os.startfile(str(result_path))
            else:
                _log.error("Result file not found: %s", result_path)
                return False
        return True

    def Geoheatmap(self, gOp: gvOptions) -> bool:
        """Generate geocoded HTML heatmap in one step.
        
        Convenience method that parses GEDCOM, geocodes locations, and generates
        HTML map with browser auto-open. Equivalent to calling ParseAndGPS()
        followed by doHTML() with fullresult=True.
        
        Args:
            gOp: Global options containing GEDCOM path, output settings, and
                 geocoding configuration.
        
        Returns:
            bool: True if successful (GEDCOM parsed and HTML generated),
                  False if errors occurred.
        
        Example:
            success = actions.Geoheatmap(gOp)
            if success:
                print("Heatmap generated and opened in browser")
        
        See Also:
            ParseAndGPS(): GEDCOM parsing and geocoding
            doHTML(): HTML map generation
        """
        people: Optional[Dict[str, Person]] = self.ParseAndGPS(gOp)
        if not people:
            _log.error("Geoheatmap: ParseAndGPS returned no people")
            return False
        return self.doHTML(gOp, people, True)

    def doKML(self, gOp: gvOptions, people: Dict[str, Person]) -> None:
        """Generate KML output for visualization in Google Earth.
        
        Creates KML file with placemarks for birth and/or death locations based on
        gOp.BornMark and gOp.DieMark settings. Generates separate layers for each
        marker type. Optionally includes all people if gOp.AllEntities is True.
        
        Process:
        1. Check which marker types are enabled (birth/death)
        2. For each enabled marker type:
           - Create Creator to generate location data
           - Export to KML layer via KmlExporter
        3. Finalize KML file
        4. Open in configured KML viewer
        
        Args:
            gOp: Global options containing:
                 - BornMark: If True, include birth markers
                 - DieMark: If True, include death markers
                 - Main: xref_id of starting person
                 - MaxMissing: Maximum years gap to interpolate
                 - AllEntities: If True, include all people
                 - resultpath, ResultFile: Output location
            people: Dictionary of Person objects keyed by xref_id.
        
        Side Effects:
            - Creates KML file at gOp.resultpath/gOp.ResultFile
            - Shows info/error messages via background process
            - Opens KML file if command is configured
        
        Raises:
            Logs error if:
            - Neither birth nor death markers enabled
            - Starting person (gOp.Main) not found
            - KML export fails
            - Configured KML command cannot be executed
        
        Example:
            gOp.set('BornMark', True)
            gOp.set('DieMark', True)
            actions.doKML(gOp, people_dict)
        """
        if not people:
            return
        kml_instance: Optional[KmlExporter] = None

        placeTypes: List[List[str]] = []
        if getattr(gOp, "BornMark", False):
            placeTypes.append(["birth", "(b)", "birth"])
        if getattr(gOp, "DieMark", False):
            placeTypes.append(["death", "(d)", "death"])

        if not placeTypes:
            try:
                gOp.stopstep("Error select at least Birth or Death markers to map")
            except Exception:
                pass
            _log.error("Neither birth or death marker is selected")
            return

        for (key, nametag, placeType) in placeTypes:
            lifeline: Creator = Creator(people, getattr(gOp, "MaxMissing", 0), gpstype=key)
            creator: list = lifeline.create(getattr(gOp, "Main", None))
            if getattr(gOp, "AllEntities", False):
                lifeline.createothers(creator)
                _log.info("Total of %i people.", len(creator))

            if getattr(gOp, "Main", None) not in people:
                _log.error("Could not find your starting person: %s", getattr(gOp, "Main", None))
                try:
                    gOp.stopstep("Error could not find first person")
                except Exception:
                    pass
                return

            try:
                gOp.setMainPerson(people[gOp.Main])
            except Exception:
                pass

            if not kml_instance:
                kml_instance = KmlExporter(gOp)

            try:
                kml_instance.export(people[gOp.Main].latlon, creator, nametag, placeType)
            except Exception:
                _log.exception("doKML: export failed for %s", nametag)

        bg = getattr(gOp, "BackgroundProcess", None)
        if kml_instance:
            try:
                kml_instance.Done()
            except Exception:
                _log.debug("doKML: KmlExporter.Done failed")
            resultFile: str = os.path.join(getattr(gOp, "resultpath", ""), getattr(gOp, "ResultFile", ""))
            if bg:
                bg.SayInfoMessage(f"KML output to : {resultFile}")
            self.LoadFile('kml', resultFile)
        else:
            _log.error("No KML output created")
            if bg:
                bg.SayInfoMessage("No KML output created - No data selected to map")

    def doKML2(self, gOp: gvOptions, people: Dict[str, Person]) -> None:
        """Generate KML output using alternate/legacy KML exporter.
        
        Creates KML file using KML_Life_Lines exporter (alternate implementation
        from render.kml module). This version creates life line connections between
        birth/death locations and includes parent connections.
        
        Args:
            gOp: Global options containing:
                 - lookup: GeolocatedGedcom instance with geocoded data
                 - resultpath, ResultFile: Output location
            people: Dictionary of Person objects (unused by this exporter).
        
        Side Effects:
            - Creates KML file at gOp.resultpath/gOp.ResultFile
            - Shows info/error messages via background process
            - Opens KML file if command is configured
        
        Raises:
            Logs error if:
            - gOp.lookup not available (GEDCOM not geocoded)
            - KML_Life_Lines creation/export fails
            - Configured KML command cannot be executed
        
        Note:
            Requires prior call to ParseAndGPS() to populate gOp.lookup.
        
        Example:
            people = actions.ParseAndGPS(gOp, stage=1)
            actions.doKML2(gOp, people)
        """
        if (not gOp.lookup):
            _log.error("doKML2: GeolocatedGedcom is not processed")
            return
        resultFile: str = os.path.join(gOp.resultpath, gOp.ResultFile)

        try:
            kml_life_lines: KML_Life_Lines = KML_Life_Lines(gedcom=gOp.lookup, kml_file=str(resultFile),
                                                connect_parents=True, save=True)
        except Exception:
            _log.exception("doKML2: KML_Life_Lines creation/export failed")
            bg = getattr(gOp, "BackgroundProcess", None)
            if bg:
                try:
                    bg.SayInfoMessage("KML(2) generation failed")
                except Exception:
                    pass
            return
        
        bg = getattr(gOp, "BackgroundProcess", None)
        if kml_life_lines:
            if bg:
                try:
                    bg.SayInfoMessage(f"KML(2) output to : {resultFile}")
                except Exception:
                    pass
            self.LoadFile('kml', resultFile)
        else:
            _log.error("No KML output created")
            if bg:
                try:
                    bg.SayInfoMessage(f"No KML output created - No data selected to map")
                except Exception:
                    pass

    def doSUM(self, gOp: gvOptions) -> None:
        """Generate various CSV summary reports from geocoded GEDCOM data.
        
        Creates multiple summary files based on settings in gOp:
        - Places summary: All unique places with geocoding info
        - People summary: All individuals with key dates/locations
        - Countries summary: Birth/death counts by country (CSV + optional chart)
        - Geocache summary: Geocoding cache for debugging
        - Alternative places: Alt place name mappings
        
        All outputs are saved to gOp.resultpath with filenames based on input
        GEDCOM filename. Optionally opens generated files if gOp.SummaryOpen is True.
        
        Args:
            gOp: Global options containing:
                 - lookup: GeolocatedGedcom with geocoded data
                 - GEDCOMinput: Input GEDCOM path (for naming outputs)
                 - resultpath: Output directory
                 - SummaryPlaces: Generate places CSV
                 - SummaryPeople: Generate people CSV
                 - SummaryCountries: Generate countries CSV
                 - SummaryCountriesGrid: Generate countries chart image
                 - SummaryGeocode: Generate geocache CSV
                 - SummaryAltPlaces: Generate alt places CSV
                 - SummaryEnrichmentIssues: Generate enhancement issues report
                 - SummaryStatistics: Generate statistics summary
                 - SummaryOpen: Auto-open generated files
        
        Side Effects:
            - Creates CSV files in gOp.resultpath
            - May create PNG chart for countries summary
            - Shows info/error messages via background process
            - Opens files if SummaryOpen is True
        
        Raises:
            Logs error if:
            - gOp.lookup not available (GEDCOM not geocoded)
            - Individual summary writer functions fail
            - File opening fails
        
        Example:
            gOp.set('SummaryPlaces', True)
            gOp.set('SummaryPeople', True)
            gOp.set('SummaryOpen', True)
            actions.doSUM(gOp)
        
        Note:
            Requires prior call to ParseAndGPS() to populate gOp.lookup.
        """
        base_file_name: str = Path(getattr(gOp, "GEDCOMinput", "")).resolve().stem
        output_folder: Path = Path(getattr(gOp, "resultpath", ".")).resolve()
        my_gedcom: Optional[GeolocatedGedcom] = getattr(gOp, "lookup", None)
        bg = getattr(gOp, "BackgroundProcess", None)

        if my_gedcom is None:
            _log.error("doSUM: geolocated GEDCOM (gOp.lookup) is not available")
            if bg:
                try:
                    bg.SayErrorMessage("doSUM: geocoded GEDCOM data not available")
                except Exception:
                    pass
            return

        # Extract summary report configuration from gOp
        config = SummaryReportConfig.from_gvOptions(gOp)

        # Generate all selected summary reports
        generate_summary_reports(config, my_gedcom, base_file_name, output_folder, bg, file_loader=self)

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
            # Parse only
            people = actions.ParseAndGPS(gOp, stage=0)
            
            # Parse and geocode
            people = actions.ParseAndGPS(gOp, stage=1)
            if people:
                print(f"Loaded {len(people)} people")
        
        Note:
            Geocoding requires internet connection and may take time for large files.
            Results are cached to avoid repeated API calls.
        """
        people: Optional[Dict[str, Person]] = None
        _log.info ("Starting parsing of GEDCOM : %s (stage: %d)", gOp.GEDCOMinput, stage)
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
                    # per_file_geo_cache=file_geo_cache_path,
                    app_hooks=gOp.app_hooks,
                    fuzz = True
                )
                _log.info ("Completed Geocode")
                gOp.lookup.save_location_cache()
                gOp.people = gOp.lookup.people
                _log.info ("Completed resolves")
                people = gOp.people
        
        if people and (not gOp.Main or not gOp.Main in list(people.keys())):
                gOp.set('Main', list(people.keys())[0])
                _log.info ("Using starting person: %s (%s)", people[gOp.Main].name, gOp.Main)
        
        return people

    def gedcom_to_map(self, gOp: gvOptions) -> None:
        """Parse GEDCOM, geocode, and generate KML visualization in one step.
        
        Convenience method that combines ParseAndGPS() and doKML() to create
        KML output from GEDCOM file in a single operation.
        
        Args:
            gOp: Global options containing GEDCOM path, output settings, and
                 KML marker configuration.
        
        Side Effects:
            - Parses and geocodes GEDCOM file
            - Creates KML file at gOp.resultpath/gOp.ResultFile
            - Opens KML file if command is configured
        
        Raises:
            Logs error if:
            - ParseAndGPS returns no people
            - Panel actions not available
        
        Example:
            gOp.set('BornMark', True)
            gOp.set('DieMark', True)
            actions.gedcom_to_map(gOp)
        
        See Also:
            ParseAndGPS(): GEDCOM parsing and geocoding
            doKML(): KML generation
        """
        people: Optional[Dict[str, Person]] = self.ParseAndGPS(gOp)
        if not people:
            _log.error("gedcom_to_map: ParseAndGPS returned no people")
            return
        panel_actions = getattr(getattr(gOp, "panel", None), "actions", None)
        if panel_actions:
            panel_actions.doKML(gOp, people)
        else:
            _log.error("gedcom_to_map: panel actions not available")

    def doTrace(self, gOp: gvOptions) -> int:
        """Trace and collect all people connected to main person.
        
        Starting from gOp.Main person, recursively finds all related people
        (ancestors, descendants, spouses) and stores their relationship paths
        in gOp.Referenced. Each person's path is a list of relationship tags
        ('F' for father, 'M' for mother, etc.) showing how they connect to
        the main person.
        
        Args:
            gOp: Global options containing:
                 - people: Dictionary of all Person objects
                 - Main: xref_id of starting person for trace
        
        Returns:
            int: Total count of people found in trace, or 0 if error.
        
        Side Effects:
            - Initializes gOp.Referenced as empty Referenced set
            - Populates gOp.Referenced with xref_ids and relationship paths
            - Sets gOp.totalpeople to count of people found
        
        Raises:
            Logs error if:
            - No people data available (gOp.people is empty)
            - Starting person (gOp.Main) not found in people dict
        
        Example:
            count = actions.doTrace(gOp)
            print(f"Found {count} related people")
            
            # Check if person is related
            if gOp.Referenced.exists('I0042'):
                path = gOp.Referenced.gettag('I0042')
                print(f"Relationship path: {path}")
        
        Note:
            Must be called before doTraceTo() or SaveTrace() to populate
            Referenced set.
        """
        
        gOp.Referenced = Referenced()
        gOp.totalpeople = 0
        
        if not gOp.people:
            _log.error ("Trace:References no people.")
            return 0
        people: Dict[str, Person] = gOp.people
        if gOp.Main not in people:
            _log.error  ("Trace:Could not find your starting person: %s", gOp.Main)
            return 0
        gOp.Referenced.add(gOp.Main)
        lifeline: CreatorTrace = CreatorTrace(people)

        creator: list = lifeline.create(gOp.Main)

        _log.info  ("Trace:Total of %i people.", len(creator)) 
        if  creator:
            for c in creator:
                gOp.Referenced.add(c.person.xref_id,tag=c.path)
        
        gOp.totalpeople = len(creator) if creator else 0
        return gOp.totalpeople

    def doTraceTo(self, gOp: gvOptions, ToID: Person) -> List[Tuple[str, str, Optional[int], str]]:
        """Trace lineage path from main person to specified target person.
        
        Builds ancestry chain connecting gOp.mainPerson to ToID by following
        the parent relationships stored in gOp.Referenced. Each step in the path
        identifies whether connection is through father or mother.
        
        Process:
        1. Calls doTrace() if gOp.Referenced not populated
        2. Starts with main person
        3. For each relationship tag in Referenced path:
           - 'F': Follow father link
           - 'M': Follow mother link
        4. Builds list of (relationship, name, birth_year, xref_id) tuples
        
        Args:
            gOp: Global options containing:
                 - mainPerson: Starting Person object
                 - people: Dictionary of all Person objects
                 - Referenced: Set with relationship paths (populated by doTrace)
            ToID: Target Person to trace lineage to.
        
        Returns:
            List[Tuple[str, str, Optional[int], str]]: List of ancestry steps, each tuple:
                - relationship: "[Father]", "[Mother]", "NotDirect", or ""
                - name: Person's name
                - birth_year: Birth year (None if unknown)
                - xref_id: Person's ID
        
            Returns list with single "NotDirect" entry if ToID not in Referenced set.
            Returns empty list if mainPerson not set.
        
        Side Effects:
            - Sets gOp.heritage to resulting lineage list
            - Calls doTrace() if not already called
        
        Raises:
            Logs error if:
            - gOp.mainPerson not set
            - Parent (father/mother) not found in people dict
            - Invalid relationship tag encountered
        
        Example:
            target = people['I0042']
            lineage = actions.doTraceTo(gOp, target)
            for rel, name, year, xref in lineage:
                print(f"{rel:15} {name:30} b.{year or '?'} ({xref})")
        
            # Output example:
            #                 John Smith                 b.1950 (I0001)
            # [Father]        Robert Smith               b.1920 (I0025)
            # [Father]        William Smith              b.1890 (I0042)
        
        Note:
            Requires prior call to doTrace() to populate Referenced set,
            though will call it automatically if needed.
        """
        if not gOp.Referenced:
            self.doTrace(gOp)
        
        if not getattr(gOp, "mainPerson", None):
            _log.error("doTraceTo: gOp.mainPerson not set")
            return []
        
        people: Dict[str, Person] = gOp.people
        heritage: List[Tuple[str, str, Optional[int], str]] = []
        heritage = [("", gOp.mainPerson.name, gOp.mainPerson.ref_year()[0], gOp.mainPerson.xref_id)]
        if gOp.Referenced.exists(ToID.xref_id):
            personRelated: Optional[List[str]] = gOp.Referenced.gettag(ToID.xref_id)
            personTrace: Person = gOp.mainPerson
            if personRelated:    
                for r in personRelated:
                    tag: str = "Unknown"  # Initialize with default value
                    if r == "F":
                        try:
                            personTrace = people[personTrace.father]
                        except KeyError:
                            _log.error("doTraceTo: father %s not in people dict", personTrace.father)
                            break
                        tag = "Father"
                    elif r == "M":
                        try:
                            personTrace = people[personTrace.mother]
                        except KeyError:
                            _log.error("doTraceTo: mother %s not in people dict", personTrace.mother)
                            break
                        tag = "Mother"
                    else:
                        _log.error("doTrace - neither Father or Mother, how did we get here?")
                        tag = "Unknown"
                    heritage.append((f"[{tag}]",personTrace.name, personTrace.ref_year()[0], personTrace.xref_id))
        else:
            heritage.append(("NotDirect", ToID.name, None, ToID.xref_id))
        gOp.heritage = heritage
        return heritage
    
    def updatestats(self):
        # count of 
        count_of = ['arrivals', 'baptism', 'departures', 'marriages', 'military', 'residences']
        used = 0
        usedNone = 0
        totaladdr = 0
        my_gedcom: Optional[GeolocatedGedcom] = getattr(self.panel.gOp, "lookup", None)
        if hasattr(my_gedcom, 'address_book') and my_gedcom.address_book:
            for place,location in my_gedcom.address_book.addresses().items():
                
                if (getattr(location, 'used',0) > 0): 
                    used += 1
                    totaladdr += getattr(location, 'used',0)
                    if (location and location.latlon is None or location.latlon.isNone()) or location is None : 
                        usedNone += 1
        hit = 1-(usedNone / used) if used > 0 else 0
        self.stats = f"Unique addresses: {used} with unresolvable: {usedNone}\nAddress hit rate {hit:.1%}\n" 
        people_list = getattr(self.panel.gOp, "people", None)
        if people_list:
            surname_list = list(person.surname.lower() for person in people_list.values() if person.surname )
            total_surname = len(set(surname_list))
            self.stats += f"Unique surnames: {total_surname}\n"
        return self.stats
