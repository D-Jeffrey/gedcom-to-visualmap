import pytest
from render.folium.name_processor import NameProcessor

def test_parse_name_and_format():
    np = NameProcessor("John Quincy Adams")
    assert np.firstName == "John"
    assert np.lastName == "Adams"
    assert np.middleNames == ["Quincy"]
    assert np.getInitials() == "JQA"
    assert np.formatName() == "Adams, John Quincy"

def test_parse_name_single():
    np = NameProcessor("Plato")
    assert np.firstName == "Plato"
    assert np.lastName is None
    assert np.middleNames == []
    assert np.getInitials() == "P"
    assert np.formatName() == "None, Plato"

def test_parse_name_two():
    np = NameProcessor("Ada Lovelace")
    assert np.firstName == "Ada"
    assert np.lastName == "Lovelace"
    assert np.middleNames == []
    assert np.getInitials() == "AL"
    assert np.formatName() == "Lovelace, Ada"

@pytest.mark.parametrize("name,expected", [
    ("John Doe", True),
    ("Marie Curie", True),
    ("John123", False),
    ("", True),
    ("Jean-Luc Picard", False),  # Hyphen not allowed
])
def test_is_valid_name(name, expected):
    assert NameProcessor.isValidName(name) == expected

@pytest.mark.parametrize("name1,name2,expected", [
    ("John Doe", "john doe", True),
    ("  Alice  ", "alice", True),
    ("Bob", "Bobby", False),
    ("Jane", "Jane ", True),
])
def test_compare_names(name1, name2, expected):
    assert NameProcessor.compareNames(name1, name2) == expected

@pytest.mark.parametrize("last,expected", [
    ("O'Connor", "oconnor"),
    ("García", "garcia"),
    ("Smith (Born Jones)", "smith"),
    ("D'Angelo", "dangelo"),
    ("Müller", "muller"),
    ("Le Blanc", "leblanc"),
])
def test_simplify_last_name(last, expected):
    assert NameProcessor.simplifyLastName(last) == expected

@pytest.mark.parametrize("last,expected", [
    ("Smith", "S530"),
    ("Johnson", "J525"),
    ("Williams", "W452"),
    ("Brown", "B650"),
    ("Müller", "M460"),
    ("O'Connor", "O256"),
    ("", ""),
])
def test_soundex(last, expected):
    assert NameProcessor.soundex(last) == expected