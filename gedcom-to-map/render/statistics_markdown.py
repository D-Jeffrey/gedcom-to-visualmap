"""
statistics_markdown.py - Generate rich Markdown reports for GEDCOM statistics.

This module creates visually appealing Markdown reports with embedded charts,
tables, and formatted statistics from genealogical data analysis.

Author: AI Assistant
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def write_statistics_html(stats_dict: Any, output_file: str) -> None:
    """
    Write statistics report as HTML that renders markdown beautifully in browser.
    
    Creates an HTML file with embedded markdown content and markdown-it library
    for client-side rendering with GitHub-style formatting.
    
    Args:
        stats_dict: Statistics object or dictionary of statistics from Stats.to_dict()
        output_file: Output HTML file path (.html extension)
    """
    try:
        # Handle both Statistics objects and dicts
        if hasattr(stats_dict, 'to_dict'):
            stats_data = stats_dict.to_dict()
        elif hasattr(stats_dict, 'results') and hasattr(stats_dict.results, 'to_dict'):
            stats_data = stats_dict.results.to_dict()
        else:
            stats_data = stats_dict
        
        markdown_content = _generate_markdown_content(stats_data)
        
        # Generate HTML with markdown renderer
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Genealogical Statistics Report</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.0/github-markdown.min.css">
    <script src="https://cdn.jsdelivr.net/npm/markdown-it@14.0.0/dist/markdown-it.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background-color: #f6f8fa;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }}
        .markdown-body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: 980px;
            margin: 0 auto;
            padding: 45px;
            background-color: white;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        }}
        @media (max-width: 767px) {{
            .markdown-body {{
                padding: 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="markdown-body" id="content"></div>
    <script>
        var md = window.markdownit({{
            html: true,
            linkify: true,
            typographer: true
        }});
        var markdownText = {repr(markdown_content)};
        document.getElementById('content').innerHTML = md.render(markdownText);
    </script>
</body>
</html>
'''
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Statistics HTML report written to {output_file}")
    except Exception as e:
        logger.error(f"Failed to write statistics HTML to {output_file}: {e}")
        raise


def write_statistics_markdown(stats_dict: Any, output_file: str) -> None:
    """
    Write comprehensive statistics report as Markdown with charts and visualizations.
    
    Creates a rich, formatted Markdown document containing:
    - Executive summary with key metrics
    - Demographic analysis with charts
    - Temporal patterns and timelines  
    - Family relationship statistics
    - Geographic distribution
    - Data quality metrics
    
    Args:
        stats_dict: Statistics object or dictionary of statistics from Stats.to_dict()
        output_file: Output markdown file path (.md extension)
        
    Example:
        stats = pipeline.run(people)
        write_statistics_markdown(stats, 'report.md')  # Handles Statistics object
        # or
        write_statistics_markdown(stats.to_dict(), 'report.md')  # Handles dict
    """
    try:
        # Handle both Statistics objects and dicts
        if hasattr(stats_dict, 'to_dict'):
            stats_data = stats_dict.to_dict()
        elif hasattr(stats_dict, 'results') and hasattr(stats_dict.results, 'to_dict'):
            stats_data = stats_dict.results.to_dict()
        else:
            stats_data = stats_dict
        
        markdown_content = _generate_markdown_content(stats_data)
        
        # Write markdown file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        logger.info(f"Statistics markdown report written to {output_file}")
        
        # Also create HTML version for browser viewing
        html_file = output_file.rsplit('.', 1)[0] + '.html'
        write_statistics_html(stats_data, html_file)
        
    except Exception as e:
        logger.error(f"Failed to write statistics markdown to {output_file}: {e}")
        raise


def _generate_markdown_content(stats: Dict[str, Any]) -> str:
    """Generate the complete markdown content."""
    sections = []
    
    # Header
    sections.append(_header())
    
    # Executive Summary
    sections.append(_executive_summary(stats))
    
    # Demographics Section
    if 'demographics' in stats or 'gender' in stats or 'names' in stats or 'ages' in stats or 'births' in stats:
        sections.append(_demographics_section(stats))
    
    # Temporal Patterns Section
    if 'longevity' in stats or 'timeline' in stats:
        sections.append(_temporal_section(stats))
    
    # Family Relationships Section
    if any(k in stats for k in ['marriage', 'children', 'relationship_status', 'divorce', 'relationship_path']):
        sections.append(_family_section(stats))
    
    # Geographic Section
    if 'geographic' in stats:
        sections.append(_geographic_section(stats))
    
    # Data Quality Section
    if 'events' in stats:
        sections.append(_data_quality_section(stats))
    
    # Footer
    sections.append(_footer())
    
    return '\n\n'.join(sections)


def _header() -> str:
    """Generate report header."""
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    return f"""# 📊 Genealogical Statistics Report

**Generated:** {now}

---

[TOC]

---"""


def _executive_summary(stats: Dict[str, Any]) -> str:
    """Generate executive summary with key metrics."""
    lines = ["## 🎯 Executive Summary\n"]
    
    # Get key metrics
    demographics = stats.get('demographics', {})
    gender = stats.get('gender', {})
    marriage = stats.get('marriage', {})
    timeline = stats.get('timeline', {})
    
    total_people = demographics.get('total_people', 'N/A')
    living = demographics.get('living', 'N/A')
    deceased = demographics.get('deceased', 'N/A')
    avg_lifespan = demographics.get('average_lifespan', 'N/A')
    
    # Format lifespan
    lifespan_str = f"{avg_lifespan:.1f} years" if isinstance(avg_lifespan, (int, float)) else str(avg_lifespan)
    
    lines.append("### Key Metrics\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| 👥 **Total People** | **{total_people:,}** |" if isinstance(total_people, int) else f"| 👥 **Total People** | {total_people} |")
    lines.append(f"| ✅ Living | {living:,} |" if isinstance(living, int) else f"| ✅ Living | {living} |")
    lines.append(f"| 💀 Deceased | {deceased:,} |" if isinstance(deceased, int) else f"| 💀 Deceased | {deceased} |")
    lines.append(f"| ⏳ Average Lifespan | {lifespan_str} |")
    
    # Gender distribution
    male = gender.get('male', 0)
    female = gender.get('female', 0)
    if male or female:
        lines.append(f"| ♂️ Male | {male:,} |")
        lines.append(f"| ♀️ Female | {female:,} |")
    
    # Marriage stats
    total_marriages = marriage.get('total_marriages_recorded', 0)
    if total_marriages:
        lines.append(f"| 💍 Total Marriages | {total_marriages:,} |")
    
    # Timeline
    earliest_year = timeline.get('earliest_year')
    latest_year = timeline.get('latest_year')
    if earliest_year and latest_year:
        span = latest_year - earliest_year
        lines.append(f"| 📅 Time Span | {earliest_year} - {latest_year} ({span} years) |")
    
    return '\n'.join(lines)


def _demographics_section(stats: Dict[str, Any]) -> str:
    """Generate demographics section with charts."""
    lines = ["## 👥 Demographics\n"]
    
    # Gender distribution
    gender = stats.get('gender', {})
    if gender:
        lines.append("### Gender Distribution\n")
        lines.append(_format_gender_chart(gender))
        lines.append("")
    
    # Names statistics
    names = stats.get('names', {})
    if names:
        lines.append("### Popular Names\n")
        lines.append(_format_names_tables(names))
        lines.append("")
    
    # Ages and lifespan
    ages = stats.get('ages', {})
    demographics = stats.get('demographics', {})
    if ages or demographics:
        lines.append("### Age & Lifespan Statistics\n")
        lines.append(_format_lifespan_stats(ages, demographics))
        lines.append("")
    
    # Birth patterns
    births = stats.get('births', {})
    if births:
        lines.append("### Birth Patterns\n")
        lines.append(_format_birth_patterns(births))
        lines.append("")
    
    return '\n'.join(lines)


def _temporal_section(stats: Dict[str, Any]) -> str:
    """Generate temporal patterns section."""
    lines = ["## ⏰ Temporal Patterns\n"]
    
    # Longevity trends
    longevity = stats.get('longevity', {})
    if longevity:
        lines.append("### Longevity & Mortality\n")
        lines.append(_format_longevity_stats(longevity))
        lines.append("")
    
    # Timeline and events
    timeline = stats.get('timeline', {})
    if timeline:
        lines.append("### Historical Timeline\n")
        lines.append(_format_timeline_stats(timeline))
        lines.append("")
    
    return '\n'.join(lines)


def _family_section(stats: Dict[str, Any]) -> str:
    """Generate family relationships section."""
    lines = ["## 👨‍👩‍👧‍👦 Family Relationships\n"]
    
    # Marriage statistics
    marriage = stats.get('marriage', {})
    if marriage:
        lines.append("### Marriage Statistics\n")
        lines.append(_format_marriage_stats(marriage))
        lines.append("")
    
    # Divorce statistics
    divorce = stats.get('divorce', {})
    if divorce:
        lines.append("### Divorce Patterns\n")
        lines.append(_format_divorce_stats(divorce))
        lines.append("")
    
    # Children statistics
    children = stats.get('children', {})
    if children:
        lines.append("### Children & Family Size\n")
        lines.append(_format_children_stats(children))
        lines.append("")
    
    # Relationship status
    rel_status = stats.get('relationship_status', {})
    if rel_status:
        lines.append("### Relationship Status\n")
        lines.append(_format_relationship_status(rel_status))
        lines.append("")
    
    # Relationship paths
    rel_path = stats.get('relationship_path', {})
    if rel_path:
        lines.append("### Family Connections\n")
        lines.append(_format_relationship_path(rel_path))
        lines.append("")
    
    return '\n'.join(lines)


def _geographic_section(stats: Dict[str, Any]) -> str:
    """Generate geographic distribution section."""
    lines = ["## 🌍 Geographic Distribution\n"]
    
    geographic = stats.get('geographic', {})
    if not geographic:
        return ""
    
    # Top birth places
    birth_places = geographic.get('most_common_birth_places', {})
    if birth_places:
        lines.append("### Most Common Birth Places\n")
        lines.append(_format_place_table(birth_places, "Birth Place"))
        lines.append("")
    
    # Top death places
    death_places = geographic.get('most_common_death_places', {})
    if death_places:
        lines.append("### Most Common Death Places\n")
        lines.append(_format_place_table(death_places, "Death Place"))
        lines.append("")
    
    return '\n'.join(lines)


def _data_quality_section(stats: Dict[str, Any]) -> str:
    """Generate data quality metrics section."""
    lines = ["## 📈 Data Quality Metrics\n"]
    
    events = stats.get('events', {})
    if not events:
        return ""
    
    lines.append("### Event Data Completeness\n")
    
    completeness = events.get('completeness', {})
    if completeness:
        lines.append("| Event Type | Total | With Date | With Place | Date % | Place % |")
        lines.append("|------------|-------|-----------|------------|--------|---------|")
        
        # Event types stored in lowercase by collector, but display capitalized
        event_types = [('birth', 'Birth'), ('death', 'Death'), ('marriage', 'Marriage'), ('burial', 'Burial')]
        
        for event_key, event_display in event_types:
            event_data = completeness.get(event_key, {})
            if event_data:
                total = event_data.get('total', 0)
                with_date = event_data.get('with_date', 0)
                with_place = event_data.get('with_place', 0)
                date_pct = event_data.get('date_percentage', 0)
                place_pct = event_data.get('place_percentage', 0)
                
                lines.append(f"| {event_display} | {total:,} | {with_date:,} | {with_place:,} | {date_pct:.1f}% | {place_pct:.1f}% |")
    
    return '\n'.join(lines)


def _footer() -> str:
    """Generate report footer."""
    return """---

## 📝 Notes

This report was automatically generated from GEDCOM data using the gedcom-to-visualmap statistics module.

**Methodology:**
- Statistics are collected using specialized analyzer modules
- Charts and visualizations provide quick insights into patterns
- Missing data is excluded from calculations where appropriate

**Interpreting Results:**
- Percentages are rounded to one decimal place
- Age calculations use complete date information when available
- Family relationships are traced through parent-child and spouse connections

---

*Generated by gedcom-to-visualmap Statistics Module*"""


# Formatting helper functions

def _format_gender_chart(gender: Dict[str, Any]) -> str:
    """Create ASCII bar chart for gender distribution."""
    male = gender.get('male', 0)
    female = gender.get('female', 0)
    unknown = gender.get('unknown', 0)
    total = male + female + unknown
    
    if total == 0:
        return "No gender data available."
    
    male_pct = (male / total * 100) if total > 0 else 0
    female_pct = (female / total * 100) if total > 0 else 0
    unknown_pct = (unknown / total * 100) if total > 0 else 0
    
    # Calculate bar widths (out of 50 chars)
    male_bar = int(male_pct / 2)
    female_bar = int(female_pct / 2)
    unknown_bar = int(unknown_pct / 2)
    
    lines = []
    lines.append("| Gender | Count | Percentage | Distribution |")
    lines.append("|--------|-------|------------|--------------|")
    lines.append(f"| ♂️ Male | {male:,} | {male_pct:.1f}% | {'█' * male_bar} |")
    lines.append(f"| ♀️ Female | {female:,} | {female_pct:.1f}% | {'█' * female_bar} |")
    if unknown > 0:
        lines.append(f"| ❓ Unknown | {unknown:,} | {unknown_pct:.1f}% | {'█' * unknown_bar} |")
    
    return '\n'.join(lines)


def _format_names_tables(names: Dict[str, Any]) -> str:
    """Format top names as tables with horizontal bar charts."""
    lines = []
    
    # First names
    first_names = names.get('most_common_first_names', {})
    if first_names:
        lines.append("**Most Common First Names:**\n")
        lines.append("| Rank | Name | Count | Distribution |")
        lines.append("|------|------|-------|--------------|")
        
        # Get top 10 names and calculate max for scaling
        top_first = list(first_names.items())[:10]
        max_count = max((count for _, count in top_first), default=1)
        
        for i, (name, count) in enumerate(top_first, 1):
            # Create horizontal bar (max 30 chars)
            bar_length = int((count / max_count) * 30) if max_count > 0 else 0
            bar = '█' * bar_length
            lines.append(f"| {i} | {name} | {count:,} | {bar} |")
        lines.append("")
    
    # Surnames
    surnames = names.get('most_common_surnames', {})
    if surnames:
        lines.append("**Most Common Surnames:**\n")
        lines.append("| Rank | Surname | Count | Distribution |")
        lines.append("|------|---------|-------|--------------|")
        
        # Get top 10 surnames and calculate max for scaling
        top_surnames = list(surnames.items())[:10]
        max_count = max((count for _, count in top_surnames), default=1)
        
        for i, (name, count) in enumerate(top_surnames, 1):
            # Create horizontal bar (max 30 chars)
            bar_length = int((count / max_count) * 30) if max_count > 0 else 0
            bar = '█' * bar_length
            lines.append(f"| {i} | {name} | {count:,} | {bar} |")
    
    return '\n'.join(lines)


def _format_lifespan_stats(ages: Dict[str, Any], demographics: Dict[str, Any]) -> str:
    """Format lifespan and age statistics."""
    lines = []
    
    # Key lifespan metrics
    avg_lifespan = demographics.get('average_lifespan')
    median_lifespan = demographics.get('median_lifespan')
    min_lifespan = demographics.get('min_lifespan')
    max_lifespan = demographics.get('max_lifespan')
    
    if any([avg_lifespan, median_lifespan, min_lifespan, max_lifespan]):
        lines.append("**Lifespan Overview:**\n")
        lines.append("| Metric | Years |")
        lines.append("|--------|-------|")
        if avg_lifespan is not None:
            lines.append(f"| Average | {avg_lifespan:.1f} |")
        if median_lifespan is not None:
            lines.append(f"| Median | {median_lifespan:.1f} |")
        if min_lifespan is not None:
            lines.append(f"| Minimum | {min_lifespan} |")
        if max_lifespan is not None:
            lines.append(f"| Maximum | {max_lifespan} |")
        lines.append("")
    
    # Oldest/youngest living
    oldest_living = ages.get('oldest_living')
    youngest_living = ages.get('youngest_living')
    
    if oldest_living or youngest_living:
        lines.append("**Living Individuals:**\n")
        if oldest_living:
            name = oldest_living.get('name', 'Unknown')
            age = oldest_living.get('age', 'Unknown')
            lines.append(f"- 👴 **Oldest Living:** {name} ({age} years)")
        if youngest_living:
            name = youngest_living.get('name', 'Unknown')
            age = youngest_living.get('age', 'Unknown')
            lines.append(f"- 👶 **Youngest Living:** {name} ({age} years)")
    
    return '\n'.join(lines)


def _format_birth_patterns(births: Dict[str, Any]) -> str:
    """Format birth pattern statistics."""
    lines = []
    
    # Birth months
    months = births.get('birth_months_distribution', {})
    if months:
        lines.append("**Birth Months Distribution:**\n")
        # Convert to sorted list
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        
        lines.append("| Month | Births | Chart |")
        lines.append("|-------|--------|-------|")
        
        max_count = max(months.values()) if months else 1
        for month_name in month_names:
            count = months.get(month_name, 0)
            if count > 0:
                bar_length = int((count / max_count) * 20)
                lines.append(f"| {month_name} | {count:,} | {'▓' * bar_length} |")
        lines.append("")
    
    # Most/least common months
    most_common = births.get('most_common_birth_month')
    least_common = births.get('least_common_birth_month')
    
    if most_common or least_common:
        lines.append("**Notable Patterns:**\n")
        if most_common:
            month = most_common.get('month', 'Unknown')
            count = most_common.get('count', 0)
            lines.append(f"- 📈 **Peak Birth Month:** {month} ({count:,} births)")
        if least_common:
            month = least_common.get('month', 'Unknown')
            count = least_common.get('count', 0)
            lines.append(f"- 📉 **Lowest Birth Month:** {month} ({count:,} births)")
    
    return '\n'.join(lines)


def _format_longevity_stats(longevity: Dict[str, Any]) -> str:
    """Format longevity and mortality statistics."""
    lines = []
    
    # Century-based life expectancy
    century_life_exp = longevity.get('century_life_expectancy', {})
    if century_life_exp:
        lines.append("**Life Expectancy by Birth Century:**\n")
        lines.append("| Century | Average Lifespan | Individuals |")
        lines.append("|---------|-----------------|-------------|")
        for century, data in sorted(century_life_exp.items()):
            avg = data.get('average', 0)
            count = data.get('count', 0)
            lines.append(f"| {century} | {avg:.1f} years | {count:,} |")
        lines.append("")
    
    # Decade mortality patterns
    decade_mortality = longevity.get('decade_mortality_rate', {})
    if decade_mortality:
        lines.append("**Mortality Rates by Decade:**\n")
        lines.append("| Decade | Deaths | Rate |")
        lines.append("|--------|--------|------|")
        for decade, rate in sorted(decade_mortality.items())[-10:]:  # Last 10 decades
            if isinstance(rate, dict):
                count = rate.get('deaths', 0)
                pct = rate.get('rate', 0)
                lines.append(f"| {decade}s | {count:,} | {pct:.1f}% |")
    
    return '\n'.join(lines)


def _format_timeline_stats(timeline: Dict[str, Any]) -> str:
    """Format timeline statistics."""
    lines = []
    
    # Time span
    earliest = timeline.get('earliest_year')
    latest = timeline.get('latest_year')
    span = timeline.get('time_span')
    
    if earliest and latest:
        lines.append(f"**Dataset Coverage:** {earliest} to {latest} ({span} years)\n")
    
    # Events by decade
    events_by_decade = timeline.get('events_by_decade', {})
    if events_by_decade:
        lines.append("**Events by Decade (Most Recent):**\n")
        lines.append("| Decade | Events | Chart |")
        lines.append("|--------|--------|-------|")
        
        max_events = max(events_by_decade.values()) if events_by_decade else 1
        for decade in sorted(events_by_decade.keys())[-10:]:  # Last 10 decades
            count = events_by_decade[decade]
            bar_length = int((count / max_events) * 30)
            lines.append(f"| {decade} | {count:,} | {'█' * bar_length} |")
        lines.append("")
    
    # Peak period
    peak_decade = timeline.get('peak_decade')
    if peak_decade:
        decade = peak_decade.get('decade', 'Unknown')
        events = peak_decade.get('events', 0)
        lines.append(f"**Peak Activity:** {decade} with {events:,} events\n")
    
    return '\n'.join(lines)


def _format_marriage_stats(marriage: Dict[str, Any]) -> str:
    """Format marriage statistics."""
    lines = []
    
    total = marriage.get('total_marriages_recorded', 0)
    avg_age = marriage.get('average_marriage_age')
    avg_duration = marriage.get('average_marriage_duration')
    
    lines.append("**Overview:**\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Marriages | {total:,} |")
    if avg_age:
        lines.append(f"| Average Marriage Age | {avg_age:.1f} years |")
    if avg_duration:
        lines.append(f"| Average Duration | {avg_duration:.1f} years |")
    lines.append("")
    
    # Youngest/oldest married
    youngest = marriage.get('youngest_married')
    oldest = marriage.get('oldest_married')
    
    if youngest or oldest:
        lines.append("**Age Records:**\n")
        if youngest:
            name = youngest.get('name', 'Unknown')
            age = youngest.get('age', 'Unknown')
            lines.append(f"- 👶 **Youngest Married:** {name} ({age} years)")
        if oldest:
            name = oldest.get('name', 'Unknown')
            age = oldest.get('age', 'Unknown')
            lines.append(f"- 👴 **Oldest Married:** {name} ({age} years)")
        lines.append("")
    
    # Longest/shortest marriage
    longest = marriage.get('longest_marriage')
    if longest:
        couple = longest.get('couple', 'Unknown')
        duration = longest.get('duration', 0)
        lines.append(f"**Longest Marriage:** {couple} ({duration} years)\n")
    
    return '\n'.join(lines)


def _format_divorce_stats(divorce: Dict[str, Any]) -> str:
    """Format divorce statistics."""
    lines = []
    
    total = divorce.get('total_divorces', 0)
    rate = divorce.get('divorce_rate_percentage')
    avg_age = divorce.get('average_age_at_divorce')
    avg_duration = divorce.get('average_marriage_duration_before_divorce')
    
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Divorces | {total:,} |")
    if rate is not None:
        lines.append(f"| Divorce Rate | {rate:.1f}% |")
    if avg_age:
        lines.append(f"| Average Age at Divorce | {avg_age:.1f} years |")
    if avg_duration:
        lines.append(f"| Average Marriage Duration | {avg_duration:.1f} years |")
    
    return '\n'.join(lines)


def _format_children_stats(children: Dict[str, Any]) -> str:
    """Format children and family size statistics."""
    lines = []
    
    avg_children = children.get('average_children_per_person')
    total_families = children.get('total_families')
    avg_family_size = children.get('average_family_size')
    
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    if avg_children is not None:
        lines.append(f"| Average Children per Person | {avg_children:.2f} |")
    if total_families:
        lines.append(f"| Total Families | {total_families:,} |")
    if avg_family_size is not None:
        lines.append(f"| Average Family Size | {avg_family_size:.2f} |")
    lines.append("")
    
    # Most children
    most_children = children.get('person_with_most_children')
    if most_children:
        name = most_children.get('name', 'Unknown')
        count = most_children.get('children', 0)
        lines.append(f"**Most Children:** {name} ({count} children)\n")
    
    return '\n'.join(lines)


def _format_relationship_status(rel_status: Dict[str, Any]) -> str:
    """Format relationship status statistics."""
    lines = []
    
    never_married = rel_status.get('never_married', 0)
    married = rel_status.get('married', 0)
    widowed = rel_status.get('widowed', 0)
    divorced = rel_status.get('divorced', 0)
    
    total = never_married + married + widowed + divorced
    
    if total == 0:
        return "No relationship status data available."
    
    lines.append("| Status | Count | Percentage | Chart |")
    lines.append("|--------|-------|------------|-------|")
    
    for status, count in [
        ('Never Married', never_married),
        ('Married', married),
        ('Widowed', widowed),
        ('Divorced', divorced)
    ]:
        if count > 0:
            pct = (count / total * 100)
            bar = int(pct / 2)
            lines.append(f"| {status} | {count:,} | {pct:.1f}% | {'█' * bar} |")
    
    return '\n'.join(lines)


def _format_relationship_path(rel_path: Dict[str, Any]) -> str:
    """Format relationship path statistics."""
    lines = []
    
    focus_person = rel_path.get('focus_person')
    if focus_person:
        lines.append(f"**Focus Person:** {focus_person}\n")
    
    ancestors = rel_path.get('direct_ancestors', 0)
    descendants = rel_path.get('direct_descendants', 0)
    blood = rel_path.get('blood_relatives', 0)
    marriage = rel_path.get('relatives_by_marriage', 0)
    
    lines.append("| Relationship Type | Count |")
    lines.append("|-------------------|-------|")
    lines.append(f"| Direct Ancestors | {ancestors:,} |")
    lines.append(f"| Direct Descendants | {descendants:,} |")
    lines.append(f"| Blood Relatives | {blood:,} |")
    lines.append(f"| By Marriage | {marriage:,} |")
    lines.append("")
    
    # Farthest connections
    farthest_ancestor = rel_path.get('farthest_ancestor')
    farthest_descendant = rel_path.get('farthest_descendant')
    
    if farthest_ancestor or farthest_descendant:
        lines.append("**Notable Connections:**\n")
        if farthest_ancestor:
            name = farthest_ancestor.get('name', 'Unknown')
            steps = farthest_ancestor.get('steps', 0)
            gen = farthest_ancestor.get('generation', 0)
            lines.append(f"- 🔝 **Farthest Ancestor:** {name} ({steps} steps, {gen} generations)")
        if farthest_descendant:
            name = farthest_descendant.get('name', 'Unknown')
            steps = farthest_descendant.get('steps', 0)
            gen = abs(farthest_descendant.get('generation', 0))
            lines.append(f"- 🔽 **Farthest Descendant:** {name} ({steps} steps, {gen} generations)")
    
    return '\n'.join(lines)


def _format_place_table(places: Dict[str, int], label: str) -> str:
    """Format place frequency table with horizontal bar charts."""
    if not places:
        return "No data available."
    
    lines = []
    lines.append(f"| Rank | {label} | Count | Distribution |")
    lines.append("|------|" + "-" * (len(label) + 2) + "|-------|--------------|")
    
    # Get top 15 places and calculate max for scaling
    top_places = list(places.items())[:15]
    max_count = max((count for _, count in top_places), default=1)
    
    for i, (place, count) in enumerate(top_places, 1):
        # Create horizontal bar (max 30 chars)
        bar_length = int((count / max_count) * 30) if max_count > 0 else 0
        bar = '█' * bar_length
        lines.append(f"| {i} | {place} | {count:,} | {bar} |")
    
    return '\n'.join(lines)
