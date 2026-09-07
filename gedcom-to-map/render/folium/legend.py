"""
Legend overlay for Folium maps using a Jinja2 template.
"""

from branca.element import MacroElement, Template
from .constants import MidPointMarker

def _build_legend_items() -> str:
    """Build HTML legend items from MidPointMarker dictionary."""
    items = []
    for key, (icon, color, _shown) in MidPointMarker.items():
        item_html = (
            f'<div style="margin: 5px;">'
            f'<i class="fa fa-{icon}" style="color: {color};"></i> '
            f'{key}</div>'
        )
        items.append(item_html)
    return ''.join(items)

legend_template = f"""
{{% macro html(this, kwargs) %}}
    <div id="map_legend" class="legend">
        <h4>Legend</h4>
        <!-- Dynamic generation of legend items -->
        {_build_legend_items()}
    </div>
    <style>
        .legend {{
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
        }}
        .legend div {{
            display: flex;
            align-items: center;
        }}
        .legend i {{
            margin-right: 5px;
        }}
    </style>
{{% endmacro %}}
"""


class Legend(MacroElement):
    """
    A Folium MacroElement for displaying a custom legend on the map.
    """

    def __init__(self) -> None:
        super().__init__()
        self._template = Template(legend_template)
