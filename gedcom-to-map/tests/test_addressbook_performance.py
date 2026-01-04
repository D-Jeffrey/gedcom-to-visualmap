import os
import timeit
import pytest
import yaml
from typing import List, Dict, Any, Tuple, Iterator
from geo_gedcom.addressbook import FuzzyAddressBook
from geo_gedcom.geocache import GeoCache
from geo_gedcom.location import Location

def load_geo_cache(cache_file: str) -> Dict[str, Any]:
    always_geocode = False
    alt_place_file_path = None
    file_geo_cache_path = ''
    cache = GeoCache(cache_file, always_geocode, alt_place_file_path, file_geo_cache_path)
    geo_cache = cache.geo_cache
    assert len(geo_cache) > 0
    return geo_cache

def create_locations(geo_cache: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float]:
    t0 = timeit.default_timer()
    address_location_list = []
    for lookup in geo_cache.values():
        address = lookup['address']
        location = Location(address=lookup['address'], latitude=lookup['latitude'], longitude=lookup['longitude'],
                            country_name=lookup['country_name'], country_code=lookup['country_code'],
                            found_country=lookup['found_country'], alt_addr=lookup['alt_addr'])
        address_location_list.append({'address': address, 'location': location})
    t1 = timeit.default_timer()
    return address_location_list, t1 - t0

def add_addresses_to_book(address_location_list: List[Dict[str, Any]], fuzz: bool = True) -> Tuple[FuzzyAddressBook, float]:
    ab = FuzzyAddressBook(fuzz=fuzz)
    t0 = timeit.default_timer()
    for item in address_location_list:
        address = item['address']
        location = item['location']
        ab.add_address(address, location)
    t1 = timeit.default_timer()
    return ab, t1 - t0

def fuzzy_lookup_success(geo_cache: Dict[str, Any], ab: FuzzyAddressBook) -> Tuple[int, float]:
    t0 = timeit.default_timer()
    fuzzy_success = 0
    for lookup in geo_cache.values():
        ladr = lookup['address']
        adr = ab.fuzzy_lookup_address(ladr)
        if adr is not None:
            fuzzy_success += 1
    t1 = timeit.default_timer()
    return fuzzy_success, t1 - t0

def get_address_success(geo_cache: Dict[str, Any], ab: FuzzyAddressBook) -> Tuple[int, float]:
    t0 = timeit.default_timer()
    get_success = 0
    for lookup in geo_cache.values():
        ladr = lookup['address']
        adr = ab.get_address(ladr)
        if adr is not None and adr.address == ladr:
            get_success += 1
    t1 = timeit.default_timer()
    return get_success, t1 - t0

@pytest.fixture(scope="session")
def performance_results() -> Iterator[Dict[str, Any]]:
    """
    Collects and prints address book performance results, and writes them to YAML.
    """
    results = []
    yield results
    print("\n### Addressbook Performance")
    header = [
        "Gedcom Sample", "Fuzz", "Entries", "Fuzzy %", "Get %", "Fuzz Rate (/s)", "Get Rate (/s)",
        "Location Time (s)", "Add address Time (s)", "Fuzzy Time (s)", "Get Time (s)",
        "Total Time (s)", "Fuzzy #", "Get #"
    ]
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for r in results:
        row = [
            str(r["Gedcom Sample"]),
            str(r["Fuzz"]),
            str(r["Entries"]),
            r["Fuzzy %"],
            r["Get %"],
            f"{r['Fuzz Rate (/s)']:,}",
            f"{r['Get Rate (/s)']:,}",
            f"{r['Location Time (s)']:.5f}",
            f"{r['Add address Time (s)']:.5f}",
            f"{r['Fuzzy Time (s)']:.5f}",
            f"{r['Get Time (s)']:.5f}",
            f"{r['Total Time (s)']:.5f}",
            str(r["Fuzzy #"]),
            str(r["Get #"])
        ]
        print("| " + " | ".join(row) + " |")
    yaml_path = os.path.join(os.path.dirname(__file__), "addressbook_performance_results.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump({'results': results}, f, default_flow_style=False)

@pytest.mark.slow
@pytest.mark.parametrize("fuzz", [False, True])
@pytest.mark.parametrize("label,cache_file_path", [
    ('simple', 'gedcom-samples/geo_cache.csv'),
    ('pres2020', 'gedcom-samples/pres/geo_cache.csv'),
    ('royal92', 'gedcom-samples/royal/geo_cache.csv'),
    # ('habs', 'gedcom-samples/habs/geo_cache.csv'),
    # ('ivar', 'gedcom-samples/ivar/geo_cache.csv'),
    # ('queen', 'gedcom-samples/queen/geo_cache.csv'),
    # ('bourbon', 'gedcom-samples/sample-bourbon/geo_cache.csv'),
    # ('kennedy', 'gedcom-samples/sample-kennedy/geo_cache.csv'),
    # ('longsword', 'gedcom-samples/longsword/geo_cache.csv'),
])
def test_addressbook_performance(label: str, cache_file_path: str, fuzz: bool, performance_results: List[Dict[str, Any]]):
    run_performance_test(label, cache_file_path, performance_results, fuzz)

def run_performance_test(label: str, cache_file_path: str, performance_results: List[Dict[str, Any]], fuzz: bool) -> None:
    """
    Runs a single address book performance test and appends the ordered result dict to performance_results.
    """
    geo_cache = load_geo_cache(cache_file_path)
    print(f"File: {label}, Fuzz: {fuzz}")

    address_location_list, t_location = create_locations(geo_cache)
    ab, t_add = add_addresses_to_book(address_location_list, fuzz=fuzz)
    fuzzy_success, t_fuzzy = fuzzy_lookup_success(geo_cache, ab)
    get_success, t_get = get_address_success(geo_cache, ab)
    
    fuzzy_success_percent = fuzzy_success / len(geo_cache) * 100 if len(geo_cache) > 0 else 0
    get_success_percent = get_success / len(geo_cache) * 100 if len(geo_cache) > 0 else 0
    fuzzy_rate = fuzzy_success / t_fuzzy if t_fuzzy > 0 else 0
    get_rate = get_success / t_get if t_get > 0 else 0
    total_time = t_location + t_add + t_fuzzy + t_get
    sample_label = label.replace(")", "").strip()
    ordered_result = {
        "Gedcom Sample": sample_label,
        "Fuzz": fuzz,
        "Entries": len(geo_cache),
        "Fuzzy %": f"{fuzzy_success_percent:.1f}%",
        "Get %": f"{get_success_percent:.1f}%",
        "Fuzz Rate (/s)": float(f"{fuzzy_rate:.1f}"),
        "Get Rate (/s)": float(f"{get_rate:.1f}"),
        "Location Time (s)": float(f"{t_location:.5f}"),
        "Add address Time (s)": float(f"{t_add:.5f}"),
        "Fuzzy Time (s)": float(f"{t_fuzzy:.5f}"),
        "Get Time (s)": float(f"{t_get:.5f}"),
        "Total Time (s)": float(f"{total_time:.5f}"),
        "Fuzzy #": fuzzy_success,
        "Get #": get_success
    }
    performance_results.append(ordered_result)
