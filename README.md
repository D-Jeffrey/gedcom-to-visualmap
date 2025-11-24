[![GitHub Activity][releases-shield]][releases]
[![License][license-shield]]([license])
![Project Maintenance][maintenance-shield]
[![GitHub Activity][commits-shield]][commits]


# gedcom-to-visualmap

Read a GEDCOM file and translate the locations into GPS addresses.
- Produces different KML map types which should have timelines and movements around the earth.
- Produces HTML file which is interactive.
- Produces Summary stats on you places and locations (Geocoding addresses to 95%+)
- Allow you to see the family linage - ascendants and descendants.

In collaboration with [colin0brass](https://github.com/colin0brass). This contains two interfaces: command-line and GUI (GUI is tested on Windows MacOS and and Windows Sub-system for Linux). Orginally forked from [https://github.com/lmallez/gedcom-to-map]

## Who Should Try This
- Genealogy hobbyists wanting spatial context for life events.
- Historians and researchers mapping migrations and demographic clusters.
- Developers and data scientists who want GEDCOM-derived geodata for further analysis or visualization.

# Quick Start Tips
- Use the GUI to pick your GEDCOM, choose output type, then click Load to parse and resolve places.
- Double-left-click a person in the GUI list to set the starting person for traces and timelines.
- Edit `geo_cache.csv` to correct or refine geocoding, then save and re-run to apply fixes.
- Export KML to inspect results in Google Earth Pro, Google MyMaps, or ArcGIS Earth.
- Generate tables and CSV files listing People, places and lifelines.

# How to Run

Assuming you have Python installed (otherwise see https://github.com/PackeTsar/Install-Python#readme)

1. Clone the repository: (in powershell or bash)
```
git clone https://github.com/D-Jeffrey/gedcom-to-visualmap
cd gedcom-to-visualmap
```
-- or --

Alternatively download the zip package of the latest [release](https://github.com/D-Jeffrey/gedcom-to-visualmap/releases) and unzip the package into a directory (such as gedcom-to-visualmap)
2. Create virtual env for Python3 to run this

for Windows (powershell)
```
python3 -m venv venv
venv\bin\activate
```
-- or --
for Linux and Mac
```
python3 -m venv venv
source venv/bin/activate
```
3. Install dependencies:
```
python3 -m venv venv
source myvenv/bin/activate
pip install -r requirements.txt
```

4. Run the GUI interface:
```
cd gedcom-to-map
python3 gv.py 
```
--or--

Start the command line  (Not recommended as there are so many options)
```
cd gedcom-to-map
python3 gedcom-to-map.py /users/darren/documents/myhertitagetree.ged myTree -main "@I500003@" 
```

5. Later on you can update your code by using the command:
```
cd gedcom-to-map
git pull https://github.com/D-Jeffrey/gedcom-to-visualmap
pip install -r requirements.txt
```

## GUI
![img](docs/img/GUI-python_2025-11.gif)

To use the GUI version, click on `Input File` and select your .ged file.
Set your options in the GUI interface  
- Type in the Output file name (Default is same name, different extension in same directory as the Input file).
- Result type drives the options mixture

Once you have selected your options, 
- click the `Load` button and it will start to load the GED and then resolve the addresses.
- `Draw Update` button is a 'Save' button.  For HTML it will try and open the file with your web browser automatically.  For KML, it will save the file so you can load it onto a map.  (See below)
- `Open GPS` button will open the CSV file in Excel if you have it... (I'm thinking that does not work on a Mac)  Make sure you close it before running again, or it may not be able to update the CSV file.
- `Stop` will allow you to abort the Load/ Resolving of addresses without killing the GUI, allowing you to pick different options.
- Using the `double-left-click` to select the starting person in (Star)

- `Geo Table` open the CSV file for the resolved and cached names.  You can edit the fields and change the `alt` column so substatute in a new name for alternate look up.
TODO Needs more description.
- `Trace` Create a list of the individuals from the starting person.  See below
- `Browser` Open the web browser using the last current output html file
- Use the `right-click` on the list of people to bring up some known **details** and how it was geocoded

The Age column can be very useful for testing to see if the parents are of the proper age, showing when thheir age when their child was born.
![img](docs/img/age_2025-08.png)

- When the people are loaded you can sort by the various columns by clicking on the column.  When the list of people is selected for display it is relative to this starting person, unless you select the `Map all people`
- You can resize the window (larger or maximized) to see more details about the people.
- When displaying people on the HTML map, you can choose to list them as 
  - single people, 
  - as a group by the last name 
  - or by their parents

### GUI Issues
Unix may not like the Font size of 8.  If you get errors, then change the font size in const.py  The interface needs a smaller font or it will throw 
off all the layout measurements.  (Need to add math to get actual font size)


## Addresses and Alternative Address File
The `geo_cache.csv` is created automatically as a function of looking up the addresses by loading the GEDCOM file. You can using an _alternative address file_ to in addition to the `.ged` by creating a file with the `.csv` extension in the same directory.  So if the GEDCOM file was `my_family.ged`, then the alternate address file would be `my_family.csv` in the same directory.  The structure of the CSV file is the same as output from the SUM '_cached.csv' file (as [example](samples/shakespeare_cache.csv)).

Make sure that you do not have an CSV files 'locked' open by Excel or other application so they can not be read or updated (close those applications instances).

# Results
## KML Example revised
### Google Earth Online
(Uncheck FlyTo Balloon)
![img](docs/img/Google_earth_2025-03.png)
* KML Output  : [samples/input.kml](samples/input.kml) using 'native' only
### Google Earth Pro
(Check FlyTo Balloon)
![img](docs/img/googleearth_2025-09-01.jpg)
* KML Output  : [samples/royal92.kml](samples/royal92.kml) all people, birth, death

### ArcGIS Earth
(Uncheck FlyTo Balloon)
![img](docs/img/ArcGISEarth_2025-03-input.jpg)

Go to https://www.google.ca/maps/about/mymaps  
- Click on `Getting Started`
- Click `Create a New Map`
- On `Untitled map` click on the `Import` options and open your KML file
#### Note this does not work in Google Earth as the lines don't appear, not sure about other KML viewers.

The *`geo_cache.csv`* file can be edited to feed back in new Addresses for GeoCoding.  Just edit or clear any column except the *Name* column to have it re-lookup that address.  Especially useful if you want to make a bad or old-style name resolve to a new name/location.
If you do not have GPS location in your GEDCOM file, then use -born or -born -death so have it use the place where the person was born and/or died.

* Cache : [samples/geo_cache](samples/geo_cache.csv)



## Examples using Royal92.ged 
###  HTML
Royal92.ged  No ordering 
![img](docs/img/2025-11-15.png) 

Royal92.ged Last Name
![img](docs/img/2025-11-21.png)

Royal92.ged Full Name 
![img](docs/img/2025-11-46.png) 

###  KML
![img](docs/img/2025-11-16.png) 

###  KML2
![img](docs/img/2025-11-19.png)

## Trace button
Load your GED file.  Make sure that you have set an output file (click on the `Output File` label for quick access to the Save As).  Make sure you have selecte HTML mode (not KML).  Double click on a person to trace from that person back.  Then all the traced individuals will light up as green (with the starting person in grey).  Then click on the Trace button.  
This will produce a text file and the name will be shown be show in the Information section of the top left.  (Same directory as the output but with a different name '.trace.txt. instead of .HTML).  If you open this in Excel, you can reformat the last columns and then use that to identify the number of generations. 

See [same trace output](samples/shakespeare.trace.txt)

## Heatmap Timeline
![img](docs/img/Heatmap_2025-03.gif)

## Cluster Markers
If you turn off the Markers in HTML mode, then it will turn on Clustered markers.  Trying that out and seeing if this become a better way to do markers.  This is W, working towards leverage this feature more consistantly.
![img](docs/img/markers-2025-03.png)

# Parameter and settings
## Options Values

You can set what CSV or KML viewer you want to option by access the menu Options -> Setup.  Within there you can set the command lines.  using `$n` to use as a placeholder for the filename the applicaiton will be used as part of the command like
#### KML Editor options :
  - `googleearth.exe $n` 
  - `"C:\Program Files\ArcGIS\Earth\ArcGISEarth.exe" "$n"`
  - `$n`
#### CSV Editor or Trace Table Editor options :
  - `numbers $n` 
  - `$n`
  - `soffice $n`
  - `notepad $n`

KML2 is an improved version of KML

## Summary
SUM is a summary CSV files and plot of birth vs death related to continent and country

#### Country Heatmap for Shakespeare
![img](samples/shakespeare_countries_heatmap.png)
#### Country Heatmap for Royal92
![img](samples/royal92_countries_heatmap.png)

## Running on Linux
- [See Running on WSL](docs/running-on-wsl.md)

## Other Ideas
- [See Exploring Family trees](docs/otherlearnings.md)

## Comparing MyHeritage PedigreeMap Heatmap and GedcomVisual Heatmap
I noticed that the MyHeritage added a heatmap a year or so ago and it has a lot of overlap with the GedcomVisual heatmap.

![img](docs/img/MyHeritage-2023-10-09.png) and ![img](docs/img/gedcomVisual-2023-10-09.png)


# Output to HTML using folium

 ### Usage
 
 *Deprecated functionality*
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
It produces a HTML file which is interactive and shows relationships betwenn childern and parents and where people live 
over the years.  It includes a heatmap to show busier places.  If you zoom in enough, you can see the different markers 
which are overlayed on each other.



```
cd samples
python3 ..\gedcom-to-map\gedcom-to-map.py input.ged output  -format HTML -groupby 1
python3 ..\gedcom-to-map\gedcom-to-map.py input.ged output -main "@I0000@" -format KML

```


# 
# Built using
| Project | Githib Repo | Documentation | Purpose
| --- | --- | --- | --- | 
| wxPython |  https://github.com/wxWidgets/Phoenix  | https://wxpython.org/ | Toolkit and provides access to the user interface
| ged4py | https://github.com/andy-z/ged4py  | https://simplekml.readthedocs.io/en/latest/ | Implementation of the GEDCOM parser in Python
| simplekml | https://github.com/eisoldt/simplekml | https://app.readthedocs.org/projects/simplekml/ | created to generate kml (or kmz)
| geopy | https://github.com/geopy/geopy |https://geopy.readthedocs.io/en/latest/#geocoders |
| folium | https://github.com/python-visualization/folium | https://python-visualization.github.io/folium/latest/|
| xyzservices | https://github.com/geopandas/xyzservices | https://xyzservices.readthedocs.io/en/stable/index.html |
| nnjeim/world | https://github.com/nnjeim/world | https://github.com/nnjeim/world?tab=readme-ov-file#available-actions 
| pyyaml | https://github.com/yaml/pyyaml | | A full-featured YAML processing framework for Python
| rapidfuzz | https://github.com/rapidfuzz/RapidFuzz | | Rapid fuzzy string matching in Python and C++ using the Levenshtein Distance
| pycountry | https://github.com/pycountry/pycountry
| pycountry-convert | https://github.com/jefftune/pycountry-convert | | pycountry-convert is a Python module for TUNE Multiverse Libraries.
| pandas | https://github.com/pandas-dev/pandas | | A Powerful Python Data Analysis Toolkit
| seaborn | https://github.com/mwaskom/seaborn | https://seaborn.pydata.org/ | Seaborn is a Python visualization library based on matplotlib. 
| matplotlib | https://github.com/matplotlib/matplotlib | https://matplotlib.org/ |Matplotlib is a comprehensive library for creating static, animated, and interactive visualizations in Python.

### Other sample GED files:
- https://github.com/findmypast/gedcom-samples

## TODO
- Add a tree hierarchy selector to enable people as groups and add expand/collapse to navigation
- option to remove 'lines' to not core points (such as RESI or other)
- Sort the Last Name by the highest number of people first or by distance from star
- create a marker animation by year (in time steps)
- in Person dialog show something for people still alive (vs None or Unknown)
- add histical timeline and reference events in the area from https://www.vizgr.org/historical-events/ & https://github.com/dh3968mlq/hdtimelines/
- need to determine how do deal with very large HTML files.  Could use a limit of the number of people included in the selection
- Improve the KML version of the maps by grouping and improving the track of a person.  Add description bits to people in the KML version
- Improve marker clusters to have the proper icon
- Move some configuration to YAML to preserve customization over releases
- Major refactoring to make this *real* Python code

## Issues
- Linux does not save FileHistory

### GUI
- Need to separate the Load and GPS resolve steps (currently reloads after 30 seconds of looking up values)

## Releases
### V0.2.8.0
- Major regorganation of the GUI code base
### v0.2.7.1
- Better feedback during load and geocode
- regrouped and fix GUI layout issues
- save addressbook perodically during long load and lookup
- mid life events are in HTML and KML again
### v0.2.7.0.3
- more bug fixes
- Regrouping of options based on Output type
- Default country text input
- Update and stop buttons fixed
- Different font config for defferent platforms, adjustable from the menu
### v0.2.7.0.1
- Bug fixes for the quick related of 0.2.7.  Lots of fixes with the assistance of @colin0brass
### v0.2.7.0
- MAJOR UPGRADE/REFACTOR
- This is a major rework of many components to merge in new address lookup and gedcom reading approch from @colin0brass
- New KML (2) a new approach to rendering the KML output using @colin0brass approach
- Added in data summaries by @colin0brass
- There continue to be a lot of bugs after the retrofit.  It will have bugs, wait for next release
### v0.2.6.9
- improved options stats
- refactor Pos with LatLon
- refactor Human into Person and humans into people
- preparing for replacement modules from @colin0brass
### v0.2.6.8
- Enriched Balloon in KML with proper linked to children and parents
- Add folders to KML
- Add children to Person Dialog
- Add age checking (problems flag in yellow for the lineage people)
- Dynamic KML/HTML options
- Refactored long standing inconsistency related to drawing the first person in KML
### v0.2.6.7
- Added FlyTo, Line Weigth & Trace cmdline to configuration
- Input/Output as Buttons
- Updates Samples output
### v0.2.6.6.x
- Working on KML functions and reworking GUI.  
- Fix HTML to use markers properly, optional timeline in KML
- Fixed issue when loading GED with missing children records 
### v0.2.6.4.1
- Fixed balloonflyto and added children to KML
### v0.2.6.4
- Fixed Logging Save settings
- Worked on KML to add FlyTo and improve features and labels
- working to refactor and enrich the kml results
- ballonflyto does not work yet
### v0.2.6.3
- Add images for Bourbon sample, bug fixes for f{}
### v0.2.6.2
- @colin0brass - Fixes to make it work properly on a Mac as well as a number of other pure programmer errors identified
- Improve Person Dialog (Displays picture if available)
### v0.2.6.1
- Added person attributes age
- Fixed age calc in Person dialog for parents, scroll grid on parents, click on a parent to bring up there details in a seperate window
- Improved last Name grouping on Folium maps, added soundex matching option
- Adjusted for variation in BC or negative dates
### v0.2.6.0
- New :main program gv.py
- fixed the logging level settings and reapply of log settings
- bumped folium version
- Added a dynamic Legend to replace the static pixely image
- Large refactored of FoliumExp, including - Tiles selection (move to GUI for selection), Added Cluster Markers, Additional icons for locations types, 
- Linux compatible fixing/testing
- Added color to kml markers and provide different born, death and native types
- Update Colors and centralize code for color choices
- Multiple marriage
- Load tested to 132K GEDCOM records loads in less than 5 minutes, 1600 people loads in 9 seconds.
- Person show list of all direct F/M + ancestors + years
- View only direct ancestors
- Sorts all dates include BC/B.C.
- Added a Find found to search names.
- Provides information about relation to selected person
- Added option to open program for KML (or use a http address)
- Better saving of previous options, remembers selection Main person
### v0.2.5
- Added `Trace` to trace from selected person and dump to a text file
- Help & About
- Estimating the number of addresses to resolve
- Sorting for Last Name, People and None
- Person dialog shows delta between Active and displayed person
- file selection dialog automatically opens file
- Added dynamic highlighting based on main selection for HTML
- Added Statistics menu under Actions
- Adjustable GUI Font (See const.py to set it)
### v0.2.3
- re-org the project files
### v0.2.2
- corrected imports (removed gedcom package dependacy) and requirements.txt (again)
- on Linux sample
- more pylint
- fixed sorting of people
### v0.2.1
- Added support for Windows and Mac open of CSV
- more issues with cache, the first time you run it in the new directory
- added Kennedy samples
- improved setup.py
### v0.2.0
- fixed requirements.txt
- Add highlighting of people used in the draw
- Major improvements to KML Exporting
- improved feedback loop on loading in Visual
- Fixed issue with selection (broken in 0.1.2), fix issue with caching
- Added Legend (Needs work)
### v0.1.x
- New details dialog about people, fixed issues with GPS lookup, options 
- Folded in GUI bugs from @rajeeshp & @frankbracq
- Adjusted GUI and saving of cache file location, Fixed issue if the cache file

[license-shield]: https://img.shields.io/github/license/D-Jeffrey/gedcom-to-visualmap.svg?style=for-the-badge
[license]: LICENSE
[commits]: https://github.com/D-Jeffrey/gedcom-to-visualmap/commits
[commits-shield]: https://img.shields.io/github/commit-activity/y/D-Jeffrey/gedcom-to-visualmap?style=for-the-badge
[maintenance-shield]: https://img.shields.io/maintenance/yes/2025.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/v/release/D-Jeffrey/gedcom-to-visualmap.svg?style=for-the-badge
[releases]: https://github.com/crowbarz/D-Jeffrey/gedcom-to-visualmap/releases
