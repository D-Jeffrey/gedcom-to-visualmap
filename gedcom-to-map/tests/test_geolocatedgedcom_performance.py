"""
Performance tests for GeolocatedGedcom initialization with fuzz=True and fuzz=False
across multiple GEDCOM samples. Prints results as a markdown table.
"""

import os
import pytest
import timeit
from pathlib import Path
from typing import List, Dict, Any

from geo_gedcom.geolocated_gedcom import GeolocatedGedcom

gedcom_samples: List[tuple[str, str, str]] = [
    ('simple', 'gedcom-samples/geo_cache.csv', 'gedcom-samples/input.ged'),
    ('pres2020', 'gedcom-samples/pres/geo_cache.csv', 'gedcom-samples/pres/pres2020.ged'),
    ('royal92', 'gedcom-samples/royal/geo_cache.csv', 'gedcom-samples/royal/royal92.ged'),
    ('habs', 'gedcom-samples/habs/geo_cache.csv', 'gedcom-samples/habs/Habsburg.ged'),
    ('ivar', 'gedcom-samples/ivar/geo_cache.csv', 'gedcom-samples/ivar/IvarKingOfDublin.ged'),
    ('queen', 'gedcom-samples/queen/geo_cache.csv', 'gedcom-samples/queen/Queen.ged'),
    ('bourbon', 'gedcom-samples/sample-bourbon/geo_cache.csv', 'gedcom-samples/sample-bourbon/sample-bourbon.ged'),
    ('kennedy', 'gedcom-samples/sample-kennedy/geo_cache.csv', 'gedcom-samples/sample-kennedy/sample-kennedy.ged'),
    ('longsword', 'gedcom-samples/longsword/geo_cache.csv', 'gedcom-samples/longsword/longsword.ged'),
]

def run_geolocatedgedcom_perf(
    label: str,
    cache_file_path: str,
    gedcom_file_path: str,
    fuzz: bool
) -> Dict[str, Any]:
    """
    Initialize GeolocatedGedcom and measure performance.

    Args:
        label: Sample label.
        cache_file_path: Path to geo cache file.
        gedcom_file_path: Path to GEDCOM file.
        fuzz: Whether to use fuzzy matching.

    Returns:
        Dictionary with performance metrics.
    """
    assert os.path.exists(cache_file_path), f"Missing cache file: {cache_file_path}"
    assert os.path.exists(gedcom_file_path), f"Missing gedcom file: {gedcom_file_path}"
    t0 = timeit.default_timer()
    geo = GeolocatedGedcom(
        gedcom_file=Path(gedcom_file_path),
        location_cache_file=Path(cache_file_path),
        default_country=None,
        always_geocode=False,
        cache_only=True,
        fuzz=fuzz
    )
    t1 = timeit.default_timer()
    return {
        'label': label,
        'fuzz': fuzz,
        'entries': len(geo.address_book.addresses()),
        'people': len(geo.people),
        'time': t1 - t0
    }

def test_geolocatedgedcom_performance():
    """
    Runs GeolocatedGedcom performance test for each sample and each fuzz setting.
    Prints results as a markdown table.
    """
    results: List[Dict[str, Any]] = []
    for label, cache_file_path, gedcom_file_path in gedcom_samples:
        for fuzz_value in [False, True]:
            res = run_geolocatedgedcom_perf(label, cache_file_path, gedcom_file_path, fuzz_value)
            results.append(res)

    # Print markdown table
    print("\n### GeolocatedGedcom Performance")
    header = ["Gedcom Sample", "Fuzz", "Entries", "People", "Init Time (s)"]
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for r in results:
        row = [
            r['label'],
            str(r['fuzz']),
            str(r['entries']),
            str(r['people']),
            f"{r['time']:.5f}"
        ]
        print("| " + " | ".join(row) + " |")
