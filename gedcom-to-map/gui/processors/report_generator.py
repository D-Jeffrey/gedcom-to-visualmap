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
from services.interfaces import IConfig, IState, IProgressTracker
from services.state_service import GVState
from services.progress_service import GVProgress

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
            panel: Parent VisualMapPanel instance providing access to services
            actions: Parent VisualMapActions instance for LoadFile method (optional)
        """
        self.panel: Any = panel
        self.actions: Optional[Any] = actions

    def doSUM(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> None:
        """Generate various CSV summary reports from geocoded GEDCOM data.

        Creates multiple summary files based on settings:
        - Places summary: All unique places with geocoding info
        - People summary: All individuals with key dates/locations
        - Countries summary: Birth/death counts by country (CSV + optional chart)
        - Geocache summary: Geocoding cache for debugging
        - Alternative places: Alt place name mappings

        All outputs are saved to resultpath with filenames based on input
        GEDCOM filename. Optionally opens generated files if SummaryOpen is True.

        Args:
            svc_config: Configuration service
            svc_state: Runtime state service (provides lookup via svc_state.lookup)
            svc_progress: Progress tracking service

        Side Effects:
            - Creates CSV files in resultpath
            - May create PNG chart for countries summary
            - Shows info/error messages via background process
            - Opens files if SummaryOpen is True

        Raises:
            Logs error if:
            - svc_state.lookup not available (GEDCOM not geocoded)
            - Individual summary writer functions fail
            - File opening fails

        Example:
            svc_config.set('SummaryPlaces', True)
            svc_config.set('SummaryPeople', True)
            svc_config.set('SummaryOpen', True)
            generator = ReportGenerator(panel)
            if svc_progress is None:
                svc_progress = GVProgress()
            if svc_state is None:
                svc_state = GVState()
            generator.doSUM(svc_config, svc_state, svc_progress)

        Note:
            Requires prior call to ParseAndGPS() to populate svc_state.lookup.
        """
        base_file_name: str = Path(svc_config.get("GEDCOMinput", "")).resolve().stem
        output_folder: Path = Path(svc_config.get("resultpath", ".")).resolve()
        my_gedcom: Optional[GeolocatedGedcom] = svc_state.lookup
        bg = self.panel.background_process if hasattr(self.panel, "background_process") else None

        if my_gedcom is None:
            _log.error("doSUM: geolocated GEDCOM (svc_state.lookup) is not available")
            if bg:
                try:
                    bg.SayErrorMessage("doSUM: geocoded GEDCOM data not available")
                except Exception:
                    pass
            return

        # Extract summary report configuration from config service
        config = SummaryReportConfig(
            places=svc_config.get("SummaryPlaces", False),
            people=svc_config.get("SummaryPeople", False),
            countries=svc_config.get("SummaryCountries", False),
            countries_grid=svc_config.get("SummaryCountriesGrid", False),
            geocode=svc_config.get("SummaryGeocode", False),
            alt_places=svc_config.get("SummaryAltPlaces", False),
            enrichment_issues=svc_config.get("SummaryEnrichmentIssues", False),
            statistics=svc_config.get("SummaryStatistics", False),
            auto_open=svc_config.get("SummaryOpen", False),
        )

        # Generate all selected summary reports
        # Pass actions (parent VisualMapActions) for LoadFile capability
        generate_summary_reports(config, my_gedcom, base_file_name, output_folder, bg, file_loader=self.actions)
