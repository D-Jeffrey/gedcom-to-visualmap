# KML Mode
KML mode has two approaches to generating KML for your GED family.  The first is Native which assuming that you have GPS positional values in your GED file.  This is done using PLAC with a _LATI and _LONG (or LATI and LONG) attributes

for example
```
2 PLAC Lyon, France
3 MAP
4 LATI N45.757814
4 LONG E4.832011
```
or
```
2 PLAC Our Lady of Calvary Cemetery, 134 Forest Street, Yarmouth, Yarmouth County, Nova Scotia, Canada
3 MAP
4 LATI 43.831944
4 LONG -66.102222
```

# Options

## KML Command Line
set the KML to open Google Earth by setting the KML value to:
```
    https://earth.google.com/
```

If you are using Esri.ArcGISEarth or Google Earth Pro installed on your computer, you can set the launch command line to be:
```
$n
```


# TODO List
- Add more details in description of people panel, ~~including age~~
- for sorting of last name in Folium fold case, remove of punction and think about soundex match option
- Add mother and father to legend
- fix missing relationship in people
- add more detail in the KML version
- build a life description for using in KML, Popup on Folium and People Panel
- Need to sort HTML by # of instances of name
- 