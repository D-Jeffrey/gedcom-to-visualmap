# models Module

This module contains the core data structures and utilities for representing and rendering visual maps from GEDCOM data. It provides foundational classes for people, events, locations, colors, and lines, which are used throughout the mapping and visualization pipeline.

## Key Classes

- **Color:** RGB color representation for map elements.
- **LatLon:** Latitude/longitude coordinate pair with validation and utility methods.
- **Line:** Represents a polyline or connection between locations/people, with support for color, path, and branch/prof attributes.
- **Person:** Data model for an individual in the family tree, including references to events and relationships.
- **LifeEvent:** Represents a life event (birth, death, etc.) with date, place, and event type.
- **Creator:** Logic for generating lines and traversing the family tree for visualization.
- **Rainbow:** Color generator for assigning visually distinct colors to lines or groups.

## Example Usage

```python
from models import Person, LifeEvent, LatLon, Line, Color, Creator, Rainbow

# Create a person and a life event
p = Person("I1")
event = LifeEvent(place="London", date="1900", what="BIRT")
p.birth = event

# Create a line between two locations
ll1 = LatLon(51.5, -0.1)
ll2 = LatLon(52.0, 0.1)
color = Color(255, 0, 0)
line = Line([ll1, ll2], fromlocation=ll1, tolocation=ll2, color=color, path="test", branch=0, prof=1)

# Use Rainbow to get a color
rb = Rainbow()
c = rb.get(0.5)
```

## Directory Structure

```
models/
├── __init__.py
├── color.py
├── creator.py
├── line.py
├── rainbow.py
├── person.py
├── lifeevent.py
├── latlon.py
├── tests/
│   ├── test_color.py
│   ├── test_creator.py
│   ├── test_line.py
│   ├── test_rainbow.py
│   └── ...
└── README.md
```

## Testing

To run the model tests:
```sh
pytest models/tests/
```

## Notes

- These classes are designed to be used as part of the larger `gedcom-to-visualmap` project.
- All classes include type hints and docstrings for clarity and maintainability.
- See the main project documentation for integration and usage examples.

## Authors

- @colin0brass
- @D-jeffrey

## License

See the main repository LICENSE.txt for details.