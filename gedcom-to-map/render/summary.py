"""
summary.py - Functions for writing summary CSVs and visualizations for GEDCOM geolocation.

Contains functions to write places, people, country summaries, and birth/death heatmaps.

Author: @colin0brass
"""

import csv
import logging
from typing import Dict, Any, Optional
import os
from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import seaborn as sns
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from geo_gedcom.addressbook import AddressBook
from geo_gedcom.geolocated_gedcom import GeolocatedGedcom

logger = logging.getLogger(__name__)
# Avoid using any interactive backends
matplotlib.use("Agg")


@dataclass
class SummaryReportConfig:
    """Configuration for which summary reports to generate.

    Attributes:
        places: Generate places CSV summary
        people: Generate people CSV summary
        countries: Generate countries CSV summary
        countries_grid: Generate countries heatmap chart image
        geocode: Generate geocache CSV for debugging
        alt_places: Generate alternative place names CSV
        enrichment_issues: Generate enrichment issues report CSV
        statistics: Generate statistics summary (YAML/Markdown/HTML)
        auto_open: Auto-open generated files after creation
    """

    places: bool = False
    people: bool = False
    countries: bool = False
    countries_grid: bool = False
    geocode: bool = False
    alt_places: bool = False
    enrichment_issues: bool = False
    statistics: bool = False
    auto_open: bool = False

    @classmethod
    def from_config(cls, config: Any) -> "SummaryReportConfig":
        """Extract summary report configuration from a config object (GVConfig or compatible).

        Args:
            gOp: Global options object with Summary* attributes

        Returns:
            SummaryReportConfig with boolean flags for each report type
        """
        return cls(
            places=getattr(gOp, "SummaryPlaces", False),
            people=getattr(gOp, "SummaryPeople", False),
            countries=getattr(gOp, "SummaryCountries", False),
            countries_grid=getattr(gOp, "SummaryCountriesGrid", False),
            geocode=getattr(gOp, "SummaryGeocode", False),
            alt_places=getattr(gOp, "SummaryAltPlaces", False),
            enrichment_issues=getattr(gOp, "SummaryEnrichmentIssues", False),
            statistics=getattr(gOp, "SummaryStatistics", False),
            auto_open=getattr(gOp, "SummaryOpen", False),
        )


def _generate_report(
    output_file: Path,
    writer_func: callable,
    writer_args: tuple,
    display_name: str,
    file_type: str,
    bg: Optional[Any],
    config: SummaryReportConfig,
    file_loader: Optional[Any],
    fatal_on_error: bool = False,
) -> Optional[Any]:
    """Helper function to generate a single report with consistent error handling.

    Args:
        output_file: Path to output file
        writer_func: Function to call to write the report
        writer_args: Arguments to pass to writer_func
        display_name: Human-readable name for status messages
        file_type: File type for LoadFile ('csv', 'default', 'html', etc.)
        bg: Optional background process for status messages
        config: Configuration with auto_open flag
        file_loader: Optional object with LoadFile method
        fatal_on_error: If True, return None on error to signal early termination

    Returns:
        Return value from writer_func, or None if fatal_on_error and exception occurred
    """
    logger.info("Writing %s to %s", display_name.lower(), output_file)
    result = None
    try:
        result = writer_func(*writer_args)
    except Exception:
        logger.exception(f"generate_summary_reports: {writer_func.__name__} failed")
        if bg:
            bg.SayErrorMessage(f"Error writing {display_name.lower()} to {output_file}")
        if fatal_on_error:
            return None

    if output_file.exists():
        if bg:
            bg.SayInfoMessage(f"{display_name}: {output_file}")
        if config.auto_open and file_loader:
            file_loader.LoadFile(file_type, str(output_file))

    return result


def generate_summary_reports(
    config: SummaryReportConfig,
    my_gedcom: GeolocatedGedcom,
    base_file_name: str,
    output_folder: Path,
    bg: Optional[Any] = None,
    file_loader: Optional[Any] = None,
) -> None:
    """Generate selected summary reports based on configuration.

    Args:
        config: SummaryReportConfig specifying which reports to generate
        my_gedcom: GeolocatedGedcom instance with geocoded data
        base_file_name: Base filename for output files
        output_folder: Directory for output files
        bg: Optional background process for status messages
        file_loader: Optional object with LoadFile method for opening files

    Side Effects:
        - Creates CSV/YAML/HTML/PNG files in output_folder
        - Shows info/error messages via bg if provided
        - Opens files if config.auto_open is True and file_loader provided
    """
    from const import FILE_GEOCACHE_FILENAME_SUFFIX
    from render.statistics_markdown import write_statistics_markdown

    if config.places:
        places_file = (output_folder / f"{base_file_name}_places.csv").resolve()
        result = _generate_report(
            places_file,
            write_places_summary,
            (my_gedcom.address_book, str(places_file)),
            "Places Summary",
            "csv",
            bg,
            config,
            file_loader,
            fatal_on_error=True,
        )

    if config.people:
        people_file = (output_folder / f"{base_file_name}_people.csv").resolve()
        _generate_report(
            people_file,
            write_people_summary,
            (my_gedcom.people, str(people_file)),
            "People Summary",
            "csv",
            bg,
            config,
            file_loader,
        )

    if config.countries or config.countries_grid:
        countries_file = (output_folder / f"{base_file_name}_countries.csv").resolve()
        img_file = _generate_report(
            countries_file,
            write_birth_death_countries_summary,
            (my_gedcom.people, str(countries_file), base_file_name),
            "Countries summary",
            "csv",
            bg,
            config if config.countries else SummaryReportConfig(),
            file_loader,
        )

        if config.countries_grid and img_file:
            img_path = Path(img_file)
            if img_path.exists():
                if bg:
                    bg.SayInfoMessage(f"Countries summary Graph: {img_file}")
                if config.auto_open and file_loader:
                    file_loader.LoadFile("default", str(img_file))

    if config.geocode:
        cache_file = (output_folder / f"{base_file_name}{FILE_GEOCACHE_FILENAME_SUFFIX}").resolve()
        _generate_report(
            cache_file,
            write_geocache_summary,
            (my_gedcom.address_book, str(cache_file)),
            "Geo cache",
            "csv",
            bg,
            config,
            file_loader,
        )

    if config.alt_places:
        alt_places_file = (output_folder / f"{base_file_name}_alt_places.csv").resolve()
        _generate_report(
            alt_places_file,
            write_alt_places_summary,
            (my_gedcom.address_book, str(alt_places_file)),
            "Alternative places summary",
            "csv",
            bg,
            config,
            file_loader,
        )

    if config.enrichment_issues:
        issues_file = (output_folder / f"{base_file_name}_enrichment_issues.csv").resolve()
        _generate_report(
            issues_file,
            write_enrichment_issues_summary,
            (my_gedcom.people, my_gedcom.enrichment.issues, str(issues_file)),
            "Enhancement issues summary",
            "csv",
            bg,
            config,
            file_loader,
        )

    if config.statistics:
        # Generate YAML statistics summary
        yaml_file = (output_folder / f"{base_file_name}_statistics.yaml").resolve()
        _generate_report(
            yaml_file,
            write_statistics_summary,
            (my_gedcom.statistics, str(yaml_file)),
            "Statistics summary",
            "default",
            bg,
            config,
            file_loader,
        )

        # Generate Markdown statistics report with visualizations
        md_file = (output_folder / f"{base_file_name}_statistics.md").resolve()
        _generate_report(
            md_file,
            write_statistics_markdown,
            (my_gedcom.statistics, str(md_file)),
            "Statistics markdown report",
            "default",
            bg,
            SummaryReportConfig(),  # Don't auto-open markdown file
            file_loader,
        )

        # Open the HTML version in browser (automatically created alongside .md)
        html_file = (output_folder / f"{base_file_name}_statistics.html").resolve()
        if html_file.exists():
            if bg:
                bg.SayInfoMessage(f"Statistics report: {html_file}")
            if config.auto_open and file_loader:
                file_loader.LoadFile("html", str(html_file))


def write_places_summary(address_book: AddressBook, output_file: str) -> None:
    """
    Write a summary of all geolocated places to a CSV file.

    Each row contains: count, latitude, longitude, found_country,
    place, country_name, continent.

    Args:
        args (Namespace): Parsed CLI arguments.
        address_book (AddressBook): Address book containing geolocated places.
        output_file (str): Output CSV file path.
    """
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            csv_header = ["count", "latitude", "longitude", "found_country", "place", "country_name", "continent"]
            csv_writer = csv.writer(csvfile, dialect="excel")
            csv_writer.writerow(csv_header)
            for place, location in address_book.addresses().items():
                # location = data.get('location', None)
                latitude = getattr(location.latlon, "lat", "") if location and getattr(location, "latlon", None) else ""
                longitude = (
                    getattr(location.latlon, "lon", "") if location and getattr(location, "latlon", None) else ""
                )
                found_country = getattr(location, "found_country", "") if location else ""
                country_name = getattr(location, "country_name", "") if location else ""
                continent = getattr(location, "continent", "") if location else ""
                r = [location.used, latitude, longitude, found_country, place, country_name, continent]
                csv_writer.writerow(r)
    except IOError as e:
        logger.error(f"Failed to write places summary to {output_file}: {e}")


def write_people_summary(people: Dict[str, Any], output_file: str) -> None:
    """
    Write a summary of all people to a CSV file.

    Each row contains: ID, Name, birth/death place/date/country/continent.

    Args:
        args (Namespace): Parsed CLI arguments.
        people (dict): Dictionary of people.
        output_file (str): Output CSV file path.
    """
    people_summary = []
    for person_id, person in people.items():
        birth_event = person.get_event("birth") if person else None
        death_event = person.get_event("death") if person else None

        birth_place = birth_event.place if birth_event else ""
        birth_continent = getattr(getattr(birth_event, "location", None), "continent", "") if birth_event else ""
        if birth_place and not birth_continent:
            logger.warning(
                f"Birth continent not found for {person.name}; place: {birth_place}; continent: {birth_continent}"
            )
        people_summary.append(
            {
                "ID": person_id,
                "Name": person.name,
                "birth_place": birth_place,
                "birth_alt_addr": (
                    getattr(getattr(birth_event, "location", None), "alt_addr", "") if birth_event else ""
                ),
                "birth_date": birth_event.date.year_num if birth_event else "",
                "birth_country": (
                    getattr(getattr(birth_event, "location", None), "country_name", "") if birth_event else ""
                ),
                "birth_continent": birth_continent,
                "death_place": death_event.place if death_event else "",
                "death_alt_addr": (
                    getattr(getattr(death_event, "location", None), "alt_addr", "") if death_event else ""
                ),
                "death_date": death_event.date.year_num if death_event else "",
                "death_country": (
                    getattr(getattr(death_event, "location", None), "country_name", "") if death_event else ""
                ),
                "death_continent": (
                    getattr(getattr(death_event, "location", None), "continent", "") if death_event else ""
                ),
            }
        )

    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile, dialect="excel")
            csv_writer.writerow(
                [
                    "ID",
                    "Name",
                    "birth_place",
                    "birth_alt_addr",
                    "birth_date",
                    "birth_country",
                    "birth_continent",
                    "death_place",
                    "death_alt_addr",
                    "death_date",
                    "death_country",
                    "death_continent",
                ]
            )
            for summary in people_summary:
                csv_writer.writerow(
                    [
                        summary["ID"],
                        summary["Name"],
                        summary["birth_place"],
                        summary["birth_alt_addr"],
                        summary["birth_date"],
                        summary["birth_country"],
                        summary["birth_continent"],
                        summary["death_place"],
                        summary["death_alt_addr"],
                        summary["death_date"],
                        summary["death_country"],
                        summary["death_continent"],
                    ]
                )
    except IOError as e:
        logger.error(f"Failed to write people summary to {output_file}: {e}")


def save_birth_death_heatmap_matrix(
    birth_death_countries_summary: Dict[Any, Any], output_image_file: str, gedcom_file_name: str
) -> None:
    """
    Generate and save a heatmap image showing birth/death country pairs by continent.

    Adds a footer with filename and total number of people.

    Args:
        birth_death_countries_summary (dict): Summary of birth/death country pairs.
        output_image_file (str): Output image file path.
        gedcom_file_name (str): GEDCOM file name for labeling.
    """
    if not birth_death_countries_summary:
        logger.warning(f"No data to plot for birth/death country heatmap: {output_image_file}")
        return

    # Prepare data for DataFrame
    records = []
    for (birth_country, death_country), data in birth_death_countries_summary.items():
        birth_continent = data["birth_continent"]
        death_continent = data["death_continent"]
        records.append(
            {
                "Birth Continent": birth_continent,
                "Birth Country": birth_country,
                "Death Continent": death_continent,
                "Death Country": death_country,
                "Count": data["count"],
            }
        )

    # Move records with 'none' as continent to the start
    records = [rec for rec in records if rec["Birth Continent"] == "none" or rec["Death Continent"] == "none"] + [
        rec for rec in records if rec["Birth Continent"] != "none" and rec["Death Continent"] != "none"
    ]

    # Get a combined set of birth and death continents
    colours = ["red", "blue", "green", "purple", "orange", "teal", "brown", "black"]
    all_continents = set(rec["Birth Continent"] for rec in records) | set(rec["Death Continent"] for rec in records)
    continent_colours = {continent: colour for continent, colour in zip(all_continents, colours)}

    df = pd.DataFrame(records)
    heatmap_df = df.pivot_table(
        index=["Birth Continent", "Birth Country"],
        columns=["Death Continent", "Death Country"],
        values="Count",
        fill_value=0,
        aggfunc="sum",
    )

    num_people = int(df["Count"].sum())

    plt.figure(figsize=(max(10, heatmap_df.shape[1] * 0.5), max(8, heatmap_df.shape[0] * 0.5)))
    ax = sns.heatmap(
        heatmap_df,
        annot=False,
        fmt="d",
        cmap="Blues",
        cbar=False,
        cbar_kws={"label": "Count"},
        linewidths=0.5,
        linecolor="gray",
    )
    xlabel_text = ax.set_xlabel("Death Country", color="red")
    ylabel_text = ax.set_ylabel("Birth Country", color="blue")
    plt.title(f"{gedcom_file_name} : Birth & Death Country Heatmap (by Continent)")

    fig = plt.gcf()
    fig.canvas.draw()  # Needed to compute text position

    label_obj = ax.xaxis.label
    bbox = label_obj.get_window_extent(fig.canvas.get_renderer())
    inv = ax.transData.inverted()
    _, y0 = inv.transform((bbox.x0, bbox.y0))
    _, y1 = inv.transform((bbox.x1, bbox.y1))
    xlabel_height = abs(y1 - y0)

    label_obj = ax.yaxis.label
    bbox = label_obj.get_window_extent(fig.canvas.get_renderer())
    inv = ax.transData.inverted()
    x0, _ = inv.transform((bbox.x0, bbox.y0))
    x1, _ = inv.transform((bbox.x1, bbox.y1))
    ylabel_width = abs(x1 - x0)

    # Set blank tick labels (we'll draw our own centered labels)
    ax.set_xticks([])
    ax.set_yticks([])

    # Add count numbers to each cell with auto-scaled font size to fit in the cell
    heatmap = heatmap_df.values
    nrows, ncols = heatmap.shape
    im = ax.collections[0]

    # Get axis size in inches and figure DPI
    bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    ax_width_in, ax_height_in = bbox.width, bbox.height
    cell_width_in = ax_width_in / ncols
    cell_height_in = ax_height_in / nrows
    # Convert to points (1 inch = 72 points)
    cell_width_pt = cell_width_in * 72
    cell_height_pt = cell_height_in * 72

    gap_pixels = 30

    for i in range(nrows):
        for j in range(ncols):
            count = heatmap[i, j]
            if count > 0:
                # Choose white or black font depending on background intensity
                bg_intensity = im.cmap(im.norm(count))
                r, g, b = bg_intensity[:3]
                luminance = 0.299 * r + 0.587 * g + 0.114 * b
                font_color = "black" if luminance > 0.5 else "white"

                num_digits = len(str(count))

                # Estimate font size: fit width and height, and adjust for digit count
                font_size_w = cell_width_pt / (num_digits * 1.0)
                font_size_h = cell_height_pt * 1.0
                font_size = min(font_size_w, font_size_h)
                font_size = max(6, min(font_size, 14))  # Clamp between 6 and 14

                ax.text(
                    j + 0.5,
                    i + 0.5,
                    str(count),
                    ha="center",
                    va="center",
                    color=font_color,
                    fontsize=font_size,
                    fontweight="bold",
                    clip_on=True,
                )

    # Draw country labels beside x-axis, centered below each column
    label_heights = []
    country_labels_y = len(heatmap_df.index) + 2 * xlabel_height
    for j, col in enumerate(heatmap_df.columns):
        text_obj = ax.annotate(
            col[1],
            xy=(j + 0.5, country_labels_y),
            xycoords=("data", "data"),
            ha="center",
            va="top",
            fontsize=10,
            fontweight="normal",
            rotation=90,
            clip_on=False,
        )
        # Get bounding box in display coordinates
        bbox = text_obj.get_window_extent()
        # Convert height from pixels to data coordinates
        inv = ax.transData.inverted()
        x0, y0 = inv.transform((bbox.x0, bbox.y0))
        x1, y1 = inv.transform((bbox.x1, bbox.y1))
        label_heights.append(abs(y1 - y0))
        gap_y = abs(inv.transform((0, gap_pixels))[1] - inv.transform((0, 0))[1])
    max_label_height = max(label_heights) if label_heights else 0

    # Draw country labels beside y-axis, centered on each row
    label_widths = []
    country_labels_x = -2 * ylabel_width
    for i, idx in enumerate(heatmap_df.index):
        text_obj = ax.annotate(
            idx[1],
            xy=(country_labels_x, i + 0.5),
            xycoords=("data", "data"),
            ha="right",
            va="center",
            fontsize=10,
            fontweight="normal",
            rotation=0,
            clip_on=False,
        )
        # Get bounding box in display coordinates
        bbox = text_obj.get_window_extent()
        # Convert width from pixels to data coordinates
        inv = ax.transData.inverted()
        x0, y0 = inv.transform((bbox.x0, bbox.y0))
        x1, y1 = inv.transform((bbox.x1, bbox.y1))
        label_widths.append(abs(x1 - x0))
        gap_x = abs(inv.transform((gap_pixels, 0))[0] - inv.transform((0, 0))[0])
    max_label_width = max(label_widths) if label_widths else 0

    # Improved group (continent) labels below x-axis
    group_positions_x = {}
    line_y = country_labels_y + max_label_height + 2 * gap_y
    continent_labels_y = line_y + gap_y
    for i, g in enumerate(heatmap_df.columns.get_level_values(0)):
        group_positions_x.setdefault(g, []).append(i)
    for idx, (group, positions) in enumerate(group_positions_x.items()):
        start = min(positions)
        end = max(positions)
        x = (start + end + 1) / 2
        colour = continent_colours.get(group, "black")
        ax.annotate(
            group,
            xy=(x, continent_labels_y),
            xycoords=("data", "data"),
            ha="center",
            va="top",
            fontsize=12,
            fontweight="bold",
            color=colour,
            rotation=90,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7),
        )
        # Draw horizontal lines (in alternating colours) to show the size of each group
        ax.plot(
            [start + 0.2, end + 1 - 0.2],
            [line_y, line_y],  # +1 so the line covers the full group
            color=colour,
            linewidth=2,
            solid_capstyle="round",
            clip_on=False,
        )

    # Improved group (continent) labels beside y-axis
    group_positions_y = {}
    line_x = country_labels_x - max_label_width - gap_x
    continent_labels_x = line_x - gap_x
    for i, g in enumerate(heatmap_df.index.get_level_values(0)):
        group_positions_y.setdefault(g, []).append(i)
    for idx, (group, positions) in enumerate(group_positions_y.items()):
        start = min(positions)
        end = max(positions)
        y = (start + end + 1) / 2
        colour = continent_colours.get(group, "black")
        ax.annotate(
            group,
            xy=(continent_labels_x, y),
            xycoords=("data", "data"),
            ha="right",
            va="center",
            fontsize=12,
            fontweight="bold",
            color=colour,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7),
        )
        # Draw vertical lines (in alternating colours) to show the size of each group
        ax.plot(
            [line_x, line_x],
            [start + 0.2, end + 1 - 0.2],  # +1 so the line covers the full group
            color=colour,
            linewidth=2,
            solid_capstyle="round",
            clip_on=False,
        )

    fig.canvas.draw()  # Needed to compute text position

    # Add footer text with filename root and total number of people
    footer_text = f"File: {gedcom_file_name}   |   Total people: {num_people}   |   (including spouses)"
    plt.figtext(0.01, 0.01, footer_text, ha="left", va="bottom", fontsize=10, color="gray")

    plt.tight_layout()
    plt.savefig(output_image_file)
    plt.close()


def write_birth_death_countries_summary(people: Dict[str, Any], output_file: str, gedcom_file_name: str) -> None:
    """
    Write a summary of birth and death countries to a CSV file.

    Also generates a heatmap matrix image showing birth/death country pairs by continent.

    Args:
        args (Namespace): Parsed CLI arguments.
        people (dict): Dictionary of people.
        output_file (str): Output CSV file path.
        gedcom_file_name (str): GEDCOM file name for labeling.
    """
    birth_death_countries_summary = {}

    for person_id, person in people.items():
        birth_event = person.get_event("birth") if person else None
        death_event = person.get_event("death") if person else None
        birth_location = getattr(birth_event, "location", None) if birth_event else None
        death_location = getattr(death_event, "location", None) if death_event else None

        birth_country = getattr(birth_location, "country_name", "none") if birth_location else "none"
        birth_country_continent = getattr(birth_location, "continent", "none") if birth_location else "none"
        death_country = getattr(death_location, "country_name", "none") if death_location else "none"
        death_country_continent = getattr(death_location, "continent", "none") if death_location else "none"

        key = (birth_country, death_country)
        if key not in birth_death_countries_summary:
            birth_death_countries_summary[key] = {"count": 0}
        birth_death_countries_summary[key]["count"] += 1
        birth_death_countries_summary[key]["birth_country"] = birth_country
        birth_death_countries_summary[key]["death_country"] = death_country
        birth_death_countries_summary[key]["birth_continent"] = birth_country_continent
        birth_death_countries_summary[key]["death_continent"] = death_country_continent

    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile, dialect="excel")
            csv_writer.writerow(["Birth Country", "Birth Continent", "Death Country", "Death Continent", "Count"])
            for (birth_country, death_country), data in birth_death_countries_summary.items():
                csv_writer.writerow(
                    [birth_country, data["birth_continent"], death_country, data["death_continent"], data["count"]]
                )
    except IOError as e:
        logger.error(f"Failed to write birth/death countries summary to {output_file}: {e}")

    output_image_file = os.path.splitext(output_file)[0] + "_heatmap.png"
    save_birth_death_heatmap_matrix(birth_death_countries_summary, output_image_file, gedcom_file_name)
    logger.info(f"Saved heatmap matrix image to {output_image_file}")
    return output_image_file


def write_geocache_summary(address_book: AddressBook, output_file: str) -> None:
    """
    Write the geocoded location cache to a CSV file using pandas DataFrame.

    Drops duplicate addresses, keeping the first occurrence.

    Args:
        address_book (AddressBook): Address book containing geolocated places.
        output_file (str): Output CSV file path.
    """
    # Prepare data for DataFrame
    records = []
    for place in address_book.get_address_list():
        record = address_book.get_summary_row_dict(place)
        records.append(record)

    df = pd.DataFrame(records, columns=address_book.summary_columns)

    # Drop rows with duplicate 'address', keeping the first occurrence
    df = df.drop_duplicates(subset=["address"], keep="first")

    try:
        df.to_csv(output_file, index=False, encoding="utf-8")
    except IOError as e:
        logger.error(f"Failed to write places summary to {output_file}: {e}")


def write_alt_places_summary(address_book: AddressBook, output_file: str) -> None:
    """
    Write a summary of all alternative place names to a CSV file.

    Each row contains: alt_addr, count, associated_address, and optionally canonical_address.

    Args:
        args (Namespace): Parsed CLI arguments.
        address_book (AddressBook): Address book containing geolocated places.
        output_file (str): Output CSV file path.
    """
    records = []
    has_canonical = False
    for alt_addr in address_book.get_alt_addr_list():
        associated_addresses = address_book.get_address_list_for_alt_addr(alt_addr)
        for address in associated_addresses:
            location = address_book.get_address(address)
            canonical_addr = getattr(location, "canonical_addr", None) if location else None
            if canonical_addr:
                has_canonical = True
            records.append((alt_addr, len(associated_addresses), address, canonical_addr if canonical_addr else ""))

    columns = ["alt_addr", "count", "associated_address", "canonical_address"]
    if not has_canonical:
        columns.remove("canonical_address")
        records = [r[:-1] for r in records]

    df = pd.DataFrame(records, columns=columns)
    try:
        df.to_csv(output_file, index=False, encoding="utf-8")
    except IOError as e:
        logger.error(f"Failed to write alternative places summary to {output_file}: {e}")


def write_enrichment_issues_summary(people: Dict[str, Any], issues: Dict[str, Any], output_file: str) -> None:
    """
    Write a summary of all enrichment issues to a CSV file.

    Each row contains: person_id, severity, issue_type, message.

    Args:
        args (Namespace): Parsed CLI arguments.
        issues (list): List of enrichment issues.
        output_file (str): Output CSV file path.
    """
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile, dialect="excel")
            csv_writer.writerow(["person_id", "name", "severity", "issue_type", "message"])
            for issue in issues:
                person = people.get(issue.person_id, None)
                name = person.name if person else "Unknown"
                csv_writer.writerow([issue.person_id, name, issue.severity, issue.issue_type, issue.message])
    except IOError as e:
        logger.error(f"Failed to write enhancement issues summary to {output_file}: {e}")


def write_statistics_summary(stats: Dict[str, Any], output_file: str) -> None:
    """
    Write a summary of statistics to a YAML file.

    Args:
        args (Namespace): Parsed CLI arguments.
        stats (dict): Dictionary of statistics.
        output_file (str): Output YAML file path.
    """
    try:
        stats_results = stats.results if hasattr(stats, "results") else stats
        import yaml

        with open(output_file, "w", encoding="utf-8") as yamlfile:
            yaml.dump(stats_results, yamlfile, default_flow_style=False, sort_keys=False, allow_unicode=True)
    except IOError as e:
        logger.error(f"Failed to write statistics summary to {output_file}: {e}")
