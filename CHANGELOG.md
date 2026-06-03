# Changelog - PlanX CartoLab

## [1.2.3] - 2026-06-03

- Add per-floor colour band renderer for 2.5D styling

## [1.2.3] - 2026-06-03

- Add sample-QML-style per-floor colour band rendering for floor-count 2.5D building styling

## [1.2.2] - 2026-06-03

- Add explicit floor-count mode for 2.5D building styling

## [1.2.1] - 2026-06-03

- Fix QGIS 2.5D height expression parser compatibility

## [1.2.0] - 2026-06-03

### Added
- Native QGIS 2.5D building styling engine with height-field extrusion, material presets, soft shadows, wall shading, optional stepped floors, and QML export.
- Dashboard 2.5D Styling tab plus a direct PlanX CartoLab menu action.
- Processing Toolbox algorithm: Apply 2.5D Building Style.
- GitHub Pages showcase, documentation set, and issue/PR templates for a more polished repository presentation.

### Changed
- Main dashboard copy and project diagnostics now use English-only visible text for the newly touched surfaces.
- GitHub showcase and repository support files are excluded from the QGIS Plugin Hub ZIP through `.zipignore`.

## [1.1.0] - 2026-05-29

- Official 1.1.0 release: full print layout support with rotated diamond and square legends, and Forecasting Studio export controls

## [1.1.0-beta.1] - 2026-05-29

- Beta-1 release with dynamic bivariate palettes, custom corner colors, and polished radar charts

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-26

### Added
- Professional PlanX ecosystem icon for QGIS Plugin Manager, toolbar, and Processing provider surfaces.
- QGIS 3.44/QGIS 4 runtime smoke coverage for CartoLab dashboard and Processing provider lifecycle.

### Fixed
- Qt6-compatible enum usage in the dashboard, floating annotation dialog, layout grid styler, and typography engine.

## [0.2.0] - 2026-05-26

### Added
- Production dashboard with module cards, dependency health, quick actions, and layout automation launchers.
- Floating annotation map tool, isometric/typography/grid/legend layout utilities, improved cartogram kernel, graduated symbology, and dependency manager with pip installer.
- 71 unit tests for core cartography engines.

## [0.1.0] - 2026-05-26

### Added
- Adaptive Geometric Interval Classifier (GIC) with automatic ratio optimisation
- Head/Tail Breaks algorithm for heavy-tailed (power-law) data
- Fisher-Jenks natural breaks (dynamic programming with DP matrix backtracking)
- Bivariate choropleth engine: NxN colour matrix via bilinear interpolation
- Continuous-area diffusion cartogram (Gastner & Newman method, ground-up reimplementation)
- Ridge-line (Joy Division style) vector mesh generator from raster data
- Value-by-Alpha (VbA) opacity mapper for uncertainty visualisation
- Isometric layout stacker: axonometric explosion of map layers in Print Layout
- HTML/Canvas floating annotation cards with embedded radar (spider) charts
- Swiss-style typography engine (Inter / IBM Plex Mono hierarchy)
- Minimalist coordinate-grid styler for publication-ready layouts
- Bivariate SVG legend embedder for Print Layout
- Full Processing Toolbox provider with 5 algorithms
- Dockable multi-tab panel (Bivariate, Cartogram, Ridge Map, VbA, Isometric)
