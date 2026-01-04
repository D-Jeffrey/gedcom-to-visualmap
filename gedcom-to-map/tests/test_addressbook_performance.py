import os
import timeit
import pytest
from geo_gedcom.addressbook import FuzzyAddressBook
from geo_gedcom.geocache import GeoCache
from geo_gedcom.location import Location

def load_geo_cache(cache_file):
    always_geocode = False
    alt_place_file_path = None
    file_geo_cache_path = ''
    cache = GeoCache(cache_file, always_geocode, alt_place_file_path, file_geo_cache_path)
    geo_cache = cache.geo_cache
    assert len(geo_cache) > 0
    return geo_cache

def create_locations(geo_cache):
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

def add_addresses_to_book(address_location_list, fuzz: bool = True):
    ab = FuzzyAddressBook(fuzz=fuzz)
    t0 = timeit.default_timer()
    for item in address_location_list:
        address = item['address']
        location = item['location']
        ab.add_address(address, location)
    t1 = timeit.default_timer()
    return ab, t1 - t0



def fuzzy_lookup_success(geo_cache, ab):
    t0 = timeit.default_timer()
    fuzzy_success = 0
    for lookup in geo_cache.values():
        ladr = lookup['address']
        adr = ab.fuzzy_lookup_address(ladr)
        if adr is not None:
            fuzzy_success += 1
        else:
            pass
            # print (f"Fuzzy failed: `{ladr}`")

    t1 = timeit.default_timer()
    return fuzzy_success, t1 - t0

def get_address_success(geo_cache, ab):
    t0 = timeit.default_timer()
    get_success = 0
    for lookup in geo_cache.values():
        ladr = lookup['address']
        adr = ab.get_address(ladr)
        if adr is not None and adr.address == ladr:
            get_success += 1
        else:
            pass
            #if adr is None:
            #    print (f"Get failed  : `{ladr}` vs none")
            #else:
            #    print (f"Get failed  : `{ladr}` vs `{adr.address}`")
    t1 = timeit.default_timer()
    return get_success, t1 - t0

@pytest.fixture(scope="session")
def performance_results():
    results = []
    yield results
    print("\n### Addressbook Performance")
    header = [
        "Gedcom Sample", "Entries", "Fuzzy %", "Get %", "Fuzz Rate (/s)", "Get Rate (/s)",
        "Location Time (s)", "Add address Time (s)", "Fuzzy Time (s)", "Get Time (s)",
        "Total Time (s)", "Fuzzy #", "Get #"
    ]
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for r in results:
        fuzzy_success_percent = r['fuzzy_success'] / r['entries'] * 100 if r['entries'] > 0 else 0
        get_success_percent = r['get_success'] / r['entries'] * 100 if r['entries'] > 0 else 0
        fuzzy_rate = r['fuzzy_success'] / r['t_fuzzy'] if r['t_fuzzy'] > 0 else 0
        get_rate = r['get_success'] / r['t_get'] if r['t_get'] > 0 else 0
        total_time = r['t_location'] + r['t_add'] + r['t_fuzzy'] + r['t_get']
        # Remove any trailing parenthesis or stray characters from sample label
        sample_label = r['gedcom_sample'].replace(")", "").strip()
        row = [
            sample_label,
            str(r['entries']),
            f"{fuzzy_success_percent:.1f}%",
            f"{get_success_percent:.1f}%",
            f"{fuzzy_rate:,.1f}",
            f"{get_rate:,.1f}",
            f"{r['t_location']:.5f}",
            f"{r['t_add']:.5f}",
            f"{r['t_fuzzy']:.5f}",
            f"{r['t_get']:.5f}",
            f"{total_time:.5f}",
            str(r['fuzzy_success']),
            str(r['get_success'])
        ]
        print("| " + " | ".join(row) + " |")

@pytest.mark.parametrize("label,cache_file_path", [
    ('simple', 'gedcom-samples/geo_cache.csv'),
    ('pres2020', 'gedcom-samples/pres/geo_cache.csv'),
    ('royal92', 'gedcom-samples/royal/geo_cache.csv'),
    ('habs', 'gedcom-samples/habs/geo_cache.csv'),
    ('ivar', 'gedcom-samples/ivar/geo_cache.csv'),
    ('queen', 'gedcom-samples/queen/geo_cache.csv'),
    ('bourbon', 'gedcom-samples/sample-bourbon/geo_cache.csv'),
    ('kennedy', 'gedcom-samples/sample-kennedy/geo_cache.csv'),
    ('longsword', 'gedcom-samples/longsword/geo_cache.csv'),
])
def test_addressbook_performance(label, cache_file_path, performance_results):
    for fuzz in [False, True]:
        fuzz_label = "Fuzzy" if fuzz else "Exact"
        print(f"\n--- Testing {fuzz_label} AddressBook Performance for {label} ---")
        run_performance_test(label + " " + fuzz_label, cache_file_path, performance_results, fuzz)

def run_performance_test(label, cache_file_path, performance_results, fuzz: bool):
    geo_cache = load_geo_cache(cache_file_path)
    cache_file_leafname = os.path.basename(cache_file_path)
    print("====================================")
    print(f"Testing cache file: {label} ({cache_file_leafname}); Entries: {len(geo_cache)}")

    address_location_list, t_location = create_locations(geo_cache)
    print(f"- Location time : {t_location:.4f}s")
    
    ab, t_add = add_addresses_to_book(address_location_list, fuzz=fuzz)
    print(f"- Add_address time : {t_add:.4f}s")

    fuzzy_success, t_fuzzy = fuzzy_lookup_success(geo_cache, ab)
    get_success, t_get = get_address_success(geo_cache, ab)

    print(f"- Fuzzy_lookup_address time {t_fuzzy:.4f}s with {fuzzy_success} successes out of {len(geo_cache)}")
    print(f"- Get_address time {t_get:.4f}s with {get_success} successes out of {len(geo_cache)}")
    
    summary = {
        'gedcom_sample': f"{label})",
        'entries': len(geo_cache),
        't_location': t_location,
        't_add': t_add,
        't_fuzzy': t_fuzzy,
        't_addoff': t_add,
        't_get': t_get,
        'fuzzy_success': fuzzy_success,
        'get_success': get_success
    }

    performance_results.append(summary)

    # Print timings for manual review
    print(f"{cache_file_path}: Location: {t_location:.4f}s, Add: {t_add:.4f}s, Add: {t_add:.4f}s, Fuzzy: {t_fuzzy:.4f}s, Get: {t_get:.4f}s, Fuzzy Success: {fuzzy_success}, Get Success: {get_success}")

    # Assert high success rates
    # assert fuzzy_success / len(geo_cache) > 0.99, f"Fuzzy lookup success rate below 99% - only {(fuzzy_success/len(geo_cache)*100):.3f}%"
    # assert get_success / len(geo_cache) > 0.50, f"Get retrieval success rate below 50% - only {(get_success/len(geo_cache)*100):.3f}%"

    