# Changelog - PlanX CartoLab

## [1.4.2] - 2026-07-10

- Fix responsive 2.5D and Layout UI; rename System Health to Readiness

## [1.4.1] - 2026-07-10

- Fix helpUrl inheritance and commit e2e regression guard

## [1.4.0] - 2026-07-10

- release.ps1 added; helpUrl() for all 12 algorithms; 4 deprecated setMode() calls fixed (QgsClassificationCustom); e2e algorithm-count regression guard added (==12); dead-import and lint cleanup (flake8 128->109, bandit 10->7 Low); COMMAND_GUIDE.html added

## [1.3.1] - 2026-06-18

- docs: add CITATION.cff for Zenodo DOI integration

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-06-17

### Added
- **Dot-Density Map** — seeded, hole-aware dots scattered inside polygons (one dot per N units of a count field); dots inherit source attributes for multi-group dot maps.
- **Proportional Symbols** — Flannery-compensated (or true-area) graduated point symbols with data-defined size and suggested nested-legend values.
- **Hexbin Aggregation** — bin a point layer into a pointy-top hexagonal grid (count / sum / mean), emitting only occupied cells, graduated on the chosen statistic.
- **Visual-Center Label Points** — pole of inaccessibility (polylabel) per polygon, so label anchors always sit inside the shape; largest part used for multipart features.
- **Graticule / Reference Grid** — meridians and parallels on nice round intervals, each carrying its orientation, coordinate and a formatted label.
- **Choropleth Normalization & Rates** — rate (numerator/denominator × scale), z-score, robust MAD z-score, min-max, percentile rank and log, written to a `norm_value` field and graduated.

### Fixed
- **Ridge Map** — replaced an invalid `QgsRasterBlock.isNoData()` call (crashed on current QGIS) with a validity/empty check, and fixed the optional-extent path that produced a NaN when no extent was supplied.

### Notes
- Pure-Python cores for all six new tools (no new dependencies); headless unit tests grew to 192 checks and a real-QGIS end-to-end harness validates all 12 algorithms on QGIS 3.44 LTR and QGIS 4.

## [1.2.6] - 2026-06-05

- Make 2.5D floor bands legend-friendly

## [1.2.5] - 2026-06-04

- Add automatic floor-band detection for 2.5D styling

## [1.2.4] - 2026-06-04

- Fix QGIS Hub metadata homepage URL

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
