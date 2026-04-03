# Migration Flow Visualization (Sankey Diagrams)

Generate interactive Sankey diagrams showing how families migrated between geographic locations over time.

## Overview

The migration flow visualization reveals population movement patterns without requiring individual person-by-person tracking. Instead, it aggregates flows: "How many people moved FROM location A TO location B in the 1850s?"

### Key Features

- **Interactive Sankey Diagrams**: Visualize migration flows as proportional streams
- **Time Period Grouping**: Analyze migrations by decade, generation, century, or custom periods
- **Multiple Event Types**: Track births, deaths, residences, and burials
- **Statistical Analysis**: Diaspora index, top destinations, most common routes
- **Dark Mode Support**: Automatic light/dark theme detection
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Usage

### Basic Export

```python
from render.migration.sankey_exporter import MigrationFlowExporter
from services.config_service import GVConfig
from services.state_service import GVState
from services.progress_service import GVProgress

# Initialize services
config = GVConfig()
state = GVState()
progress = GVProgress()

# Create exporter
exporter = MigrationFlowExporter(config, state, progress)

# Generate visualization
output_file = exporter.export(
    geolocated_gedcom,
    output_file="family_migrations.html"
)
print(f"Visualization saved to {output_file}")