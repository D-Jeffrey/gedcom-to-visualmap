from render.result_type import ResultType

"""
Map visualization generation (HTML/KML formats).

This module handles generation of interactive maps and KML files from geocoded GEDCOM data.
Extracted from visual_map_actions.py for better separation of concerns.
"""
import logging
import os
from pathlib import Path
from typing import Any, Optional, Dict, List

from models.creator import Creator, LifetimeCreator, Person
from render.folium.folium_exporter import foliumExporter
from render.kml1.kml_exporter import KmlExporter
from render.kml2 import KML_Life_Lines
from services.progress_service import GVProgress
from services.interfaces import IConfig, IState, IProgressTracker

_log = logging.getLogger(__name__.lower())


class MapGenerator:
    """Handles generation of HTML and KML map visualizations.

    Responsibilities:
    - Generate interactive HTML maps using Folium
    - Generate KML files for Google Earth (two implementations)
    - Handle browser/viewer opening

    Attributes:
        panel: Reference to parent VisualMapPanel for UI updates
    """

    def __init__(self, panel: Any) -> None:
        """Initialize map generator.

        Args:
            panel: Parent VisualMapPanel instance providing access to services
        """
        self.panel: Any = panel

    def doHTML(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker, fullresult: bool) -> bool:
        """Generate interactive HTML map using Folium library.

        Creates lifetime lines for selected people (starting from Main) and
        exports to interactive HTML map with Folium. Optionally includes all people
        in dataset if AllEntities is True.

        Process:
        1. Create LifetimeCreator with people data
        2. Generate lifetime lines starting from main person
        3. Optionally add all other people
        4. Export to HTML using foliumExporter
        5. Optionally open in browser if fullresult=True

        Args:
            svc_config: Configuration service
            svc_state: Runtime state service (provides people via svc_state.people)
            svc_progress: Progress tracking service
            fullresult: If True, opens generated HTML in browser after creation.

        Returns:
            bool: True if HTML generation succeeded, False if errors occurred.

        Side Effects:
            - Sets svc_state.main_person to starting Person object
            - Creates HTML file at config.result_file
            - Opens browser if fullresult=True

        Raises:
            Logs error and returns False if:
            - No people in state
            - Starting person not found in people dict
            - Folium export fails
            - Result file not found after generation

        Example:
            generator = MapGenerator(panel)
            success = generator.doHTML(svc_config, svc_state, svc_progress, fullresult=True)
            if success:
                print("Map generated and opened in browser")
        """
        people = svc_state.people
        if not people:
            _log.error("doHTML: no people provided")
            return False

        main_id = svc_config.get("Main")
        max_missing = svc_config.get("MaxMissing", 0)
        all_entities = svc_config.get("AllEntities", False)

        svc_progress.step("Creating HTML map - initializing")
        _log.debug("Creating Lifeline (fullresult:%s)", fullresult)
        lifeline: LifetimeCreator = LifetimeCreator(people, max_missing)
        svc_progress.step("Generating lifetime lines")
        _log.debug("Creating People ")
        creator: list = lifeline.create(main_id)

        if main_id not in people:
            _log.error("Could not find your starting person: %s", main_id)
            try:
                if svc_progress is None:
                    svc_progress = GVProgress()
                svc_progress.stopstep("Error could not find first person")
            except Exception:
                pass
            return False

        svc_state.main_person = people[main_id]
        if all_entities:
            svc_progress.step("Creating life line for everyone")
            lifeline.createothers(creator)
            _log.info("Total of %i people & events.", len(creator))
        svc_state.totalpeople = len(creator)

        svc_progress.step("Initializing map renderer")
        try:
            foliumExporter(svc_config, svc_state, svc_progress).export(people[main_id], creator, saveresult=True)
        except Exception:
            _log.exception("doHTML: folium export failed")
            return False

        # Verify file was created
        if fullresult:
            result_path_str = svc_config.get("resultpath", "")
            result_file = svc_config.get("ResultFile", "")
            if result_path_str and result_file:
                result_path: Path = Path(result_path_str) / result_file
            else:
                result_path: Path = Path(result_file) if result_file else Path()
            if not result_path.exists():
                _log.error("Result file not found: %s", result_path)
                return False
        return True

    def doKML(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> None:
        """Generate KML output for visualization in Google Earth.

        Creates KML file with placemarks for birth and/or death locations based on
        BornMark and DieMark settings. Generates separate layers for each
        marker type. Optionally includes all people if AllEntities is True.

        Process:
        1. Check which marker types are enabled (birth/death)
        2. For each enabled marker type:
           - Create Creator to generate location data
           - Export to KML layer via KmlExporter
        3. Finalize KML file
        4. Open in configured KML viewer

        Args:
            svc_config: Configuration service
            svc_state: Runtime state service (provides people via svc_state.people)
            svc_progress: Progress tracking service

        Side Effects:
            - Creates KML file at config.result_file
            - Shows info/error messages via background process
            - Opens KML file if command is configured

        Raises:
            Logs error if:
            - Neither birth nor death markers enabled
            - Starting person not found
            - KML export fails
            - Configured KML command cannot be executed

        Example:
            svc_config.set('BornMark', True)
            svc_config.set('DieMark', True)
            generator = MapGenerator(panel)
            generator.doKML(svc_config, svc_state, svc_progress)
        """
        people = svc_state.people
        if not people:
            return
        kml_instance: Optional[KmlExporter] = None

        placeTypes: List[List[str]] = []
        if svc_config.get("BornMark", False):
            placeTypes.append(["birth", "(b)", "birth"])
        if svc_config.get("DieMark", False):
            placeTypes.append(["death", "(d)", "death"])

        if not placeTypes:
            try:
                svc_progress.stopstep("Error select at least Birth or Death markers to map")
            except Exception:
                pass
            _log.error("Neither birth or death marker is selected")
            return

        main_id = svc_config.get("Main")
        max_missing = svc_config.get("MaxMissing", 0)
        all_entities = svc_config.get("AllEntities", False)

        for key, nametag, placeType in placeTypes:
            lifeline: Creator = Creator(people, max_missing, gpstype=key)
            creator: list = lifeline.create(main_id)
            if all_entities:
                lifeline.createothers(creator)
                _log.info("Total of %i people.", len(creator))

            if main_id not in people:
                _log.error("Could not find your starting person: %s", main_id)
                try:
                    svc_progress.stopstep("Error could not find first person")
                except Exception:
                    pass
                return

            try:
                svc_state.main_person = people[main_id]
            except Exception:
                pass

            if not kml_instance:
                kml_instance = KmlExporter(svc_config, svc_state, svc_progress)

            try:
                kml_instance.export(people[main_id].latlon, creator, nametag, placeType)
            except Exception:
                _log.exception("doKML: export failed for %s", nametag)

        bg = self.panel.background_process if hasattr(self.panel, "background_process") else None
        if kml_instance:
            try:
                kml_instance.Done()
            except Exception:
                _log.debug("doKML: KmlExporter.Done failed")
            resultFile: str = str(svc_config.get("ResultFile", "")) if svc_config.get("ResultFile") else ""
            if bg:
                bg.SayInfoMessage(f"KML output to : {resultFile}")
        else:
            _log.error("No KML output created")
            if bg:
                bg.SayInfoMessage("No KML output created - No data selected to map")

    def doKML2(self, svc_config: IConfig, svc_state: IState) -> None:
        """Generate KML output using alternate/legacy KML exporter.

        Creates KML file using KML_Life_Lines exporter (alternate implementation
        from render.kml module). This version creates life line connections between
        birth/death locations and includes parent connections.

        Args:
            svc_config: Configuration service
            svc_state: Runtime state service (provides lookup via svc_state.lookup)

        Side Effects:
            - Creates KML file at config.result_file
            - Shows info/error messages via background process
            - Opens KML file if command is configured

        Raises:
            Logs error if:
            - lookup not available (GEDCOM not geocoded)
            - KML_Life_Lines creation/export fails
            - Configured KML command cannot be executed

        Note:
            Requires prior call to ParseAndGPS() to populate state.lookup.

        Example:
            generator = MapGenerator(panel)
            generator.doKML2(svc_config, svc_state)
        """
        if not svc_state.lookup:
            _log.error("doKML2: GeolocatedGedcom is not processed")
            return
        result_path_str = svc_config.get("resultpath", "")
        result_file = svc_config.get("ResultFile", "")
        if result_path_str and result_file:
            resultFile: str = str(Path(result_path_str) / result_file)
        else:
            resultFile: str = str(result_file) if result_file else ""

        try:
            kml_life_lines: KML_Life_Lines = KML_Life_Lines(
                gedcom=svc_state.lookup, kml_file=resultFile, connect_parents=True, save=True
            )
        except Exception:
            _log.exception("doKML2: KML_Life_Lines creation/export failed")
            bg = self.panel.background_process if hasattr(self.panel, "background_process") else None
            if bg:
                try:
                    bg.SayInfoMessage("KML(2) generation failed")
                except Exception:
                    pass
            return

        bg = self.panel.background_process if hasattr(self.panel, "background_process") else None
        if kml_life_lines:
            if bg:
                try:
                    bg.SayInfoMessage(f"KML(2) output to : {resultFile}")
                except Exception:
                    pass
        else:
            _log.error("No KML output created")
            if bg:
                try:
                    bg.SayInfoMessage(f"No KML output created - No data selected to map")
                except Exception:
                    pass
