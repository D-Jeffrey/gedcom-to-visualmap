"""
Summary report generation for genealogical data analysis.

This module handles creation of various CSV and statistics reports from geocoded GEDCOM data.
Extracted from visual_map_actions.py for better separation of concerns.
"""
import logging
from pathlib import Path
from typing import Any, Optional

from geo_gedcom.geolocated_gedcom import GeolocatedGedcom
from render.summary import SummaryReportConfig, generate_summary_reports
from gedcom_options import gvOptions

_log = logging.getLogger(__name__.lower())


class ReportGenerator:
    """Handles generation of summary reports and statistics from GEDCOM data.
    
    Responsibilities:
    - Generate CSV reports (places, people, countries, geocache, alt places)
    - Generate statistics summaries
    - Handle file opening after generation
    
    Attributes:
        panel: Reference to parent VisualMapPanel for accessing configuration
        actions: Reference to parent VisualMapActions for file operations
    """
    
    def __init__(self, panel: Any, actions: Optional[Any] = None) -> None:
        """Initialize report generator.
        
        Args:
            panel: Parent VisualMapPanel instance providing access to gOp
            actions: Parent VisualMapActions instance for LoadFile method (optional)
        """
        self.panel: Any = panel
        self.actions: Optional[Any] = actions
    
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
            generator = ReportGenerator(panel)
            generator.doSUM(gOp)
        
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
        # Pass actions (parent VisualMapActions) for LoadFile capability
        generate_summary_reports(config, my_gedcom, base_file_name, output_folder, bg, file_loader=self.actions)
