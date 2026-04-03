"""
Migration Flow Visualization using Sankey Diagrams.

Generates interactive Sankey diagrams showing how populations moved between
geographic locations over time periods. Reveals migration patterns, diaspora,
and family clustering without needing individual person tracking.

Features:
    - Flow visualization showing volume of people moving between locations
    - Time-period grouping (decades, generations, eras)
    - Multiple visualization modes (births, deaths, residences)
    - Interactive HTML output with filtering and drill-down
    - Statistics on migration patterns (top flows, route diversity, etc.)
"""

__all__ = ["MigrationFlowExporter", "MigrationFlowAnalyzer", "SankeyBuilder"]

import logging
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from services.interfaces import IConfig, IState, IProgressTracker
from render.folium.name_processor import NameProcessor

_log = logging.getLogger(__name__.lower())


class MigrationEventType(Enum):
    """Types of life events that trigger migration analysis."""
    BIRTH = "BIRT"
    DEATH = "DEAT"
    RESIDENCE = "RESI"
    BURIAL = "BURI"
    ARRIVAL = "ARRV"
    DEPARTURE = "DEPT"



class TimePeriodMode(Enum):
    """How to group people into time periods."""
    DECADE = "decade"  # 1850-1859, 1860-1869, etc.
    GENERATION = "generation"  # ~25 year intervals
    CENTURY = "century"  # 1800s, 1900s, etc.
    CUSTOM = "custom"  # User-defined year ranges


@dataclass
class LocationNode:
    """Represents a geographic location in migration flow."""
    location_name: str
    country: str = ""
    continent: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    event_count: int = 0
    
    def __hash__(self):
        return hash((self.location_name, self.country))
    
    def __eq__(self, other):
        if not isinstance(other, LocationNode):
            return NotImplemented
        return self.location_name == other.location_name and self.country == other.country
    
    def __repr__(self) -> str:
        return f"{self.location_name}, {self.country}"
    
    def get_display_name(self, grouping: str) -> str:
        """Get display name based on grouping level."""
        if grouping == "Country":
            return self.country or self.location_name
        elif grouping == "City and Country":
            if self.country:
                return f"{self.location_name}, {self.country}"
            else:
                return self.location_name
        else:
            return self.location_name


@dataclass
class MigrationFlow:
    """Represents flow of people between two locations in a time period."""
    from_location: LocationNode
    to_location: LocationNode
    time_period: str
    flow_count: int = 0
    people_ids: Set[str] = field(default_factory=set)
    event_types: Counter = field(default_factory=Counter)
    path_weight: int = 0
    path_weight: int = 0
    
    def add_person(self, person_id: str, event_type: MigrationEventType):
        """Record a person moving in this flow."""
        self.people_ids.add(person_id)
        self.event_types[event_type.value] += 1
        self.flow_count = len(self.people_ids)


@dataclass
class MigrationStats:
    """Aggregated migration statistics."""
    total_flows: int = 0
    total_people_moved: int = 0
    top_destinations: List[Tuple[str, int]] = field(default_factory=list)
    top_origins: List[Tuple[str, int]] = field(default_factory=list)
    most_common_routes: List[Tuple[Tuple[str, str], int]] = field(default_factory=list)
    time_periods_covered: List[str] = field(default_factory=list)
    average_flow_size: float = 0.0
    diaspora_index: float = 0.0  # Measure of family spread


class MigrationFlowAnalyzer:
    """Analyzes genealogical data to extract migration patterns."""
    
    def __init__(self, geolocated_gedcom, location_grouping: str = "City and Country", use_soundex: bool = True):
        """
        Initialize migration analyzer.
        
        Args:
            geolocated_gedcom: GeolocatedGedcom instance with geocoded people and events
            location_grouping: How to display locations ("Country" or "City and Country")
            use_soundex: If True, group similar-sounding locations using Soundex
        """
        self.geolocated_gedcom = geolocated_gedcom
        self.location_grouping = location_grouping
        self.use_soundex = use_soundex
        self.flows: List[MigrationFlow] = []
        self.locations: Set[LocationNode] = set()
        self.stats = MigrationStats()
        self._location_node_cache: Dict[str, LocationNode] = {}
        _log.info("MigrationFlowAnalyzer initialized with %d people", 
                 len(geolocated_gedcom.people) if hasattr(geolocated_gedcom, 'people') else 0)
    
    def extract_events_with_locations(self, person, event_type: MigrationEventType) -> List[Tuple[str, str, Optional[int]]]:
        """
        Extract birth/death/residence events with their years and locations.
        
        Args:
            person: Person object from genealogy
            event_type: Type of event to extract (BIRTH, DEATH, RESIDENCE, BURIAL)
        
        Returns:
            List of (location, country, year) tuples where event occurred
        """
        events = []
        
        # Map event type to person attributes
        event_map = {
            MigrationEventType.BIRTH: 'birth',
            MigrationEventType.DEATH: 'death',
            MigrationEventType.RESIDENCE: 'residence',
            MigrationEventType.BURIAL: 'burial',
            MigrationEventType.ARRIVAL: 'arrival',
            MigrationEventType.DEPARTURE: 'residence'  # Treat arrival/departure as residence for location extraction
        }
        
        attr_name = event_map.get(event_type)
        if not attr_name:
            return events

        event = None
        if hasattr(person, 'get_event') and callable(getattr(person, 'get_event')):
            event = person.get_event(attr_name)
        else:
            event = getattr(person, attr_name, None)

        if not event:
            return events

        if event and hasattr(event, 'place') and hasattr(event, 'date'):
            place = event.place
            year = event.date.year_num
            
            # Parse place into location and country
            if place:
                parts = [p.strip() for p in place.split(',')]
                # Remove leading empty parts
                while parts and not parts[0]:
                    parts.pop(0)
                if not parts:
                    location = place
                    country = ""
                else:
                    country = parts[-1] if len(parts) > 1 else ""
                    if len(parts) <= 3:
                        location = parts[0] if parts else place
                    else:
                        if parts[1] and not parts[1].isdigit():
                            location = parts[1]
                        else:
                            location = parts[0]
                events.append((location, country, year))
        
        return events
    
    def _normalize_name(self, name: Optional[str]) -> str:
        """Normalize a place name for matching/grouping."""
        if not name:
            return ""
        if self.use_soundex:
            return NameProcessor.soundex(name)
        return NameProcessor.simplifyLastName(name)

    def _location_group_key(self, location: str, country: str) -> Tuple[str, str]:
        """Compute grouping key and display components for a location."""
        normalized_location = self._normalize_name(location)
        normalized_country = self._normalize_name(country)

        if self.location_grouping == "Country":
            key = f"country:{normalized_country or location.lower().strip()}"
            display = country or location
            return key, display

        # city + country grouping
        key = f"city:{normalized_location or location.lower().strip()};country:{normalized_country or country.lower().strip()}"
        if location and country:
            display = f"{location}, {country}"
        elif location:
            display = location
        else:
            display = country
        return key, display

    def group_by_time_period(self, year: Optional[int], mode: TimePeriodMode) -> str:
        """
        Group a year into a time period based on mode.
        
        Args:
            year: Calendar year (or None for unknown)
            mode: Grouping mode (decade, generation, century, custom)
        
        Returns:
            String representing the time period (e.g., "1850-1859" for decade)
        """
        if year is None or not isinstance(year, int) or year <= 0:
            return "Unknown"
        
        if mode == TimePeriodMode.DECADE:
            decade_start = (year // 10) * 10
            return f"{decade_start}-{decade_start + 9}"
        
        elif mode == TimePeriodMode.GENERATION:
            gen_start = (year // 25) * 25
            return f"{gen_start}-{gen_start + 24}"
        
        elif mode == TimePeriodMode.CENTURY:
            century = (year // 100) * 100
            return f"{century}s"
        
        else:  # CUSTOM - would be handled by caller
            return str(year)
    
    def analyze(self, mode: TimePeriodMode = TimePeriodMode.DECADE, 
                event_types: Optional[List[MigrationEventType]] = None,
                max_lines: Optional[int] = None) -> MigrationStats:
        """
        Analyze migration flows from genealogical data.
        
        Args:
            mode: How to group people by time period
            event_types: Which event types to analyze (default: all)
            max_lines: Maximum number of links to keep for visualization (top by count)
        
        Returns:
            MigrationStats with analysis results
        """
        if event_types is None:
            event_types = [MigrationEventType.BIRTH, MigrationEventType.DEATH, 
                          MigrationEventType.RESIDENCE]
        
        flow_dict: Dict[Tuple[str, str], MigrationFlow] = {}
        self.locations = set()
        self._location_node_cache = {}

        _log.info("Analyzing migration flows with %d event types", len(event_types))

        # Determine people iterable; GeolocatedGedcom.people can be dict or list
        if hasattr(self.geolocated_gedcom, 'people'):
            if isinstance(self.geolocated_gedcom.people, dict):
                people_iterable = list(self.geolocated_gedcom.people.values())
            else:
                people_iterable = self.geolocated_gedcom.people
        else:
            people_iterable = []

        # Step 1: Extract all location/time events for each person
        for person_id, person in enumerate(people_iterable):
            if not person:
                _log.warning("Skipping empty person entry at index %d", person_id)
                continue
            person_events = []  # List of (location, country, year, period, event_type)
            
            for evt_type in event_types:
                events = self.extract_events_with_locations(person, evt_type)
                for loc, country, year in events:
                    if loc and year:
                        period = self.group_by_time_period(year, mode)
                        person_events.append((loc, country, year, period, evt_type))
            
            person_events.sort(key=lambda x: x[2] if x[2] else 0)
            
            if len(person_events) >= 2:
                for i in range(len(person_events) - 1):
                    from_loc, from_country, from_year, from_period, _ = person_events[i]
                    to_loc, to_country, to_year, to_period, to_event_type = person_events[i + 1]

                    from_key, _ = self._location_group_key(from_loc, from_country)
                    to_key, _ = self._location_group_key(to_loc, to_country)

                    # Only create flow if actually moved (different normalized keys)
                    if from_key != to_key:
                        # preserve canonical nodes in cache (using raw location/country)
                        if from_key not in self._location_node_cache:
                            from_node = LocationNode(from_loc, from_country)
                            self._location_node_cache[from_key] = from_node
                            self.locations.add(from_node)
                        else:
                            from_node = self._location_node_cache[from_key]

                        if to_key not in self._location_node_cache:
                            to_node = LocationNode(to_loc, to_country)
                            self._location_node_cache[to_key] = to_node
                            self.locations.add(to_node)
                        else:
                            to_node = self._location_node_cache[to_key]

                        flow_key = (from_key, to_key)

                        if flow_key not in flow_dict:
                            flow = MigrationFlow(from_node, to_node, from_period)
                            flow_dict[flow_key] = flow
                        else:
                            flow = flow_dict[flow_key]

                        flow.add_person(str(person_id), to_event_type)

        self.flows = list(flow_dict.values())

        # Calculate path weights for prioritizing flows
        path_counter = Counter()
        for person_id, person in enumerate(people_iterable):
            if not person:
                continue
            person_events = []
            for evt_type in event_types:
                events = self.extract_events_with_locations(person, evt_type)
                for loc, country, year in events:
                    if loc and year:
                        period = self.group_by_time_period(year, mode)
                        loc_key, _ = self._location_group_key(loc, country)
                        person_events.append((loc_key, period))
            person_events.sort(key=lambda x: x[1])  # sort by period
            unique_locs = []
            seen = set()
            for loc_key, period in person_events:
                if loc_key not in seen:
                    unique_locs.append(loc_key)
                    seen.add(loc_key)
            if len(unique_locs) >= 2:
                path = tuple(unique_locs)
                path_counter[path] += 1

        # Assign path weights to flows
        for flow in self.flows:
            from_key = self._location_group_key(flow.from_location.location_name, flow.from_location.country)[0]
            to_key = self._location_group_key(flow.to_location.location_name, flow.to_location.country)[0]
            weight = 0
            for path, count in path_counter.items():
                if from_key in path and to_key in path:
                    # Check if they are consecutive in the path
                    try:
                        from_idx = path.index(from_key)
                        to_idx = path.index(to_key)
                        if to_idx == from_idx + 1:
                            weight += count
                    except ValueError:
                        pass
            flow.path_weight = weight

        # Top-N filtering to avoid clutter, prioritize by path weight
        if max_lines is not None and max_lines > 0:
            self.flows.sort(key=lambda f: f.path_weight, reverse=True)
            self.flows = self.flows[:max_lines]

        self._calculate_statistics()

        _log.info("Migration analysis complete: %d flows, %d unique locations", 
                 len(self.flows), len(self.locations))
        
        return self.stats
    
    def _calculate_statistics(self):
        """Calculate aggregate migration statistics."""
        if not self.flows:
            return
        
        destination_counter = Counter()
        origin_counter = Counter()
        route_counter = Counter()
        all_people_moved = set()
        
        for flow in self.flows:
            to_display = flow.to_location.get_display_name(self.location_grouping)
            from_display = flow.from_location.get_display_name(self.location_grouping)
            destination_counter[to_display] += flow.flow_count
            origin_counter[from_display] += flow.flow_count
            route_counter[(from_display, to_display)] += flow.flow_count
            all_people_moved.update(flow.people_ids)
        
        self.stats.total_flows = len(self.flows)
        self.stats.total_people_moved = len(all_people_moved)
        self.stats.top_destinations = destination_counter.most_common(10)
        self.stats.top_origins = origin_counter.most_common(10)
        self.stats.most_common_routes = route_counter.most_common(10)
        self.stats.average_flow_size = (self.stats.total_people_moved / self.stats.total_flows 
                                       if self.stats.total_flows > 0 else 0)

        _log.info(
            "Migration stats: total_flows=%d total_people_moved=%d top_routes=%s",
            self.stats.total_flows,
            self.stats.total_people_moved,
            self.stats.most_common_routes[:5]
        )
        
        # Diaspora index: measure of how spread out family is
        # Higher = more dispersed, lower = concentrated
        if len(self.locations) > 1:
            self.stats.diaspora_index = len(self.locations) / max(1, len(all_people_moved))
        
        self.stats.time_periods_covered = sorted(set(f.time_period for f in self.flows))


class SankeyBuilder:
    """Constructs Plotly Sankey diagram from migration flows."""
    
    @staticmethod
    def build_sankey_data(flows: List[MigrationFlow], display_func=None) -> Tuple[List[str], Dict[str, int], List[int], List[int], List[int]]:
        """
        Build node and link data for Sankey diagram.
        
        Args:
            flows: List of MigrationFlow objects
            display_func: Function to get display name from LocationNode, defaults to str
        
        Returns:
            Tuple of (labels, location_to_index_map, source_indices, target_indices, values)
        """
        if display_func is None:
            display_func = str
        
        labels: List[str] = []
        location_to_index: Dict[str, int] = {}
        source_indices: List[int] = []
        target_indices: List[int] = []
        values: List[int] = []
        
        # Build unique location list
        for flow in flows:
            from_label = display_func(flow.from_location)
            to_label = display_func(flow.to_location)
            
            if from_label not in location_to_index:
                location_to_index[from_label] = len(labels)
                labels.append(from_label)
            
            if to_label not in location_to_index:
                location_to_index[to_label] = len(labels)
                labels.append(to_label)
        
        # Build links
        for flow in flows:
            from_idx = location_to_index[display_func(flow.from_location)]
            to_idx = location_to_index[display_func(flow.to_location)]
            
            source_indices.append(from_idx)
            target_indices.append(to_idx)
            values.append(flow.flow_count)
        
        return labels, location_to_index, source_indices, target_indices, values
    
    @staticmethod
    def _get_period_color(time_period: str) -> str:
        """Assign color based on time period for visual differentiation."""
        # Extract start year for color gradient
        try:
            if time_period == "Unknown":
                return "rgba(200, 200, 200, 0.4)"
            
            # Parse decade format "1850-1859"
            start_year = int(time_period.split('-')[0])
            
            # Color gradient from red (1700s) to blue (2000s)
            # Normalize year to 0-1 range (1700-2000)
            normalized = max(0, min(1, (start_year - 1700) / 300))
            
            # Red -> Yellow -> Green -> Blue gradient
            if normalized < 0.33:
                # Red to Yellow
                r, g, b = 255, int(255 * (normalized / 0.33)), 0
            elif normalized < 0.66:
                # Yellow to Green
                r, g, b = int(255 * (1 - (normalized - 0.33) / 0.33)), 255, 0
            else:
                # Green to Blue
                r, g, b = 0, int(255 * (1 - (normalized - 0.66) / 0.34)), int(255 * ((normalized - 0.66) / 0.34))
            
            return f"rgba({r}, {g}, {b}, 0.4)"
        except (ValueError, IndexError):
            return "rgba(100, 100, 100, 0.4)"
    
    @staticmethod
    def create_sankey_figure(flows: List[MigrationFlow], title: str = "Family Migration Flow", display_func=None) -> go.Figure:
        """
        Create interactive Plotly Sankey figure.
        
        Args:
            flows: List of MigrationFlow objects
            title: Title for the visualization
            display_func: Function to get display name from LocationNode
        
        Returns:
            Plotly Figure object
        """
        if not flows:
            _log.warning("No migration flows to visualize")
            return go.Figure().add_annotation(text="No migration data available")
        
        labels, _, source_idx, target_idx, values = SankeyBuilder.build_sankey_data(flows, display_func)
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color='black', width=0.5),
                label=labels,
                color=['rgba(0, 100, 200, 0.7)' if i < len(labels)//2 else 'rgba(200, 100, 0, 0.7)' 
                       for i in range(len(labels))]
            ),
            link=dict(
                source=source_idx,
                target=target_idx,
                value=values,
                color=[SankeyBuilder._get_period_color(flows[i].time_period) for i in range(len(flows))]
            )
        )])
        
        fig.update_layout(
            title=title,
            font=dict(size=10),
            height=600,
            hovermode='closest',
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        return fig


class MigrationFlowExporter:
    """
    Main exporter for migration flow visualizations.
    
    Generates interactive HTML and static visualizations showing how families
    migrated between locations across time periods.
    """
    
    def __init__(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker):
        """
        Initialize migration flow exporter.
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service
            svc_progress: Progress tracking service
        """
        self.svc_config = svc_config
        self.svc_state = svc_state
        self.svc_progress = svc_progress
        self.file_name = self.svc_config.get("resultpath") + "/" + self.svc_config.get("ResultFile")
        self.file_name = self.file_name.replace(".html", "_migration_sankey.html")
    
    def export(self, geolocated_gedcom, output_file: Optional[str] = None,
               mode: TimePeriodMode = TimePeriodMode.DECADE,
               include_all_modes: bool = False, location_grouping: str = "City and Country",
               use_soundex: bool = True, max_lines: int = 100) -> str:
        """
        Generate and export migration flow visualizations.
        
        Args:
            geolocated_gedcom: GeolocatedGedcom instance with geocoded data
            output_file: Output HTML file path (uses default if not provided)
            mode: Time period grouping mode
            include_all_modes: Generate visualizations for all grouping modes
            location_grouping: How to display locations ("Country" or "City and Country")
        
        Returns:
            Path to generated HTML file
        """
        if output_file is None:
            output_file = self.file_name
        
        self.svc_progress.step("Analyzing migration flows...")
        
        _log.info(f"export: mode={mode}, location_grouping={location_grouping}")
        
        analyzer = MigrationFlowAnalyzer(geolocated_gedcom, location_grouping, use_soundex=use_soundex)
        
        # Generate analysis
        stats = analyzer.analyze(mode=mode, max_lines=max_lines)
        
        display_func = lambda loc: loc.get_display_name(location_grouping)
        
        _log.info("Migration analysis complete: %d flows from %d locations",
                 stats.total_flows, len(analyzer.locations))
        _log.info("Top destinations: %s", stats.top_destinations[:5])
        _log.info("Most common routes: %s", stats.most_common_routes[:5])
        _log.info("Diaspora index (family spread): %.2f", stats.diaspora_index)
        
        self.svc_progress.step("Generating Sankey visualizations...")
        
        # Create main Sankey figure
        fig = SankeyBuilder.create_sankey_figure(
            analyzer.flows,
            title=f"Family Migration Flows ({mode.value.title()})",
            display_func=display_func
        )
        
        # Generate additional visualizations
        figs = [fig]
        
        if include_all_modes:
            for alt_mode in [m for m in TimePeriodMode if m != mode and m != TimePeriodMode.CUSTOM]:
                alt_stats = analyzer.analyze(mode=alt_mode)
                alt_fig = SankeyBuilder.create_sankey_figure(
                    analyzer.flows,
                    title=f"Family Migration Flows ({alt_mode.value.title()})",
                    display_func=display_func
                )
                figs.append(alt_fig)
        
        self.svc_progress.step("Creating interactive HTML...")
        
        # Generate comprehensive HTML with multiple tabs
        html_content = self._generate_html(figs, stats, analyzer)
        
        # Write HTML file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        _log.info("Migration flow visualization saved to %s", output_path)
        
        return str(output_path)
    
    def _generate_html(self, figs: List[go.Figure], stats: MigrationStats, 
                      analyzer: MigrationFlowAnalyzer) -> str:
        """
        Generate comprehensive HTML document with all visualizations and statistics.
        
        Args:
            figs: List of Plotly figures
            stats: Migration statistics
            analyzer: Migration analyzer with detailed data
        
        Returns:
            HTML content as string
        """
        fig_htmls = [fig.to_html(include_plotlyjs=False) for fig in figs]
        
        # Build statistics table
        stats_html = f"""
        <div class="stats-panel">
            <h2>Migration Statistics</h2>
            <table class="stats-table">
                <tr><td><strong>Total Migration Flows:</strong></td><td>{stats.total_flows}</td></tr>
                <tr><td><strong>Total People Moved:</strong></td><td>{stats.total_people_moved}</td></tr>
                <tr><td><strong>Average Flow Size:</strong></td><td>{stats.average_flow_size:.1f} people</td></tr>
                <tr><td><strong>Unique Locations:</strong></td><td>{len(analyzer.locations)}</td></tr>
                <tr><td><strong>Diaspora Index (spread):</strong></td><td>{stats.diaspora_index:.3f}</td></tr>
            </table>
            
            <h3>Top 5 Destinations</h3>
            <ol>
                {''.join(f'<li>{loc}: {count} people</li>' for loc, count in stats.top_destinations[:5])}
            </ol>
            
            <h3>Top 5 Origins</h3>
            <ol>
                {''.join(f'<li>{loc}: {count} people</li>' for loc, count in stats.top_origins[:5])}
            </ol>
            
            <h3>Most Common Routes</h3>
            <ol>
                {''.join(f'<li>{from_loc} → {to_loc}: {count} people</li>' 
                         for (from_loc, to_loc), count in stats.most_common_routes[:5])}
            </ol>
            
            <p><strong>Time Periods Covered:</strong> {', '.join(stats.time_periods_covered)}</p>
        </div>
        """
        
        # Build tab structure for multiple views
        tab_content = ""
        for i, fig_html in enumerate(fig_htmls):
            tab_id = f"tab-{i}"
            active_class = "active" if i == 0 else ""
            tab_content += f"""
            <div id="{tab_id}" class="tab-pane {active_class}">
                <div class="plotly-container">
                    {fig_html}
                </div>
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Family Migration Flow Visualization</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                }}
                
                .header h1 {{
                    font-size: 2.5em;
                    margin-bottom: 10px;
                }}
                
                .header p {{
                    font-size: 1.1em;
                    opacity: 0.9;
                }}
                
                .content {{
                    display: flex;
                    min-height: 1200px;
                }}
                
                .sidebar {{
                    width: 350px;
                    background: #f8f9fa;
                    padding: 30px 20px;
                    overflow-y: auto;
                    border-right: 1px solid #dee2e6;
                }}
                
                .main {{
                    flex: 1;
                    padding: 30px;
                    overflow-y: auto;
                }}
                
                .stats-panel {{
                    background: white;
                }}
                
                .stats-panel h2 {{
                    color: #333;
                    font-size: 1.3em;
                    margin-bottom: 15px;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 10px;
                }}
                
                .stats-panel h3 {{
                    color: #555;
                    font-size: 1em;
                    margin-top: 20px;
                    margin-bottom: 10px;
                }}
                
                .stats-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                    font-size: 0.9em;
                }}
                
                .stats-table tr:nth-child(odd) {{
                    background: #f8f9fa;
                }}
                
                .stats-table td {{
                    padding: 8px;
                    border: 1px solid #dee2e6;
                }}
                
                .stats-table td:first-child {{
                    font-weight: 500;
                    color: #555;
                }}
                
                .stats-panel ol {{
                    margin-left: 20px;
                    font-size: 0.9em;
                    line-height: 1.6;
                    color: #555;
                }}
                
                .stats-panel ol li {{
                    margin-bottom: 5px;
                }}
                
                .plotly-container {{
                    width: 100%;
                    height: 600px;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    overflow: hidden;
                }}
                
                .tabs {{
                    display: flex;
                    gap: 0;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #dee2e6;
                }}
                
                .tab-button {{
                    padding: 12px 20px;
                    background: #f8f9fa;
                    border: none;
                    cursor: pointer;
                    font-size: 0.95em;
                    font-weight: 500;
                    color: #555;
                    border-bottom: 3px solid transparent;
                    transition: all 0.3s ease;
                }}
                
                .tab-button:hover {{
                    background: #e9ecef;
                    color: #333;
                }}
                
                .tab-button.active {{
                    background: white;
                    color: #667eea;
                    border-bottom-color: #667eea;
                }}
                
                .tab-pane {{
                    display: none;
                }}
                
                .tab-pane.active {{
                    display: block;
                }}
                
                .legend {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                    margin-top: 20px;
                    font-size: 0.85em;
                    color: #555;
                    line-height: 1.6;
                }}
                
                .legend strong {{
                    display: block;
                    margin-bottom: 8px;
                    color: #333;
                }}
                
                .legend-item {{
                    margin-bottom: 5px;
                }}
                
                @media (max-width: 1024px) {{
                    .content {{
                        flex-direction: column;
                    }}
                    .sidebar {{
                        width: 100%;
                        border-right: none;
                        border-bottom: 1px solid #dee2e6;
                    }}
                }}
                
                @media (prefers-color-scheme: dark) {{
                    body {{
                        background: #1a1a1a;
                    }}
                    .container {{
                        background: #2d2d2d;
                    }}
                    .sidebar {{
                        background: #3d3d3d;
                        border-right-color: #555;
                    }}
                    .stats-panel h2, .stats-panel h3 {{
                        color: #e0e0e0;
                    }}
                    .stats-table tr:nth-child(odd) {{
                        background: #3d3d3d;
                    }}
                    .stats-table {{
                        border-color: #555;
                    }}
                    .stats-table td {{
                        border-color: #555;
                        color: #e0e0e0;
                    }}
                    .tab-button {{
                        background: #3d3d3d;
                        color: #b0b0b0;
                        border-bottom-color: transparent;
                    }}
                    .tab-button:hover {{
                        background: #4d4d4d;
                        color: #e0e0e0;
                    }}
                    .tab-button.active {{
                        background: #2d2d2d;
                        color: #667eea;
                    }}
                    .legend {{
                        background: #3d3d3d;
                        color: #b0b0b0;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌍 Family Migration Flows</h1>
                    <p>Sankey Diagram Analysis of Genealogical Movement Patterns</p>
                </div>
                
                <div class="content">
                    <div class="sidebar">
                        {stats_html}
                        <div class="legend">
                            <strong>About This Visualization</strong>
                            <div class="legend-item">
                                📊 <strong>Sankey Diagram:</strong> Shows the flow of people between locations.
                                Wider flows indicate more people moved on that route.
                            </div>
                            <div class="legend-item">
                                🎨 <strong>Colors:</strong> Flows are colored by time period:
                                Red = Early periods, Green = Medieval, Blue = Recent.
                            </div>
                            <div class="legend-item">
                                📍 <strong>Nodes:</strong> Geographic locations where family lived.
                                Left side = origins, right side = destinations.
                            </div>
                            <div class="legend-item">
                                📈 <strong>Diaspora Index:</strong> Measures family spread.
                                Higher values = more geographically dispersed.
                            </div>
                        </div>
                    </div>
                    
                    <div class="main">
                        <div class="tabs">
                            {''.join(f'<button class="tab-button{" active" if i == 0 else ""}" onclick="switchTab(\'{i}\')">'
                                   f'View {i+1}</button>' for i in range(len(figs)))}
                        </div>
                        {tab_content}
                    </div>
                </div>
            </div>
            
            <script>
                function switchTab(tabId) {{
                    // Hide all tabs
                    document.querySelectorAll('.tab-pane').forEach(tab => {{
                        tab.classList.remove('active');
                    }});
                    document.querySelectorAll('.tab-button').forEach(btn => {{
                        btn.classList.remove('active');
                    }});
                    
                    // Show selected tab
                    document.getElementById(`tab-${{tabId}}`).classList.add('active');
                    event.target.classList.add('active');
                }}
            </script>
        </body>
        </html>
        """
        
        return html