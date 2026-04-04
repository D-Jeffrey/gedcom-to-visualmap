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
        assert node_no_continent.get_display_name("Continent") == "France"
    
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
        assert events[0] == ("Boston", "USA", 1850, "")
    
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

        # result hould cut off the 3rd item
        labels, idx_map, src, tgt, vals, incoming, outgoing = SankeyBuilder.build_sankey_data(flows, 2)
        
        assert len(labels) == 3
        assert "Boston, USA" in labels
        assert "NYC, USA" in labels
        assert "Winnipeg, Canada" in labels
        assert "London, UK" not in labels
        assert len(src) == 2
        assert len(tgt) == 2
        assert vals[0] == 5
        assert vals[1] == 2
        assert incoming[idx_map["NYC, USA"]] == 5
        assert outgoing[idx_map["Boston, USA"]] == 5 + 2
        assert incoming[idx_map["Winnipeg, Canada"]] == 2

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
            "GEDCOMinput": "test.ged"
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
            assert "Country" in content
            assert "Continent" in content
            assert "tab-0" in content
            assert "tab-1" in content
            assert "tab-2" in content


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