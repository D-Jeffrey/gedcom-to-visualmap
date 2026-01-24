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
from gedcom_options import gvOptions, ResultType

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
            panel: Parent VisualMapPanel instance providing access to gOp
        """
        self.panel: Any = panel
    
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
            generator = MapGenerator(panel)
            success = generator.doHTML(gOp, people_dict, fullresult=True)
            if success:
                print("Map generated and opened in browser")
        """
        if (not people):
            _log.error("doHTML: no people provided")
            return False
        
        _log.debug("Creating Lifeline (fullresult:%s)", fullresult)
        lifeline: LifetimeCreator = LifetimeCreator(people, gOp.MaxMissing)    
        _log.debug("Creating People ")
        creator: list = lifeline.create(gOp.Main)    
        
        if gOp.Main not in people:
            _log.error("Could not find your starting person: %s", gOp.Main)
            try:
                gOp.stopstep('Error could not find first person')
            except Exception:
                pass
            return False
        
        gOp.setMainPerson(people[gOp.Main])
        if gOp.AllEntities:
            gOp.step('Creating life line for everyone')
            lifeline.createothers(creator)
            _log.info("Total of %i people & events.", len(creator))   
        gOp.totalpeople = len(creator)

        try:
            foliumExporter(gOp).export(people[gOp.Main], creator, fullresult)
        except Exception:
            _log.exception("doHTML: folium export failed")
            return False
        
        # Verify file was created
        if fullresult:
            result_path: Path = Path(gOp.resultpath) / gOp.ResultFile
            if not result_path.exists():
                _log.error("Result file not found: %s", result_path)
                return False
        return True
    
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
            generator = MapGenerator(panel)
            generator.doKML(gOp, people_dict)
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
            generator = MapGenerator(panel)
            generator.doKML2(gOp, people)
        """
        if (not gOp.lookup):
            _log.error("doKML2: GeolocatedGedcom is not processed")
            return
        resultFile: str = os.path.join(gOp.resultpath, gOp.ResultFile)

        try:
            kml_life_lines: KML_Life_Lines = KML_Life_Lines(
                gedcom=gOp.lookup,
                kml_file=str(resultFile),
                connect_parents=True,
                save=True
            )
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
        else:
            _log.error("No KML output created")
            if bg:
                try:
                    bg.SayInfoMessage(f"No KML output created - No data selected to map")
                except Exception:
                    pass
