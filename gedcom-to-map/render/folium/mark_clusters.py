"""
Marker cluster management for Folium maps.
"""
import folium
from folium.plugins import MarkerCluster
from geo_gedcom.lat_lon import LatLon


class MyMarkClusters:
    """
    Manages marker clusters for a Folium map.

    Attributes:
        mymap (folium.Map): The Folium map instance.
        step (int): The time step for clustering.
    """
    def __init__(self, mymap: folium.Map, step: int) -> None:
        """
        Initialize the marker cluster manager.
        Args:
            mymap (folium.Map): The Folium map instance.
            step (int): The time step for clustering.
        """
        self.pmarker: dict = dict()
        self.cmarker: dict = dict()
        self.markercluster: dict = dict()
        self.mymap: folium.Map = mymap
        self.step: int = step

    def mark(self, spot: LatLon, when: int | None = None) -> None:
        """
        Add a marker to the cluster for a given spot and optional time.
        Args:
            spot (LatLon): The location to mark.
            when (int, optional): The time value for clustering.
        """
        if spot and spot.hasLocation():
            cnt = 1
            if when is not None:
                when = int(when) - (int(when) % self.step)
                markname = f"{spot.lat}{spot.lon}{when}"
            else:
                markname = f"{spot.lat},{spot.lon}"
            if markname in self.pmarker:
                cnt = self.pmarker[markname][2] + 1
            self.pmarker[markname] = (spot.lat, spot.lon, cnt, when)

    def checkmarker(self, lat: float, long: float, name: str) -> MarkerCluster | None:
        """
        Check or create a marker cluster for the given coordinates.
        Args:
            lat (float): Latitude.
            long (float): Longitude.
            name (str): Name for the marker cluster.
        Returns:
            MarkerCluster or None: The marker cluster instance or None if not created.
        """
        if lat is not None and long is not None:
            markname = f"{lat},{long}"
            if self.cmarker.get(markname) == 1:
                return None
            if markname in self.markercluster:
                return self.markercluster[markname]
            else:
                self.markercluster[markname] = MarkerCluster(name).add_to(self.mymap)
                return self.markercluster[markname]
