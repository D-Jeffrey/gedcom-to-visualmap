"""
Performance tests for GeolocatedGedcom initialization with fuzz=True and fuzz=False
across multiple GEDCOM samples. Prints results as a markdown table and writes YAML output.
"""

from cProfile import label
import os
import pytest
import timeit
import yaml
from pathlib import Path
from typing import List, Dict, Any
from geo_gedcom.geolocated_gedcom import GeolocatedGedcom


@pytest.fixture(scope="session", autouse=True)
def collect_and_report_results(request):
    """
    Session-scoped fixture to collect performance results and output markdown/YAML after all tests.
    """
    results: List[Dict[str, Any]] = []
    yield results
    if not results:
        return
    header = ["Fuzz", "Gedcom Sample", "Entries", "People", "Init Time (s)"]
    print("\n### GeolocatedGedcom Performance Results")
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for res in results:
        row = [
            res['Gedcom Sample'],
            str(res['Fuzz']),
            str(res['Entries']),
            str(res['People']),
            f"{res['Init Time (s)']:.5f}"
        ]
        print("| " + " | ".join(row) + " |")
    results_path = os.path.join(os.path.dirname(__file__), "geolocatedgedcom_performance_results.yaml")
    with open(results_path, "w") as f:
        yaml.dump({'results': results}, f, default_flow_style=False)

def run_geolocatedgedcom_perf(
    label: str,
    cache_file_path: str,
    gedcom_file_path: str,
    fuzz: bool
) -> Dict[str, Any]:
    """
    Initialize GeolocatedGedcom and measure performance. Returns an ordered result dict.
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
        "Fuzz": fuzz,
        "Gedcom Sample": label,
        "Entries": len(geo.address_book.addresses()),
        "People": len(geo.people),
        "Init Time (s)": float(f"{t1 - t0:.5f}")
    }

@pytest.mark.slow
@pytest.mark.parametrize("fuzz", [False, True])
@pytest.mark.parametrize("label,cache_file_path,gedcom_file_path", [
    ('simple', 'gedcom-samples/geo_cache.csv', 'gedcom-samples/input.ged'),
    ('pres2020', 'gedcom-samples/pres/geo_cache.csv', 'gedcom-samples/pres/pres2020.ged'),
    # ('royal92', 'gedcom-samples/royal/geo_cache.csv', 'gedcom-samples/royal/royal92.ged'),
    # ('habs', 'gedcom-samples/habs/geo_cache.csv', 'gedcom-samples/habs/Habsburg.ged'),
    # ('ivar', 'gedcom-samples/ivar/geo_cache.csv', 'gedcom-samples/ivar/IvarKingOfDublin.ged'),
    # ('queen', 'gedcom-samples/queen/geo_cache.csv', 'gedcom-samples/queen/Queen.ged'),
    # ('bourbon', 'gedcom-samples/sample-bourbon/geo_cache.csv', 'gedcom-samples/sample-bourbon/bourbon.ged'),
    # ('kennedy', 'gedcom-samples/sample-kennedy/geo_cache.csv', 'gedcom-samples/sample-kennedy/kennedy.ged'),
    # ('longsword', 'gedcom-samples/longsword/geo_cache.csv', 'gedcom-samples/longsword/longsword.ged'),
])
def test_geolocatedgedcom_performance(label: str, cache_file_path: str, gedcom_file_path: str, fuzz: bool, collect_and_report_results):
    """
    Runs GeolocatedGedcom performance test for each sample and fuzz setting.
    Appends results to the session-scoped results list.
    """
    print(f"File: {label}, Fuzz: {fuzz}")
    res = run_geolocatedgedcom_perf(label, cache_file_path, gedcom_file_path, fuzz)
    collect_and_report_results.append(res)
