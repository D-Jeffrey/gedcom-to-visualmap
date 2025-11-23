import os
import sys
import time
import subprocess
import webbrowser
import shutil
import logging
from datetime import datetime
from typing import Any
import wx
from pathlib import Path

from models.Creator import Creator, LifetimeCreator, CreatorTrace, Person
from models.Creator import Creator, Person
from render.foliumExp import foliumExporter
from render.KmlExporter import KmlExporter
from render.kml import KML_Life_Lines
from render.Referenced import Referenced
from render.summary import write_places_summary, write_people_summary, write_birth_death_countries_summary, write_geocache_summary, write_alt_places_summary

from gedcom_options import gvOptions
from gedcom.gedcom import GeolocatedGedcom

from const import GLOBAL_GEO_CACHE_FILENAME, FILE_ALT_PLACE_FILENAME_SUFFIX, FILE_GEOCACHE_FILENAME_SUFFIX, GEO_CONFIG_FILENAME

_log = logging.getLogger(__name__.lower())


class VisualMapActions:
    """Panel action helpers moved out of VisualMapPanel to keep lifecycle code concise.

    Use by creating VisualMapActions(panel) and calling the methods. Methods
    reference panel attributes (gOp, background_process, id, peopleList, frame).
    """

    def __init__(self, panel: Any) -> None:
        self.panel = panel

    def LoadGEDCOM(self) -> None:
        """Trigger background parse/load (copied from original panel implementation)."""
        bp = self.panel.background_process
        gOp = self.panel.gOp
        if getattr(bp, "IsTriggered", lambda: False)():
            gOp.stopping = True
        else:
            self.panel.OnBusyStart(-1)
            time.sleep(0.1)
            gOp.set('GridView', False)
            try:
                self.panel.id.CBGridView.SetValue(False)
            except Exception:
                pass

            cachepath, _ = os.path.split(gOp.get('GEDCOMinput'))
            if gOp.get('gpsfile'):
                sourcepath, _ = os.path.split(gOp.get('gpsfile'))
            else:
                sourcepath = None
            if getattr(gOp, "lookup", None) and cachepath != sourcepath:
                try:
                    del gOp.lookup
                except Exception:
                    gOp.lookup = None
            gOp.step('Loading GEDCOM')
            bp.Trigger(1)

    def DrawGEDCOM(self) -> None:
        """Trigger background generation of output (HTML/KML/SUM)."""
        if not self.panel.gOp.get('ResultFile'):
            _log.error("Error: Not output file name set")
            self.panel.background_process.SayErrorMessage("Error: Please set the Output file name")
        else:
            self.panel.OnBusyStart(-1)
            self.panel.background_process.Trigger(2 | 4)

    def OpenCSV(self) -> None:
        """Open CSV output (delegates to runCMDfile)."""
        self.runCMDfile(self.panel.gOp.get('CSVcmdline'), self.panel.gOp.get('gpsfile'))

    def runCMDfile(self, cmdline: str, datafile: str, isHTML: bool = False) -> None:
        """Run an external command or open a file/URL according to application options."""
        orgcmdline = cmdline
        if datafile and datafile != '' and datafile is not None:
            cmdline = cmdline.replace('$n', f'{datafile}')
            try:
                if isHTML:  # Force it to run in a browser
                    _log.info('browserstart %s', cmdline)
                    webbrowser.open(datafile, new=0, autoraise=True)
                elif orgcmdline == '$n':
                    if os.name == "nt" or (hasattr(os, "startfile") and os.name == "nt"):
                        _log.info('startfile %s', datafile)
                        os.startfile(datafile)
                    elif sys_platform := getattr(__import__("sys"), "platform", "") == "darwin":
                        opener = "open"
                        _log.info('subprocess.Popen %s', datafile)
                        subprocess.Popen([opener, datafile])
                    else:
                        opener = "xdg-open"
                        if not shutil.which(opener):
                            raise EnvironmentError(f"{opener} not found. Install it or use a different method.")
                        _log.info('subprocess.Popen %s', datafile)
                        subprocess.Popen([opener, datafile])
                else:
                    if cmdline.startswith('http'):
                        _log.info('webbrowser run `%s`', cmdline)
                        webbrowser.open(cmdline, new=0, autoraise=True)
                    else:
                        if '$n' in orgcmdline:
                            _log.info('subprocess.Popen file %s', cmdline)
                            subprocess.Popen(cmdline, shell=True)
                        else:
                            _log.info('subprocess.Popen line %s ; %s', cmdline, datafile)
                            subprocess.Popen([cmdline, datafile], shell=True)
            except Exception as e:
                _log.exception("Issues in runCMDfile")
                _log.error("Failed to open file: %s", e)
        else:
            _log.error("Error: runCMDfile-unknown cmdline %s", datafile)

    def SaveTrace(self) -> None:
        """Dump a trace file describing each referenced person and optionally open it."""
        gOp = self.panel.gOp
        bp = self.panel.background_process

        if gOp.ResultFile and getattr(gOp, "Referenced", None):
            if not getattr(gOp, "lastlines", None):
                _log.error("No lastline values in SaveTrace (do draw first using HTML Mode for this to work)")
                return

            tracepath = os.path.splitext(gOp.ResultFile)[0] + ".trace.txt"
            try:
                trace = open(tracepath, "w")
            except Exception as e:
                _log.error("Could not open trace file %s for writing %s", tracepath, e)
                bp.SayErrorMessage(f"Error: Could not open trace file {tracepath} for writing {e}")
                return

            trace.write("id\tName\tYear\tWhere\tGPS\tPath\n")
            people = bp.people or {}
            for h in people:
                try:
                    if gOp.Referenced.exists(people[h].xref_id):
                        refyear, _ = people[h].refyear()
                        (location, where) = people[h].bestlocation()
                        personpath = gOp.lastlines[people[h].xref_id].path
                        trace.write(
                            f"{people[h].xref_id}\t{people[h].name}\t{refyear}\t{where}\t{location}\t" + "\t".join(personpath) + "\n"
                        )
                except Exception:
                    _log.exception("SaveTrace: writing person %r failed", h)
            trace.close()
            _log.info("Trace file saved %s", tracepath)
            withall = "with all people" if gOp.get('AllEntities') else ""
            bp.SayInfoMessage(f"Trace file {withall} saved: {tracepath}", True)
            self.runCMDfile(gOp.get('Tracecmdline'), tracepath)
        else:
            _log.error("SaveTrace: missing ResultFile or Referenced")

    def OpenBrowser(self) -> None:
        """Open the generated result in a browser or the default KML viewer."""
        gOp = self.panel.gOp
        if gOp.get('ResultType'):
            path = os.path.join(gOp.resultpath, gOp.ResultFile)
            self.runCMDfile(gOp.get('KMLcmdline'), path, True)
        else:
            self.runCMDfile('$n', getattr(__import__("const"), "KMLMAPSURL", "/"), True)

    def open_html_file(self, html_path: str) -> None:
        """Legacy helper to attempt activation/reload of a browser tab."""
        try:
            browser = webbrowser.get()
            browser_tab = browser.open_new_tab(html_path)
            time.sleep(1)
            for window in browser.windows():
                for tab in window.tabs:
                    if tab == browser_tab:
                        window.activate()
                        break
                else:
                    continue
                break
            try:
                browser_tab.reload()
            except Exception:
                pass
        except Exception:
            _log.exception("open_html_file failed")

    def doHTML(self, gOp: gvOptions, people, fullresult):
        """Generate HTML map output using folium exporter.
        
        Creates lifetime lines for all selected people and exports to HTML/folium map.
        Optionally opens result in browser if fullresult=True.
        
        Args:
            gOp: Global options containing settings and paths.
            people: Dictionary of Person objects keyed by xref_id.
            fullresult: If True, opens result in browser after generation.
        
        Returns:
            bool: True if successful, False if errors occurred.
        """
        if (not people):
            _log.error("doHTML: no people provided")
            return False
        
        _log.debug  ("Creating Lifeline (fullresult:%s)", fullresult)
        lifeline = LifetimeCreator(people, gOp.MaxMissing)    
        _log.debug  ("Creating People ")
        creator = lifeline.create(gOp.Main)    
        if gOp.Main not in people:
            _log.error ("Could not find your starting person: %s", gOp.Main)
            try:
                gOp.stopstep('Error could not find first person')
            except Exception:
                pass
            return False
        
        gOp.setMainPerson(people[gOp.Main])
        if gOp.AllEntities:
            gOp.step('Creating life line for everyone')
            lifeline.createothers(creator)
            _log.info ("Total of %i people & events.", len(creator))   
        gOp.totalpeople = len(creator)

        try:
            foliumExporter(gOp).export(people[gOp.Main], creator, fullresult)
        except Exception:
            _log.exception("doHTML: folium export failed")
            return False
        
        if (fullresult):
            result_path = Path(gOp.resultpath) / gOp.ResultFile
            result_path = result_path.resolve()
            if result_path.exists():
                url = result_path.as_uri()
                opened = webbrowser.open(url, new=0, autoraise=True)
                if not opened:
                    # platform fallbacks
                    if sys.platform == "darwin":
                        subprocess.run(["open", str(result_path)])
                    elif os.name == "posix":
                        subprocess.run(["xdg-open", str(result_path)])
                    elif os.name == "nt":
                        os.startfile(str(result_path))
            else:
                _log.error("Result file not found: %s", result_path)
                return False
        return True

    def Geoheatmap(self, gOp : gvOptions):
        """Parse GEDCOM, geocode, and generate HTML heatmap with browser open.
        
        Convenience wrapper that calls ParseAndGPS followed by doHTML with fullresult=True.
        
        Args:
            gOp: Global options containing GEDCOM path and settings.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        people = self.ParseAndGPS(gOp)
        if not people:
            _log.error("Geoheatmap: ParseAndGPS returned no people")
            return False
        return self.doHTML(gOp, people, True)

    def doKML(self, gOp: gvOptions, people: list[Person]) -> None:
        """Generate KML output for the supplied people/options (moved from gedcomvisual.doKML)."""
        if not people:
            return
        kmlInstance = None

        placeTypes = []
        if getattr(gOp, "BornMark", False):
            placeTypes.append(["birth", "(b)", "birth"])
        if getattr(gOp, "DieMark", False):
            placeTypes.append(["death", "(d)", "death"])

        if not placeTypes:
            try:
                gOp.stopstep("Error select at least Birth or Death markers to map")
            except Exception:
                pass
            _log.error("Neither birth or death marker is selected")

        for (key, nametag, placeType) in placeTypes:
            lifeline = Creator(people, getattr(gOp, "MaxMissing", 0), gpstype=key)
            creator = lifeline.create(getattr(gOp, "Main", None))
            if getattr(gOp, "AllEntities", False):
                lifeline.createothers(creator)
                _log.info("Total of %i people.", len(creator))

            if getattr(gOp, "Main", None) not in people:
                _log.error("Could not find your starting person: %s", getattr(gOp, "Main", None))
                try:
                    gOp.stopstep("Error could not find first person")
                except Exception:
                    pass
                return

            try:
                gOp.setMainPerson(people[gOp.Main])
            except Exception:
                pass

            if not kmlInstance:
                kmlInstance = KmlExporter(gOp)

            try:
                kmlInstance.export(people[gOp.Main].latlon, creator, nametag, placeType)
            except Exception:
                _log.exception("doKML: export failed for %s", nametag)

        bg = getattr(gOp, "BackgroundProcess", None)
        if kmlInstance:
            try:
                kmlInstance.Done()
            except Exception:
                _log.debug("doKML: KmlExporter.Done failed")
            cmdfile = os.path.join(getattr(gOp, "resultpath", ""), getattr(gOp, "ResultFile", ""))
            if bg:
                bg.SayInfoMessage(f"KML output to : {cmdfile}")
            if getattr(gOp, "KMLcmdline", None):
                # use the actions' runCMDfile implementation
                try:
                    self.runCMDfile(gOp.KMLcmdline, cmdfile)
                except Exception:
                    _log.exception("doKML: failed to run KMLcmdline")
            else:
                _log.error("Use Options -> Options Setup to define a command line to run")
        else:
            _log.error("No KML output created")
            if bg:
                bg.SayInfoMessage("No KML output created - No data selected to map")

    def doKML2(self, gOp: gvOptions, people: list[Person]) -> None:
        """Create KML (legacy / alternate exporter) and open it via configured command.

        Defensive: checks gOp.lookup/result paths, imports exporter with fallback,
        catches exceptions and uses self.runCMDfile to open results.
        
        Args:
            gOp: Global options with lookup (GeolocatedGedcom) and output paths.
            people: List of Person objects (unused by this exporter).
        """
        if (not gOp.lookup):
            _log.error("doKML2: GeolocatedGedcom is not processed")
            return
        resultFile = os.path.join(gOp.resultpath, gOp.ResultFile)

        try:
            kml_life_lines = KML_Life_Lines(gedcom=gOp.lookup, kml_file=str(resultFile),
                                                connect_parents=True, save=True)
        except Exception:
            _log.exception("doKML2: KML_Life_Lines creation/export failed")
            bg = getattr(gOp, "BackgroundProcess", None)
            if bg:
                try:
                    bg.SayInfoMessage("KML(2) generation failed")
                except Exception:
                    pass
            return
        
        bg = getattr(gOp, "BackgroundProcess", None)
        if kml_life_lines:
            if bg:
                try:
                    bg.SayInfoMessage(f"KML(2) output to : {resultFile}")
                except Exception:
                    pass
            if gOp.KMLcmdline:
                try:
                    self.runCMDfile(gOp.KMLcmdline, resultFile)
                except Exception:
                    _log.exception("doKML2: failed to open result via runCMDfile")
            else:
                _log.error("Use Options -> Options Setup to define a command line to run")
        else:
            _log.error("No KML output created")
            if bg:
                try:
                    bg.SayInfoMessage(f"No KML output created - No data selected to map")
                except Exception:
                    pass

    def doSUM(self, gOp: gvOptions) -> None:
        """Generate various summary files (places, people, countries, geocache, alt places).

        Writes outputs into gOp.resultpath and optionally opens them using the configured
        command line (uses self.runCMDfile). Guards missing data and logs progress.
        """
        base_file_name = Path(getattr(gOp, "GEDCOMinput", "")).resolve().stem
        output_folder = Path(getattr(gOp, "resultpath", ".")).resolve()
        my_gedcom = getattr(gOp, "lookup", None)
        bg = getattr(gOp, "BackgroundProcess", None)

        if my_gedcom is None:
            _log.error("doSUM: geolocated GEDCOM (gOp.lookup) is not available")
            if bg:
                try:
                    bg.SayErrorMessage("doSUM: geocoded GEDCOM data not available")
                except Exception:
                    pass
            return

        # only attempt to auto-open when the panel/actions exist
        panel_actions = self

        if getattr(gOp, "SummaryPlaces", False):
            places_summary_file = (output_folder / f"{base_file_name}_places.csv").resolve()
            _log.info("Writing places summary to %s", places_summary_file)
            write_places_summary(my_gedcom.address_book, str(places_summary_file))
            if places_summary_file.exists():
                if bg:
                    bg.SayInfoMessage(f"Places Summary: {places_summary_file}")
                if getattr(gOp, "SummaryOpen", False):
                    panel_actions.runCMDfile("$n", str(places_summary_file))

        if getattr(gOp, "SummaryPeople", False):
            people_summary_file = (output_folder / f"{base_file_name}_people.csv").resolve()
            _log.info("Writing people summary to %s", people_summary_file)
            write_people_summary(my_gedcom.people, str(people_summary_file))
            if people_summary_file.exists():
                if bg:
                    bg.SayInfoMessage(f"People Summary: {people_summary_file}")
                if getattr(gOp, "SummaryOpen", False):
                    panel_actions.runCMDfile("$n", str(people_summary_file))

        if getattr(gOp, "SummaryCountries", False) or getattr(gOp, "SummaryCountriesGrid", False):
            countries_summary_file = (output_folder / f"{base_file_name}_countries.csv").resolve()
            _log.info("Writing countries summary to %s", countries_summary_file)
            img_file = write_birth_death_countries_summary(my_gedcom.people, str(countries_summary_file), base_file_name)
            if getattr(gOp, "SummaryCountries", False) and countries_summary_file.exists():
                if bg:
                    bg.SayInfoMessage(f"Countries summary: {countries_summary_file}")
                if getattr(gOp, "SummaryOpen", False):
                    panel_actions.runCMDfile("$n", str(countries_summary_file))
            if getattr(gOp, "SummaryCountriesGrid", False) and img_file:
                if bg:
                    bg.SayInfoMessage(f"Countries summary Graph: {img_file}")
                if getattr(gOp, "SummaryOpen", False):
                    panel_actions.runCMDfile("$n", str(img_file))

        if getattr(gOp, "SummaryGeocode", False):
            per_file_cache = (output_folder / f"{base_file_name}{FILE_GEOCACHE_FILENAME_SUFFIX}").resolve()
            _log.info("Writing geo cache to %s", per_file_cache)
            write_geocache_summary(my_gedcom.address_book, str(per_file_cache))
            if per_file_cache.exists():
                if bg:
                    bg.SayInfoMessage(f"Geo cache: {per_file_cache}")
                if getattr(gOp, "SummaryOpen", False):
                    panel_actions.runCMDfile("$n", str(per_file_cache))

        if getattr(gOp, "SummaryAltPlaces", False):
            alt_places_summary_file = (output_folder / f"{base_file_name}_alt_places.csv").resolve()
            _log.info("Writing alternative places summary to %s", alt_places_summary_file)
            write_alt_places_summary(my_gedcom.address_book, str(alt_places_summary_file))
            if alt_places_summary_file.exists():
                if bg:
                    bg.SayInfoMessage(f"Alternative places summary: {alt_places_summary_file}")
                if getattr(gOp, "SummaryOpen", False):
                    panel_actions.runCMDfile("$n", str(alt_places_summary_file))

    def ParseAndGPS(self, gOp: gvOptions, stage: int = 0 ):
        """
        ParseAndGPS: Parse the GEDCOM file and optionally resolve addresses to GPS coordinates.
            - Resolve paths and filenames.
            - Parse and correct GEDCOM file.
            - Geocode places and cache results.
            - Optionally use alternative place/address files.
            - Save updated cache.
        """
        people = None
        _log.info ("Starting parsing of GEDCOM : %s (stage: %d)", gOp.GEDCOMinput, stage)
        if (stage == 0 or stage == 1):
            if gOp.people:
                del gOp.people
                gOp.people = None
            gOp.newload = True
            if hasattr(gOp, "UpdateBackgroundEvent") and hasattr(gOp.UpdateBackgroundEvent, "updategrid"):
                gOp.UpdateBackgroundEvent.updategrid = True

        if (stage == 1):
                if gOp.lookup:
                    del gOp.lookup
                _log.info ("Starting Address to GPS resolution")
                input_path = Path(gOp.GEDCOMinput)
                if not input_path.is_absolute():
                    input_path = (Path.cwd() / input_path).resolve()
                base_file_name = input_path.stem
                
                cachefile = input_path.parent / GLOBAL_GEO_CACHE_FILENAME
                gOp.gpsfile = cachefile
                alt_place_file_path = input_path.parent / f"{base_file_name}{FILE_ALT_PLACE_FILENAME_SUFFIX}"
                file_geo_cache_path = input_path.parent / f"{base_file_name}{FILE_GEOCACHE_FILENAME_SUFFIX}"
                geo_config_path = Path(__file__).parent.resolve() / GEO_CONFIG_FILENAME
                defaultCountry = gOp.get('defaultCountry') or None
                gOp.lookup = GeolocatedGedcom(
                    gedcom_file=input_path.resolve(), 
                    location_cache_file=cachefile,
                    default_country=defaultCountry,
                    always_geocode=gOp.UseGPS,
                    use_alt_places = not gOp.skip_file_alt_places,
                    alt_place_file_path=alt_place_file_path if not gOp.skip_file_alt_places else None,
                    gOp=gOp
                )
                _log.info ("Completed Geocode")
                gOp.lookup.save_location_cache()
                gOp.people = gOp.lookup.people
                _log.info ("Completed resolves")
                people = gOp.people
        
        if people and (not gOp.Main or not gOp.Main in list(people.keys())):
                gOp.set('Main', list(people.keys())[0])
                _log.info ("Using starting person: %s (%s)", people[gOp.Main].name, gOp.Main)
        
        return people

    def gedcom_to_map(self, gOp: gvOptions):
        """Parse GEDCOM, geocode, and generate KML output.
        
        Convenience wrapper that parses/geocodes via ParseAndGPS then generates KML.
        
        Args:
            gOp: Global options containing GEDCOM path and output settings.
        """
        people = self.ParseAndGPS(gOp)
        if not people:
            _log.error("gedcom_to_map: ParseAndGPS returned no people")
            return
        panel_actions = getattr(getattr(gOp, "panel", None), "actions", None)
        if panel_actions:
            panel_actions.doKML(gOp, people)
        else:
            _log.error("gedcom_to_map: panel actions not available")

    def doTrace(self, gOp: gvOptions):
        """
        Trace and collect referenced people in the genealogical data starting from a main person.
        
        This function initializes the tracing process by finding all related people connected
        to a specified starting person (gOp.Main) and stores their references along with their
        relationship paths.
        
        Args:
            gOp (gvOptions): Options object containing:
                - people (dict): Dictionary of all people in the genealogical data
                - Main (str): The xref_id of the starting person for the trace
                - Referenced (Referenced): Set to store all found people references
                - totalpeople (int): Counter for total people processed
        
        Returns:
            int: Total count of people found in trace, or 0 if error.
        
        Raises:
            Logs errors if:
                - No people data is available
                - The specified starting person (gOp.Main) is not found in the people data
        
        Side Effects:
            - Initializes gOp.Referenced as an empty Referenced set
            - Populates gOp.Referenced with xref_ids and their relationship paths
            - Logs the total count of people found in the trace
        """
        
        gOp.Referenced = Referenced()
        gOp.totalpeople = 0
        
        if not gOp.people:
            _log.error ("Trace:References no people.")
            return 0
        people = gOp.people
        if gOp.Main not in people:
            _log.error  ("Trace:Could not find your starting person: %s", gOp.Main)
            return 0
        gOp.Referenced.add(gOp.Main)
        lifeline = CreatorTrace(people)

        creator = lifeline.create(gOp.Main)

        _log.info  ("Trace:Total of %i people.", len(creator)) 
        if  creator:
            for c in creator:
                gOp.Referenced.add(c.person.xref_id,tag=c.path)
        
        gOp.totalpeople = len(creator) if creator else 0
        return gOp.totalpeople

    # Trace from the main person to this ID
    def doTraceTo(self, gOp: gvOptions, ToID : Person):
        """Trace lineage path from main person to specified person.
        
        Builds a list of ancestors connecting gOp.mainPerson to ToID by following
        the relationship tags stored in gOp.Referenced. Calls doTrace() first if
        Referenced is not yet populated.
        
        Args:
            gOp: Global options with mainPerson, people dict, and Referenced set.
            ToID: Target Person to trace lineage to.
        
        Returns:
            list: List of tuples (relationship, name, birth_year, xref_id) forming
                  the ancestry path from main person to ToID. Returns list with
                  single "NotDirect" entry if no relationship exists.
        """
        if not gOp.Referenced:
            self.doTrace(gOp)
        
        if not getattr(gOp, "mainPerson", None):
            _log.error("doTraceTo: gOp.mainPerson not set")
            return []
        
        people = gOp.people
        heritage = []
        heritage = [("", gOp.mainPerson.name, gOp.mainPerson.refyear()[0], gOp.mainPerson.xref_id)]
        if gOp.Referenced.exists(ToID.xref_id):
            personRelated = gOp.Referenced.gettag(ToID.xref_id)
            personTrace = gOp.mainPerson
            if personRelated:    
                for r in personRelated:
                    if r == "F":
                        try:
                            personTrace = people[personTrace.father]
                        except KeyError:
                            _log.error("doTraceTo: father %s not in people dict", personTrace.father)
                            break
                        tag = "Father"
                    elif r == "M":
                        try:
                            personTrace = people[personTrace.mother]
                        except KeyError:
                            _log.error("doTraceTo: mother %s not in people dict", personTrace.mother)
                            break
                        tag = "Mother"
                    else:
                        _log.error("doTrace - neither Father or Mother, how did we get here?")
                        tag = "?????"
                    heritage.append((f"[{tag}]",personTrace.name, personTrace.refyear()[0], personTrace.xref_id))
        else:
            heritage.append(("NotDirect", ToID.name, None, ToID.xref_id))
        gOp.heritage = heritage
        return heritage