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
from typing import List, Dict, Any, Optional
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
    header = ["Gedcom Sample", "Fuzz", "Geo Cache Mode", "Cache Only", "Always Geocode", "Entries", "Entries Existed", "Entries Didn't Exist", "People", "Init Time (s)"]
    print("\n### GeolocatedGedcom Performance Results")
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for res in results:
        row = [
            res['Gedcom Sample'],
            str(res['Fuzz']),
            str(res['Geo Cache Mode']),
            str(res['Cache Only']),
            str(res['Always Geocode']),
            str(res['Entries']),
            str(res['Entries Existed']),
            str(res["Entries Didn't Exist"]),
            str(res['People']),
            f"{res['Init Time (s)']:.5f}"
        ]
        print("| " + " | ".join(row) + " |")
    results_path = os.path.join(os.path.dirname(__file__), "geolocatedgedcom_performance_results.yaml")
    with open(results_path, "w") as f:
        yaml.dump({'results': results}, f, default_flow_style=False)

def run_geolocatedgedcom_perf(
    label: str,
    cache_file_path: "Optional[str]",
    gedcom_file_path: str,
    geo_config_path: str,
    cache_only: bool = True,
    always_geocode: bool = False,
    geo_cache_mode: str = "CacheOnly",
    fuzz: bool = False
) -> Dict[str, Any]:
    """
    Initialize GeolocatedGedcom and measure performance. Returns an ordered result dict.
    """
    if cache_file_path is not None:
        assert os.path.exists(cache_file_path), f"Missing cache file: {cache_file_path}"
    assert os.path.exists(gedcom_file_path), f"Missing gedcom file: {gedcom_file_path}"
    assert os.path.exists(geo_config_path), f"Missing geo config file: {geo_config_path}"
    t0 = timeit.default_timer()
    geo = GeolocatedGedcom(
        gedcom_file=Path(gedcom_file_path),
        location_cache_file=Path(cache_file_path) if cache_file_path else None,
        default_country=None,
        always_geocode=always_geocode,
        geo_config_path=Path(geo_config_path),
        cache_only=cache_only,
        fuzz=fuzz
    )
    t1 = timeit.default_timer()
    return {
        "Gedcom Sample": label,
        "Fuzz": fuzz,
        "Geo Cache Mode": geo_cache_mode,
        "Cache Only": cache_only,
        "Always Geocode": always_geocode,
        "Entries": len(geo.address_book.addresses()),
        "Entries Existed": geo.address_book.address_existed,
        "Entries Didn't Exist": geo.address_book.address_didnt_exist,
        "People": len(geo.people),
        "Init Time (s)": float(f"{t1 - t0:.5f}")
    }

@pytest.mark.slow
@pytest.mark.parametrize("fuzz", [False, True])
@pytest.mark.parametrize("label,cache_file_path,gedcom_file_path", [
    ('simple', 'gedcom-samples/geo_cache.csv', 'gedcom-samples/input.ged'),
    ('pres2020', 'gedcom-samples/pres/geo_cache.csv', 'gedcom-samples/pres/pres2020.ged'),
    ('royal92', 'gedcom-samples/royal/geo_cache.csv', 'gedcom-samples/royal/royal92.ged'),
    # ('habs', 'gedcom-samples/habs/geo_cache.csv', 'gedcom-samples/habs/Habsburg.ged'),
    # ('ivar', 'gedcom-samples/ivar/geo_cache.csv', 'gedcom-samples/ivar/IvarKingOfDublin.ged'),
    # ('queen', 'gedcom-samples/queen/geo_cache.csv', 'gedcom-samples/queen/Queen.ged'),
    # ('bourbon', 'gedcom-samples/sample-bourbon/geo_cache.csv', 'gedcom-samples/sample-bourbon/bourbon.ged'),
    # ('kennedy', 'gedcom-samples/sample-kennedy/geo_cache.csv', 'gedcom-samples/sample-kennedy/kennedy.ged'),
    # ('longsword', 'gedcom-samples/longsword/geo_cache.csv', 'gedcom-samples/longsword/longsword.ged'),
])
@pytest.mark.parametrize("geo_config_path", ['geo_config.yaml'])
# @pytest.mark.parametrize("cache_only", [False, True])
@pytest.mark.parametrize("geo_cache_mode", ["CacheOnly", "CacheAndGeocode", "GeocodeNoCache"])
def test_geolocatedgedcom_performance(label: str, cache_file_path: str, gedcom_file_path: str, geo_config_path: str, fuzz: bool, geo_cache_mode: str, collect_and_report_results):
    """
    Runs GeolocatedGedcom performance test for each sample and fuzz setting.
    Appends results to the session-scoped results list.
    """
    print(f"File: {label}, Fuzz: {fuzz}, Geo Mode: {geo_cache_mode}")
    cache_only = (geo_cache_mode == "CacheOnly")
    always_geocode = False
    if geo_cache_mode == "GeocodeNoCache":
        cache_file_path = None
    res = run_geolocatedgedcom_perf(label, cache_file_path, gedcom_file_path, geo_config_path, cache_only, always_geocode, geo_cache_mode, fuzz)
    collect_and_report_results.append(res)
