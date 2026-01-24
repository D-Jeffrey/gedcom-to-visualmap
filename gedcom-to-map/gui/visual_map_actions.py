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
from .gedcom_loader import GedcomLoader
from .map_generator import MapGenerator
from .report_generator import ReportGenerator
from .lineage_tracer import LineageTracer

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
        
        # Initialize specialized modules
        self.gedcom_loader: GedcomLoader = GedcomLoader(panel)
        self.map_generator: MapGenerator = MapGenerator(panel)
        self.report_generator: ReportGenerator = ReportGenerator(panel, actions=self)
        self.lineage_tracer: LineageTracer = LineageTracer(panel)

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
        
        Delegates to GedcomLoader and MapGenerator.
        
        Args:
            gOp: Global options
        
        Returns:
            bool: True if successful, False otherwise
        """
        people: Optional[Dict[str, Person]] = self.ParseAndGPS(gOp, stage=1)
        if not people:
            _log.error("Geoheatmap: ParseAndGPS returned no people")
            return False
        return self.map_generator.doHTML(gOp, people, True)

    def doKML(self, gOp: gvOptions, people: Dict[str, Person]) -> None:
        """Generate KML output for visualization in Google Earth.
        
        Delegates to MapGenerator.doKML().
        
        Args:
            gOp: Global options
            people: Dictionary of Person objects
        """
        self.map_generator.doKML(gOp, people)

    def doKML2(self, gOp: gvOptions, people: Dict[str, Person]) -> None:
        """Generate KML output using alternate/legacy KML exporter.
        
        Delegates to MapGenerator.doKML2().
        
        Args:
            gOp: Global options
            people: Dictionary of Person objects
        """
        self.map_generator.doKML2(gOp, people)

    def doSUM(self, gOp: gvOptions) -> None:
        """Generate various CSV summary reports from geocoded GEDCOM data.
        
        Delegates to ReportGenerator.doSUM().
        
        Args:
            gOp: Global options
        """
        self.report_generator.doSUM(gOp)

    def ParseAndGPS(self, gOp: gvOptions, stage: int = 0) -> Optional[Dict[str, Person]]:
        """Parse GEDCOM file and resolve addresses to GPS coordinates.
        
        Delegates to GedcomLoader.ParseAndGPS().
        
        Args:
            gOp: Global options
            stage: Processing stage (0 or 1)
        
        Returns:
            Optional[Dict[str, Person]]: Dictionary of Person objects or None
        """
        return self.gedcom_loader.ParseAndGPS(gOp, stage)

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
        
        Delegates to LineageTracer.doTrace().
        
        Args:
            gOp: Global options
        
        Returns:
            int: Total count of people found in trace
        """
        return self.lineage_tracer.doTrace(gOp)

    def doTraceTo(self, gOp: gvOptions, ToID: Person) -> List[Tuple[str, str, Optional[int], str]]:
        """Trace lineage path from main person to specified target person.
        
        Delegates to LineageTracer.doTraceTo().
        
        Args:
            gOp: Global options
            ToID: Target Person to trace lineage to
        
        Returns:
            List[Tuple[str, str, Optional[int], str]]: List of ancestry steps
        """
        return self.lineage_tracer.doTraceTo(gOp, ToID)
    
    def updatestats(self):
        """Calculate geocoding statistics.
        
        Delegates to GedcomLoader.updatestats().
        
        Returns:
            str: Formatted statistics string
        """
        return self.gedcom_loader.updatestats()


# Standalone wrapper functions for backwards compatibility with command-line interface
def Geoheatmap(gOp: gvOptions) -> bool:
    """Standalone wrapper for VisualMapActions.Geoheatmap().
    
    Creates a minimal VisualMapActions instance to call the Geoheatmap method.
    Used by command-line interface (gedcom-to-map.py).
    
    Args:
        gOp: Global options
    
    Returns:
        bool: True if successful
    """
    # Create minimal panel object with gOp
    class MinimalPanel:
        def __init__(self, gOp):
            self.gOp = gOp
    
    panel = MinimalPanel(gOp)
    actions = VisualMapActions(panel)
    return actions.Geoheatmap(gOp)


def gedcom_to_map(gOp: gvOptions) -> None:
    """Standalone wrapper for VisualMapActions.gedcom_to_map().
    
    Creates a minimal VisualMapActions instance to call the gedcom_to_map method.
    Used by command-line interface (gedcom-to-map.py).
    
    Args:
        gOp: Global options
    """
    # Create minimal panel object with gOp
    class MinimalPanel:
        def __init__(self, gOp):
            self.gOp = gOp
    
    panel = MinimalPanel(gOp)
    actions = VisualMapActions(panel)
    actions.gedcom_to_map(gOp)
