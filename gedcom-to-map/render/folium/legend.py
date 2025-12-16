"""
Legend overlay for Folium maps using a Jinja2 template.
"""
from branca.element import MacroElement, Template

legend_template = """
{% macro html(this, kwargs) %}
    <div id="map_legend" class="legend">
        <h4>Legend</h4>
        <!-- Dynamic generation of legend items -->
        {{ this.legend_items|safe }}
    </div>
    <style>
        .legend {
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 5px rgba(0,0,0,0.5);
            font-size: 14px;
            line-height: 1.5;
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
        }
        .legend div {
            display: flex;
            align-items: center;
        }
        .legend i {
            margin-right: 5px;
        }
    </style>
{% endmacro %}
"""

# Use MacroElement to add the template to the map

class Legend(MacroElement):
    """
    A Folium MacroElement for displaying a custom legend on the map.
    """
    def __init__(self) -> None:
        super().__init__()
        self._template = Template(legend_template)
