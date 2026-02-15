"""
kml.py - KML exporter for geolocated GEDCOM data.

Exports genealogical events and relationships to KML for visualization in Google Earth.

Author: @colin0brass
"""

from typing import Optional
import logging

from geo_gedcom.geolocated_gedcom import GeolocatedGedcom
from .kml_life_lines_creator import KML_Life_Lines_Creator
from .kml_exporter_refined import KmlExporterRefined
from services.interfaces import IProgressTracker

logger = logging.getLogger(__name__)

from .kml_exporter_refined import BIRTH_ICON, MARRIAGE_ICON, DEATH_ICON

__all__ = ["KmlExporterRefined", "KML_Life_Lines_Creator", "KML_Life_Lines"]


class KML_Life_Lines:
    """
    High-level wrapper for creating and saving KML life lines for a GEDCOM dataset.

    This class uses KML_Life_Lines_Creator to add people, connect parents, set camera view,
    and save the resulting KML file. It is intended to simplify the workflow for exporting
    genealogical relationships to KML for visualization.

    Attributes:
        gedcom (GeolocatedGedcom): Geolocated GEDCOM data.
        kml_file (str): Path to output KML file.
        kml_life_lines_creator (KML_Life_Lines_Creator): Instance of the KML life lines creator.
    """

    __slots__ = ["gedcom", "kml_file", "kml_life_lines_creator"]

    def __init__(
        self,
        gedcom: GeolocatedGedcom,
        kml_file: str,
        connect_parents: bool = True,
        save: bool = True,
        svc_progress: Optional[IProgressTracker] = None,
    ):
        """
        Initialize the KML_Life_Lines wrapper.

        This sets up the KML life lines creator, adds people, optionally connects parents,
        sets the camera view to the main person, and optionally saves the KML file.

        Args:
            gedcom (GeolocatedGedcom): Geolocated GEDCOM data.
            kml_file (str): Path to output KML file.
            connect_parents (bool, optional): Whether to draw parent-child lines. Defaults to True.
            save (bool, optional): Whether to save the KML file immediately. Defaults to True.
            svc_progress (Optional[IProgressTracker], optional): Progress tracker for GUI updates. Defaults to None.
        """

        self.kml_life_lines_creator = KML_Life_Lines_Creator(
            gedcom=gedcom, kml_file=kml_file, svc_progress=svc_progress
        )
        self.kml_life_lines_creator.add_people()

        if connect_parents:
            self.kml_life_lines_creator.connect_parents()

        if save:
            self.kml_life_lines_creator.save_kml()

    def save(self) -> None:
        """
        Save the KML file to disk.

        This method calls the underlying KML_Life_Lines_Creator's save_kml method.
        """
        self.kml_life_lines_creator.save_kml()
