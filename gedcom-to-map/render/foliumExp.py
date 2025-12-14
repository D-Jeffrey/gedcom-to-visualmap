__all__ = ['MyMarkClusters', 'foliumExporter']

import logging
import math
import os.path
import random
import json

from branca.element import MacroElement, Template
import folium
import xyzservices.providers as xyz

from folium.plugins import (AntPath, FloatImage, GroupedLayerControl,
                            HeatMapWithTime, MiniMap, Search, MarkerCluster) 
from gedcom_options import gvOptions
from models.line import Line
from geo_gedcom.lat_lon import LatLon
from .referenced import Referenced
from .name_processor import NameProcessor
from models.creator import DELTA


_log = logging.getLogger(__name__.lower())
# TODO need to create this Legend to explain things HACK
legend_file = 'file://' + __file__ + '/../legend.png'
lgd_txt = '<span style="color: {col};">{txt}</span>'



MidPointMarker = {
    'born' : ('baby', 'orange', False),
    'death' : ('cross', 'gray', False),
    'home' : ('home', 'lightred', False),
    'Marriage' : ('ring', 'orange', True),
    'IMMI' : ('ship', 'darkgreen', True),
    'CHR' : ('church', 'darkgreen', True),
    'BAPM' : ('church', 'darkgreen', True),
    'Deed' : ('landmark', 'darkgreen', True),
    'Arrival' : ('ship', 'darkgreen', True),
    'Other' : ('shoe-prints', 'lightgray', True)
}

legend_template = f"""
{{% macro html(this, kwargs) %}}
    <div id="map_legend" class="legend">
        <h4>Legend</h4>
        <!-- Dynamic generation of legend items -->
        {''.join([
            f'<div style="margin: 5px;">'
            f'<i class="fa fa-{icon}" style="color: {color};"></i> {key}</div>'
            for key, (icon, color, shown) in MidPointMarker.items()
        ])}
    </div>
    <style>
        /* Legend styling */
        .legend {{
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 5px rgba(0,0,0,0.5);
            font-size: 14px;
            line-height: 1.5;
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000; /* Ensure legend is above the map */
        }}
        .legend div {{
            display: flex;
            align-items: center;
        }}
        .legend i {{
            margin-right: 5px;
        }}
    </style>
{{% endmacro %}}
"""
# Use MacroElement to add the template to the map
class Legend(MacroElement):
    """A Folium MacroElement for displaying a map legend."""
    def __init__(self):
        """Initialize the legend with a predefined template."""
        super().__init__()
        self._template = Template(legend_template)

def Drift(l: float) -> float:
    """
    Apply a small random drift to a coordinate value to avoid marker overlap.

    Args:
        l (float): The original coordinate value.

    Returns:
        float: The drifted coordinate value.
    """
    d = ((random.random() * 0.001) - 0.0005)
    return float(l) + d if l is not None else None

# --------------------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------------------
icon_create_function = """\
function(cluster) {
    return L.divIcon({
    html: '<b>' + cluster.getChildCount() + '</b>',
    className: 'marker-cluster marker-cluster-large',
    iconSize: new L.Point(20, 20)
    });
}"""

class MyMarkClusters:
    """
    Manages marker clusters for a Folium map.

    Attributes:
        mymap (folium.Map): The Folium map instance.
        step (int): The time step for clustering.
    """
    def __init__(self, mymap: folium.Map, step: int):
        """
        Initialize the marker cluster manager.

        Args:
            mymap (folium.Map): The map to add clusters to.
            step (int): The time step for clustering.
        """
        self.pmarker = dict()
        self.cmarker = dict()
        self.markercluster = dict()
        self.mymap = mymap
        self.step = step

    def mark(self, spot: LatLon, when: int = None) -> None:
        """
        Add a marker to the cluster.

        Args:
            spot (LatLon): The location to mark.
            when (int, optional): The year or time for the marker.
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

    def checkmarker(self, lat: float, long: float, name: str):
        """
        Check or create a marker cluster for a given location.

        Args:
            lat (float): Latitude.
            long (float): Longitude.
            name (str): Name for the cluster.

        Returns:
            MarkerCluster or None: The marker cluster object.
        """
        if lat is not None and long is not None:
            markname = f"{lat},{long}"
            if self.cmarker.get(markname) == 1:
                return None
            if markname in self.markercluster:
                return self.markercluster[markname]
            else:
                self.markercluster[markname] = folium.plugins.MarkerCluster(name).add_to(self.mymap)
                return self.markercluster[markname]

class foliumExporter:
    """
    Exports genealogical data to an interactive Folium map.

    Attributes:
        file_name (str): Output HTML file path.
        max_line_weight (int): Maximum line weight for polylines.
        gOp (gvOptions): Options/configuration object.
        fglastname (dict): Feature groups by last name.
        saveresult (bool): Whether to save the result.
        fm (folium.Map): The Folium map instance.
        locations (list): List of marker locations.
        popups (list): List of popup contents.
        soundexLast (bool): Whether to use Soundex for grouping.
    """
    def __init__(self, gOp: gvOptions):
        """
        Initialize the Folium exporter.

        Args:
            gOp (gvOptions): The options/configuration object.
        """
        self.file_name = os.path.join(gOp.resultpath, gOp.ResultFile)
        self.max_line_weight = gOp.MaxLineWeight
        self.gOp = gOp
        self.fglastname = dict()
        self.saveresult = False
        self.fm = None
        self.locations = []
        self.popups = []
        self.soundexLast = gOp.GroupBy == 2
        
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
                'feature_group':  None  # flp
            }
        
        # Default relation options
        options = {
            'start_color': 'green',
            'start_icon': 'baby-carriage',
            'end_color': 'green', 
            'end_icon': None,
            'line_color': 'green',
            'dash_array': [5,5],
            'feature_group': None # flr
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

    def _add_point_marker(self, fg: folium.FeatureGroup, point: list, options: dict, 
                        tooltip: str, popup: str, icon_name: str, color: str) -> None:
        """Add a marker to the feature group"""
        if self.gOp.MarksOn:
            marker = folium.Marker(
                point,
                tooltip=tooltip,
                popup=popup,
                opacity=0.5,
                icon=folium.Icon(color=color, icon=icon_name, prefix='fa', extraClasses='fas')
            )
            fg.add_child(marker)
        else:
            self.locations.append(point)
            self.popups.append(popup)
    
    def setoptions(self):

        return

    def Done(self):
        """Finalize and save the map."""
        if self.saveresult:
            self.gOp.step("Writing Folium HTML")
            self.fm.save(self.file_name)
            self.gOp.step("Done")
        # self.gOp.stop()
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
        birth_event = line.person.birth if line.person else None
        birth_latlon = birth_event.getattr('latlon') if birth_event else None
        birth_date = birth_event.getattr('date') if birth_event else None
        birth_year_num = birth_date.year_num if birth_date else None

        if line.person.birth and birth_latlon and birth_date:
            mycluster.mark(birth_latlon, birth_year_num)
            minyear = birth_year_num
        
        # Add death year if available
        death_event = line.person.death if line.person else None
        death_date = death_event.getattr('date') if death_event else None
        death_year_num = death_date.year_num if death_date else None
        if line.person.death and death_date:
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
        
        birth_event = line.person.birth if line.person else None
        birth_latlon = birth_event.getattr('latlon') if birth_event else None
        activepos = birth_latlon
            
        for year in range(minyear, maxyear):
            # Update active position if we have a midpoint for this year
            for mids in line.midpoints:
                if mids.date.year_num == year:
                    activepos = mids.latlon
            if activepos and activepos.lat and activepos.lon:
                mycluster.mark(activepos, year)

    def _normalize_heat_data(self, heat_data: list) -> None:
        """Normalize heat data to range [0,1]"""
        if not heat_data:
            return
            
        # Find maximum value across all data points
        max_value = max(
            point[2] for year_data in heat_data 
            for point in year_data
        )
        
        # Normalize all values
        for year_data in heat_data:
            for point in year_data:
                point[2] = float(point[2])/max_value

    def _create_timeline_heatmap(self, lines: list[Line], mycluster: MyMarkClusters, fm: folium.Map) -> None:
        """Create a timeline-based heatmap visualization"""
        _log.info("Building timeline heatmap clusters")
        
        # Process life events for each line
        for line in lines:
            if self.gOp.step():
                break
                
            if not (getattr(line, 'style', None) == 'Life'):
                continue

            person = line.person    
            self.gOp.Referenced.add(person.xref_id, 'heat')
            minyear, maxyear = self._process_timeline_data(line, mycluster)
            self._build_yearly_positions(line, minyear, maxyear, mycluster)
            
            # Add death location if available
            death_event = person.death if person else None
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
            self.gOp.step()
            mycluster.mark(line.fromlocation)
            mycluster.mark(line.tolocation)
            if line.midpoints:
                for mids in line.midpoints:
                    event_latlon = mids.getattr('latlon') if mids else None
                    mycluster.mark(event_latlon, None)

        # Create feature group and heat data
        fg = folium.FeatureGroup(
            name=lgd_txt.format(txt= 'Heatmap', col='black'),
            show=self.gOp.HeatMap
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
    def export(self, main: LatLon,  lines: list[Line], saveresult = True):
        
        if not self.gOp.people:
            _log.warning("No people to plot on map.")
            return
        
        people = self.gOp.people
        main_person = self.gOp.mainPerson if self.gOp.mainPerson else None
        main_person_latlon = getattr(main_person, 'latlon', None) if main_person else None

        if not self.fm:
            # if (self.gOp.MapStyle < 1 or self.gOp.MapStyle > len(backTypes)):
              #  self.gOp.MapStyle = 3

            try:
                tile = xyz.query_name(self.gOp.MapStyle)
            except Exception as e:
                tile = xyz.CartoDB

            birth_event = getattr(self.gOp.mainPerson, 'birth', None)
            death_event = getattr(self.gOp.mainPerson, 'death', None)
            birth_latlon = birth_event.getattr('latlon') if birth_event else None
            death_latlon = death_event.getattr('latlon') if death_event else None

            if death_latlon or birth_latlon:
                self.fm = folium.Map(location=[0, 0], zoom_start=4, tiles= tile)
            else:
                self.fm = folium.Map(location=main_person_latlon, zoom_start=4, tiles = tile)
            if (self.gOp.mapMini):
                folium.plugins.MiniMap(toggle_display=True).add_to(self.fm)
            
            random.seed()

            self.gOp.Referenced = Referenced()
            _log.debug  ("Building Referenced - quick only: %s", not saveresult)
            for line in lines:
                if (getattr(line,'style', None) == 'Life'):
                    self.gOp.Referenced.add(line.person.xref_id, 'quick')
            self.gOp.lastlines = {}

            # make a Dict array of lines 
            for line in lines:
                self.gOp.lastlines[line.person.xref_id] = line
            if (not saveresult):
                return

        SortByLast = (self.gOp.GroupBy == 1 or self.gOp.GroupBy == 2)
        SortByPerson = (self.gOp.GroupBy == 3)
        fm = self.fm
        self.saveresult = saveresult
        
        self.gOp.step("Preparing")
        self.fglastname = dict()
        
        flr = folium.FeatureGroup(name= lgd_txt.format(txt= 'Relations', col='green'), show=False  )
        flp = folium.FeatureGroup(name= lgd_txt.format(txt= 'People', col='Black'), show=False  )
        mycluster = MyMarkClusters(fm, self.gOp.HeatMapTimeStep)

        # *****************************  
        #    HEAT MAP Section            
        # ***************************** 
        
        if self.gOp.MapTimeLine:
            self._create_timeline_heatmap(lines, mycluster, fm)
        else:
            self._create_static_heatmap(lines, mycluster, fm)
        
        #My to use the jquery hack to MAGIC HACK fix the Folium code to use Font Awesome! 
        # missing tag a the end on purpose
        fm.default_js.append(['hack.js', 'https://use.fontawesome.com/releases/v6.5.1/js/all.js" data-auto-replace-svg="nest'])
    
        # ***************************** 
        #     Line Drawing Section      
        # ***************************** 
        
        i = 0
        self.gOp.step("Building lines")
        lines_sorted = lines if SortByLast else sorted(
            lines, 
            key=lambda x: x.prof * ((x.branch/DELTA)+1) + x.prof
        )

        # Process only lines with style attribute
        styled_lines = [line for line in lines_sorted if hasattr(line, 'style')]

        # Log initial line information
        for line in styled_lines:
            _log.info(f"{line.prof * ((line.branch/DELTA)+1)+ line.prof:8f} {line.path:8} "
                     f"{line.branch:.8f} {line.prof:2} "
                     f"{line.parentofperson.name if line.parentofperson else '':20} from {line.name:20}")

        for line in styled_lines:
            self.gOp.step()
            i += 1
            
            # Get styling options based on line type
            marker_options = self._create_marker_options(line)
            
            # Generate label and group name
            label_name = line.name[:25] + "..." if len(line.name) > 25 else line.name
            group_name = lgd_txt.format(txt=label_name, col=marker_options['line_color'])
            
            # Generate popup content
            person = line.person
            birth_year_num = person.birth.date.year_num if person.birth and person.birth.date else None
            death_year_num = person.death.date.year_num if person.death and person.death.date else None
            birth_info = f"{birth_year_num} (Born)" if birth_year_num else ''
            death_info = f"{death_year_num} (Died)" if death_year_num else ''
            popup_content = self._create_popup_content(line, birth_info, death_info)

            # Initialize feature group
            fg = None
            new_fg = False

            # Determine feature group based on sorting options
            if SortByLast:
                fg = self.getFeatureGroup(line.person.surname, line.prof)
            if SortByPerson:
                parent_name = line.parentofperson.name if line.parentofperson else line.person.name
                fg = self.getFeatureGroup(parent_name, line.prof)
            if not fg:
                fg = folium.FeatureGroup(name=group_name, show=True)
                new_fg = True

            # Add start marker
            if line.fromlocation and line.fromlocation.hasLocation():
                start_point = [Drift(line.fromlocation.lat), Drift(line.fromlocation.lon)]
                if self.gOp.MarksOn and self.gOp.BornMark:
                    self._add_point_marker(fg, start_point, marker_options, 
                                       f"Life of {line.name}".replace("`", "‛").replace("'", "‛"), 
                                       popup_content + "\nbirth", marker_options['start_icon'], marker_options['start_color'])

            # Add end marker
            if line.tolocation and line.tolocation.hasLocation():
                end_point = [Drift(line.tolocation.lat), Drift(line.tolocation.lon)]
                if self.gOp.MarksOn and self.gOp.DieMark:
                    self._add_point_marker(fg, end_point, marker_options, 
                                       f"Life of {line.name}".replace("`", "‛").replace("'", "‛"), 
                                       popup_content + "\ndeath", marker_options['end_icon'], marker_options['end_color'])

            # Add midpoints
            fm_line = []
            if line.fromlocation and line.fromlocation.hasLocation():
                fm_line.append(tuple(start_point))
            if line.midpoints:
                for mids in line.midpoints:
                    mid_point = [Drift(mids.location.latlon.lat), Drift(mids.location.latlon.lon)]
                    fm_line.append(tuple(mid_point))
                    if self.gOp.HomeMarker and self.gOp.MarksOn:
                        point_type = mids.what if mids.what in MidPointMarker else "Other"
                        marker = MidPointMarker[point_type][0]
                        color = MidPointMarker[point_type][1]
                        tooltip = mids.what + ' ' + mids.place.place if mids.what else '?? ' + mids.place.place
                        self._add_point_marker(fg, mid_point, marker_options, tooltip, popup_content, marker, color)
            if line.tolocation and line.tolocation.hasLocation():
                fm_line.append(tuple(end_point))

            # Add polyline
            if len(fm_line) > 1:
                line_color = marker_options['line_color']
                # Protect the exp from overflow for very long linages
                line_width = max(int(self.max_line_weight / math.exp(0.5 * min(line.prof,1000))), 2) if line.prof else 1
                if self.gOp.UseAntPath:
                    polyline = folium.plugins.AntPath(fm_line, weight=line_width, opacity=.7, tooltip=line.name, popup=popup_content, color=line_color, lineJoin='arcs')
                else:
                    polyline = folium.features.PolyLine(fm_line, color=line_color, weight=line_width, opacity=1, tooltip=line.name, popup=popup_content, dash_array=marker_options['dash_array'], lineJoin='arcs')
                fg.add_child(polyline)

            # Add feature group to map
            if new_fg:
                fg.layer_name = f"{fg.layer_name} ({len(fm_line) + 1 if line.tolocation else 0})"
                fm.add_child(fg)

        # Add feature groups to map for the sortby options
        for fgn in sorted(self.fglastname.keys(), key=lambda x: self.fglastname[x][2], reverse=False):
            self.fglastname[fgn][0].layer_name = f"{self.fglastname[fgn][3]} : {self.fglastname[fgn][1]}"
            fm.add_child(self.fglastname[fgn][0])

        sc = False if self.gOp.showLayerControl else True
        
        if self.locations:
            # popups = ["lon:{}<br>lat:{}".format(lon, lat) for (lat, lon) in self.locations]
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

        birth_event = getattr(main, 'birth', None)
        birth_latlon = birth_event.getattr('latlon') if birth_event else None
        if main and birth_latlon:
            lat = birth_latlon.lat
            lon = birth_latlon.lon
            if not birth_latlon.isNone():
                folium.Marker([Drift(lat), Drift(lon)], tooltip=main.name, opacity=0.5, icon=folium.Icon(color='lightred', icon='star', prefix='fa', iconSize=['50%', '50%'])).add_to(fm)
        else:
            _log.warning("No GPS locations to generate a Star on the map.")

        #------------LEGEND if there are Markers --------------------
        if self.gOp.MarksOn:
            fm.add_child(Legend())
        
        if SortByLast:
            _log.info("Number of FG lastName: %i", len(self.fglastname))

        self.Done()
        return



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