import numpy as nump
import math
import random
import folium 
# import simplekml as simplekml
from models.Line import Line
from models.Pos import Pos
import webbrowser
import time
from folium.plugins import FloatImage, AntPath, MiniMap, HeatMapWithTime
legend_file = 'legend.png'
lgd_txt = '<span style="color: {col};">{txt}</span>'

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
        self.markercluster = dict()
        self.mymap = mymap
        self.step = step

    def mark (self, spot, when=None):
        if spot and spot.lat and spot.lon:
            cnt = 1
            if (when):
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
            if (self.cmarker[mark] == 1):
                return None
            if (markname in self.markercluster.keys()):
                return self.markercluster[markname]
            else:
                self.markercluster[markname] = folium.MarkerCluster(name), add_to(self.mymap)
                return self.markercluster[markname]

class setGeoExpOptions:
    def __init__ (self, MarksOn = True, HeatMap = True, MarkStarOn = True, BornMark = False, DieMark = True, MapStyle = 3, GroupBy=0, AntPath=True, HeatMapTimeLine=False, HeatMapTimeStep=1, HomeMarker=False):

        self.MarksOn = MarksOn
        self.HeatMap = HeatMap
        self.BornMark = BornMark
        self.DieMark = DieMark
        self.MapStyle = MapStyle
        self.MarkStarOn = MarkStarOn
        self.GroupBy = GroupBy
        self.UseAntPath = AntPath
        self.HeatMapTimeLine = HeatMapTimeLine
        self.HeatMapTimeStep = HeatMapTimeStep
        self.HomeMarker = HomeMarker

        
class foliumExporter:
    def __init__(self, file_name, max_line_weight=1, gOptions : setGeoExpOptions = setGeoExpOptions()):
        self.file_name = file_name
        self.kml = None
        self.max_line_weight = max_line_weight
        self.gOptions = gOptions
        self.fm = folium.Map(location=[0, 0], zoom_start=2)
        
        backTypes = ('Open Street Map', 'Stamen Terrain', 'CartoDB Positron', 'Stamen Toner',  'Stamen Watercolor', 'Cartodbdark_matter')
        if (self.gOptions.MapStyle < 1 or self.gOptions.MapStyle > len(backTypes)):
            self.gOptions.MapStyle = 3
        for bt in range(0,4):
            folium.raster_layers.TileLayer(backTypes[bt], name=backTypes[bt]).add_to(self.fm)
        

        folium.plugins.MiniMap(toggle_display=True).add_to(self.fm)
        
        random.seed()
        

    def setoptions(self):

        return

    def Done(self):
        self.fm.save(self.file_name)
        self.fm = None

    def getFeatureGroup(self, thename, depth):
        if not thename in self.fglastname:
            self.fglastname[thename] = [folium.FeatureGroup(name= thename, show=False), 0, 0]
                             
        thefg = self.fglastname[thename][0]
        self.fglastname[thename][1] += 1
        self.fglastname[thename][2] = depth
        return thefg

    def export(self, main: Pos, lines: [Line], ntag =""):

        SortByLast = (self.gOptions.GroupBy == 1)
        SortByPerson = (self.gOptions.GroupBy == 2)
        fm = self.fm
        
        
        self.fglastname = dict()
        

        flr = folium.FeatureGroup(name= lgd_txt.format(txt= 'Relations', col='green'), show=False  )
        flp = folium.FeatureGroup(name= lgd_txt.format(txt= 'People', col='Black'), show=False  )
        mycluster = MyMarkClusters(fm, self.gOptions.HeatMapTimeStep)

        print("building clusters")

        """ *****************************
            HEAT MAP Section
            *****************************
        """
        if self.gOptions.HeatMapTimeLine:
            
           
            
            for line in lines:
                if (line.style == 'Life'):
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
                if type(mycluster.pmarker[marker][3]) == type(' '):
                        print (mycluster.pmarker[marker])
                theyear = mycluster.pmarker[marker][3]
                if not theyear in years: 
                        years.append(theyear)
               
            years.sort()
            
                        
            heat_data = [[] for _ in range (0,len(years))] 
    
            
            for mkyear in range(0,len(years)):
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
            
            
            hm = folium.plugins.HeatMapWithTime(heat_data,index = years , name= 'Heatmap', max_opacity=0.8, min_speed=1, speed_step=1, max_speed=25,
                                            gradient={'0':'Navy', '0.25':'Blue','0.5':'Green', '0.75':'Yellow','1': 'Red'})
            fm.add_child( hm)
        else:
            for line in lines:
                mycluster.mark(line.a)
                mycluster.mark(line.b)
                if line.midpoints:
                    for mids in (line.midpoints):
                        mycluster.mark(mids.pos, None)
      
            fg = folium.FeatureGroup(name= lgd_txt.format(txt= 'Heatmap', col='black'), show=(self.gOptions.HeatMap))
            heat_data = []
            for markname in (mycluster.pmarker):
                heat_data.append([mycluster.pmarker[markname][0], mycluster.pmarker[markname][1], mycluster.pmarker[markname][2]])
                 
            
            hm = folium.plugins.HeatMap(heat_data,max_opacity=0.8, name= 'Heatmap')
            fg.add_child(hm)
            fm.add_child( fg)
        
            
        #My to use the jquery hack to MAGIC HACK fix the Folium code to use Font Awesome! 
        # missing tag a the end on purpose
        fm.default_js.append(['hack.js', 'https://use.fontawesome.com/releases/v5.15.4/js/all.js" data-auto-replace-svg="nest'])
    
        """ *****************************
            Line Drawing Section
            *****************************
        """
        
        i = 0
        for line in lines:
          i += 1
          if (line.style == 'Life'):
             flc = flp
             aicc = 'orange'
             aici = 'child'
             bicc = 'gray'
             bici = 'cross'
             lc = '#' + line.color.to_hexa()
             da = []
             ln = line.parentofhuman
             g = ""
             markertipname = "Life of " + line.name
             markhome = 'house'
          else: 
             flc = flr
             aicc = 'green'
             aici = 'baby'
             bicc = 'green'
             lc = 'green'
             da = [5,5]
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
             markertipname = line.name +  " " + line.style + " of "+ line.parentofhuman
          fg = None
          newfg = False
          labelname = str(i) +' '+ ln
          if (len(labelname) > 25): labelname = labelname[1:25] +"..."
          gn = lgd_txt.format( txt=labelname, col= lc)
          fm_line = []
          fancyname = line.name + line.style + " of "+ line.parentofhuman
          
          bextra = "Born {}".format(line.human.birth.whenyear()) if line.human.birth and line.human.birth.when else ''
          dextra = "Died {}".format(line.human.death.whenyear()) if line.human.death and line.human.death.when else ''
          fancyname = fancyname + "<br>" + bextra +" "+ dextra if (bextra != '') or (dextra != '') else fancyname
          if line.human.photo:
                fancyname = fancyname + "<img src='{}' width='150'>".format(line.human.photo)
          difta = diftb = None
          if (line.a and line.a.lat and line.a.lon):
                # color = father/mother, born = baby, male, female
                difta = [dift(line.a.lat), dift(line.a.lon)]
                if self.gOptions.MarksOn:
                    if self.gOptions.BornMark:
                        mk = folium.features.Marker(difta,tooltip=markertipname , popup=fancyname, opacity=.5, icon=folium.Icon(color=aicc,icon=aici, prefix='fa' ))
                        if SortByLast:
                            fg = self.getFeatureGroup(line.human.surname, line.prof)
                        if SortByPerson:
                            fg = self.getFeatureGroup(line.parentofhuman, line.prof)
                        if (not fg):
                            fg = folium.FeatureGroup(name= gn, show=False)
                            newfg = True
                        fg.add_child(mk)
                # 'tombstone' or  'cross'
          if (line.b and line.b.lat and line.b.lon):
                diftb = [dift(line.b.lat), dift(line.b.lon)]
                if self.gOptions.MarksOn:
                    mk = folium.features.Marker(diftb,tooltip =markertipname , popup=fancyname, opacity=.5,icon=folium.Icon(color=bicc,icon=bici, prefix='fa', extraClasses = 'fas'))
                    if SortByLast:
                            fg = self.getFeatureGroup(line.human.surname, line.prof)
                    if SortByPerson:
                            fg = self.getFeatureGroup(line.parentofhuman, line.prof)
                        
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
            lwidth = max(int(self.max_line_weight/math.exp(0.5*line.prof)), 2)
            if self.gOptions.UseAntPath:
                if line.style == 'Life':
                    pl = folium.plugins.AntPath(fm_line, weight=lwidth, opacity=.7, tooltip=ln, popup=fancyname, color=lcolor, lineJoin='arcs')
                else:
                    pl = folium.features.PolyLine(fm_line, color=lcolor, weight=lwidth, opacity=1, tooltip=ln, popup=fancyname, dash_array = da, lineJoin='arcs' )
            else:
                pl = folium.features.PolyLine(fm_line, color=lcolor, weight=lwidth, opacity=1, tooltip=ln,  popup=fancyname, dash_array = da, lineJoin='arcs')
            if (pl):
              if SortByLast:
                   fg = self.getFeatureGroup(line.human.surname, line.prof)
              if SortByPerson:
                   fg = self.getFeatureGroup(line.parentofhuman, line.prof)
                        
              
              if (not fg):
                  fg = folium.FeatureGroup(name= gn, show=False)
                  newfg = True
              fg.add_child(pl)
          
          print(f"Name:{line.human.name:30};\tParent:{line.parentofhuman:30};\tStyle:{line.style};\tfrom:{line.a}; to:{line.b}")

          # Did we just create a feature group for this person?
          if newfg:
            fg.layer_name = fg.layer_name + " ({})".format(len(fm_line) + 1 if diftb else 0 + 1 if diftb else 0)     
            fm.add_child(fg)

        for fgn in sorted(self.fglastname.keys(), key=lambda x: self.fglastname[x][2], reverse = False ):
            # print ("]]{} : {}".format(fgn, fglastname[fgn][1]))          
            self.fglastname[fgn][0].layer_name = "{} : {}".format(fgn, self.fglastname[fgn][1])          
            fm.add_child(self.fglastname[fgn][0])
        folium.map.LayerControl('topleft', collapsed= False).add_to(fm)

        if main and main.birth and main.birth.pos and main.birth.pos.lat:         
            #TODO Look at MarkerClusters           
            if self.gOptions.MarkStarOn:
                folium.Marker([dift(main.birth.pos.lat), dift(main.birth.pos.lon)], tooltip = main.name, opacity=0.5, icon=folium.Icon(color='lightred',icon='star', prefix='fa', iconSize = ['50%', '50%'])).add_to(fm)
        else:
            print ("No GPS locations to generate a map.")
        
        # TODO Add a legend
        # FloatImage(image_file, bottom=0, left=86).add_to(fm)
        if SortByLast:
               print ("Number of FG lastName: {}".format(len(self.fglastname)))
            
        self.Done()
        webbrowser.open(self.file_name, new = 0, autoraise = True)
        return
