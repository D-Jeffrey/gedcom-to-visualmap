__all__ = ['MyMarkClusters', 'foliumExporter']

import logging
import math
import os.path
import random

import folium
from folium.plugins import (AntPath, FloatImage, GroupedLayerControl,
                            HeatMapWithTime, MiniMap)
from gedcomoptions import gvOptions
from models.Line import Line
from models.Pos import Pos
from render.Referenced import Referenced
from models.Creator import DELTA


_log = logging.getLogger(__name__)
# TODO need to create this Legend to explain things HACK
legend_file = 'file://' + __file__ + '/../legend.png'
lgd_txt = '<span style="color: {col};">{txt}</span>'

# --------------------------------------------------------------------------------------------------
# Drift is used to create some distance between point so when multiple come/live in the same place, 
# the lines and pins will have some distances and the are not stack on top of each other
#
def dift(l):
    d  = ((random.random() * 0.001) - 0.0005)
    #d = 0
    if (l):
        return (float(l)+d)
    else:
        return None


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

# Dervived fromm https://github.com/leaflet-extras/leaflet-providers/blob/master/leaflet-providers.js 
#  See https://leaflet-extras.github.io/leaflet-providers/preview/ for alternate map layers        
backTypes = ( 'OpenStreetMap', 'Stamen Toner', 'Stadia.StamenTonerLite',  'Stadia.StamenWatercolor',  'OpenTopoMap', 'ESRI.WorldImagery',  'CartoBD Voyager', 'CartoDB Positron' )        

def backTypeSettings (ms):        

    subdomains = None
    if ms == 1: #OpenStreetMap
            attribution ='&copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a>'
            tileurl = backTypes[ms]
    elif ms == 2: #Stamen Toner
            attribution = ( '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> ' 
							'&copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> ' 
							'&copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> ' 
							'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors')
            tileurl = "https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}{r}.png"
    elif ms == 3: # Stadia.StamenTonerLite
            attribution = ( '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a>'
                           ' &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a>'
                           ' &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a>'
                           ' &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors')
            tileurl = 'https://tiles.stadiamaps.com/tiles/stamen_toner_lite/{z}/{x}/{y}{r}.png'
    elif ms ==  4: # Stadia.StamenWatercolor
            attribution = ( '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> ' 
							'&copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> ' 
							'&copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> ' 
                            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors')
            tileurl = 'https://tiles.stadiamaps.com/tiles/stamen_watercolor/{z}/{x}/{y}.jpg'
            
    elif ms ==  5: # OpenTopoMap
            attribution =  ('Map data: {attribution.OpenStreetMap}, <a href="http://viewfinderpanoramas.org">SRTM</a> ' 
                            '| Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)' )
            tileurl = 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png'
    elif ms ==  6: # ESRI.WorldImagery
            attribution =  ('{attribution.Esri} &mdash; ' 
							'Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community' )
            tileurl = 'https://server.arcgisonline.com/ArcGIS/rest/services/WorldImagery/MapServer/tile/{z}/{y}/{x}'
    elif ms ==  7 or ms == 8: # CartoBD Voyager / CartoDB Positron
            attribution ='&copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a>'
            tileurl = backTypes[ms]
            subdomain = 'abcd' 
        
    return (attribution, tileurl, subdomains) 
    
class foliumExporter:
    def __init__(self, gOptions : gvOptions):
        self.file_name = os.path.join(gOptions.resultpath, gOptions.Result)
        self.max_line_weight = gOptions.MaxLineWeight
        self.gOptions = gOptions
        self.fglastname = dict()
        self.saveresult = False
        self.fm = None
        

    
    def setoptions(self):

        return

    def Done(self):
        if self.saveresult:
            self.fm.save(self.file_name)
        self.gOptions.stop()
        # self.fm = None

    def getFeatureGroup(self, thename, depth):
        if not thename in self.fglastname:
            self.fglastname[thename] = [folium.FeatureGroup(name= thename, show=False), 0, 0]
                             
        thefg = self.fglastname[thename][0]
        self.fglastname[thename][1] += 1
        self.fglastname[thename][2] = depth
        return thefg

        # ***************************** 
        #    Export results into HTML   
        # ***************************** 
        # lines are from creator
    def export(self, main: Pos,  lines: [Line], saveresult = True):
        
        if not self.fm:
            if (self.gOptions.MapStyle < 1 or self.gOptions.MapStyle > len(backTypes)):
                self.gOptions.MapStyle = 3

            if (self.gOptions.humans and self.gOptions.mainHumanPos and self.gOptions.mainHumanPos.isNone()):
                self.fm = folium.Map(location=[0, 0], zoom_start=4)
            else:
                lat = float(self.gOptions.mainHumanPos.lat)
                lon = float(self.gOptions.mainHumanPos.lon)
                self.fm = folium.Map(location=[lat,lon], zoom_start=4)
            
                
            for bt in range(1,len(backTypes)):
                (attribution, tileurl,subdomains) = backTypeSettings(bt)
                if subdomains:
                    folium.raster_layers.TileLayer( tiles=tileurl, attr=attribution, subdomains = subdomains , name = backTypes[bt]).add_to(self.fm)
                else:
                    folium.raster_layers.TileLayer( tiles=tileurl, attr=attribution,  name = backTypes[bt]).add_to(self.fm)
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
            _log.info("building clusters")    
           
            self.gOptions.step("Building Heatmap Clusters")
            for line in lines:
                if (self.gOptions.step()):
                    break
                if (hasattr(line,'style') and line.style == 'Life'):
                    self.gOptions.Referenced.add(line.human.xref_id, 'heat')
                    if line.human.birth and line.human.birth.pos:
                        mycluster.mark(line.human.birth.pos, line.human.birth.whenyearnum())
                        minyear = line.human.birth.whenyearnum()
                    else:
                        minyear = None
                    if line.human.death and line.human.death.when:
                        maxyear = line.human.death.whenyearnum(True)
                    else:
                        maxyear = None
                        for mids in (line.midpoints):
                            y = mids.whenyearnum()
                            if y:
                                if minyear:
                                    minyear = min(int(y), minyear)
                                else:
                                    minyear = int(y)
                            y = mids.whenyearnum(True)
                            if y: 
                                if maxyear:
                                    maxyear = max(int(y), maxyear)
                                else:
                                    maxyear = int(y)
                    if minyear and maxyear:
                        activepos = Pos(None, None)
                        if line.human.birth and line.human.birth.pos:
                            (activepos.lat, activepos.lon) = (line.human.birth.pos.lat, line.human.birth.pos.lon)
                        for year in range(minyear,maxyear):
                            for mids in (line.midpoints):
                                if mids.whenyearnum() == year:
                                    activepos = mids.pos
                            if activepos and activepos.lat and activepos.lon:
                                mycluster.mark(activepos, year)
                    if line.human.death and line.human.death.pos:
                        mycluster.mark(line.human.death.pos, line.human.death.whenyearnum())            
            years= []
            for marker in mycluster.pmarker:
                self.gOptions.step()
                if isinstance(mycluster.pmarker[marker][3], str):
                    _log.debug (mycluster.pmarker[marker])
                theyear = mycluster.pmarker[marker][3]
                if theyear and not theyear in years: 
                    years.append(theyear)
               
            years.sort()
            
                        
            heat_data = [[] for _ in range (0,len(years))] 
    
            
            for mkyear in range(0,len(years)):
                self.gOptions.step()
                for markname in (mycluster.pmarker):
                    if years[mkyear] == mycluster.pmarker[markname][3]:
                        heat_data[mkyear].append([mycluster.pmarker[markname][0], mycluster.pmarker[markname][1], mycluster.pmarker[markname][2]])
            
            #Normalize the data
            mx=0
            for i in range(len(heat_data)):
                for j in range(len(heat_data[i])):
                    mx = max(mx, heat_data[i][j][2])
            for i in range(len(heat_data)):
                for j in range(len(heat_data[i])):
                    heat_data[i][j][2] = float(heat_data[i][j][2])/mx
            
            
            hm = folium.plugins.HeatMapWithTime(heat_data,index = years , name= 'Heatmap', max_opacity=0.9, min_speed=1, speed_step=1, max_speed=25,
                                            gradient={'0':'Navy', '0.25':'Blue','0.5':'Green', '0.75':'Yellow','1': 'Red'})
            fm.add_child( hm)
        else:
            for line in lines:
                self.gOptions.step()
                mycluster.mark(line.a)
                mycluster.mark(line.b)
                if line.midpoints:
                    for mids in (line.midpoints):
                        mycluster.mark(mids.pos, None)
      
            fg = folium.FeatureGroup(name= lgd_txt.format(txt= 'Heatmap', col='black'), show=(self.gOptions.HeatMap))
            heat_data = []
            for markname in (mycluster.pmarker):
                self.gOptions.step()
                heat_data.append([mycluster.pmarker[markname][0], mycluster.pmarker[markname][1], mycluster.pmarker[markname][2]])
                 
            
            hm = folium.plugins.HeatMap(heat_data,max_opacity=0.8, name= 'Heatmap')
            fg.add_child(hm)
            fm.add_child( fg)
        
            
        #My to use the jquery hack to MAGIC HACK fix the Folium code to use Font Awesome! 
        # missing tag a the end on purpose
        fm.default_js.append(['hack.js', 'https://use.fontawesome.com/releases/v6.5.1/js/all.js" data-auto-replace-svg="nest'])
    
        """ ***************************** """ 
        """     Line Drawing Section      """ 
        """ ***************************** """ 
        
        
        i = 0
        self.gOptions.step("Building lines")
        if SortByLast:
            lines_sorted = lines
        else:
            lines_sorted = sorted(lines, key=lambda x: x.prof * ((x.branch/DELTA)+1)+ x.prof)
        for line in (list(filter (lambda line: hasattr(line,'style'), lines_sorted))):
            _log.info("{:8f} {:8}  {:.8f} {:2} {:20} from {:20}".format((line.prof * ((line.branch/DELTA)+1)+ line.prof),  line.path, line.branch, line.prof, (line.parentofhuman.name if line.parentofhuman else "" ), line.name))
            
        for line in (list(filter (lambda line: hasattr(line,'style'), lines_sorted))):
            self.gOptions.step()
            i += 1
            _log.debug("{:8}  {:.10f} {:2} {:20} from {:20}".format(line.path, line.branch, line.prof, (line.parentofhuman.name if line.parentofhuman else "" ), line.name))
            if ( line.style == 'Life'):
                flc = flp                                                   # Feature Group Class   (To create a Hierachary NOT USED)
                aicc = 'orange'                                             # Start Point Icon color
                aici = 'child'                                              # Start Point Icon itself
                bicc = 'gray'                                               # End Point Icon color
                bici = 'cross'                                              # End Point Icon itself
                lc = '#' + line.color.to_hexa()                             # Line Color
                da = []
                ln = line.name                                              # Line Name
                g = ""
                markertipname = f"Life of {line.name}"                      # Marker Tool Tip
                fancyname = f"{line.style} of {line.name}"                 # the line represents and name for Tool Tip
                markhome = 'house'                                          # Icon to put at the Start  (NOT USED)
            else: 
                flc = flr
                aicc = 'green'
                aici = 'baby-carriage'
                bicc = 'green'
                lc = 'green'
                da = [5,5]
                # If it is a link to the father, then color it blue if mother then pink, otherwise it is green
                if (line.style == 'father'):                                
                    lc = 'blue'
                    lc = '#2b8cbe'
                    bici = 'male'
                    bicc = 'blue'
                if (line.style == 'mother'):  
                    lc = 'pink'
                    bici = 'female'
                    bicc = 'pink'
                ln = line.name
                g = line.name.split(' ',2)[0] 
                markertipname = f"{line.name} {line.style} of " + (line.parentofhuman.name if line.parentofhuman else '')
                fancyname = f"{line.name} {line.style} of " + (line.parentofhuman.name if line.parentofhuman else '')
            self.gOptions.Referenced.add(line.human.xref_id, 'line', ln)        # Line ID
            fg = None
            newfg = False
            # labelname = str(i) +' '+ ln
            labelname = ln
            if (len(labelname) > 25): labelname = labelname[1:25] +"..."
            gn = lgd_txt.format( txt=labelname, col= lc)
            fm_line = []
          
            bextra = "{} (Born)".format(line.human.birth.whenyear()) if line.human.birth and line.human.birth.when else ''
            dextra = "{} (Died)".format(line.human.death.whenyear()) if line.human.death and line.human.death.when else ''
            fancyname = fancyname + "<br>" + bextra +" "+ dextra if (bextra != '') or (dextra != '') else fancyname
            fancypopup = f"<div style='min-width: 150px'>{fancyname}</div>"
            if line.human.photo:
                fancypopup = fancypopup + "<img src='{}' width='150'>".format(line.human.photo)
            difta = diftb = None
            
            if (line.a and line.a.lat and line.a.lon):
                # color = father/mother or born = baby, male, female
                difta = [dift(line.a.lat), dift(line.a.lon)]
                if self.gOptions.MarksOn:
                    if self.gOptions.BornMark:
                        mk = folium.features.Marker(difta,tooltip=markertipname , popup=fancypopup, opacity=.5, icon=folium.Icon(color=aicc,icon=aici, prefix='fa' ))
                        #
                        ## We are going to either create a new Feature Group or get an existing one or create a new one if that existing does not work with the get
                        if SortByLast:
                            fg = self.getFeatureGroup(line.human.surname, line.prof)
                        if SortByPerson:
                            parentname = line.parentofhuman.name if line.parentofhuman else line.human.name
                            fg = self.getFeatureGroup(parentname , line.prof)
                        if (not fg):
                            fg = folium.FeatureGroup(name= gn, show=False)
                            newfg = True
                        fg.add_child(mk)
                # 'tombstone' or  'cross'
            if (line.b and line.b.lat and line.b.lon):
                diftb = [dift(line.b.lat), dift(line.b.lon)]
                if self.gOptions.MarksOn:
                    mk = folium.features.Marker(diftb,tooltip =markertipname , popup=fancypopup, opacity=.5,icon=folium.Icon(color=bicc,icon=bici, prefix='fa', extraClasses = 'fas'))
                    if SortByLast:
                        fg = self.getFeatureGroup(line.human.surname, line.prof)
                    if SortByPerson:
                        parentname = line.parentofhuman.name if line.parentofhuman else line.human.name
                        fg = self.getFeatureGroup(parentname, line.prof)
                        
                    if (not fg):
                        fg = folium.FeatureGroup(name= gn, show=False)
                        newfg = True
                    fg.add_child(mk)
            if difta:
                fm_line.append(tuple(difta))
            if line.midpoints:
                # Change line type
                lc = "gray"
                for mids in (line.midpoints):
                    midspot = tuple([dift(mids.pos.lat), dift(mids.pos.lon)])
                    fm_line.append(midspot)
                    if self.gOptions.HomeMarker and fg:
                        if mids.what == 'home':
                            mker = 'home'
                            mkcolor = bicc
                            tip = mids.where
                        else:
                            mker = 'shoe-prints'
                            mkcolor = 'lightgray'
                            if mids.what:
                                tip = mids.what + ' ' + mids.where
                            else:
                                tip = '?? ' + mids.where
                        mk = folium.features.Marker(midspot,tooltip =tip, opacity=.5, icon=folium.Icon(color=mkcolor,icon=mker, prefix='fa', extraClasses = 'fas'))
                        fg.add_child(mk)
                    
            if diftb:
                fm_line.append(tuple(diftb))

            if (len(fm_line) > 1):                     
                lcolor = line.color.to_hexa()
                lcolor = lc
                if line.prof:
                    lwidth = max(int(self.max_line_weight/math.exp(0.5*line.prof)), 2)
                else:
                    lwidth = 1
                if self.gOptions.UseAntPath:
                    if line.style == 'Life':
                        pl = folium.plugins.AntPath(fm_line, weight=lwidth, opacity=.7, tooltip=ln, popup=fancypopup, color=lcolor, lineJoin='arcs')
                    else:
                        pl = folium.features.PolyLine(fm_line, color=lcolor, weight=lwidth, opacity=1, tooltip=ln, popup=fancypopup, dash_array = da, lineJoin='arcs' )
                else:
                    pl = folium.features.PolyLine(fm_line, color=lcolor, weight=lwidth, opacity=1, tooltip=ln,  popup=fancypopup, dash_array = da, lineJoin='arcs')
                if (pl):
                    if SortByLast:
                        fg = self.getFeatureGroup(line.human.surname, line.prof)
                    if SortByPerson:
                        parentname = line.parentofhuman.name if line.parentofhuman else line.human.name
                        fg = self.getFeatureGroup(parentname, line.prof)
                        
                        
              
                    if (not fg):
                        fg = folium.FeatureGroup(name= gn, show=False)

                        newfg = True
                    fg.add_child(pl)
            parentname = line.parentofhuman.name if line.parentofhuman else line.human.name
            _log.info(f"Name:{line.human.name:30};\tParent:{parentname:30};\tStyle:{line.style};\tfrom:{line.a}; to:{line.b}")

            # Did we just create a feature group for this person?
            if newfg:
                fg.layer_name = fg.layer_name + " ({})".format(len(fm_line) + 1 if diftb else 0 + 1 if diftb else 0)     
                fm.add_child(fg)
        fglc = []
        for fgn in sorted(self.fglastname.keys(), key=lambda x: self.fglastname[x][2], reverse = False ):
            _log.debug ("]]%s : %s", fgn, self.fglastname[fgn][1])
            self.fglastname[fgn][0].layer_name = "{} : {}".format(fgn, self.fglastname[fgn][1])          
            fm.add_child(self.fglastname[fgn][0])
            fglc.append(self.fglastname[fgn][0])
        sc = False if self.gOptions.showLayerControl else True
        
        # folium.plugins.GroupedLayerControl(
        #    groups={'People': fglc},
        #    exclusive_groups=False,
        #    collapsed=False,
        #    ).add_to(fm)
        folium.map.LayerControl('topleft', collapsed= sc).add_to(fm)

        if main and main.birth and main.birth.pos and main.birth.pos.lat:         
            #TODO Look at MarkerClusters           
            if self.gOptions.MarkStarOn:
                folium.Marker([dift(main.birth.pos.lat), dift(main.birth.pos.lon)], tooltip = main.name, opacity=0.5, icon=folium.Icon(color='lightred',icon='star', prefix='fa', iconSize = ['50%', '50%'])).add_to(fm)
        else:
            _log.warning ("No GPS locations to generate a map.")
        
        # Add a legend
        if self.gOptions.HeatMapTimeLine: 
            ImgBottom = 6
        else:
            ImgBottom = 2
        FloatImage(legend_file, bottom=ImgBottom, left=10).add_to(fm)
        if SortByLast:
            _log.info ("Number of FG lastName: %i", len(self.fglastname))
            
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