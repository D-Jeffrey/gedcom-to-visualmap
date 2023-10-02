__all__ = ['MyMarkClusters', 'foliumExporter']

import math
import random
import folium 
from folium.plugins import GroupedLayerControl

from models.Line import Line
from models.Pos import Pos
from render.Referenced import Referenced
import os.path
import logging

from gedcomoptions import gvOptions
from folium.plugins import FloatImage, AntPath, MiniMap, HeatMapWithTime

logger = logging.getLogger(__name__)
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
                if type(when) == type (" "):
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
        
        backTypes = ('OpenStreetMap', 'Stamen Terrain', 'CartoDB Positron', 'Stamen Toner',  'Stamen Watercolor', 'Cartodbdark_matter')
        if (self.gOptions.MapStyle < 1 or self.gOptions.MapStyle > len(backTypes)):
            self.gOptions.MapStyle = 3

        self.fm = folium.Map(location=[0, 0], zoom_start=2, tiles=backTypes[self.gOptions.MapStyle])
        for bt in range(0,len(backTypes)):
            if bt + 1 !=  self.gOptions.MapStyle:
                folium.raster_layers.TileLayer(backTypes[bt], name=backTypes[bt]).add_to(self.fm)
        if (self.gOptions.mapMini):
            folium.plugins.MiniMap(toggle_display=True).add_to(self.fm)
        
        random.seed()
        self.gOptions.step()
        self.gOptions.Referenced = Referenced()

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

    def export(self, main: Pos,  lines: [Line], saveresult = True):
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
            logger.info("building clusters")    
           
            self.gOptions.step("Building Heatmap Clusters")
            for line in lines:
                if (self.gOptions.step()):
                    break
                if (hasattr(line,'style') and line.style == 'Life'):
                    Referenced.add(line.human.xref_id, 'heat')
                    if line.human.birth and line.human.birth.pos:
                        mycluster.mark(line.human.birth.pos, line.human.birth.whenyear())
                        minyear = line.human.birth.whenyearnum()
                    else:
                        minyear = None
                    if line.human.death and line.human.death.when:
                        maxyear = line.human.death.whenyearnum(True)
                    else:
                        maxyear = None
                        for mids in (line.midpoints):
                            y = mids.whenyear()
                            if y:
                                if minyear:
                                    minyear = min(int(y), minyear)
                                else:
                                    minyear = int(y)
                            y = mids.whenyear(True)
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
                if type(mycluster.pmarker[marker][3]) == type(' '):
                    logger.debug (mycluster.pmarker[marker])
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
        fm.default_js.append(['hack.js', 'https://use.fontawesome.com/releases/v5.15.4/js/all.js" data-auto-replace-svg="nest'])
    
        """ ***************************** """ 
        """     Line Drawing Section      """ 
        """ ***************************** """ 
        
        
        i = 0
        self.gOptions.step("Building lines")
        if SortByLast:
            lines_sorted = lines
        else:
            lines_sorted = sorted(lines, key=lambda x: x.prof)
        for line in (list(filter (lambda line: hasattr(line,'style'), lines_sorted))):
            self.gOptions.step()
            i += 1
            self.gOptions.Referenced.add(line.human.xref_id, 'line')        # Line ID
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
                markertipname = "Life of " + line.name                      # Marker Tool Tip
                fancyname = line.style + " of " + line.name                 # the line represents and name for Tool Tip
                markhome = 'house'                                          # Icon to put at the Start  (NOT USED)
            else: 
                flc = flr
                aicc = 'green'
                aici = 'baby'
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
                markertipname = line.name +  " " + line.style + " of "+ (line.parentofhuman.name if line.parentofhuman else '')
                fancyname = line.name + " " + line.style + " of "+ (line.parentofhuman.name if line.parentofhuman else '')
            fg = None
            newfg = False
            # labelname = str(i) +' '+ ln
            labelname = ln
            if (len(labelname) > 25): labelname = labelname[1:25] +"..."
            gn = lgd_txt.format( txt=labelname, col= lc)
            fm_line = []
          
            bextra = "Born {}".format(line.human.birth.whenyear()) if line.human.birth and line.human.birth.when else ''
            dextra = "Died {}".format(line.human.death.whenyear()) if line.human.death and line.human.death.when else ''
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
                            parentname = line.parentofhuman.name if line.parentofhuman else ''
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
                        parentname = line.parentofhuman.name if line.parentofhuman else ''
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
                        parentname = line.parentofhuman.name if line.parentofhuman else ''
                        fg = self.getFeatureGroup(parentname, line.prof)
                        
              
                    if (not fg):
                        fg = folium.FeatureGroup(name= gn, show=False)

                        newfg = True
                    fg.add_child(pl)
            parentname = line.parentofhuman.name if line.parentofhuman else ''
            logger.info(f"Name:{line.human.name:30};\tParent:{parentname:30};\tStyle:{line.style};\tfrom:{line.a}; to:{line.b}")

            # Did we just create a feature group for this person?
            if newfg:
                fg.layer_name = fg.layer_name + " ({})".format(len(fm_line) + 1 if diftb else 0 + 1 if diftb else 0)     
                fm.add_child(fg)
        fglc = []
        for fgn in sorted(self.fglastname.keys(), key=lambda x: self.fglastname[x][2], reverse = False ):
            logger.debug ("]]%s : %s", fgn, self.fglastname[fgn][1])
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
            logger.warning ("No GPS locations to generate a map.")
        
        # Add a legend
        FloatImage(legend_file, bottom=0, left=86).add_to(fm)
        if SortByLast:
            logger.info ("Number of FG lastName: %i", len(self.fglastname))
            
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