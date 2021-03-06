# gedcom-to-visualmap

Orginally forked from [https://github.com/lmallez/gedcom-to-map]

Read a GEDCOM file and translate the locations into GPS addresses.
The produces different KML map types which should timelines and movements around the earth.
The produces HTML file which is interactive..

This contains two interfaces: command-line and GUI (only tested on Windows)

# How to Run

1. Clone the repository:
```
$ git clone git@github.com:D-Jeffrey/gedcom-to-visualmap
$ cd gedcom-to-visualmap
```

2. Install dependencies:
```
$ pip install -r requirements.txt
```

3. Start the command line
```
cd gedcom-to-map
python gedcom-to-map.py myhertitagetree.ged myTree -main "@I500003@" 
```
3b or Run the GUI interface:
```
cd gedcom-to-map
python gedcomVisualGUI.py 
```

GUI
![img](samples/pythonw3.9_2022-02-20a.png)


Output to HTML using folium

 ### Usage
 
 ```
 usage: gedcom-to-map.py [-h] [-main MAIN] [-format {HTML,KML}] [-max_missing MAX_MISSING] [-max_line_weight MAX_LINE_WEIGHT] [-everyone] [-gpscache] [-nogps] [-nomarker] [-nobornmarker] [-noheatmap]
                        [-maptiletype {1,2,3,4,5,6,7}] [-nomarkstar] [-groupby {0,1,2}] [-antpath] [-heattime] [-heatstep HEATSTEP] [-homemarker] [-born] [-death]
                        input_file output_file

convert gedcom to kml file and lookup GPS addresses

positional arguments:
  input_file            GEDCOM file, usually ends at .ged
  output_file           results file, extension will be added if none is given

optional arguments:
  -h, --help            show this help message and exit
  -main MAIN            if this is missing it will use the first person in the GEDCOM file
  -format {HTML,KML}    type of output result for map format
  -max_missing MAX_MISSING
                        maximum generation missing (0 = no limit)
  -max_line_weight MAX_LINE_WEIGHT
                        Line maximum weight
  -everyone             Plot everyone in your tree

Geocoding:
  -gpscache             Use the GPS cache only
  -nogps                Do not lookup places using geocode to determine GPS, use built in GPS values

Folium Map as HTML (format HTML):
  -nomarker             Turn off the markers
  -nobornmarker         Turn off the markers for born
  -noheatmap            Turn off the heat map
  -maptiletype {1,2,3,4,5,6,7}
                        Map tile styles
  -nomarkstar           Turn off the markers starting person
  -groupby {0,1,2}      1 - Family Name, 2 - Person
  -antpath              Turn on AntPath
  -heattime             Turn on heatmap timeline
  -heatstep HEATSTEP    years per heatmap group step
  -homemarker           Turn on marking homes

KML processing:
  -born                 use place born for mapping
  -death                use place born for mapping
```
It produces a HTML file which is interactive and shows relationships betwenn childern and parents and where people lived 
over the years.  It includes a heatmap to show busiey places.  If you zoom in enough you can see the different markers 
which are overlayed on each other.



```
pip install -r requirements.txt
cd samples
python ..\gedcom-to-map\gedcom-to-map.py input.ged out  -format HTML -groupby 1
python ..\gedcom-to-map\gedcom-to-map.py input.ged out -main "@I0000@" -format KML

```

* HTML Output : [samples/output.html](samples/output.html)

## KML Example revised
![img](samples/msedge_2022-01-02_12-36-33.png)
* KML Output  : [samples/output.kml](samples/output.kml)

Go to https://www.google.ca/maps/about/mymaps  and open the KML file
The *geodat-address-cache.csv* file can be edited to feed back in new Addresses for GeoCoding.  Just edit or clear any column except the *Name* column to have it re-lookup that address.  Especially useful if you want to make a bad or old style name resolve to a new name/location.
If you do not have GPS location in your GEDCOM file, then use -born or -born -death so have it use the place where the person was born and/or died.

* Cache : [samples/geodat-address-cache.csv](samples/geodat-address-cache.csv)



![img](samples/pres2020.png)
```
cd samples
python ..\gedcom-to-map\gedcom-to-map.py pres2020.ged pres2020 -main "@I1@" -format HTML -groupby 1 -nomarkstar -antpath
```
* HTML Output  : [samples/pres2020-2.html](samples/pres2020-2.html)

![img](samples/pres2020-2.png)
```
python ..\gedcom-to-map\gedcom-to-map.py pres2020.ged pres2020-2 -main "@I676@" -format HTML -groupby 1 -nomarkstar -antpath
```

* KML Output  : [samples/pres2020-2.kml](samples/pres2020-2.kml)
```
python ..\gedcom-to-map\gedcom-to-map.py pres2020.ged pres2020-2 -main "@I676@" -format KML
```


## Complex Export of MyHeritage - intereactive map
![img](samples/msedge_2022-02-02_22-33-16.gif)


