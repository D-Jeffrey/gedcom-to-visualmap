"""
Folium-based exporter for genealogical data visualization.
"""
__all__ = ['MyMarkClusters', 'foliumExporter']


import logging
import math
import os.path

import random

import folium
import xyzservices.providers as xyz
from folium.plugins import (AntPath, FloatImage, GroupedLayerControl,
                            HeatMapWithTime, MiniMap, Search, MarkerCluster)
from services import IConfig, IState, IProgressTracker
from models.line import Line
from geo_gedcom.lat_lon import LatLon
from render.referenced import Referenced
from models.creator import DELTA
from .legend import Legend
from .mark_clusters import MyMarkClusters
from .name_processor import NameProcessor
# Import constants and utilities
from .constants import lgd_txt, MidPointMarker, icon_create_function
from .marker_utils import Drift, add_point_marker
from .polyline_utils import add_polyline
from .heatmap_utils import normalize_heat_data

_log = logging.getLogger(__name__.lower())
legend_file = 'file://' + __file__ + '/../legend.png'

class foliumExporter:
    """
    Exports genealogical data to an interactive Folium map.

    Attributes:
        file_name (str): Output HTML file path.
        max_line_weight (int): Maximum line weight for polylines.
        svc_config (IConfig): Configuration service.
        svc_state (IState): Runtime state service.
        svc_progress (IProgressTracker): Progress tracking service.
        fglastname (dict): Feature groups by last name.
        saveresult (bool): Whether to save the result.
        fm (folium.Map): The Folium map instance.
        locations (list): List of marker locations.
        popups (list): List of popup contents.
        soundexLast (bool): Whether to use Soundex for grouping.
    """
    def __init__(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker):
        """
        Initialize the Folium exporter.

        Args:
            svc_config: Configuration service
            svc_state: Runtime state service
            svc_progress: Progress tracking service
        """
        self.svc_config = svc_config
        self.svc_state = svc_state
        self.svc_progress = svc_progress
        self.file_name = os.path.join(svc_config.get('resultpath'), svc_config.get('ResultFile'))
        self.max_line_weight = svc_config.get('MaxLineWeight')
        self.fglastname = dict()
        self.saveresult = False
        self.fm = None
        self.locations = []
        self.popups = []
        self.soundexLast = svc_config.get('GroupBy') == 2
        
    def _create_marker_options(self, line) -> dict:
        """Generate marker and line options based on line style"""
        if line.style == 'Life':
            return {
                'start_color': 'orange',
                'start_icon': 'child',
                'end_color': 'gray',
                'end_icon': 'cross',
                'line_color': '#' + line.color.to_RGBhex(),
                'dash_array': [],
                'feature_group': None
            }
        # Default relation options
        options = {
            'start_color': 'green',
            'start_icon': 'baby-carriage',
            'end_color': 'green',
            'end_icon': None,
            'line_color': 'green',
            'dash_array': [5,5],
            'feature_group': None
        }
        # Customize for parent relationships
        if line.style == 'father':
            options.update({
                'line_color': '#2b8cbe',
                'end_icon': 'male',
                'end_color': 'blue'
            })
        elif line.style == 'mother':
            options.update({
                'line_color': 'pink',
                'end_icon': 'female',
                'end_color': 'pink'
            })
        return options
    def _pureName (self, name: str) -> str:
        """Clean up name for display remove the lineage before the tab if any"""
        if not name:
            return ''
        if '\t' in name:
            name = name.split('\t')[1]
        return name
    
    def _create_popup_content(self, line, birth_info: str = '', death_info: str = '') -> str:
        """Generate popup content for markers"""
        if line.style == 'Life':
            fancy_name = f"{line.style} of {self._pureName(line.name)}"
        else:
            parent_name = line.parentofperson.name if line.parentofperson else ''
            fancy_name = f"{self._pureName(line.name)} {line.style} of {parent_name}"

        if birth_info or death_info:
            fancy_name = f"{fancy_name}<br>{birth_info} {death_info}"

        popup = f"<div style='min-width: 150px'>{fancy_name}</div>"
        if line.person.photo:
            popup += f"<img src='{line.person.photo}' width='150'>"
        return popup

    # Marker utility now in marker_utils.py
    def _add_point_marker(self, fg, point, options, tooltip, popup, icon_name, color):
        add_point_marker(fg, point, options, tooltip, popup, icon_name, color, gOp=self.svc_config)
    
    def setoptions(self):

        return

    def Done(self):
        """Finalize and save the map."""
        if self.saveresult:
            self.svc_progress.step("Writing Folium HTML")
            self.fm.save(self.file_name)
            self.svc_progress.step("Done")
        # self.fm = None
    
    def getFeatureGroup(self, thename, depth):
        """Retrieve or create a feature group.
        array of values
        Index is a simplifyLastName
            [0] FeatureGroup
            [1] count of instances
            [2] depth
            [3] orginal name
        """
        # TODO could offer an option on which name folding to use (Maybe use SoundEx)
        if self.soundexLast:
            simpleLastName = NameProcessor.soundex(thename)
        else:
            simpleLastName = NameProcessor.simplifyLastName(thename)
        if not simpleLastName in self.fglastname:
            self.fglastname[simpleLastName] = [folium.FeatureGroup(name= thename, show=False), 0, 0, thename]
                             
        thefg = self.fglastname[simpleLastName][0]
        self.fglastname[simpleLastName][1] += 1
        self.fglastname[simpleLastName][2] = depth
        return thefg

    def _process_timeline_data(self, line: Line, mycluster: MyMarkClusters) -> tuple[int, int]:
        """Process timeline data for a single line and return min/max years"""
        minyear = maxyear = None
        
        # Add birth location if available
        birth_event = line.person.get_event('birth') if line.person else None
        birth_latlon = birth_event.getattr('latlon') if birth_event else None
        birth_date = birth_event.getattr('date') if birth_event else None
        birth_year_num = birth_date.year_num if birth_date else None

        if birth_event and birth_latlon and birth_date:
            mycluster.mark(birth_latlon, birth_year_num)
            minyear = birth_year_num
        
        # Add death year if available
        death_event = line.person.get_event('death') if line.person else None
        death_date = death_event.getattr('date') if death_event else None
        death_year_num = death_date.year_num if death_date else None
        if death_event and death_date:
            maxyear = death_year_num
        else:
            # Process midpoints for min/max year determination
            for mids in line.midpoints:
                start_year = mids.date.year_num
                if start_year:
                    minyear = min(int(start_year), minyear) if minyear else int(start_year)
                end_year = mids.date.year_num
                if end_year:
                    maxyear = max(int(end_year), maxyear) if maxyear else int(end_year)
        
        return minyear, maxyear

    def _build_yearly_positions(self, line: Line, minyear: int, maxyear: int, mycluster: MyMarkClusters) -> None:
        """Build position data for each year in the timeline"""
        if not (minyear and maxyear):
            return
        
        birth_event = line.person.get_event('birth') if line.person else None
        birth_latlon = birth_event.getattr('latlon') if birth_event else None
        activepos = birth_latlon
            
        for year in range(minyear, maxyear):
            # Update active position if we have a midpoint for this year
            for mids in line.midpoints:
                if mids.date.year_num == year:
                    activepos = mids.latlon
            if activepos and activepos.lat and activepos.lon:
                mycluster.mark(activepos, year)

    # Heatmap normalization utility now in heatmap_utils.py
    def _normalize_heat_data(self, heat_data: list) -> None:
        normalize_heat_data(heat_data)

    def _create_timeline_heatmap(self, lines: list[Line], mycluster: MyMarkClusters, fm: folium.Map) -> None:
        """Create a timeline-based heatmap visualization"""
        _log.info("Building timeline heatmap clusters")
        
        # Process life events for each line
        for line in lines:
            if self.svc_progress.step():
                break
                
            if not (getattr(line, 'style', None) == 'Life'):
                continue

            person = line.person    
            self.svc_state.Referenced.add(person.xref_id, 'heat')
            minyear, maxyear = self._process_timeline_data(line, mycluster)
            self._build_yearly_positions(line, minyear, maxyear, mycluster)
            
            # Add death location if available
            death_event = person.get_event('death') if person else None
            death_latlon = death_event.getattr('latlon') if death_event else None
            death_year_num = death_event.getattr('when_year_num') if death_event else None
            if death_latlon:
                mycluster.mark(death_latlon, death_year_num)

        # Extract unique years from markers
        years = sorted(set(
            year for marker in mycluster.pmarker 
            if isinstance(mycluster.pmarker[marker][3], (int, float))
            for year in [mycluster.pmarker[marker][3]]
        ))
        
        # Build heat data array
        heat_data = [
            [
                [mycluster.pmarker[markname][0], 
                 mycluster.pmarker[markname][1], 
                 mycluster.pmarker[markname][2]]
                for markname in mycluster.pmarker
                if years[year_idx] == mycluster.pmarker[markname][3]
            ]
            for year_idx in range(len(years))
        ]
        
        self._normalize_heat_data(heat_data)
        
        # Create and add heatmap
        hm = folium.plugins.HeatMapWithTime(
            heat_data,
            index=years,
            name='Heatmap',
            max_opacity=0.9,
            min_speed=1,
            speed_step=1,
            max_speed=25,
            gradient={
                '0': 'Navy',
                '0.25': 'Blue',
                '0.5': 'Green',
                '0.75': 'Yellow',
                '1': 'Red'
            }
        )
        fm.add_child(hm)

    def _create_static_heatmap(self, lines: list[Line], mycluster: MyMarkClusters, fm: folium.Map) -> None:
        """Create a static heatmap visualization"""
        # Mark all locations
        for line in lines:
            self.svc_progress.step()
            mycluster.mark(line.fromlocation)
            mycluster.mark(line.tolocation)
            if line.midpoints:
                for mids in line.midpoints:
                    event_latlon = mids.getattr('latlon') if mids else None
                    mycluster.mark(event_latlon, None)

        # Create feature group and heat data
        fg = folium.FeatureGroup(
            name=lgd_txt.format(txt= 'Heatmap', col='black'),
            show=self.svc_config.get('HeatMap')
        )
        
        heat_data = [
            [marker[0], marker[1], marker[2]]
            for markname, marker in mycluster.pmarker.items()
        ]
        
        # Add heatmap to feature group
        hm = folium.plugins.HeatMap(
            heat_data,
            max_opacity=0.8,
            name='Heatmap'
        )
        fg.add_child(hm)
        fm.add_child(fg)

    # In the export method, replace the heatmap section with:
    def export(self, main: LatLon, lines: list[Line], saveresult=True):
        """
        Export genealogical data to an interactive Folium map.
        Partitioned for clarity and maintainability.
        """
        people = self.svc_state.people
        if not people:
            _log.warning("No people to plot on map.")
            return

        main_person = self.svc_state.mainPerson if self.svc_state.mainPerson else None
        main_person_latlon = getattr(main_person, 'latlon', None) if main_person else None

        if not self.fm:
            self._init_map(main_person_latlon, lines, saveresult)
            if not saveresult:
                return

        SortByLast = (self.svc_config.get('GroupBy') == 1 or self.svc_config.get('GroupBy') == 2)
        SortByPerson = (self.svc_config.get('GroupBy') == 3)
        fm = self.fm
        self.saveresult = saveresult

        self.svc_progress.step("Preparing")
        self.fglastname = dict()

        flr = folium.FeatureGroup(name=lgd_txt.format(txt='Relations', col='green'), show=False)
        flp = folium.FeatureGroup(name=lgd_txt.format(txt='People', col='Black'), show=False)
        mycluster = MyMarkClusters(fm, self.svc_config.get('HeatMapTimeStep'))

        self._add_heatmap(lines, mycluster, fm)
        self._add_fontawesome_hack(fm)
        self._draw_lines(lines, SortByLast, SortByPerson, fm)
        self._add_feature_groups_to_map(fm)
        self._add_marker_cluster(fm)
        self._add_main_star(main, fm)
        self._add_legend(fm)
        if SortByLast:
            _log.info("Number of FG lastName: %i", len(self.fglastname))
        self.Done()
        return

    def _init_map(self, main_person_latlon, lines, saveresult):
        try:
            tile = xyz.query_name(self.svc_config.get('MapStyle'))
        except Exception:
            tile = xyz.CartoDB

        main_person = self.svc_state.mainPerson if self.svc_state.mainPerson else None
        birth_event = main_person.get_event('birth') if main_person else None
        death_event = main_person.get_event('death') if main_person else None
        birth_latlon = birth_event.getattr('latlon') if birth_event else None
        death_latlon = death_event.getattr('latlon') if death_event else None

        if death_latlon or birth_latlon:
            self.fm = folium.Map(location=[0, 0], zoom_start=4, tiles=tile)
        else:
            self.fm = folium.Map(location=main_person_latlon, zoom_start=4, tiles=tile)
        if self.svc_config.get('mapMini'):
            folium.plugins.MiniMap(toggle_display=True).add_to(self.fm)

        random.seed()
        self.svc_state.Referenced = Referenced()
        _log.debug("Building Referenced - quick only: %s", not saveresult)
        for line in lines:
            if getattr(line, 'style', None) == 'Life':
                self.svc_state.Referenced.add(line.person.xref_id, 'quick')
        self.svc_state.lastlines = {line.person.xref_id: line for line in lines}

    def _add_heatmap(self, lines, mycluster, fm):
        if self.svc_config.get('MapTimeLine'):
            self._create_timeline_heatmap(lines, mycluster, fm)
        else:
            self._create_static_heatmap(lines, mycluster, fm)

    def _add_fontawesome_hack(self, fm):
        # My to use the jquery hack to MAGIC HACK fix the Folium code to use Font Awesome!
        # missing tag a the end on purpose
        fm.default_js.append([
            'hack.js',
            'https://use.fontawesome.com/releases/v6.5.1/js/all.js" data-auto-replace-svg="nest'
        ])

    def _draw_lines(self, lines, SortByLast, SortByPerson, fm):
        i = 0
        self.svc_progress.step("Building lines")
        lines_sorted = lines if SortByLast else sorted(
            lines,
            key=lambda x: x.prof * ((x.branch/DELTA)+1) + x.prof
        )
        styled_lines = [line for line in lines_sorted if hasattr(line, 'style')]
        for line in styled_lines:
            _log.info(f"{line.prof * ((line.branch/DELTA)+1)+ line.prof:8f} {line.path:8} "
                     f"{line.branch:.8f} {line.prof:2} "
                     f"{line.parentofperson.name if line.parentofperson else '':20} from {line.name:20}")
        for line in styled_lines:
            self.svc_progress.step()
            i += 1
            self._draw_single_line(line, SortByLast, SortByPerson, fm)

    def _draw_single_line(
        self,
        line: Line,
        SortByLast: bool,
        SortByPerson: bool,
        fm: folium.Map
    ) -> None:
        """
        Draw a single genealogical line on the Folium map, including markers and polylines.
        Args:
            line (Line): The line object representing a person or relationship.
            SortByLast (bool): Whether to group by last name.
            SortByPerson (bool): Whether to group by person.
            fm (folium.Map): The Folium map instance.
        """
        marker_options = self._create_marker_options(line)
        label_name = line.name[:25] + "..." if len(line.name) > 25 else line.name
        group_name = lgd_txt.format(txt=label_name, col=marker_options['line_color'])
        person = line.person
        birth_event = person.get_event('birth') if person else None
        death_event = person.get_event('death') if person else None
        birth_year_num = birth_event.date.year_num if birth_event and birth_event.date else None
        death_year_num = death_event.date.year_num if death_event and death_event.date else None
        birth_info = f"{birth_year_num} (Born)" if birth_year_num else ''
        death_info = f"{death_year_num} (Died)" if death_year_num else ''
        popup_content = self._create_popup_content(line, birth_info, death_info)

        fg, new_fg = self._get_feature_group_for_line(line, SortByLast, SortByPerson, group_name)
        start_point = self._add_start_marker(line, fg, marker_options, popup_content)
        end_point = self._add_end_marker(line, fg, marker_options, popup_content)
        fm_line = self._add_midpoint_markers(line, fg, marker_options, popup_content, start_point, end_point)
        self._add_polyline(line, fg, fm_line, marker_options, popup_content)
        self._finalize_feature_group(fg, new_fg, fm, fm_line, line)

    def _get_feature_group_for_line(
        self,
        line: Line,
        SortByLast: bool,
        SortByPerson: bool,
        group_name: str
    ) -> tuple[folium.FeatureGroup, bool]:
        """
        Select or create the appropriate feature group for a line.
        Args:
            line (Line): The line object.
            SortByLast (bool): Whether to group by last name.
            SortByPerson (bool): Whether to group by person.
            group_name (str): The display name for the group.
        Returns:
            tuple: (FeatureGroup, is_new_group)
        """
        fg = None
        new_fg = False
        if SortByLast:
            fg = self.getFeatureGroup(line.person.surname, line.prof)
        if SortByPerson:
            parent_name = line.parentofperson.name if line.parentofperson else line.person.name
            fg = self.getFeatureGroup(parent_name, line.prof)
        if not fg:
            fg = folium.FeatureGroup(name=group_name, show=True)
            new_fg = True
        return fg, new_fg

    def _add_start_marker(
        self,
        line: Line,
        fg: folium.FeatureGroup,
        marker_options: dict,
        popup_content: str
    ) -> list[float] | None:
        """
        Add the start marker for a line if available.
        Args:
            line (Line): The line object.
            fg (FeatureGroup): The feature group to add the marker to.
            marker_options (dict): Marker styling options.
            popup_content (str): Popup HTML content.
        Returns:
            list[float] | None: The start point coordinates, or None if not present.
        """
        if line.fromlocation and line.fromlocation.hasLocation():
            start_point = [Drift(line.fromlocation.lat), Drift(line.fromlocation.lon)]
            if self.svc_config.get('MarksOn') and self.svc_config.get('BornMark'):
                self._add_point_marker(
                    fg, start_point, marker_options,
                    f"Life of {line.name}".replace("`", "‛").replace("'", "‛"),
                    popup_content + "\nbirth", marker_options['start_icon'], marker_options['start_color']
                )
            return start_point
        return None

    def _add_end_marker(
        self,
        line: Line,
        fg: folium.FeatureGroup,
        marker_options: dict,
        popup_content: str
    ) -> list[float] | None:
        """
        Add the end marker for a line if available.
        Args:
            line (Line): The line object.
            fg (FeatureGroup): The feature group to add the marker to.
            marker_options (dict): Marker styling options.
            popup_content (str): Popup HTML content.
        Returns:
            list[float] | None: The end point coordinates, or None if not present.
        """
        if line.tolocation and line.tolocation.hasLocation():
            end_point = [Drift(line.tolocation.lat), Drift(line.tolocation.lon)]
            if self.svc_config.get('MarksOn') and self.svc_config.get('DieMark'):
                self._add_point_marker(
                    fg, end_point, marker_options,
                    f"Life of {line.name}".replace("`", "‛").replace("'", "‛"),
                    popup_content + "\ndeath", marker_options['end_icon'], marker_options['end_color']
                )
            return end_point
        return None

    def _add_midpoint_markers(
        self,
        line: Line,
        fg: folium.FeatureGroup,
        marker_options: dict,
        popup_content: str,
        start_point: list[float] | None,
        end_point: list[float] | None
    ) -> list[tuple[float, float]]:
        """
        Add midpoint markers for a line and build the polyline path.
        Args:
            line (Line): The line object.
            fg (FeatureGroup): The feature group to add markers to.
            marker_options (dict): Marker styling options.
            popup_content (str): Popup HTML content.
            start_point (list[float] | None): The start point coordinates.
            end_point (list[float] | None): The end point coordinates.
        Returns:
            list[tuple[float, float]]: The list of polyline path points.
        """
        fm_line: list[tuple[float, float]] = []
        if start_point:
            fm_line.append(tuple(start_point))
        if line.midpoints:
            for mids in line.midpoints:
                mid_point = [Drift(mids.location.latlon.lat), Drift(mids.location.latlon.lon)]
                fm_line.append(tuple(mid_point))
                if self.svc_config.get('HomeMarker') and self.svc_config.get('MarksOn'):
                    point_type = mids.what if mids.what in MidPointMarker else "Other"
                    marker = MidPointMarker[point_type][0]
                    color = MidPointMarker[point_type][1]
                    tooltip = mids.what + ' ' + mids.place.place if mids.what else '?? ' + mids.place.place
                    self._add_point_marker(fg, mid_point, marker_options, tooltip, popup_content, marker, color)
        if end_point:
            fm_line.append(tuple(end_point))
        return fm_line

    # Polyline utility now in polyline_utils.py
    def _add_polyline(self, line, fg, fm_line, marker_options, popup_content):
        add_polyline(line, fg, fm_line, marker_options, popup_content, self.max_line_weight, self.svc_config.get('UseAntPath'), self.svc_config)

    def _finalize_feature_group(
        self,
        fg: folium.FeatureGroup,
        new_fg: bool,
        fm: folium.Map,
        fm_line: list[tuple[float, float]],
        line: Line
    ) -> None:
        """
        Finalize and add the feature group to the map if it is new.
        Args:
            fg (FeatureGroup): The feature group.
            new_fg (bool): Whether this is a new group.
            fm (folium.Map): The Folium map instance.
            fm_line (list): The polyline path points.
            line (Line): The line object.
        """
        if new_fg:
            fg.layer_name = f"{fg.layer_name} ({len(fm_line) + 1 if line.tolocation else 0})"
            fm.add_child(fg)

    def _add_feature_groups_to_map(self, fm):
        for fgn in sorted(self.fglastname.keys(), key=lambda x: self.fglastname[x][2], reverse=False):
            self.fglastname[fgn][0].layer_name = f"{self.fglastname[fgn][3]} : {self.fglastname[fgn][1]}"
            fm.add_child(self.fglastname[fgn][0])

    def _add_marker_cluster(self, fm):
        sc = False if self.svc_config.get('showLayerControl') else True
        if self.locations:
            marker_cluster = MarkerCluster(
                locations=self.locations,
                popups=self.popups,
                name="-markers clustered-",
                overlay=True,
                control=True,
                icon_create_function=icon_create_function,
            )
            marker_cluster.add_to(fm)
        folium.map.LayerControl('topleft', collapsed=sc).add_to(fm)

    def _add_main_star(self, main, fm):
        birth_event = getattr(main, 'birth', None)
        birth_latlon = birth_event.getattr('latlon') if birth_event else None
        if main and birth_latlon:
            lat = birth_latlon.lat
            lon = birth_latlon.lon
            if not birth_latlon.isNone():
                folium.Marker(
                    [Drift(lat), Drift(lon)],
                    tooltip=main.name,
                    opacity=0.5,
                    icon=folium.Icon(color='lightred', icon='star', prefix='fa', iconSize=['50%', '50%'])
                ).add_to(fm)
        else:
            _log.warning("No GPS locations to generate a Star on the map.")

    def _add_legend(self, fm):
        if self.svc_config.get('MarksOn'):
            fm.add_child(Legend())



        """ 
           Display people using subgroup control to navigate   
            NOT USED YET                                        
        """

    #def peopleAsTreeNav(people):
    #    peoplegroup = folium.FeatureGroup("Chránené oblasti",control=False)
    #    # https://nbviewer.org/github/chansooligans/folium/blob/plugins-groupedlayercontrol/examples/plugin-GroupedLayerControl.ipynb
    #    fg1 = folium.FeatureGroup(name='g1', show=False)
    #    fg2 = folium.FeatureGroup(name='g2', show=False)
    #    fg3 = folium.FeatureGroup(name='g3')
    #    folium.Marker([40, 74]).add_to(fg1)
    #    folium.Marker([38, 72]).add_to(fg2)
    #    folium.Marker([40, 72]).add_to(fg3)
    #    m.add_child(fg1)
    #    m.add_child(fg2)
    #    m.add_child(fg3)

    #    folium.LayerControl(collapsed=False).add_to(m)

    #    GroupedLayerControl(
    #        groups={'groups1': [fg1, fg2]},
    #        exclusive_groups=False,
    #        collapsed=False,
    #    ).add_to(m)
        
    #    # https://github.com/python-visualization/folium/issues/1712
    #    # https://nbviewer.org/github/chansooligans/folium/blob/plugins-groupedlayercontrol/examples/plugin-GroupedLayerControl.ipynb

    #    return
