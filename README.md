# PlanX CartoLab — Advanced Disruptive Cartography Suite

**Next-generation thematic mapping engine for QGIS.**

CartoLab goes beyond simple choropleth rendering. It brings together adaptive
statistical classification, continuous-area cartogram distortion, Value-by-Alpha
uncertainty visualisation, ridge-line (Joy Division style) vector meshes,
isometric layout stacking, and floating HTML/Canvas annotations — all inside
QGIS as a single integrated plugin.

## Features

| Module | Description |
|--------|-------------|
| **Adaptive GIC** | Geometric Interval Classifier that optimises the ratio to minimise class-frequency variance |
| **Head/Tail Breaks** | For heavy-tailed, power-law distributions (fractal urban growth, OSM road networks) |
| **Fisher-Jenks** | Natural breaks via dynamic programming — within-class variance minimisation |
| **Bivariate Choropleth** | N×N colour matrix (bilinear interpolation) — dual-variable thematic mapping |
| **Diffusion Cartogram** | Continuous-area polygon distortion (Gastner & Newman method, ground-up reimplementation) |
| **Ridge Maps** | Joy Division style raster-to-vector scanline deformation |
| **Value-by-Alpha** | Map opacity to a reliability/uncertainty variable |
| **Isometric Stacker** | Stacked 2.5D axonometric layout explosion |
| **HTML Annotations** | Floating radar-chart cards rendered via Canvas/JS |

## Installation

1. Download the latest `.zip` from [Releases](https://github.com/YusufEminoglu/planx_cartolab/releases).
2. In QGIS: **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Activate **PlanX CartoLab** from the plugin list.

## Quick Start

All tools are available in two ways:

1. **Processing Toolbox** → `PlanX CartoLab` → double-click any algorithm
2. **PlanX → CartoLab → CartoLab Panel** → tabbed dock with one-click launchers

## Compatibility

| Requirement | Value |
|-------------|-------|
| QGIS minimum | 3.28 |
| QGIS maximum | 4.99 |
| Python | 3.9+ |
| License | GPL-3.0 |

## Architecture

```
planx_cartolab/
  core/           # Mathematical & symbology engines
  processing/     # QgsProcessingAlgorithm implementations
  layout/         # Print Layout automation (grid, legend, isometric, typography)
  ui/             # Dock panel and HTML/CSS templates
```

## Author

**Yusuf Eminoglu** — [GitHub](https://github.com/YusufEminoglu) | yusuf.eminoglu@deu.edu.tr

[Changelog](CHANGELOG.md) · [PlanX monorepo](https://github.com/YusufEminoglu)
