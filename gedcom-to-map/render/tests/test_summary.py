import pytest
import os
import pandas as pd
from render import summary


class DummyLocation:
    def __init__(
        self, lat=0, lon=0, country_name="Country", continent="Continent", alt_addr="Alt", canonical_addr=None
    ):
        self.latlon = type("LatLon", (), {"lat": lat, "lon": lon})()
        self.found_country = "FC"
        self.country_name = country_name
        self.continent = continent
        self.alt_addr = alt_addr
        self.canonical_addr = canonical_addr
        self.used = 1  # Add this line


class DummyAddressBook:
    def addresses(self):
        return {"Place1": DummyLocation(1, 2), "Place2": DummyLocation(3, 4)}

    def get_address_list(self):
        return ["Place1", "Place2"]

    def get_summary_row_dict(self, place):
        return {"address": place, "lat": 1, "lon": 2}

    @property
    def summary_columns(self):
        return ["address", "lat", "lon"]

    def get_alt_addr_list(self):
        return ["Alt1"]

    def get_address_list_for_alt_addr(self, alt_addr):
        return ["Place1"]

    def get_address(self, address):
        return DummyLocation(canonical_addr="Canonical1")


class DummyEvent:
    def __init__(self, place, location, date):
        self.place = place
        self.location = location
        self.date = type("Date", (), {"year_num": 2000})()


class DummyPerson:
    def __init__(self, name, birth=None, death=None):
        self.name = name
        self.birth = birth
        self.death = death

    def get_event(self, event_type):
        if event_type == "birth":
            return self.birth
        elif event_type == "death":
            return self.death
        return None


def test_write_places_summary(tmp_path):
    ab = DummyAddressBook()
    out = tmp_path / "places.csv"
    summary.write_places_summary(ab, str(out))
    assert out.exists()
    df = pd.read_csv(out)
    assert "place" in df.columns


def test_write_people_summary(tmp_path):
    people = {
        "I1": DummyPerson(
            "Alice", DummyEvent("Place1", DummyLocation(), None), DummyEvent("Place2", DummyLocation(), None)
        ),
        "I2": DummyPerson("Bob"),
    }
    out = tmp_path / "people.csv"
    summary.write_people_summary(people, str(out))
    assert out.exists()
    df = pd.read_csv(out)
    assert "Name" in df.columns


def test_write_geocache_summary(tmp_path):
    ab = DummyAddressBook()
    out = tmp_path / "geocache.csv"
    summary.write_geocache_summary(ab, str(out))
    assert out.exists()
    df = pd.read_csv(out)
    assert "address" in df.columns


def test_write_alt_places_summary(tmp_path):
    ab = DummyAddressBook()
    out = tmp_path / "alt_places.csv"
    summary.write_alt_places_summary(ab, str(out))
    assert out.exists()
    df = pd.read_csv(out)
    assert "alt_addr" in df.columns


def test_write_birth_death_countries_summary(tmp_path):
    people = {
        "I1": DummyPerson(
            "Alice",
            DummyEvent("Place1", DummyLocation(country_name="A", continent="X"), None),
            DummyEvent("Place2", DummyLocation(country_name="B", continent="Y"), None),
        ),
        "I2": DummyPerson("Bob"),
    }
    out = tmp_path / "bd_countries.csv"
    img = summary.write_birth_death_countries_summary(people, str(out), "test.ged")
    assert out.exists()
    assert os.path.exists(img)


def test_save_birth_death_heatmap_matrix(tmp_path):
    data = {("A", "B"): {"count": 2, "birth_continent": "X", "death_continent": "Y"}}
    out = tmp_path / "heatmap.png"
    summary.save_birth_death_heatmap_matrix(data, str(out), "test.ged")
    assert out.exists()
