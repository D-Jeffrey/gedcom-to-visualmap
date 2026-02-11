"""
Tests for statistics_markdown module.
"""
import pytest
import os
from pathlib import Path
from render.statistics_markdown import (
    write_statistics_markdown,
    write_statistics_html,
    _generate_markdown_content,
    _format_names_tables,
    _format_gender_chart,
)


@pytest.fixture
def sample_stats_dict():
    """Create sample statistics dictionary for testing."""
    return {
        'demographics': {
            'total_people': 150,
            'living': 45,
            'deceased': 105,
            'average_lifespan': 72.5,
            'median_lifespan': 71.0,
            'min_lifespan': 0,
            'max_lifespan': 98,
        },
        'gender': {
            'male': 75,
            'female': 70,
            'unknown': 5,
            'total': 150,
            'male_percentage': 50.0,
            'female_percentage': 46.7,
            'unknown_percentage': 3.3,
        },
        'names': {
            'most_common_first_names': {
                'John': 45,
                'Mary': 38,
                'William': 32,
                'Elizabeth': 28,
                'James': 25,
            },
            'most_common_surnames': {
                'Smith': 52,
                'Johnson': 41,
                'Williams': 35,
                'Brown': 28,
                'Jones': 24,
            },
            'unique_first_names': 80,
            'unique_surnames': 120,
        },
        'ages': {
            'living_people_count': 45,
            'average_age_living': 35.5,
            'oldest_living_age': 85,
            'youngest_living_age': 0,
        },
        'births': {
            'birth_months': {
                'January': 15,
                'February': 12,
                'March': 18,
            },
            'earliest_birth_year': 1920,
            'latest_birth_year': 2020,
        },
        'births': {
            'earliest_birth_year': 1920,
            'latest_birth_year': 2020,
            'birth_year_span': 100,
            'birth_months': {
                'January': 15,
                'February': 12,
                'March': 18,
            },
        },
        'timeline': {
            'earliest_year': 1920,
            'latest_year': 2020,
            'timeline_span_years': 100,
        },
        'marriage': {
            'total_people': 150,
            'people_with_marriages': 90,
            'total_marriages_recorded': 85,
            'average_marriage_age': 25.5,
        },
        'geographic': {
            'most_common_birth_places': {
                'London': 25,
                'New York': 20,
                'Paris': 15,
            },
        },
        'events': {
            'total_people': 150,
            'completeness': {
                'birth': {
                    'total': 140,
                    'with_date': 120,
                    'with_place': 110,
                    'date_percentage': 85.7,
                    'place_percentage': 78.6,
                },
                'death': {
                    'total': 105,
                    'with_date': 95,
                    'with_place': 90,
                    'date_percentage': 90.5,
                    'place_percentage': 85.7,
                },
            },
        },
        'relationship_path': {
            'focus_person_id': 'I1',
            'focus_person_name': 'John Smith',
            'total_people_analyzed': 150,
            'total_relationships_found': 149,
            'direct_ancestors': 45,
            'direct_descendants': 32,
            'blood_relatives': 50,
            'relatives_by_marriage': 22,
            'generation_span': 7,  # 8 generations total (0 to 7, or -3 to +4, etc.)
            'oldest_generation': -3,
            'youngest_generation': 4,
        },
    }


@pytest.fixture
def sample_stats_object(sample_stats_dict):
    """Create mock Statistics object."""
    class MockStats:
        def to_dict(self):
            return sample_stats_dict
    return MockStats()


class TestWriteStatisticsMarkdown:
    """Tests for write_statistics_markdown function."""
    
    def test_write_markdown_with_dict(self, tmp_path, sample_stats_dict):
        """Test writing markdown report with dictionary input."""
        output_file = tmp_path / "test_report.md"
        html_file = tmp_path / "test_report.html"
        
        write_statistics_markdown(sample_stats_dict, str(output_file))
        
        # Check markdown file was created
        assert output_file.exists()
        content = output_file.read_text()
        
        # Verify key sections are present
        assert "# 📊 Genealogical Statistics Report" in content
        assert "## 🎯 Executive Summary" in content
        assert "## 👥 Demographics" in content
        assert "### Popular Names" in content
        assert "### Gender Distribution" in content
        
        # Check HTML file was also created
        assert html_file.exists()
    
    def test_write_markdown_with_stats_object(self, tmp_path, sample_stats_object):
        """Test writing markdown report with Statistics object input."""
        output_file = tmp_path / "test_report.md"
        
        write_statistics_markdown(sample_stats_object, str(output_file))
        
        assert output_file.exists()
        content = output_file.read_text()
        assert "Genealogical Statistics Report" in content
    
    def test_write_markdown_creates_both_files(self, tmp_path, sample_stats_dict):
        """Test that both .md and .html files are created."""
        output_file = tmp_path / "test_report.md"
        html_file = tmp_path / "test_report.html"
        
        write_statistics_markdown(sample_stats_dict, str(output_file))
        
        assert output_file.exists()
        assert html_file.exists()
    
    def test_write_markdown_with_missing_categories(self, tmp_path):
        """Test handling of missing data categories."""
        minimal_stats = {
            'demographics': {
                'total_people': 100,
            }
        }
        
        output_file = tmp_path / "minimal_report.md"
        write_statistics_markdown(minimal_stats, str(output_file))
        
        assert output_file.exists()
        content = output_file.read_text()
        assert "Executive Summary" in content


class TestWriteStatisticsHtml:
    """Tests for write_statistics_html function."""
    
    def test_write_html_with_dict(self, tmp_path, sample_stats_dict):
        """Test writing HTML report with dictionary input."""
        output_file = tmp_path / "test_report.html"
        
        write_statistics_html(sample_stats_dict, str(output_file))
        
        assert output_file.exists()
        content = output_file.read_text()
        
        # Verify HTML structure
        assert "<!DOCTYPE html>" in content
        assert "<html lang=\"en\"" in content
        assert "markdown-it" in content
        assert "github-markdown" in content
        
        # Verify dark mode support
        assert "data-color-mode=\"auto\"" in content
        assert "prefers-color-scheme: dark" in content
        assert "#0d1117" in content  # Dark mode background color
        
    def test_html_contains_markdown_content(self, tmp_path, sample_stats_dict):
        """Test that HTML file contains the markdown content."""
        output_file = tmp_path / "test_report.html"
        
        write_statistics_html(sample_stats_dict, str(output_file))
        
        content = output_file.read_text()
        
        # Check that key markdown content is embedded
        assert "Genealogical Statistics Report" in content
        assert "Executive Summary" in content


class TestFormatNamesTable:
    """Tests for _format_names_tables function."""
    
    def test_format_names_with_bar_charts(self):
        """Test that names table includes horizontal bar charts."""
        names_data = {
            'most_common_first_names': {
                'John': 45,
                'Mary': 38,
                'William': 32,
            },
            'most_common_surnames': {
                'Smith': 52,
                'Johnson': 41,
                'Williams': 35,
            },
        }
        
        result = _format_names_tables(names_data)
        
        # Check for table headers
        assert "| Rank | Name | Count | Distribution |" in result
        assert "| Rank | Surname | Count | Distribution |" in result
        
        # Check for bar characters
        assert "█" in result
        
        # Check for data rows
        assert "John" in result
        assert "45" in result
        assert "Smith" in result
        assert "52" in result
    
    def test_format_names_empty_data(self):
        """Test handling of empty names data."""
        result = _format_names_tables({})
        
        # Should return empty string or minimal content
        assert isinstance(result, str)
    
    def test_format_names_bar_scaling(self):
        """Test that bars are scaled correctly."""
        names_data = {
            'most_common_first_names': {
                'John': 100,
                'Mary': 50,
                'William': 25,
            },
        }
        
        result = _format_names_tables(names_data)
        
        # John should have the longest bar (30 chars)
        # Mary should have half (15 chars)
        # William should have quarter (7-8 chars)
        lines = result.split('\n')
        john_line = [l for l in lines if 'John' in l][0]
        mary_line = [l for l in lines if 'Mary' in l][0]
        william_line = [l for l in lines if 'William' in l][0]
        
        # Count █ characters in each
        john_bars = john_line.count('█')
        mary_bars = mary_line.count('█')
        william_bars = william_line.count('█')
        
        assert john_bars == 30  # Max bars
        assert mary_bars == 15  # Half of max
        assert william_bars == 7  # Quarter of max (rounded down)


class TestFormatGenderChart:
    """Tests for _format_gender_chart function."""
    
    def test_format_gender_chart_basic(self):
        """Test basic gender chart formatting."""
        gender_data = {
            'male': 75,
            'female': 70,
            'unknown': 5,
            'total': 150,
            'male_percentage': 50.0,
            'female_percentage': 46.7,
            'unknown_percentage': 3.3,
        }
        
        result = _format_gender_chart(gender_data)
        
        # Check for ASCII chart elements
        assert "█" in result or "■" in result
        assert "Male" in result or "♂" in result
        assert "Female" in result or "♀" in result
        assert "50.0" in result or "50%" in result
    
    def test_format_gender_chart_handles_missing_data(self):
        """Test handling of incomplete gender data."""
        gender_data = {
            'male': 50,
            'female': 50,
        }
        
        result = _format_gender_chart(gender_data)
        
        # Should not crash with missing fields
        assert isinstance(result, str)


class TestGenerateMarkdownContent:
    """Tests for _generate_markdown_content function."""
    
    def test_generate_content_includes_all_sections(self, sample_stats_dict):
        """Test that all major sections are included."""
        result = _generate_markdown_content(sample_stats_dict)
        
        # Check for all major sections
        assert "Executive Summary" in result
        assert "Demographics" in result
        assert "Temporal Patterns" in result or "timeline" in result.lower()
        assert "Family Relationships" in result or "marriage" in result.lower()
        assert "Geographic" in result or "geographic" in result.lower()
        assert "Data Quality" in result
    
    def test_generate_content_with_partial_data(self):
        """Test content generation with partial statistics."""
        partial_stats = {
            'demographics': {'total_people': 100},
            'gender': {'male': 50, 'female': 50},
        }
        
        result = _generate_markdown_content(partial_stats)
        
        # Should still generate valid markdown
        assert "# 📊" in result
        assert "Demographics" in result
    
    def test_generate_content_is_valid_markdown(self, sample_stats_dict):
        """Test that generated content is valid markdown."""
        result = _generate_markdown_content(sample_stats_dict)
        
        # Check for markdown elements
        assert result.startswith("#")  # Header
        assert "|" in result  # Tables
        assert "---" in result  # Horizontal rules
        assert "**" in result or "*" in result  # Bold/italic


class TestIntegration:
    """Integration tests for the complete workflow."""
    
    def test_end_to_end_workflow(self, tmp_path, sample_stats_dict):
        """Test complete workflow from stats dict to output files."""
        output_file = tmp_path / "integration_test.md"
        html_file = tmp_path / "integration_test.html"
        
        # Generate files
        write_statistics_markdown(sample_stats_dict, str(output_file))
        
        # Verify both files exist
        assert output_file.exists()
        assert html_file.exists()
        
        # Verify markdown content
        md_content = output_file.read_text()
        assert len(md_content) > 1000  # Should be substantial
        assert "Executive Summary" in md_content
        assert "Demographics" in md_content
        
        # Verify HTML content
        html_content = html_file.read_text()
        assert "<!DOCTYPE html>" in html_content
        assert "markdown-it" in html_content
        assert "Executive Summary" in html_content
    
    def test_file_size_reasonable(self, tmp_path, sample_stats_dict):
        """Test that generated files are reasonable in size."""
        output_file = tmp_path / "size_test.md"
        
        write_statistics_markdown(sample_stats_dict, str(output_file))
        
        md_size = output_file.stat().st_size
        html_file = tmp_path / "size_test.html"
        html_size = html_file.stat().st_size
        
        # Files should not be empty and not excessively large
        assert 500 < md_size < 500000  # 500 bytes to 500KB
        assert 1000 < html_size < 1000000  # 1KB to 1MB
