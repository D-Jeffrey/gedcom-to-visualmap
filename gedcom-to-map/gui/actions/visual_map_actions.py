from render.result_type import ResultType
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

from services.interfaces import IConfig, IState, IProgressTracker
from services.state_service import GVState
from services.progress_service import GVProgress
from .do_actions_type import DoActionsType
from .file_operations import FileOpener
from ..processors.gedcom_loader import GedcomLoader
from ..processors.map_generator import MapGenerator
from ..processors.report_generator import ReportGenerator
from ..processors.lineage_tracer import LineageTracer

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
    
    All methods use services architecture (svc_config, svc_state, svc_progress)
    for state management and configuration.
    
    Attributes:
        panel: Reference to parent VisualMapPanel containing services and UI components.
    
    Example:
        actions = VisualMapActions(visual_map_panel)
        actions.LoadGEDCOM()
        people = actions.ParseAndGPS(svc_config, svc_state, svc_progress, stage=1)
        actions.doHTML(svc_config, svc_state, svc_progress, fullresult=True)
    """

    def __init__(self, panel: Any) -> None:
        """Initialize action handler with reference to parent panel.
        
        Args:
            panel: Parent VisualMapPanel instance providing access to services
                   (svc_config, svc_state, svc_progress) and background_process.
        """
        self.panel: Any = panel
        self.file_opener: Optional['FileOpener'] = None
        
        # Initialize specialized modules
        self.gedcom_loader: 'GedcomLoader' = GedcomLoader(panel)
        self.map_generator: 'MapGenerator' = MapGenerator(panel)
        self.report_generator: 'ReportGenerator' = ReportGenerator(panel, actions=self)
        self.lineage_tracer: LineageTracer = LineageTracer(panel)

    def _get_file_opener(self) -> FileOpener:
        """Get or create FileOpener instance.
        
        Lazily initializes FileOpener with file_open_commands configuration
        from panel's services on first access.
        
        Returns:
            FileOpener instance configured with current file_open_commands.
        """
        if self.file_opener is None:
            self.file_opener = FileOpener(self.panel.svc_config)
        return self.file_opener

    def LoadGEDCOM(self) -> None:
        """Trigger background parsing and loading of GEDCOM file.
        
        Initiates asynchronous GEDCOM parsing via background process. If background
        process is already running, sets stopping flag. Disables grid view and updates
        UI to show busy state.
        
        Side Effects:
            - Sets svc_progress.stopping=True if background process is active
            - Calls panel.OnBusyStart() to show progress UI
            - Disables grid view checkbox
            - Clears svc_state.lookup if cache path differs from source path
            - Triggers background process with PARSE action
        
        Note:
            Actual parsing happens asynchronously in background thread.
        """
        bp = self.panel.background_process
        cfg = self.panel.svc_config
        st = self.panel.svc_state or GVState()
        pr = self.panel.svc_progress or GVProgress()
        
        if getattr(bp, "IsTriggered", lambda: False)():
            try:
                pr.stopping = True
            except Exception:
                pass
        else:
            self.panel.OnBusyStart(-1)
            time.sleep(0.1)
            try:
                cfg.set('GridView', False)
            except Exception:
                pass
            try:
                self.panel.id.CBGridView.SetValue(False)
            except Exception:
                pass

            try:
                cache_in = cfg.get('GEDCOMinput')
            except Exception:
                cache_in = ''
            cachepath, _ = os.path.split(cache_in)
            try:
                gpsfile_val = cfg.get('gpsfile')
            except Exception:
                gpsfile_val = ''
            if gpsfile_val:
                sourcepath, _ = os.path.split(gpsfile_val)
            else:
                sourcepath = None
            if getattr(st, "lookup", None) and cachepath != sourcepath:
                try:
                    del st.lookup
                except Exception:
                    try:
                        st.lookup = None
                    except Exception:
                        pass
            try:
                pr.step('Loading GEDCOM')
            except Exception:
                pass
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
            Logs error and shows user message if ResultFile is empty.
        
        Note:
            Actual generation happens asynchronously in background thread.
        """
        try:
            result_file = self.panel.svc_config.get('ResultFile')
        except Exception:
            result_file = None
        
        if not result_file:
            _log.error("Error: Not output file name set")
            self.panel.background_process.SayErrorMessage("Error: Please set the Output file name")
        else:
            self.panel.OnBusyStart(-1)
            action: DoActionsType = DoActionsType.GENERATE | DoActionsType.REPARSE_IF_NEEDED
            self.panel.background_process.Trigger(action)

    def OpenCSV(self) -> None:
        """Open CSV GPS output file using configured command.
        
        Retrieves GPS file path from svc_config and opens it using FileOpener.
        
        Side Effects:
            - Opens CSV file in external application via FileOpener
        """
        try:
            gps_file = str(self.panel.svc_config.get('gpsfile'))
        except Exception:
            gps_file = ''
        if gps_file:
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
            # Use panel.background_process only; otherwise, log
            bg = getattr(self.panel, "background_process", None)
            if bg and hasattr(bg, 'SayErrorMessage'):
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
        If SummaryOpen config is True, opens the trace file after creation.
        
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
            Requires prior call to doHTML() to populate svc_state.lastlines with path data.
        """
        bp = self.panel.background_process
        svc_state = self.panel.svc_state or GVState()
        svc_config = self.panel.svc_config

        try:
            result_file = svc_config.get('ResultFile')
        except Exception:
            result_file = None
        
        referenced = getattr(svc_state, 'Referenced', None)
        lastlines = getattr(svc_state, 'lastlines', None)

        if result_file and referenced:
            if not lastlines:
                _log.error("No lastline values in SaveTrace (do draw first using HTML Mode for this to work)")
                return

            tracepath: str = os.path.splitext(result_file)[0] + ".trace.txt"
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
                    if referenced.exists(people[h].xref_id):
                        ref_year, _ = people[h].ref_year()
                        (location, where) = people[h].bestlocation()
                        personpath: List[str] = lastlines[people[h].xref_id].path
                        trace.write(
                            f"{people[h].xref_id}\t{people[h].name}\t{ref_year}\t{where}\t{location}\t" + "\t".join(personpath) + "\n"
                        )
                except Exception:
                    _log.exception("SaveTrace: writing person %r failed", h)
            trace.close()
            _log.info("Trace file saved %s", tracepath)
            try:
                all_entities = svc_config.get('AllEntities')
            except Exception:
                all_entities = False
            withall: str = "with all people" if all_entities else ""
            bp.SayInfoMessage(f"Trace file {withall} saved: {tracepath}", True)
            self.LoadFile('trace', tracepath)
        else:
            _log.error("SaveTrace: missing ResultFile or Referenced")

    def OpenBrowser(self) -> None:
        """Open most recently generated output file in appropriate viewer.
        
        Opens the file specified in svc_config ResultFile using the appropriate handler
        based on ResultType:
        - SUM: Opens CSV summary file with CSV viewer
        - KML/KML2: Opens KML file with configured KML viewer/Google Earth
        - Other: Falls back to opening KMLMAPSURL in browser
        
        Side Effects:
            - Opens file in external application via LoadFile()
        
        Note:
            File must exist at Path(resultpath) / ResultFile
        """
        svc_config = self.panel.svc_config
        
        try:
            result_type = svc_config.get('ResultType')
        except Exception:
            result_type = None
        
        try:
            result_dir = svc_config.get('resultpath')
            result_name = svc_config.get('ResultFile')
        except Exception:
            result_dir = None
            result_name = None
        
        if not (result_dir and result_name):
            _log.error("OpenBrowser: resultpath or ResultFile not configured")
            return
        
        result_path: Path = (Path(result_dir) / result_name).resolve()
        if result_type and result_path.exists():
            if result_type == ResultType.SUM:
                self.LoadFile('csv', str(result_path))
            elif result_type in (ResultType.KML, ResultType.KML2):
                self.LoadFile('kml', str(result_path))
            else:
                self.LoadFile('default', getattr(__import__("const"), "KMLMAPSURL", "/"))

    def OpenConfig(self) -> None:
        """Open the Configuration Options dialog.
        
        Opens the configuration dialog where users can adjust geocoding settings,
        logging levels, and file open commands.
        """
        if hasattr(self.panel, 'frame') and hasattr(self.panel.frame, 'onOptionsSetup'):
            # Create a mock event object for onOptionsSetup
            import wx
            event = wx.CommandEvent()
            self.panel.frame.onOptionsSetup(event)
        else:
            _log.error("OpenConfig: Cannot find frame.onOptionsSetup method")

    def doHTML(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker, fullresult: bool) -> bool:
        """Generate interactive HTML map using Folium library.
        
        Delegates to MapGenerator.doHTML().
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service (provides people via svc_state.people)
            svc_progress: Progress tracking service
            fullresult: If True, opens generated HTML in browser
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.map_generator.doHTML(svc_config, svc_state, svc_progress, fullresult)

    def Geoheatmap(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> bool:
        """Generate geocoded HTML heatmap in one step.
        
        Delegates to GedcomLoader and MapGenerator.
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service
            svc_progress: Progress tracking service
        
        Returns:
            bool: True if successful, False otherwise
        """
        people: Optional[Dict[str, Person]] = self.ParseAndGPS(svc_config, svc_state, svc_progress, stage=1)
        if not people:
            _log.error("Geoheatmap: ParseAndGPS returned no people")
            return False
        return self.map_generator.doHTML(svc_config, svc_state, svc_progress, True)

    def doKML(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> None:
        """Generate KML output for visualization in Google Earth.
        
        Delegates to MapGenerator.doKML().
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service (provides people via svc_state.people)
            svc_progress: Progress tracking service
        """
        self.map_generator.doKML(svc_config, svc_state, svc_progress)

    def doKML2(self, svc_config: IConfig, svc_state: IState) -> None:
        """Generate KML output using alternate/legacy KML exporter.
        
        Delegates to MapGenerator.doKML2().
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service (provides lookup via svc_state.lookup)
        """
        self.map_generator.doKML2(svc_config, svc_state)

    def doSUM(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> None:
        """Generate various CSV summary reports from geocoded GEDCOM data.
        
        Delegates to ReportGenerator.doSUM().
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service
            svc_progress: Progress tracking service
        """
        self.report_generator.doSUM(svc_config, svc_state, svc_progress)

    def ParseAndGPS(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker, stage: int = 0) -> Optional[Dict[str, Person]]:
        """Parse GEDCOM file and resolve addresses to GPS coordinates.
        
        Delegates to GedcomLoader.ParseAndGPS().
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service
            svc_progress: Progress tracking service
            stage: Processing stage (0 or 1)
        
        Returns:
            Optional[Dict[str, Person]]: Dictionary of Person objects or None
        """
        return self.gedcom_loader.ParseAndGPS(svc_config, svc_state, svc_progress, stage)

    def gedcom_to_map(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> None:
        """Parse GEDCOM, geocode, and generate KML visualization in one step.
        
        Convenience method that combines ParseAndGPS() and doKML() to create
        KML output from GEDCOM file in a single operation.
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service
            svc_progress: Progress tracking service
        
        Side Effects:
            - Parses and geocodes GEDCOM file
            - Creates KML file at config.result_file
            - Opens KML file if command is configured
        
        Raises:
            Logs error if:
            - ParseAndGPS returns no people
        
        Example:
            svc_config.set('BornMark', True)
            svc_config.set('DieMark', True)
            actions.gedcom_to_map(svc_config, svc_state, svc_progress)
        
        See Also:
            ParseAndGPS(): GEDCOM parsing and geocoding
            doKML(): KML generation
        """
        people: Optional[Dict[str, Person]] = self.ParseAndGPS(svc_config, svc_state, svc_progress)
        if not people:
            _log.error("gedcom_to_map: ParseAndGPS returned no people")
            return
        self.doKML(svc_config, svc_state, svc_progress)

    def doTrace(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> int:
        """Trace and collect all people connected to main person.
        
        Delegates to LineageTracer.doTrace().
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service
            svc_progress: Progress tracking service
        
        Returns:
            int: Total count of people found in trace
        """
        return self.lineage_tracer.doTrace(svc_config, svc_state, svc_progress)

    def doTraceTo(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker, ToID: Person) -> List[Tuple[str, str, Optional[int], str]]:
        """Trace lineage path from main person to specified target person.
        
        Delegates to LineageTracer.doTraceTo().
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service
            svc_progress: Progress tracking service
            ToID: Target Person to trace lineage to
        
        Returns:
            List[Tuple[str, str, Optional[int], str]]: List of ancestry steps
        """
        return self.lineage_tracer.doTraceTo(svc_config, svc_state, svc_progress, ToID)
    
    def updatestats(self):
        """Calculate geocoding statistics.
        
        Delegates to GedcomLoader.updatestats().
        
        Returns:
            str: Formatted statistics string
        """
        return self.gedcom_loader.updatestats()


# Standalone wrapper functions for backwards compatibility with command-line interface
def Geoheatmap(svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> bool:
    """Generate geocoded HTML heatmap (CLI wrapper).
    
    Directly uses specialized modules for efficiency.
    
    Args:
        svc_config: Configuration service
        svc_state: Runtime state service
        svc_progress: Progress tracking service
    
    Returns:
        bool: True if successful
    """
    # Create minimal panel for module initialization
    class _MinimalCliPanel:
        pass
    panel = _MinimalCliPanel()
    loader = GedcomLoader(panel)
    map_gen = MapGenerator(panel)
    
    people = loader.ParseAndGPS(svc_config, svc_state, svc_progress, stage=1)
    if not people:
        _log.error("Geoheatmap: ParseAndGPS returned no people")
        return False
    return map_gen.doHTML(svc_config, svc_state, svc_progress, True)


def gedcom_to_map(svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> None:
    """Parse GEDCOM and generate KML (CLI wrapper).
    
    Directly uses specialized modules for efficiency.
    
    Args:
        svc_config: Configuration service
        svc_state: Runtime state service
        svc_progress: Progress tracking service
    """
    # Create minimal panel for module initialization
    class _MinimalCliPanel:
        pass
    panel = _MinimalCliPanel()
    loader = GedcomLoader(panel)
    map_gen = MapGenerator(panel)
    
    people = loader.ParseAndGPS(svc_config, svc_state, svc_progress, stage=1)
    if not people:
        _log.error("gedcom_to_map: ParseAndGPS returned no people")
        return
    map_gen.doKML(svc_config, svc_state, svc_progress)
