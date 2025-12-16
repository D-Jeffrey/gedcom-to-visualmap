__all__ = ['KmlExporter']

import logging
import math
import os.path
import random
import re

import simplekml
from models.line import Line
from geo_gedcom.lat_lon import LatLon
from render.referenced import Referenced

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gedcom_options import gvOptions

_log = logging.getLogger(__name__.lower())

class KmlExporter:
    """
    Exports genealogical data to KML format for visualization in Google Earth (legacy version).

    Args:
        gOp (gvOptions): Options and configuration for KML export.
    """
    def __init__(self, gOp: "gvOptions") -> None:
        self.file_name = os.path.join(gOp.resultpath, gOp.ResultFile)
        self.max_line_weight = gOp.MaxLineWeight
        self.kml = None
        self.gOp = gOp
        self.gOp.Referenced = Referenced()
        random.seed()
        self.driftOn = False
        self.gOp.totalpeople = 0
        self.styleA = None
        self.styleB = None
        self.styles = []
            

    def driftLatLon(self, l: LatLon) -> tuple[float | None, float | None]:
        """
        Optionally add a small random drift to a LatLon for privacy or visual separation.

        Args:
            l (LatLon): The original LatLon.
        Returns:
            tuple[float | None, float | None]: Drifted (lon, lat) or (None, None) if input is None.
        """
        if not l or not self.driftOn:
            return (l.lon, l.lat) if l else (None, None)
        return ((float(l.lon)+(random.random() * 0.001) - 0.0005), float(l.lat)+(random.random() * 0.001) - 0.0005)
        
    def Done(self) -> None:
        """
        Finalize and save the KML file, fixing up placemark links and cleaning up descriptions.
        """
        alist = []
        glist = []
        self.gOp.step("Finalizing KML")
        # Fix up the links in the placemark
        for placemark in self.kml.features:
            if getattr(placemark, 'description', None) :
                pattern = r'href=(#.*?);'
                for match in re.finditer(pattern, placemark.description):
                    tag = match.group(1)
                    if self.gOp.Referenced.exists(tag):
                        replacewith = 1 + int(self.gOp.Referenced.gettag(tag))
                        original = f"href={tag};"
                        replacement = f"href=#{replacewith};"
                        placemark.description = placemark.description.replace(original, replacement)
                        # glist.append(original+"->"+replacement)
                    else:
                        # remove the link
                        replaceit = r'(<a '+ f"href={tag};" + r'[^<]+>)([^>]+)(</a>)'
                        for ripout in re.findall(replaceit, placemark.description):
                            if ripout:
                                # alist.append(ripout[0])
                                placemark.description = placemark.description.replace(ripout[0]+ripout[1]+ripout[2], ripout[1])


        
        self.gOp.step("Saving KML")
        logging.info("Saved as %s", self.file_name)
        self.kml.save(self.file_name)
        # self.gOp.stop()
        # self.kml = None

    def export(self, main: LatLon, lines: list[Line], ntag: str = "", mark: str = "native") -> None:
        """
        Export the main person and lines to KML, creating placemarks and lines for each.

        Args:
            main (LatLon): Main person's location.
            lines (list[Line]): List of Line objects to export.
            ntag (str, optional): Tag to append to names. Defaults to "".
            mark (str, optional): Marker type. Defaults to "native".
        """
        foldermode = self.gOp.KMLsort == 1
        marktype = self._get_mark_type(mark)
        colorA, colorB = "ylw", "ltblu"

        kml, styleA, styleB = self._setup_kml_and_styles(colorA, colorB, marktype, foldermode)

        if main and (not main.lon or not main.lat):
            _log.error(f"No GPS locations to generate a map for main person for {ntag}.")
        if not lines or len(lines) == 0:
            _log.error(f"No GPS locations to generate any person for {ntag}.")

        self.gOp.step("Generating KML")
        sorted_lines = sorted(lines, key=lambda x: x.prof)
        for line in sorted_lines:
            self.gOp.step()
            self._process_line(line, ntag, mark, foldermode, kml, styleA, styleB)

    def _get_mark_type(self, mark: str) -> str:
        """
        Get the marker type string for a given mark.
        Args:
            mark (str): Marker type.
        Returns:
            str: Marker type string for KML icon.
        """
        if mark == 'death':
            return "stars"
        elif mark == "birth":
            return "circle"
        else:
            return "blank"

    def _setup_kml_and_styles(self, colorA: str, colorB: str, marktype: str, foldermode: bool) -> tuple[simplekml.Kml, simplekml.Style, simplekml.Style]:
        """
        Set up the KML document and styles for placemarks and lines.
        Args:
            colorA (str): Color for style A.
            colorB (str): Color for style B.
            marktype (str): Marker type string.
            foldermode (bool): Whether to use folders for event types.
        Returns:
            tuple: (Kml, styleA, styleB)
        """
        if self.kml:
            kml = self.kml
            styleA = self.styleA
            styleB = self.styleB
        else:
            import simplekml
            kml = simplekml.Kml()
            inputfile = os.path.basename(self.gOp.GEDCOMinput) if self.gOp.GEDCOMinput else "Unknown"
            descript = f"Family tree generated for using {inputfile}<br>{self.gOp.Name} ({self.gOp.Main}) as starting person"
            descript += f"<br>Marker types are {'Birth' if self.gOp.BornMark else ''} {'Death' if self.gOp.DieMark else ''}"
            kmloptions = []
            if self.gOp.MapTimeLine:
                kmloptions.append("Timeline enabled.")
            if self.gOp.UseBalloonFlyto:
                kmloptions.append("Balloon Flyto enabled.")
            if self.gOp.AllEntities:
                kmloptions.append("All people are included.")
            if kmloptions:
                descript += "<br>" + " ".join(kmloptions)
            kml.newdocument(name='About Geomap KML', description=descript)
            self.kml = kml
            if foldermode:
                self.folderBirth = kml.newfolder(name="Births")
                self.folderDeath = kml.newfolder(name="Deaths")
                self.folderLife = kml.newfolder(name="Lifelines")
            import simplekml
            styleA = simplekml.Style()
            styleA.iconstyle.icon.href = f'https://maps.google.com/mapfiles/kml/paddle/{colorA}-{marktype}.png'
            styleB = simplekml.Style()
            styleB.labelstyle.scale = 1
            self.styleA = styleA
            self.styleB = styleB
        return kml, styleA, styleB

    def _process_line(self, line: Line, ntag: str, mark: str, foldermode: bool, kml: simplekml.Kml, styleA: simplekml.Style, styleB: simplekml.Style) -> None:
        """
        Process a single Line object, adding placemarks and lines to the KML.
        """
        (desend, name) = line.name.split("\t")
        linage = self._format_parent_links(line, foldermode)
        familyLinage = self._format_children_links(line, foldermode)
        event = self._format_event(line)

        if line.fromlocation and line.fromlocation.hasLocation() and mark in ['birth']:
            self._add_birth_point(line, ntag, event, linage, familyLinage, foldermode, kml, styleA)
        if line.tolocation and line.tolocation.hasLocation() and mark in ['death']:
            self._add_death_point(line, ntag, event, linage, familyLinage, foldermode, kml, styleB)
        if line.fromlocation and line.fromlocation.hasLocation() and line.tolocation and line.tolocation.hasLocation():
            self._add_life_line(line, desend, event, linage, familyLinage, foldermode, kml)
        else:
            self._log_skipped_line(line)
        self.gOp.totalpeople += 1
        if line.midpoints:
            self._add_midpoints(line, name, foldermode, kml, styleA)

    def _format_parent_links(self, line: Line, foldermode: bool) -> str:
        """
        Format HTML links for a person's parents.
        """
        linage = ""
        if line.person.father:
            if self.gOp.UseBalloonFlyto:
                linage += '<br>Father: <a href=#{};balloonFlyto>{}</a></br>'.format(
                    line.person.father[1:-1], self.gOp.people[line.person.father].name)
            else:
                linage += '<br>Father: {}</br>'.format(self.gOp.people[line.person.father].name)
        if line.person.mother:
            if self.gOp.UseBalloonFlyto:
                linage += '<br>Mother: <a href=#{};balloonFlyto>{}</a></br>'.format(
                    line.person.mother[1:-1], self.gOp.people[line.person.mother].name)
            else:
                linage += '<br>Mother: {}</br>'.format(self.gOp.people[line.person.mother].name)
        return linage

    def _format_children_links(self, line: Line, foldermode: bool) -> str:
        """
        Format HTML links for a person's children.
        """
        children = line.person.children
        if not children:
            return ""
        if self.gOp.UseBalloonFlyto:
            family_links = [
                f'<a href=#{child[1:-1]};balloonFlyto>{self.gOp.people[child].name}</a>'
                for child in children
            ]
            return '<br>Children: {}</br>'.format(", ".join(family_links))
        else:
            family_names = [self.gOp.people[child].name for child in children]
            return '<br>Children: {}</br>'.format(", ".join(family_names))

    def _format_event(self, line: Line) -> str:
        """
        Format the event string for a line (birth/death/lifespan).
        """
        timeA = getattr(line, 'whenFrom', None)
        timeB = getattr(line, 'whenTo', None)
        if timeA and timeB:
            event = f"{timeA} - {timeB}"
        elif timeB:
            event = f"Death: {timeB}"
        elif timeA:
            event = f"Born: {timeA}"
        else:
            event = "Unknown dates"
        return f"<br>{event}</br>"

    def _add_birth_point(self, line: Line, ntag: str, event: str, linage: str, familyLinage: str, foldermode: bool, kml: simplekml.Kml, styleA: simplekml.Style) -> None:
        """
        Add a birth placemark to the KML.
        """
        connectWhere = self.folderBirth if foldermode else kml
        pnt = connectWhere.newpoint(
            name=line.name.split("\t")[1] + ntag,
            coords=[self.driftLatLon(line.fromlocation)],
            description="<![CDATA[ " + event + linage + familyLinage + " ]]>"
        )
        self.gOp.Referenced.add(line.person.xref_id, 'kml-a', tag=pnt.id)
        self.gOp.Referenced.add("#" + line.person.xref_id[1:-1], tag=pnt.id)
        if self.gOp.MapTimeLine and getattr(line, 'whenFrom', None) and line.whenFrom:
            pnt.timestamp.when = line.whenFrom
        pnt.style = simplekml.Style()
        pnt.style.labelstyle.scale = styleA.labelstyle.scale
        pnt.style.iconstyle.icon.href = styleA.iconstyle.icon.href

    def _add_death_point(self, line: Line, ntag: str, event: str, linage: str, familyLinage: str, foldermode: bool, kml: simplekml.Kml, styleB: simplekml.Style) -> None:
        """
        Add a death placemark to the KML.
        """
        connectWhere = self.folderDeath if foldermode else kml
        pnt = connectWhere.newpoint(
            name=line.name.split("\t")[1] + ntag,
            coords=[self.driftLatLon(line.tolocation)],
            description="<![CDATA[ " + event + linage + familyLinage + " ]]>"
        )
        self.gOp.Referenced.add(line.person.xref_id, 'kml-b')
        self.gOp.Referenced.add("#" + line.person.xref_id[1:-1], tag=pnt.id)
        if self.gOp.MapTimeLine and getattr(line, 'whenTo', None) and line.whenTo:
            pnt.timestamp.when = line.whenTo
        pnt.style = simplekml.Style()
        pnt.style.labelstyle.scale = styleB.labelstyle.scale
        pnt.style.iconstyle.icon.href = styleB.iconstyle.icon.href

    def _add_life_line(self, line: Line, desend: str, event: str, linage: str, familyLinage: str, foldermode: bool, kml: simplekml.Kml) -> None:
        """
        Add a life line (polyline) to the KML.
        """
        connectWhere = self.folderLife if foldermode else kml
        timeA = getattr(line, 'whenFrom', None)
        timeB = getattr(line, 'whenTo', None)
        event_desc = "<br>Lifespan: {} to {}, related as {}</br>".format(
            timeA if timeA else "Unknown", timeB if timeB else "Unknown", desend)
        kml_line = connectWhere.newlinestring(
            name=line.name.split("\t")[1],
            description="<![CDATA[ " + event_desc + linage + familyLinage + " ]]>",
            coords=[self.driftLatLon(line.fromlocation), self.driftLatLon(line.tolocation)]
        )
        kml_line.linestyle.color = line.color.to_hexa()
        kml_line.linestyle.width = max(int(self.max_line_weight / math.exp(0.5 * min(line.prof, 100))), .1)
        kml_line.extrude = 1
        kml_line.tessellate = 1
        import simplekml
        kml_line.altitudemode = simplekml.AltitudeMode.clamptoground
        if self.gOp.MapTimeLine:
            if timeA and timeB:
                kml_line.timespan.begin = timeA
                kml_line.timespan.end = timeB
            elif timeA:
                kml_line.timestamp.when = timeA
            elif timeB:
                kml_line.timestamp.when = timeB
        _log.info(f"    line    {line.name} ({line.fromlocation.lon}, {line.fromlocation.lat}) ({line.tolocation.lon}, {line.tolocation.lat})")

    def _log_skipped_line(self, line: Line) -> None:
        """
        Log a warning for a skipped line (missing location).
        """
        if line.fromlocation and line.tolocation:
            _log.warning(f"skipping {line.name} ({line.fromlocation.lon}, {line.fromlocation.lat}) ({line.tolocation.lon}, {line.tolocation.lat})")
        else:
            _log.warning(f"skipping {line.name} (no location): {line}")

    def _add_midpoints(self, line: Line, name: str, foldermode: bool, kml: simplekml.Kml, styleA: simplekml.Style) -> None:
        """
        Add midpoint placemarks for events along a line.
        """
        connectWhere = self.folderLife if foldermode else kml
        for mid in line.midpoints:
            event_location = getattr(mid, 'location', None)
            event_date = getattr(mid, 'date', None)
            event_latlon = getattr(event_location, 'latlon', None) if event_location else None
            if event_latlon:
                whatevent = mid.what if mid.what else "Event"
                event = "<br>{}: {}</br>".format(whatevent, event_date if event_date else "Unknown")
                pnt = connectWhere.newpoint(
                    name=f"{name} ({whatevent})",
                    coords=[self.driftLatLon(event_latlon)],
                    description="<![CDATA[ " + event + " ]]>"
                )
                pnt.style = simplekml.Style()
                pnt.style.labelstyle.scale = 0.7 * styleA.labelstyle.scale
                date_single = getattr(event_date, 'single', None)
                if date_single and self.gOp.MapTimeLine:
                    pnt.timestamp.when = date_single.isoformat() if date_single else None
                _log.info(f"    midpt   {line.name} ({event_latlon.lon}, {event_latlon.lat})")
            else:
                if mid.location and getattr(mid.location, 'latlon', None):
                    _log.warning(f"skipping {line.name} ({event_latlon.lon}, {event_latlon.lat})")
                else:
                    _log.warning(f"skipping {line.name} (no location): {mid}")
