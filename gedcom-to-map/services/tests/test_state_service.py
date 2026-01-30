from services.state_service import GVState
from geo_gedcom.person import Person


def test_gvstate_init():
    """Test GVState initialization sets all attributes correctly."""
    state = GVState()
    assert state.people is None
    assert state.lookup is None
    assert state.mainPerson is None
    assert state.Name is None
    assert state.Referenced is None
    assert state.selectedpeople == 0
    assert state.lastlines is None
    assert state.heritage is None
    assert state.timeframe == {'from': None, 'to': None}
    assert state.totalpeople == 0
    assert state.mainPersonLatLon is None
    assert state.parsed is False
    assert state.time is not None


def test_gvstate_direct_attribute_access():
    """Test direct attribute get/set works correctly."""
    state = GVState()
    
    # Test simple attribute assignment
    state.Name = 'TestPerson'
    assert state.Name == 'TestPerson'
    
    # Test lookup attribute
    state.lookup = 'mock_geocoded_gedcom'
    assert state.lookup == 'mock_geocoded_gedcom'
    
    # Test people dictionary
    state.people = {'P1': 'person1', 'P2': 'person2'}
    assert state.people == {'P1': 'person1', 'P2': 'person2'}
    
    # Test flags
    state.parsed = True
    assert state.parsed is True


def test_gvstate_timeframe_single_reference():
    """Test adding single time reference updates timeframe."""
    state = GVState()
    
    class DummyEvent:
        year_num = 1999
    
    state.addtimereference(DummyEvent())
    assert state.timeframe['from'] == 1999
    assert state.timeframe['to'] == 1999


def test_gvstate_timeframe_multiple_references():
    """Test adding multiple time references expands timeframe correctly."""
    state = GVState()
    
    class Event1:
        year_num = 1950
    
    class Event2:
        year_num = 2000
    
    class Event3:
        year_num = 1975
    
    state.addtimereference(Event1())
    assert state.timeframe['from'] == 1950
    assert state.timeframe['to'] == 1950
    
    state.addtimereference(Event2())
    assert state.timeframe['from'] == 1950
    assert state.timeframe['to'] == 2000
    
    state.addtimereference(Event3())
    assert state.timeframe['from'] == 1950
    assert state.timeframe['to'] == 2000


def test_gvstate_timeframe_reset():
    """Test resetting timeframe clears values."""
    state = GVState()
    
    class DummyEvent:
        year_num = 1999
    
    state.addtimereference(DummyEvent())
    assert state.timeframe['from'] == 1999
    
    state.resettimeframe()
    assert state.timeframe == {'from': None, 'to': None}


def test_gvstate_timeframe_ignore_invalid():
    """Test addtimereference ignores None and objects without year_num."""
    state = GVState()
    
    # None reference should be ignored
    state.addtimereference(None)
    assert state.timeframe == {'from': None, 'to': None}
    
    # Object without year_num should be ignored
    class InvalidEvent:
        pass
    
    state.addtimereference(InvalidEvent())
    assert state.timeframe == {'from': None, 'to': None}
    
    # Object with None year_num should be ignored
    class NoneYearEvent:
        year_num = None
    
    state.addtimereference(NoneYearEvent())
    assert state.timeframe == {'from': None, 'to': None}


def test_gvstate_timeframe_updates_both_bounds():
    """Test timeframe updates both from and to when appropriate."""
    state = GVState()
    
    class Event1:
        year_num = 2000
    
    # First event sets both from and to
    state.addtimereference(Event1())
    assert state.timeframe['from'] == 2000
    assert state.timeframe['to'] == 2000
    
    class Event2:
        year_num = 1980
    
    # Earlier event updates from
    state.addtimereference(Event2())
    assert state.timeframe['from'] == 1980
    assert state.timeframe['to'] == 2000
    
    class Event3:
        year_num = 2020
    
    # Later event updates to
    state.addtimereference(Event3())
    assert state.timeframe['from'] == 1980
    assert state.timeframe['to'] == 2020


def test_gvstate_setmain_with_valid_person():
    """Test setMain with valid person ID sets all related state."""
    state = GVState()
    
    # Create mock Person object
    class MockPerson:
        def __init__(self, name):
            self.name = name
        
        def bestLatLon(self):
            return (40.7128, -74.0060)  # NYC coordinates
    
    person1 = MockPerson('John Doe')
    state.people = {'P1': person1}
    
    state.setMain('P1')
    
    assert state.Main == 'P1'
    assert state.mainPerson == person1
    assert state.Name == 'John Doe'
    assert state.mainPersonLatLon == (40.7128, -74.0060)


def test_gvstate_setmain_with_invalid_person():
    """Test setMain with invalid person ID sets default values."""
    state = GVState()
    state.people = {}
    
    state.setMain('INVALID_ID')
    
    assert state.Main == 'INVALID_ID'
    assert state.mainPerson is None
    assert state.Name == '<not selected>'
    assert state.mainPersonLatLon is None


def test_gvstate_setmain_without_bestlatlon():
    """Test setMain with person that doesn't have bestLatLon method."""
    state = GVState()
    
    class SimplePerson:
        def __init__(self, name):
            self.name = name
    
    person1 = SimplePerson('Jane Doe')
    state.people = {'P1': person1}
    
    state.setMain('P1')
    
    assert state.mainPerson == person1
    assert state.Name == 'Jane Doe'
    assert state.mainPersonLatLon is None


def test_gvstate_setmain_resets_lineage_on_change():
    """Test setMain resets lineage tracking when main person changes."""
    state = GVState()
    
    class MockPerson:
        def __init__(self, name):
            self.name = name
    
    person1 = MockPerson('Person 1')
    person2 = MockPerson('Person 2')
    state.people = {'P1': person1, 'P2': person2}
    
    # Set initial main person and lineage data
    state.setMain('P1')
    state.selectedpeople = 10
    state.lastlines = {'some': 'data'}
    state.heritage = {'heritage': 'data'}
    state.Referenced = {'ref': 'data'}
    
    # Change to different person - should reset lineage
    state.setMain('P2')
    
    assert state.mainPerson == person2
    assert state.selectedpeople == 0
    assert state.lastlines is None
    assert state.heritage is None
    assert state.Referenced is None


def test_gvstate_setmain_same_person_no_reset():
    """Test setMain with same person doesn't reset lineage."""
    state = GVState()
    
    class MockPerson:
        def __init__(self, name):
            self.name = name
    
    person1 = MockPerson('Person 1')
    state.people = {'P1': person1}
    
    # Set initial main person and lineage data
    state.setMain('P1')
    state.selectedpeople = 10
    state.lastlines = {'some': 'data'}
    
    # Set same person again - should NOT reset lineage
    state.setMain('P1')
    
    assert state.mainPerson == person1
    assert state.selectedpeople == 10
    assert state.lastlines == {'some': 'data'}

