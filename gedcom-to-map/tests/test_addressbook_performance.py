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
    locations = [
        Location(address=lookup['address'], latitude=lookup['latitude'], longitude=lookup['longitude'],
                 country_name=lookup['country_name'], country_code=lookup['country_code'],
                 found_country=lookup['found_country'], alt_addr=lookup['alt_addr'])
        for lookup in geo_cache.values()
    ]
    t1 = timeit.default_timer()
    return locations, t1 - t0

def add_addresses_to_book(geo_cache):
    ab = FuzzyAddressBook()
    t0 = timeit.default_timer()
    for lookup in geo_cache.values():
        location = Location(address=lookup['address'], latitude=lookup['latitude'], longitude=lookup['longitude'],
                            country_name=lookup['country_name'], country_code=lookup['country_code'],
                            found_country=lookup['found_country'], alt_addr=lookup['alt_addr'])
        ab.add_address(lookup['address'], location)
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
    print("Cache File|Entries|Fuzzy % |Get %|Fuzz Rate|Get Rate|Location|Add address|Fuzzy Time|Get Time|Fuzzy #| Get #")
    print(f"{'---|' * 12}")
    for r in results:
        print(f"{r['cache_file']}|{r['entries']}|{r['fuzzy_success']/r['entries']*100:.1f}%|{r['get_success']/r['entries']*100:.1f}%|" +
              f"{r['fuzzy_success']/r['t_fuzzy']:,.1f}/s|{r['get_success']/r['t_get']:,.1f}/s|" + 
              f"{(r['t_location']):.5f}s|{(r['t_add']-r['t_location']):.5f}s|{r['t_fuzzy']:.5f}s|{r['t_get']:.5f}s|{r['fuzzy_success']}|{r['get_success']}")

# Note: some of these cache files are not currently included in the online repository
# They should be created from GEDCOM samples with geo-coding enabled, using the "SUM" output option.
@pytest.mark.parametrize("label,cache_file_path", [
    ('simple', 'gedcom-samples/geo_cache.csv'),
    ('pres2020', 'gedcom-to-map/geo_gedcom/gedcom-samples/pres/geo_cache.csv'),
    ('royal92', 'gedcom-to-map/geo_gedcom/gedcom-samples/royal/geo_cache.csv'),
    # these are in the online repository:
    ('ivar', 'gedcom-to-map/geo_gedcom/gedcom-samples/ivar/geo_cache.csv'),
    ('bourbon', 'gedcom-samples/sample-bourbon/geo_cache.csv'),
    ('kennedy', 'gedcom-samples/sample-kennedy/geo_cache.csv'),
    # ('longsword', 'gedcom-to-map/geo_gedcom/gedcom-samples/longsword/geo_cache.csv'),
])
def test_addressbook_performance(label, cache_file_path, performance_results):
    geo_cache = load_geo_cache(cache_file_path)
    cache_file_leafname = os.path.basename(cache_file_path)
    print("====================================")
    print(f"Testing cache file: {label} ({cache_file_leafname}); Entries: {len(geo_cache)}")

    locations, t_location = create_locations(geo_cache)
    print(f"- Location time : {t_location:.4f}s")
    
    ab, t_add = add_addresses_to_book(geo_cache)
    print(f"- Location + add_address time : {t_add:.4f}s")
    print(f"- Add_address time : {t_add - t_location:.4f}s")

    fuzzy_success, t_fuzzy = fuzzy_lookup_success(geo_cache, ab)
    get_success, t_get = get_address_success(geo_cache, ab)

    print(f"- Fuzzy_lookup_address time {t_fuzzy:.4f}s with {fuzzy_success} successes out of {len(geo_cache)}")
    print(f"- Get_address time {t_get:.4f}s with {get_success} successes out of {len(geo_cache)}")
    
    summary = {
        'cache_file': f"{label} ({cache_file_leafname})",
        'entries': len(geo_cache),
        't_location': t_location,
        't_add': t_add,
        't_fuzzy': t_fuzzy,
        't_get': t_get,
        'fuzzy_success': fuzzy_success,
        'get_success': get_success
    }

    performance_results.append(summary)

    # Print timings for manual review
    print(f"{cache_file_path}: Location: {t_location:.4f}s, Add: {t_add:.4f}s, Fuzzy: {t_fuzzy:.4f}s, Get: {t_get:.4f}s, Fuzzy Success: {fuzzy_success}, Get Success: {get_success}")

    # Assert high success rates
    assert fuzzy_success / len(geo_cache) > 0.99, f"Fuzzy lookup success rate below 99% - only {(fuzzy_success/len(geo_cache)*100):.3f}%"
    assert get_success / len(geo_cache) > 0.50, f"Get retrieval success rate below 50% - only {(get_success/len(geo_cache)*100):.3f}%"

    