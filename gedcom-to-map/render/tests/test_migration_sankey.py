"""
Unit tests for Migration Flow Sankey visualization.
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
from render.migration.sankey_exporter import (
    MigrationFlowExporter, MigrationFlowAnalyzer, SankeyBuilder,
    LocationNode, MigrationFlow, MigrationEventType
)


class MockEvent:
    def __init__(self, place, year):
        self.place = place
        self.year = year
        self.date = Mock()
        self.date.year_num = year
        self.location = None


class MockGeoConfig:
    def __init__(self):
        self.country_substitutions_lower = {
            "england": "United Kingdom",
            "scotland": "United Kingdom",
            "wales": "United Kingdom",
            "great britain": "United Kingdom",
            "uk": "United Kingdom",
            "u.k.": "United Kingdom",
            "can": "Canada",
            "united states": "USA",
            "us": "USA",
            "u.s.": "USA",
            "u.s.a.": "USA",
            "united states of america": "USA",
        }
        self.country_name_to_code_dict = {
            "United Kingdom": "GB",
            "Canada": "CA",
            "USA": "US",
        }
        self.country_code_to_name_dict = {
            "GB": "United Kingdom",
            "CA": "Canada",
            "US": "USA",
        }
        self.country_code_to_continent_dict = {
            "GB": "Europe",
            "CA": "North America",
            "US": "North America",
        }
        self.subdivision_country_lookup = {
            "ont": "Canada",
            "ontario": "Canada",
            "alta": "Canada",
            "alberta": "Canada",
            "new york": "USA",
            "massachusetts": "USA",
        }
        self.subdivision_display_lookup = {
            "ont": "Ontario",
            "ontario": "Ontario",
            "alta": "Alberta",
            "alberta": "Alberta",
            "new york": "New York",
            "massachusetts": "Massachusetts",
        }

    def substitute_country_name(self, country_name):
        substituted = self.country_substitutions_lower.get(country_name.lower())
        if substituted:
            return substituted, True
        return country_name, False

    def get_country_code(self, country_name):
        return self.country_name_to_code_dict.get(country_name)

    def get_place_and_countrycode(self, place):
        parts = [p.strip() for p in place.split(',') if p.strip()]
        country = parts[-1] if len(parts) > 1 else ""
        country, _ = self.substitute_country_name(country)
        found = bool(country)
        normalized_place = place
        if not found and parts:
            inferred_country = self.infer_country_from_place_component(parts[-1])
            if inferred_country:
                country = inferred_country
                found = True
                normalized_place = ", ".join(parts[:-1] + [country])
        return normalized_place, self.get_country_code(country) or "none", country, found

    def get_continent_for_country_code(self, country_code):
        return self.country_code_to_continent_dict.get(country_code)

    def infer_country_from_place_component(self, place_component):
        return self.subdivision_country_lookup.get(place_component.strip().lower().rstrip('.'))

    def canonicalize_subdivision_name(self, subdivision_name):
        return self.subdivision_display_lookup.get(subdivision_name.strip().lower().rstrip('.'), subdivision_name.strip())


class MockPersonForSelection:
    def __init__(self, xref_id, birth_place, birth_year, father=None, mother=None):
        self.xref_id = xref_id
        self.father = father
        self.mother = mother
        self.birth = Mock()
        self.birth.place = birth_place
        self.birth.location = None
        self.birth.getattr = lambda attr: birth_year if attr == "when_year_num" else None
        self.death = None
        self.name = xref_id

    def get_event(self, attr_name):
        if attr_name == "birth":
            return self.birth
        if attr_name == "death":
            return self.death
        return None

    def get_events(self, attr_name):
        return []


class TestLocationNode:
    """Test LocationNode dataclass."""
    
    def test_location_node_creation(self):
        node = LocationNode("New York", "United States", "North America", 40.7128, -74.0060)
        assert node.location_name == "New York"
        assert node.country == "United States"
        assert node.latitude == 40.7128
        assert node.longitude == -74.0060
    
    def test_location_node_equality(self):
        node1 = LocationNode("Boston", "USA")
        node2 = LocationNode("Boston", "USA")
        node3 = LocationNode("Boston", "Canada")
        assert node1 == node2
        assert node1 != node3
    
    def test_location_node_continent_display(self):
        node = LocationNode("Paris", "France", "Europe")
        assert node.get_display_name("Continent") == "Europe"
        node_no_continent = LocationNode("Paris", "France")
        assert node_no_continent.get_display_name("Continent") == "Unknown"

    def test_location_node_state_province_display(self):
        node = LocationNode("Albany", "USA", "North America", subdivision="New York")
        assert node.get_display_name("State/Province") == "New York, USA"

        node_without_subdivision = LocationNode("Boston", "USA")
        assert node_without_subdivision.get_display_name("State/Province") == "Unknown, USA"

    def test_location_node_country_display_unknown_without_country(self):
        node = LocationNode("New York", "")
        assert node.get_display_name("Country") == "Unknown"
    
    def test_location_node_hash(self):
        node1 = LocationNode("Boston", "USA")
        node2 = LocationNode("Boston", "USA")
        # Can be used in sets
        location_set = {node1, node2}
        assert len(location_set) == 1


class TestMigrationFlow:
    """Test MigrationFlow dataclass."""
    
    def test_migration_flow_creation(self):
        from_node = LocationNode("Boston", "USA")
        to_node = LocationNode("NYC", "USA")
        flow = MigrationFlow(from_node, to_node, "1850-1859")
        
        assert flow.flow_count == 0
        assert len(flow.people_ids) == 0
    
    def test_migration_flow_add_person(self):
        from_node = LocationNode("Boston", "USA")
        to_node = LocationNode("NYC", "USA")
        flow = MigrationFlow(from_node, to_node, "1850-1859")
        
        flow.add_person("person1", MigrationEventType.BIRTH)
        flow.add_person("person2", MigrationEventType.BIRTH)
        flow.add_person("person1", MigrationEventType.DEATH)  # Same person, different event
        
        assert flow.flow_count == 2  # 2 unique people
        assert len(flow.people_ids) == 2
        assert flow.event_types[MigrationEventType.BIRTH.value] == 2
        assert flow.event_types[MigrationEventType.DEATH.value] == 1


class TestMigrationFlowAnalyzer:
    """Test migration flow analysis."""
    
    def setup_method(self):
        """Setup mock GeolocatedGedcom."""
        self.mock_gedcom = Mock()
        self.mock_gedcom.people = []
        self.mock_gedcom.geo_config = MockGeoConfig()
    
    def test_analyzer_initialization(self):
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom)
        assert analyzer.geolocated_gedcom == self.mock_gedcom
        assert len(analyzer.flows) == 0
        assert len(analyzer.locations) == 0
    
    def test_extract_events_with_locations(self):
        """Test extraction of life events with locations."""
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom)
        
        # Create mock person with birth event
        mock_person = type('Person', (), {})
        mock_birth = MockEvent("Boston, Massachusetts, USA", 1850)
        mock_person.birth = mock_birth
        mock_person.death = None
        
        events = analyzer.extract_events_with_locations(mock_person, MigrationEventType.BIRTH)
        assert len(events) == 1
        assert events[0] == ("Boston", "Massachusetts", "USA", 1850, "North America")

    def test_extract_events_prefers_country_from_place_over_bad_geocode(self):
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom)

        mock_person = type('Person', (), {})
        mock_birth = MockEvent("Viking, Camrose, Alta., Can", 1928)
        mock_birth.location = type('Location', (), {'country_name': 'England', 'continent': 'Europe', 'address': None})()
        mock_person.birth = mock_birth
        mock_person.death = None

        events = analyzer.extract_events_with_locations(mock_person, MigrationEventType.BIRTH)
        assert len(events) == 1
        assert events[0] == ("Viking", "Alberta", "Canada", 1928, "North America")

    def test_analyze_state_province_grouping_merges_cities_in_same_subdivision(self):
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom, location_grouping="State/Province", use_soundex=False)

        person = type('Person', (), {})
        person.birth = MockEvent("Boston, Massachusetts, USA", 1850)
        person.death = MockEvent("Springfield, Massachusetts, USA", 1920)
        person.residence = None

        self.mock_gedcom.people = [person]

        stats = analyzer.analyze()

        assert stats.total_flows == 0

    def test_analyze_sorts_by_year_even_when_country_is_missing(self):
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom, use_soundex=False)

        person = type('Person', (), {})
        person.birth = MockEvent("Unknown Hamlet", 1850)
        person.death = MockEvent("Boston, Massachusetts, USA", 1920)
        person.residence = None

        self.mock_gedcom.people = [person]

        stats = analyzer.analyze()

        assert stats.total_flows == 1
    
    def test_analyze_with_flows(self):
        """Test migration analysis with sample data."""
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom)
        
        # Create mock people with migration patterns
        mock_person1 = type('Person', (), {})
        birth1 = MockEvent("Boston, USA", 1850)
        death1 = MockEvent("NYC, USA", 1920)
        mock_person1.birth = birth1
        mock_person1.death = death1
        mock_person1.residence = None
        
        self.mock_gedcom.people = [mock_person1]
        
        stats = analyzer.analyze()
        
        assert stats.total_flows >= 0
        assert len(analyzer.locations) >= 0

    def test_analyze_with_dict_people(self):
        """People as dict should be supported (as in Gedcom.people)."""
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom)

        mock_person1 = type('Person', (), {})
        mock_person1.birth = MockEvent("Boston, USA", 1850)
        mock_person1.death = MockEvent("NYC, USA", 1920)
        mock_person1.residence = None

        self.mock_gedcom.people = {"@I1@": mock_person1}

        stats = analyzer.analyze()

        assert stats.total_flows == 1
        assert stats.total_people_moved == 1
        assert len(analyzer.locations) == 2

    def test_analyze_soundex_combination(self):
        """Soundex should combine similar sounding city names."""
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom, location_grouping="City and Country", use_soundex=True)

        person_a = type('Person', (), {})
        person_a.birth = MockEvent("New Yrok, USA", 1900)
        person_a.death = MockEvent("Boston, USA", 1950)

        person_b = type('Person', (), {})
        person_b.birth = MockEvent("New York, USA", 1900)
        person_b.death = MockEvent("Boston, USA", 1950)

        self.mock_gedcom.people = [person_a, person_b]

        stats = analyzer.analyze()

        # Both flows from New Yrok and New York should be merged into a single origin
        assert stats.total_flows == 1
        assert stats.total_people_moved == 2

    def test_analyze_top_lines_limit(self):
        """Top lines cap reduces to configured maximum."""
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom, location_grouping="City and Country", use_soundex=False)

        people = []
        for i in range(10):
            p = type('Person', (), {})
            p.birth = MockEvent(f"City{i}, USA", 1900)
            p.death = MockEvent("Boston, USA", 1950)
            people.append(p)
        self.mock_gedcom.people = people

        stats = analyzer.analyze(max_lines=3)

        assert len(analyzer.flows) == 3
        assert stats.total_flows == 10

    def test_analyze_stores_person_xref_ids_in_flow_people_ids(self):
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom)

        person = type('Person', (), {})
        person.xref_id = "@I42@"
        person.surname = "Smith"
        person.name = "John /Smith/"
        person.birth = MockEvent("Boston, USA", 1850)
        person.death = MockEvent("Toronto, Canada", 1920)
        person.residence = None

        self.mock_gedcom.people = [person]

        analyzer.analyze()

        assert analyzer.flows[0].people_ids == {"@I42@"}

    def test_country_aliases_are_canonicalized_for_grouping(self):
        analyzer = MigrationFlowAnalyzer(self.mock_gedcom, location_grouping="Country", use_soundex=False)

        person_a = type('Person', (), {})
        person_a.birth = MockEvent("London, England", 1900)
        person_a.birth.location = type('Location', (), {'country_name': 'England', 'continent': 'Europe', 'address': None})()
        person_a.death = MockEvent("Cardiff, United Kingdom", 1950)
        person_a.death.location = type('Location', (), {'country_name': 'United Kingdom', 'continent': 'Europe', 'address': None})()
        person_a.residence = None

        person_b = type('Person', (), {})
        person_b.birth = MockEvent("Toronto, Can", 1910)
        person_b.birth.location = type('Location', (), {'country_name': 'Can', 'continent': 'North America', 'address': None})()
        person_b.death = MockEvent("Vancouver, Canada", 1970)
        person_b.death.location = type('Location', (), {'country_name': 'Canada', 'continent': 'North America', 'address': None})()
        person_b.residence = None

        person_c = type('Person', (), {})
        person_c.birth = MockEvent("Boston, USA", 1920)
        person_c.birth.location = type('Location', (), {'country_name': 'USA', 'continent': 'North America', 'address': None})()
        person_c.death = MockEvent("Chicago, United States", 1980)
        person_c.death.location = type('Location', (), {'country_name': 'United States', 'continent': 'North America', 'address': None})()
        person_c.residence = None

        self.mock_gedcom.people = [person_a, person_b, person_c]

        stats = analyzer.analyze()

        assert stats.total_flows == 0


class TestSankeyBuilder:
    """Test Sankey diagram construction."""
    
    def test_build_sankey_data(self):
        from_loc = LocationNode("Boston", "USA")
        to_loc = LocationNode("NYC", "USA")
        flow = MigrationFlow(from_loc, to_loc, "1850-1859")
        flow.flow_count = 5
        
        labels, idx_map, src, tgt, vals, incoming, outgoing = SankeyBuilder.build_sankey_data([flow], 10)
        
        assert len(labels) == 2
        assert "Boston, USA" in labels
        assert "NYC, USA" in labels
        assert len(src) == 1
        assert len(tgt) == 1
        assert vals[0] == 5
        assert incoming[idx_map["NYC, USA"]] == 5
        assert outgoing[idx_map["Boston, USA"]] == 5

        from_loc2 = LocationNode("Boston", "USA")
        to_loc2 = LocationNode("Winnipeg", "Canada")
        flow2 = MigrationFlow(from_loc2, to_loc2, "1890-1899")
        flow2.flow_count = 2
        flows = [flow, flow2]
        
        labels, idx_map, src, tgt, vals, incoming, outgoing = SankeyBuilder.build_sankey_data(flows, 10)
        
        assert len(labels) == 3
        assert "Boston, USA" in labels
        assert "NYC, USA" in labels
        assert "Winnipeg, Canada" in labels
        assert len(src) == 2
        assert len(tgt) == 2
        assert vals[0] == 5
        assert vals[1] == 2
        assert incoming[idx_map["NYC, USA"]] == 5
        assert outgoing[idx_map["Boston, USA"]] == 5 + 2
        assert incoming[idx_map["Winnipeg, Canada"]] == 2

        to_loc3 = LocationNode("London", "UK")
        flow3 = MigrationFlow(from_loc, to_loc3, "1990-1999")
        flow3.flow_count = 1
        flows = [flow, flow2, flow3]

        labels, idx_map, src, tgt, vals, incoming, outgoing = SankeyBuilder.build_sankey_data(flows, 10)
        assert len(labels) == 4
        assert "Boston, USA" in labels
        assert "NYC, USA" in labels
        assert "Winnipeg, Canada" in labels
        assert "London, UK"  in labels
        assert len(src) == 3
        assert len(tgt) == 3
        assert vals[0] == 5
        assert vals[1] == 2
        assert vals[2] == 1
        assert incoming[idx_map["NYC, USA"]] == 5
        assert outgoing[idx_map["Boston, USA"]] == 5 + 2 + 1
        assert incoming[idx_map["Winnipeg, Canada"]] == 2
        assert incoming[idx_map["London, UK"]] == 1

        # Result should keep only the top 2 nodes by incoming + outgoing flow.
        labels, idx_map, src, tgt, vals, incoming, outgoing = SankeyBuilder.build_sankey_data(flows, 2)
        
        assert len(labels) == 2
        assert "Boston, USA" in labels
        assert "NYC, USA" in labels
        assert "Winnipeg, Canada" not in labels
        assert "London, UK" not in labels
        assert len(src) == 1
        assert len(tgt) == 1
        assert vals[0] == 5
        assert incoming[idx_map["NYC, USA"]] == 5
        assert outgoing[idx_map["Boston, USA"]] == 5

    def test_build_sankey_data_returns_filtered_flow_indices(self):
        from_loc = LocationNode("Boston", "USA")
        flow1 = MigrationFlow(from_loc, LocationNode("NYC", "USA"), "1850-1859")
        flow1.flow_count = 5
        flow2 = MigrationFlow(from_loc, LocationNode("Winnipeg", "Canada"), "1890-1899")
        flow2.flow_count = 2
        flow3 = MigrationFlow(from_loc, LocationNode("London", "UK"), "1990-1999")
        flow3.flow_count = 1

        result = SankeyBuilder.build_sankey_data([flow1, flow2, flow3], 2, return_flow_indices=True)
        kept_flow_indices = result[-1]

        assert kept_flow_indices == [0]

    def test_period_color_assignment(self):
        """Test that time periods get assigned colors."""
        color_1800 = SankeyBuilder._get_period_color("1800-1809")
        color_1900 = SankeyBuilder._get_period_color("1900-1909")
        color_2000 = SankeyBuilder._get_period_color("2000-2009")
        
        # Just verify they're valid color strings
        assert "rgba" in color_1800
        assert "rgba" in color_1900
        assert "rgba" in color_2000
        assert color_1800 != color_1900  # Different periods should have different colors
    
    def test_create_sankey_figure_empty(self):
        """Test Sankey creation with no flows."""
        fig = SankeyBuilder.create_sankey_figure([])
        assert fig is not None


class TestMigrationFlowExporter:
    """Test migration flow exporter."""
    
    def setup_method(self):
        """Setup mock services."""
        self.mock_config = Mock()
        self.mock_config.get.side_effect = lambda x, default=None: {
            "resultpath": "/tmp",
            "ResultFile": "test.html",
            "GEDCOMinput": "test.ged",
            "LabelNames": False,
            "ExcludeUnknownMigrationCountries": False,
        }.get(x, default)
        
        self.mock_state = Mock()
        self.mock_progress = Mock()
        
        self.mock_gedcom = Mock()
        self.mock_gedcom.people = []
    
    def test_exporter_initialization(self):
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)
        assert exporter.svc_config == self.mock_config
        assert "_migration_sankey.html" in exporter.file_name
    
    def test_export_generates_html(self, tmp_path):
        """Test that export generates valid HTML file."""
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)
        
        output_file = str(tmp_path / "migration.html")
        result = exporter.export(self.mock_gedcom, output_file=output_file)
        
        assert Path(result).exists()
        
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "<!DOCTYPE html>" in content
            assert "Family Migration Flows" in content
            assert "plotly" in content.lower()
            assert "City and Country" in content
            assert "State/Province" in content
            assert "Country" in content
            assert "Continent" in content
            assert "tab-0" in content
            assert "tab-1" in content
            assert "tab-2" in content
            assert "tab-3" in content
            assert content.count("<html") == 1
            assert content.count("<body") == 1

    def test_build_scoped_gedcom_uses_referenced_people_when_all_entities_disabled(self):
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)

        person1 = Mock()
        person1.xref_id = "@I1@"
        person2 = Mock()
        person2.xref_id = "@I2@"
        self.mock_gedcom.people = {"@I1@": person1, "@I2@": person2}

        referenced = Mock()
        referenced.items = {"@I1@": {"value": "@I1@", "count": 1, "tag": None}}
        self.mock_state.Referenced = referenced

        scoped_gedcom = exporter._build_scoped_gedcom(self.mock_gedcom)

        assert scoped_gedcom is not self.mock_gedcom
        assert list(scoped_gedcom.people.keys()) == ["@I1@"]

    def test_build_scoped_gedcom_derives_selected_people_from_main_when_all_entities_disabled(self):
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)

        self.mock_state.Referenced = None
        self.mock_config.get.side_effect = lambda x, default=None: {
            "resultpath": "/tmp",
            "ResultFile": "test.html",
            "GEDCOMinput": "test.ged",
            "AllEntities": False,
            "Main": "@I1@",
            "MaxMissing": 0,
        }.get(x, default)

        main_person = MockPersonForSelection("@I1@", "Boston, USA", 1900, father="@I2@")
        father_person = MockPersonForSelection("@I2@", "London, UK", 1870)
        unrelated_person = MockPersonForSelection("@I3@", "Paris, France", 1910)

        self.mock_state.people = {
            "@I1@": main_person,
            "@I2@": father_person,
            "@I3@": unrelated_person,
        }
        self.mock_gedcom.people = dict(self.mock_state.people)

        scoped_gedcom = exporter._build_scoped_gedcom(self.mock_gedcom)

        assert scoped_gedcom is not self.mock_gedcom
        assert set(scoped_gedcom.people.keys()) == {"@I1@", "@I2@"}

    def test_filter_flows_for_known_countries_excludes_unknown_endpoints_when_enabled(self):
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)
        self.mock_config.get.side_effect = lambda x, default=None: {
            "resultpath": "/tmp",
            "ResultFile": "test.html",
            "GEDCOMinput": "test.ged",
            "LabelNames": False,
            "ExcludeUnknownMigrationCountries": True,
        }.get(x, default)

        known_flow = MigrationFlow(LocationNode("Boston", "United States"), LocationNode("Toronto", "Canada"), "1900-1909")
        unknown_start_flow = MigrationFlow(LocationNode("Albany", "New York"), LocationNode("Toronto", "Canada"), "1900-1909")
        unknown_end_flow = MigrationFlow(LocationNode("Boston", "United States"), LocationNode("Ontario", "Ont."), "1900-1909")

        filtered = exporter._filter_flows_for_known_countries(
            [known_flow, unknown_start_flow, unknown_end_flow],
            type("Gedcom", (), {"geo_config": MockGeoConfig()})(),
        )

        assert filtered == [known_flow]

    def test_build_flow_last_name_labels_limits_to_ten_surnames_sorted_by_frequency(self):
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)

        flow = MigrationFlow(LocationNode("Boston", "United States"), LocationNode("Toronto", "Canada"), "1900-1909")
        for person_id in [
            "@I1@", "@I2@", "@I3@", "@I4@", "@I5@", "@I6@",
            "@I7@", "@I8@", "@I9@", "@I10@", "@I11@", "@I12@", "@I13@", "@I14@",
        ]:
            flow.add_person(person_id, MigrationEventType.BIRTH)

        def make_person(person_id, surname):
            person = Mock()
            person.xref_id = person_id
            person.surname = surname
            person.name = f"Test /{surname}/"
            return person

        scoped_gedcom = type("Gedcom", (), {
            "people": {
                "@I1@": make_person("@I1@", "Smith"),
                "@I2@": make_person("@I2@", "Jones"),
                "@I3@": make_person("@I3@", "Brown"),
                "@I4@": make_person("@I4@", "Taylor"),
                "@I5@": make_person("@I5@", "Clark"),
                "@I6@": make_person("@I6@", "Smith"),
                "@I7@": make_person("@I7@", "Smith"),
                "@I8@": make_person("@I8@", "Brown"),
                "@I9@": make_person("@I9@", "Jones"),
                "@I10@": make_person("@I10@", "Adams"),
                "@I11@": make_person("@I11@", "Baker"),
                "@I12@": make_person("@I12@", "Cooper"),
                "@I13@": make_person("@I13@", "Davis"),
                "@I14@": make_person("@I14@", "Evans"),
            }
        })()

        labels = exporter._build_flow_last_name_labels([flow], scoped_gedcom)

        assert labels == ["Smith, Brown, Jones, Adams, Baker, Clark, Cooper, Davis, Evans, Taylor"]

    def test_build_flow_last_name_labels_uses_analyzed_flow_person_ids(self):
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)

        person = type('Person', (), {})
        person.xref_id = "@I1@"
        person.surname = "Smith"
        person.name = "John /Smith/"
        person.birth = MockEvent("Boston, USA", 1850)
        person.death = MockEvent("Toronto, Canada", 1920)
        person.residence = None

        scoped_gedcom = Mock()
        scoped_gedcom.people = [person]
        scoped_gedcom.geo_config = MockGeoConfig()

        analyzer = MigrationFlowAnalyzer(scoped_gedcom)
        analyzer.analyze()

        labels = exporter._build_flow_last_name_labels(analyzer.flows, scoped_gedcom)

        assert labels == ["Smith"]

    def test_aggregate_flows_for_state_province_merges_matching_routes(self):
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)

        flow_a = MigrationFlow(
            LocationNode("Boston", "USA", "North America", subdivision="Massachusetts"),
            LocationNode("Toronto", "Canada", "North America", subdivision="Ontario"),
            "1900-1909",
        )
        flow_a.add_person("@I1@", MigrationEventType.BIRTH)

        flow_b = MigrationFlow(
            LocationNode("Springfield", "USA", "North America", subdivision="Massachusetts"),
            LocationNode("Ottawa", "Canada", "North America", subdivision="Ontario"),
            "1900-1909",
        )
        flow_b.add_person("@I2@", MigrationEventType.BIRTH)

        aggregated_flows, aggregated_locations = exporter._aggregate_flows_for_grouping(
            [flow_a, flow_b],
            "State/Province",
        )

        assert len(aggregated_flows) == 1
        assert aggregated_flows[0].flow_count == 2
        assert aggregated_flows[0].from_location.get_display_name("State/Province") == "Massachusetts, USA"
        assert aggregated_flows[0].to_location.get_display_name("State/Province") == "Ontario, Canada"
        assert len(aggregated_locations) == 2

    def test_aggregate_flows_for_country_merges_matching_routes(self):
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)

        flow_a = MigrationFlow(
            LocationNode("Boston", "USA", "North America", subdivision="Massachusetts"),
            LocationNode("Toronto", "Canada", "North America", subdivision="Ontario"),
            "1900-1909",
        )
        flow_a.add_person("@I1@", MigrationEventType.BIRTH)

        flow_b = MigrationFlow(
            LocationNode("Chicago", "USA", "North America", subdivision="Illinois"),
            LocationNode("Vancouver", "Canada", "North America", subdivision="British Columbia"),
            "1900-1909",
        )
        flow_b.add_person("@I2@", MigrationEventType.BIRTH)

        aggregated_flows, _ = exporter._aggregate_flows_for_grouping([flow_a, flow_b], "Country")

        assert len(aggregated_flows) == 1
        assert aggregated_flows[0].flow_count == 2
        assert aggregated_flows[0].from_location.get_display_name("Country") == "USA"
        assert aggregated_flows[0].to_location.get_display_name("Country") == "Canada"

    def test_aggregate_flows_for_country_keeps_different_time_periods_separate(self):
        exporter = MigrationFlowExporter(self.mock_config, self.mock_state, self.mock_progress)

        flow_a = MigrationFlow(
            LocationNode("Boston", "USA", "North America", subdivision="Massachusetts"),
            LocationNode("Toronto", "Canada", "North America", subdivision="Ontario"),
            "1900-1909",
        )
        flow_a.add_person("@I1@", MigrationEventType.BIRTH)

        flow_b = MigrationFlow(
            LocationNode("Chicago", "USA", "North America", subdivision="Illinois"),
            LocationNode("Vancouver", "Canada", "North America", subdivision="British Columbia"),
            "1910-1919",
        )
        flow_b.add_person("@I2@", MigrationEventType.BIRTH)

        aggregated_flows, _ = exporter._aggregate_flows_for_grouping([flow_a, flow_b], "Country")

        assert len(aggregated_flows) == 2
        assert {flow.time_period for flow in aggregated_flows} == {"1900-1909", "1910-1919"}


class TestSankeyFigureLayout:
    def test_calculate_plot_height_uses_minimum_for_small_flow_counts(self):
        assert SankeyBuilder.calculate_plot_height(25) == 500

    def test_calculate_plot_height_uses_maximum_for_large_flow_counts(self):
        assert SankeyBuilder.calculate_plot_height(250) == 1200

    def test_calculate_plot_height_scales_between_thresholds(self):
        assert SankeyBuilder.calculate_plot_height(125) == 850

    def test_create_sankey_figure_adds_top_clearance_for_title(self):
        flow = MigrationFlow(
            LocationNode("Boston", "United States"),
            LocationNode("Toronto", "Canada"),
            "1900-1909",
        )
        flow.add_person("@I1@", MigrationEventType.BIRTH)

        fig = SankeyBuilder.create_sankey_figure([flow], title="Sample Title")

        assert fig.layout.height == 620
        assert fig.layout.margin.t == 110
        assert fig.layout.margin.b == 120
        assert fig.layout.title.pad.b == 24

    def test_create_sankey_figure_uses_dynamic_height_for_total_flow_count(self):
        flow = MigrationFlow(
            LocationNode("Boston", "United States"),
            LocationNode("Toronto", "Canada"),
            "1900-1909",
        )
        flow.add_person("@I1@", MigrationEventType.BIRTH)

        additional_flows = []
        for index in range(60):
            extra_flow = MigrationFlow(
                LocationNode(f"City{index}", "United States"),
                LocationNode(f"Town{index}", "Canada"),
                "1900-1909",
            )
            extra_flow.add_person(f"@I{index + 2}@", MigrationEventType.BIRTH)
            additional_flows.append(extra_flow)

        fig = SankeyBuilder.create_sankey_figure([flow, *additional_flows], max_flow_count=25, title="Sample Title")

        assert fig.layout.height == 671

    def test_create_sankey_figure_includes_last_names_in_hover_when_provided(self):
        flow = MigrationFlow(
            LocationNode("Boston", "United States"),
            LocationNode("Toronto", "Canada"),
            "1900-1909",
        )
        flow.add_person("@I1@", MigrationEventType.BIRTH)

        fig = SankeyBuilder.create_sankey_figure([flow], title="Sample Title", link_labels=["Smith, Jones"])

        assert "last names:" in fig.data[0].link.hovertemplate
        assert list(fig.data[0].link.customdata) == ["Smith, Jones"]


class TestIntegration:
    """Integration tests with realistic data."""
    
    @pytest.mark.slow
    def test_full_migration_flow_analysis(self):
        """Test complete migration analysis workflow."""
        # Create mock genealogical data
        mock_gedcom = Mock()
        
        # Create mock people with realistic migration patterns
        people = []
        
        for i in range(5):
            person = type('Person', (), {})
            
            # Birth in Europe
            birth = type('Birth', (), {})
            birth.place = "London, England"
            birth.date = type('Date', (), {'year_num': 1800 + (i * 10)})
            person.birth = birth
            
            # Death in America
            death = type('Death', (), {})
            death.place = "Boston, Massachusetts, USA"
            death.date = type('Date', (), {'year_num': 1880 + (i * 10)})
            person.death = death
            
            person.residence = None
            people.append(person)
        
        mock_gedcom.people = people
        
        # Analyze
        analyzer = MigrationFlowAnalyzer(mock_gedcom)
        stats = analyzer.analyze()
        
        # Verify results
        assert stats.total_flows > 0
        assert stats.total_people_moved > 0
        assert len(analyzer.locations) >= 2  # At least origin and destination