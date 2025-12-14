"""
summary.py - Functions for writing summary CSVs and visualizations for GEDCOM geolocation.

Contains functions to write places, people, country summaries, and birth/death heatmaps.

Author: @colin0brass
"""

import csv
import logging
from typing import Dict, Any
import os
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from geo_gedcom.addressbook import FuzzyAddressBook

logger = logging.getLogger(__name__)
# Avoid using any interactive backends
matplotlib.use("Agg")


def write_places_summary(address_book: FuzzyAddressBook, output_file: str) -> None:
    """
    Write a summary of all geolocated places to a CSV file.

    Each row contains: count, latitude, longitude, found_country,
    place, country_name, continent.

    Args:
        args (Namespace): Parsed CLI arguments.
        address_book (FuzzyAddressBook): Address book containing geolocated places.
        output_file (str): Output CSV file path.
    """
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            csv_header = [
                'count', 'latitude', 'longitude', 'found_country',
                'place', 'country_name', 'continent'
            ]
            csv_writer = csv.writer(csvfile, dialect='excel')
            csv_writer.writerow(csv_header)
            for place, location in address_book.addresses().items():
                # location = data.get('location', None)
                latitude = getattr(location.latlon, 'lat', '') if location and getattr(location, 'latlon', None) else ''
                longitude = getattr(location.latlon, 'lon', '') if location and getattr(location, 'latlon', None) else ''
                found_country = getattr(location, 'found_country', '') if location else ''
                country_name = getattr(location, 'country_name', '') if location else ''
                continent = getattr(location, 'continent', '') if location else ''
                r = [
                    location.used, latitude, longitude, found_country,
                    place, country_name, continent
                ]
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
        birth_place = person.birth.place if person.birth else ''
        birth_continent = getattr(getattr(person.birth, 'location', None), 'continent', '') if person.birth else ''
        if birth_place and not birth_continent:
            logger.warning(f"Birth continent not found for {person.name}; place: {birth_place}; continent: {birth_continent}")
        people_summary.append({
            'ID': person_id,
            'Name': person.name,
            'birth_place': birth_place,
            'birth_alt_addr': getattr(getattr(person.birth, 'location', None), 'alt_addr', '') if person.birth else '',
            'birth_date': person.birth.date.year_num if person.birth else '',
            'birth_country': getattr(getattr(person.birth, 'location', None), 'country_name', '') if person.birth else '',
            'birth_continent': birth_continent,
            'death_place': person.death.place if person.death else '',
            'death_alt_addr': getattr(getattr(person.death, 'location', None), 'alt_addr', '') if person.death else '',
            'death_date': person.death.date.year_num if person.death else '',
            'death_country': getattr(getattr(person.death, 'location', None), 'country_name', '') if person.death else '',
            'death_continent': getattr(getattr(person.death, 'location', None), 'continent', '') if person.death else ''
        })

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile, dialect='excel')
            csv_writer.writerow(['ID', 'Name', 'birth_place', 'birth_alt_addr', 'birth_date', 'birth_country', 'birth_continent', 'death_place', 'death_alt_addr', 'death_date', 'death_country', 'death_continent'])
            for summary in people_summary:
                csv_writer.writerow([summary['ID'],
                                     summary['Name'],
                                     summary['birth_place'],
                                     summary['birth_alt_addr'],
                                     summary['birth_date'],
                                     summary['birth_country'],
                                     summary['birth_continent'],
                                     summary['death_place'],
                                     summary['death_alt_addr'],
                                     summary['death_date'],
                                     summary['death_country'],
                                     summary['death_continent']])
    except IOError as e:
        logger.error(f"Failed to write people summary to {output_file}: {e}")

def save_birth_death_heatmap_matrix(birth_death_countries_summary: Dict[Any, Any], output_image_file: str, gedcom_file_name: str) -> None:
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
        birth_continent = data['birth_continent']
        death_continent = data['death_continent']
        records.append({
            'Birth Continent': birth_continent,
            'Birth Country': birth_country,
            'Death Continent': death_continent,
            'Death Country': death_country,
            'Count': data['count']
        })

    # Move records with 'none' as continent to the start
    records = (
        [rec for rec in records if rec['Birth Continent'] == 'none' or rec['Death Continent'] == 'none'] +
        [rec for rec in records if rec['Birth Continent'] != 'none' and rec['Death Continent'] != 'none']
    )

    # Get a combined set of birth and death continents
    colours = ['red', 'blue', 'green', 'purple', 'orange', 'teal', 'brown', 'black']
    all_continents = set(rec['Birth Continent'] for rec in records) | set(rec['Death Continent'] for rec in records)
    continent_colours = {continent: colour for continent, colour in zip(all_continents, colours)}

    df = pd.DataFrame(records)
    heatmap_df = df.pivot_table(
        index=['Birth Continent', 'Birth Country'],
        columns=['Death Continent', 'Death Country'],
        values='Count',
        fill_value=0,
        aggfunc='sum'
    )

    num_people = int(df['Count'].sum())

    plt.figure(figsize=(max(10, heatmap_df.shape[1] * 0.5), max(8, heatmap_df.shape[0] * 0.5)))
    ax = sns.heatmap(
        heatmap_df, annot=False, fmt='d', cmap='Blues', cbar=False,
        cbar_kws={'label': 'Count'}, linewidths=0.5, linecolor='gray'
    )
    xlabel_text = ax.set_xlabel('Death Country', color='red')
    ylabel_text = ax.set_ylabel('Birth Country', color='blue')
    plt.title(f'{gedcom_file_name} : Birth & Death Country Heatmap (by Continent)')

    fig = plt.gcf()
    fig.canvas.draw() # Needed to compute text position

    label_obj = ax.xaxis.label
    bbox = label_obj.get_window_extent(fig.canvas.get_renderer())
    inv = ax.transData.inverted()
    _ , y0 = inv.transform((bbox.x0, bbox.y0))
    _ , y1 = inv.transform((bbox.x1, bbox.y1))
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
                font_color = 'black' if luminance > 0.5 else 'white'

                num_digits = len(str(count))

                # Estimate font size: fit width and height, and adjust for digit count
                font_size_w = cell_width_pt / (num_digits * 1.0)
                font_size_h = cell_height_pt * 1.0
                font_size = min(font_size_w, font_size_h)
                font_size = max(6, min(font_size, 14))  # Clamp between 6 and 14

                ax.text(
                    j + 0.5, i + 0.5, str(count),
                    ha='center', va='center',
                    color=font_color,
                    fontsize=font_size,
                    fontweight='bold',
                    clip_on=True
                )

    # Draw country labels beside x-axis, centered below each column
    label_heights = []
    country_labels_y = len(heatmap_df.index) + 2*xlabel_height
    for j, col in enumerate(heatmap_df.columns):
        text_obj = ax.annotate(
            col[1],
            xy=(j + 0.5, country_labels_y), xycoords=('data', 'data'),
            ha='center', va='top',
            fontsize=10, fontweight='normal', rotation=90, clip_on=False
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
    country_labels_x = -2*ylabel_width
    for i, idx in enumerate(heatmap_df.index):
        text_obj = ax.annotate(
            idx[1],
            xy=(country_labels_x, i + 0.5), xycoords=('data', 'data'),
            ha='right', va='center',
            fontsize=10, fontweight='normal', rotation=0, clip_on=False
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
    line_y = country_labels_y + max_label_height + 2*gap_y
    continent_labels_y = line_y + gap_y
    for i, g in enumerate(heatmap_df.columns.get_level_values(0)):
        group_positions_x.setdefault(g, []).append(i)
    for idx, (group, positions) in enumerate(group_positions_x.items()):
        start = min(positions)
        end = max(positions)
        x = (start + end + 1) / 2
        colour = continent_colours.get(group, 'black')
        ax.annotate(
            group,
            xy=(x, continent_labels_y), xycoords=('data', 'data'),
            ha='center', va='top',
            fontsize=12, fontweight='bold', color=colour, rotation=90,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
        )
        # Draw horizontal lines (in alternating colours) to show the size of each group
        ax.plot(
            [start + 0.2, end + 1 - 0.2],  [line_y, line_y], # +1 so the line covers the full group
            color=colour, linewidth=2, solid_capstyle='round', clip_on=False
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
        colour = continent_colours.get(group, 'black')
        ax.annotate(
            group,
            xy=(continent_labels_x, y), xycoords=('data', 'data'),
            ha='right', va='center',
            fontsize=12, fontweight='bold', color=colour,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
        )
        # Draw vertical lines (in alternating colours) to show the size of each group
        ax.plot(
            [line_x, line_x], [start + 0.2, end + 1 - 0.2],  # +1 so the line covers the full group
            color=colour, linewidth=2, solid_capstyle='round', clip_on=False
        )

    fig.canvas.draw() # Needed to compute text position

    # Add footer text with filename root and total number of people
    footer_text = f"File: {gedcom_file_name}   |   Total people: {num_people}   |   (including spouses)"
    plt.figtext(
        0.01, 0.01, footer_text,
        ha='left', va='bottom',
        fontsize=10, color='gray'
    )

    plt.tight_layout()
    plt.savefig(output_image_file)
    plt.close()

def write_birth_death_countries_summary( people: Dict[str, Any], output_file: str, gedcom_file_name: str) -> None:
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
        birth_location = getattr(person.birth, 'location', None) if person.birth else None
        death_location = getattr(person.death, 'location', None) if person.death else None

        birth_country = getattr(birth_location, 'country_name', 'none') if birth_location else 'none'
        birth_country_continent = getattr(birth_location, 'continent', 'none') if birth_location else 'none'
        death_country = getattr(death_location, 'country_name', 'none') if death_location else 'none'
        death_country_continent = getattr(death_location, 'continent', 'none') if death_location else 'none'

        key = (birth_country, death_country)
        if key not in birth_death_countries_summary:
            birth_death_countries_summary[key] = {'count': 0}
        birth_death_countries_summary[key]['count'] += 1
        birth_death_countries_summary[key]['birth_country'] = birth_country
        birth_death_countries_summary[key]['death_country'] = death_country
        birth_death_countries_summary[key]['birth_continent'] = birth_country_continent
        birth_death_countries_summary[key]['death_continent'] = death_country_continent

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile, dialect='excel')
            csv_writer.writerow(['Birth Country', 'Birth Continent', 'Death Country', 'Death Continent', 'Count'])
            for (birth_country, death_country), data in birth_death_countries_summary.items():
                csv_writer.writerow([birth_country, data['birth_continent'], death_country, data['death_continent'], data['count']])
    except IOError as e:
        logger.error(f"Failed to write birth/death countries summary to {output_file}: {e}")

    output_image_file = os.path.splitext(output_file)[0] + "_heatmap.png"
    save_birth_death_heatmap_matrix(birth_death_countries_summary, output_image_file, gedcom_file_name)
    logger.info(f"Saved heatmap matrix image to {output_image_file}")
    return output_image_file

def write_geocache_summary(address_book: FuzzyAddressBook, output_file: str) -> None:
    """
    Write the geocoded location cache to a CSV file using pandas DataFrame.

    Drops duplicate addresses, keeping the first occurrence.

    Args:
        address_book (FuzzyAddressBook): Address book containing geolocated places.
        output_file (str): Output CSV file path.
    """
    # Prepare data for DataFrame
    records = []
    for place in address_book.get_address_list():
        record = address_book.get_summary_row_dict(place)
        records.append(record)

    df = pd.DataFrame(records, columns=address_book.summary_columns)

    # Drop rows with duplicate 'address', keeping the first occurrence
    df = df.drop_duplicates(subset=['address'], keep='first')

    try:
        df.to_csv(output_file, index=False, encoding='utf-8')
    except IOError as e:
        logger.error(f"Failed to write places summary to {output_file}: {e}")

def write_alt_places_summary(address_book: FuzzyAddressBook, output_file: str) -> None:
    """
    Write a summary of all alternative place names to a CSV file.

    Each row contains: alt_addr, count, associated_address, and optionally canonical_address.

    Args:
        args (Namespace): Parsed CLI arguments.
        address_book (FuzzyAddressBook): Address book containing geolocated places.
        output_file (str): Output CSV file path.
    """
    records = []
    has_canonical = False
    for alt_addr in address_book.get_alt_addr_list():
        associated_addresses = address_book.get_address_list_for_alt_addr(alt_addr)
        for address in associated_addresses:
            location = address_book.get_address(address)
            canonical_addr = getattr(location, 'canonical_addr', None) if location else None
            if canonical_addr:
                has_canonical = True
            records.append((alt_addr, len(associated_addresses), address, canonical_addr if canonical_addr else ''))

    columns = ['alt_addr', 'count', 'associated_address', 'canonical_address']
    if not has_canonical:
        columns.remove('canonical_address')
        records = [r[:-1] for r in records]

    df = pd.DataFrame(records, columns=columns)
    try:
        df.to_csv(output_file, index=False, encoding='utf-8')
    except IOError as e:
        logger.error(f"Failed to write alternative places summary to {output_file}: {e}")