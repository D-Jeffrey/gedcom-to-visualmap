"""
Layer Control buttons for checking/unchecking all layers on a Folium map.
"""

from branca.element import MacroElement, Template

layer_control_template = """
{% macro html(this, kwargs) %}
    <div id="layer_control_buttons" style="
        position: absolute;
        top: 10px;
        left: 50px;
        z-index: 999;
        background: white;
        padding: 8px;
        border-radius: 5px;
        box-shadow: 0 0 5px rgba(0,0,0,0.5);
    ">
        <button id="check_all_btn" style="
            padding: 6px 12px;
            margin: 2px;
            border: 1px solid #ccc;
            border-radius: 3px;
            background-color: #fff;
            cursor: pointer;
            font-size: 12px;
        ">Check All</button>
        <button id="uncheck_all_btn" style="
            padding: 6px 12px;
            margin: 2px;
            border: 1px solid #ccc;
            border-radius: 3px;
            background-color: #fff;
            cursor: pointer;
            font-size: 12px;
        ">Uncheck All</button>
    </div>

    <script>
        // Wait for the map to be fully loaded
        setTimeout(function() {
            document.getElementById('check_all_btn').addEventListener('click', function() {
                // Get all checkboxes in the layer control, excluding the Heatmap
                var checkboxes = document.querySelectorAll('.leaflet-control-layers-overlays input[type="checkbox"]');
                checkboxes.forEach(function(checkbox) {
                    var label = checkbox.nextElementSibling;
                    // Skip the heatmap checkbox
                    if (label && !label.textContent.toLowerCase().includes('heatmap')) {
                        checkbox.checked = true;
                        // Trigger the change event to update the map
                        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            });

            document.getElementById('uncheck_all_btn').addEventListener('click', function() {
                // Get all checkboxes in the layer control, excluding the Heatmap
                var checkboxes = document.querySelectorAll('.leaflet-control-layers-overlays input[type="checkbox"]');
                checkboxes.forEach(function(checkbox) {
                    var label = checkbox.nextElementSibling;
                    // Skip the heatmap checkbox
                    if (label && !label.textContent.toLowerCase().includes('heatmap')) {
                        checkbox.checked = false;
                        // Trigger the change event to update the map
                        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            });
        }, 500);  // Small delay to ensure layer control is rendered
    </script>
{% endmacro %}
"""


class LayerControlButtons(MacroElement):
    """
    A Folium MacroElement that adds 'Check All' and 'Uncheck All' buttons
    to quickly toggle all overlay layers on the map.
    """

    def __init__(self) -> None:
        super().__init__()
        self._template = Template(layer_control_template)
