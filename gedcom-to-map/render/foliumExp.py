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
from gedcomoptions import gvOptions
from models.Line import Line
from models.Pos import Pos
from render.Referenced import Referenced
from models.Creator import DELTA


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
    def __init__(self):
        super().__init__()
        self._template = Template(legend_template)

# --------------------------------------------------------------------------------------------------
# Drift is used to create some distance between point so when multiple come/live in the same place, 
# the lines and pins will have some distances and the are not stack on top of each other
#
def Drift(l):
    d  = ((random.random() * 0.001) - 0.0005)
    #d = 0
    if (l):
        return (float(l)+d)
    else:
        return None

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
    def __init__(self, mymap, step):
        self.pmarker = dict()
        self.cmarker = dict()
        self.markercluster = dict()
        self.mymap = mymap
        self.step = step

    def mark (self, spot, when=None):
        if spot and spot.lat and spot.lon:
            cnt = 1
            if (when):
                # TODO this is a range date hack
                if isinstance(type(when), str):
                    when = when[0:4]
                when = int(when) - (int(when) % self.step)
                markname = str(spot.lat)+ str(spot.lon)  + str(when)
            else:
                markname = str(spot.lat)+","+ str(spot.lon)
            if (markname in self.pmarker.keys()):
                cnt = self.pmarker[markname][2]+1
            self.pmarker[markname] = (spot.lat, spot.lon, cnt, when)
            
    
    def checkmarker(self, lat, long, name):
        if lat and long:
            markname = str(lat)+","+ str(long)
            if (self.cmarker[markname] == 1):
                return None
            if (markname in self.markercluster.keys()):
                return self.markercluster[markname]
            else:
                self.markercluster[markname] = folium.plugins.MarkerCluster(name).add_to(self.mymap)
                return self.markercluster[markname]

class foliumExporter:
    def __init__(self, gOptions : gvOptions):
        self.file_name = os.path.join(gOptions.resultpath, gOptions.Result)
        self.max_line_weight = gOptions.MaxLineWeight
        self.gOptions = gOptions
        self.fglastname = dict()
        self.saveresult = False
        self.fm = None
        self.locations = []
        self.popups = []
        
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

    def _create_popup_content(self, line, birth_info: str = '', death_info: str = '') -> str:
        """Generate popup content for markers"""
        if line.style == 'Life':
            fancy_name = f"{line.style} of {line.name}"
        else:
            parent_name = line.parentofhuman.name if line.parentofhuman else ''
            fancy_name = f"{line.name} {line.style} of {parent_name}"

        if birth_info or death_info:
            fancy_name = f"{fancy_name}<br>{birth_info} {death_info}"

        popup = f"<div style='min-width: 150px'>{fancy_name}</div>"
        if line.human.photo:
            popup += f"<img src='{line.human.photo}' width='150'>"
        return popup

    def _add_point_marker(self, fg: folium.FeatureGroup, point: list, options: dict, 
                        tooltip: str, popup: str, icon_name: str, color: str) -> None:
        """Add a marker to the feature group"""
        if self.gOptions.MarksOn:
            marker = folium.features.Marker(
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
            self.fm.save(self.file_name)
        # self.gOptions.stop()
        # self.fm = None

    def getFeatureGroup(self, thename, depth):
        """Retrieve or create a feature group."""
        if not thename in self.fglastname:
            self.fglastname[thename] = [folium.FeatureGroup(name= thename, show=False), 0, 0]
                             
        thefg = self.fglastname[thename][0]
        self.fglastname[thename][1] += 1
        self.fglastname[thename][2] = depth
        return thefg

    def _process_timeline_data(self, line: Line, mycluster: MyMarkClusters) -> tuple[int, int]:
        """Process timeline data for a single line and return min/max years"""
        minyear = maxyear = None
        
        # Add birth location if available
        if line.human.birth and line.human.birth.pos:
            mycluster.mark(line.human.birth.pos, line.human.birth.whenyearnum())
            minyear = line.human.birth.whenyearnum()
        
        # Add death year if available
        if line.human.death and line.human.death.when:
            maxyear = line.human.death.whenyearnum(True)
        else:
            # Process midpoints for min/max year determination
            for mids in line.midpoints:
                start_year = mids.whenyearnum()
                if start_year:
                    minyear = min(int(start_year), minyear) if minyear else int(start_year)
                end_year = mids.whenyearnum(True)
                if end_year:
                    maxyear = max(int(end_year), maxyear) if maxyear else int(end_year)
        
        return minyear, maxyear

    def _build_yearly_positions(self, line: Line, minyear: int, maxyear: int, mycluster: MyMarkClusters) -> None:
        """Build position data for each year in the timeline"""
        if not (minyear and maxyear):
            return
            
        activepos = Pos(None, None)
        if line.human.birth and line.human.birth.pos:
            activepos = line.human.birth.pos
            
        for year in range(minyear, maxyear):
            # Update active position if we have a midpoint for this year
            for mids in line.midpoints:
                if mids.whenyearnum() == year:
                    activepos = mids.pos
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
            if self.gOptions.step():
                break
                
            if not (hasattr(line, 'style') and line.style == 'Life'):
                continue
                
            self.gOptions.Referenced.add(line.human.xref_id, 'heat')
            minyear, maxyear = self._process_timeline_data(line, mycluster)
            self._build_yearly_positions(line, minyear, maxyear, mycluster)
            
            # Add death location if available
            if line.human.death and line.human.death.pos:
                mycluster.mark(line.human.death.pos, line.human.death.whenyearnum())

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
            self.gOptions.step()
            mycluster.mark(line.a)
            mycluster.mark(line.b)
            if line.midpoints:
                for mids in line.midpoints:
                    mycluster.mark(mids.pos, None)

        # Create feature group and heat data
        fg = folium.FeatureGroup(
            name=lgd_txt.format(txt='Heatmap', col='black'),
            show=self.gOptions.HeatMap
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
    def export(self, main: Pos,  lines: list[Line], saveresult = True):
        
        if not self.fm:
            # if (self.gOptions.MapStyle < 1 or self.gOptions.MapStyle > len(backTypes)):
              #  self.gOptions.MapStyle = 3

            if (self.gOptions.humans and self.gOptions.mainHumanPos and self.gOptions.mainHumanPos.isNone()):
                self.fm = folium.Map(location=[0, 0], zoom_start=4, tiles= xyz.query_name(self.gOptions.MapStyle))
            else:
                lat = float(self.gOptions.mainHumanPos.lat)
                lon = float(self.gOptions.mainHumanPos.lon)
                self.fm = folium.Map(location=[lat,lon], zoom_start=4, tiles = xyz.query_name(self.gOptions.MapStyle) )
            if (self.gOptions.mapMini):
                folium.plugins.MiniMap(toggle_display=True).add_to(self.fm)
            

            random.seed()

            self.gOptions.Referenced = Referenced()
            _log.debug  ("Building Referenced - quick only: %s", not saveresult)
            for line in lines:
                if (hasattr(line,'style') and line.style == 'Life'):
                    self.gOptions.Referenced.add(line.human.xref_id, 'quick')
            self.gOptions.lastlines = {}
            # make a Dict array of lines 
            for line in lines:
                self.gOptions.lastlines[line.human.xref_id] = line
            if (not saveresult):
                return

        SortByLast = (self.gOptions.GroupBy == 1)
        SortByPerson = (self.gOptions.GroupBy == 2)
        fm = self.fm
        self.saveresult = saveresult
        
        self.gOptions.step("Preparing")
        self.fglastname = dict()
        

        flr = folium.FeatureGroup(name= lgd_txt.format(txt= 'Relations', col='green'), show=False  )
        flp = folium.FeatureGroup(name= lgd_txt.format(txt= 'People', col='Black'), show=False  )
        mycluster = MyMarkClusters(fm, self.gOptions.HeatMapTimeStep)


        

        # *****************************  
        #    HEAT MAP Section            
        # ***************************** 
        
        if self.gOptions.HeatMapTimeLine:
            self._create_timeline_heatmap(lines, mycluster, fm)
        else:
            self._create_static_heatmap(lines, mycluster, fm)
        
            
        #My to use the jquery hack to MAGIC HACK fix the Folium code to use Font Awesome! 
        # missing tag a the end on purpose
        fm.default_js.append(['hack.js', 'https://use.fontawesome.com/releases/v6.5.1/js/all.js" data-auto-replace-svg="nest'])
    
        """ ***************************** """ 
        """     Line Drawing Section      """ 
        """ ***************************** """ 
        


        i = 0
        self.gOptions.step("Building lines")
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
                     f"{line.parentofhuman.name if line.parentofhuman else '':20} from {line.name:20}")

        for line in styled_lines:
            self.gOptions.step()
            i += 1
            
            # Get styling options based on line type
            marker_options = self._create_marker_options(line)
            
            # Generate label and group name
            label_name = line.name[:25] + "..." if len(line.name) > 25 else line.name
            group_name = lgd_txt.format(txt=label_name, col=marker_options['line_color'])
            
            # Generate popup content
            birth_info = f"{line.human.birth.whenyear()} (Born)" if line.human.birth and line.human.birth.when else ''
            death_info = f"{line.human.death.whenyear()} (Died)" if line.human.death and line.human.death.when else ''
            popup_content = self._create_popup_content(line, birth_info, death_info)

            # Initialize feature group
            fg = None
            new_fg = False

            # Determine feature group based on sorting options
            if SortByLast:
                fg = self.getFeatureGroup(line.human.surname, line.prof)
            if SortByPerson:
                parent_name = line.parentofhuman.name if line.parentofhuman else line.human.name
                fg = self.getFeatureGroup(parent_name, line.prof)
            if not fg:
                fg = folium.FeatureGroup(name=group_name, show=False)
                new_fg = True

            # Add start marker
            if line.a and line.a.lat and line.a.lon:
                start_point = [Drift(line.a.lat), Drift(line.a.lon)]
                self._add_point_marker(fg, start_point, marker_options, 
                                       f"Life of {line.name}".replace("`", "‛").replace("'", "‛"), 
                                       popup_content, marker_options['start_icon'], marker_options['start_color'])

            # Add end marker
            if line.b and line.b.lat and line.b.lon:
                end_point = [Drift(line.b.lat), Drift(line.b.lon)]
                self._add_point_marker(fg, end_point, marker_options, 
                                       f"Life of {line.name}".replace("`", "‛").replace("'", "‛"), 
                                       popup_content, marker_options['end_icon'], marker_options['end_color'])

            # Add midpoints
            fm_line = []
            if line.a and line.a.lat and line.a.lon:
                fm_line.append(tuple(start_point))
            if line.midpoints:
                for mids in line.midpoints:
                    mid_point = [Drift(mids.pos.lat), Drift(mids.pos.lon)]
                    fm_line.append(tuple(mid_point))
                    if self.gOptions.HomeMarker:
                        point_type = mids.what if mids.what in MidPointMarker else "Other"
                        marker = MidPointMarker[point_type][0]
                        color = MidPointMarker[point_type][1]
                        tooltip = mids.what + ' ' + mids.where if mids.what else '?? ' + mids.where
                        self._add_point_marker(fg, mid_point, marker_options, tooltip, popup_content, marker, color)
            if line.b and line.b.lat and line.b.lon:
                fm_line.append(tuple(end_point))

            # Add polyline
            if len(fm_line) > 1:
                line_color = marker_options['line_color']
                line_width = max(int(self.max_line_weight / math.exp(0.5 * line.prof)), 2) if line.prof else 1
                if self.gOptions.UseAntPath:
                    polyline = folium.plugins.AntPath(fm_line, weight=line_width, opacity=.7, tooltip=line.name, popup=popup_content, color=line_color, lineJoin='arcs')
                else:
                    polyline = folium.features.PolyLine(fm_line, color=line_color, weight=line_width, opacity=1, tooltip=line.name, popup=popup_content, dash_array=marker_options['dash_array'], lineJoin='arcs')
                fg.add_child(polyline)

            # Add feature group to map
            if new_fg:
                fg.layer_name = f"{fg.layer_name} ({len(fm_line) + 1 if line.b else 0})"
                fm.add_child(fg)

        # Add feature groups to map for the sortby options
        for fgn in sorted(self.fglastname.keys(), key=lambda x: self.fglastname[x][2], reverse=False):
            self.fglastname[fgn][0].layer_name = f"{fgn} : {self.fglastname[fgn][1]}"
            fm.add_child(self.fglastname[fgn][0])

        sc = False if self.gOptions.showLayerControl else True
        
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

        if main and main.birth and main.birth.pos and main.birth.pos.lat:
            if self.gOptions.MarkStarOn:
                folium.Marker([Drift(main.birth.pos.lat), Drift(main.birth.pos.lon)], tooltip=main.name, opacity=0.5, icon=folium.Icon(color='lightred', icon='star', prefix='fa', iconSize=['50%', '50%'])).add_to(fm)
        else:
            _log.warning("No GPS locations to generate a Star on the map.")

        #------------LEGEND if there are Markers --------------------
        if self.gOptions.MarksOn:
            fm.add_child(Legend())
        
        if SortByLast:
            _log.info("Number of FG lastName: %i", len(self.fglastname))

        self.Done()
        return



        """ *****************************************************  """ 
        """    Display people using subgroup control to navigate   """ 
        """    NOT USED YET                                        """ 
        """ *****************************************************  """ 

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