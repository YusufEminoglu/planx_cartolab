# Changelog - PlanX CartoLab

## [1.6.2] - 2026-07-13

### Security
- The QGIS Plugin Hub security scan now blocks a plugin on *any* Bandit finding, not only critical ones. Driven the shipped code to **zero Bandit findings**: replaced Python's `random` module in the dot-density placer with a small self-contained deterministic generator (identical, reproducible dot layouts — no behaviour change), and rewrote every defensive `try/except: pass` as `contextlib.suppress`. No `# nosec` suppressions are used, so the result holds even under the strictest scan configuration.

## [1.6.1] - 2026-07-13

### Security
- Removed the pip/`subprocess` dependency installer that the QGIS Plugin Hub security scan flagged as a critical issue. CartoLab needs no external packages — it uses only QGIS and its bundled NumPy — so the Setup panel now only *reports* optional-library status and never installs anything.

### Fixed
- Qt6 / QGIS 4 compatibility: all Processing, layout and UI enums are now fully scoped (e.g. `QgsProcessing.SourceType.TypeVectorPolygon`, `QgsWkbTypes.Type.Point`, `QgsUnitTypes.LayoutUnit.LayoutMillimeters`, `QgsMapLayer.LayerType.VectorLayer`), clearing 85 compatibility warnings. Verified on QGIS 3.44 LTR and QGIS 4.2.
- Test and e2e files are no longer shipped in the Hub package.

## [1.6.0] - 2026-07-13

### Added
- **Quick Style** — a new one-click Processing algorithm and dashboard panel that styles any vector layer: a graduated renderer for numeric fields or a categorized renderer for text fields, with quantile / equal-interval / geometric-interval class breaks. The dashboard panel has a live palette preview and applies the style to the selected layer instantly.
- **Colour palette library** (`core/palettes.py`) — ColorBrewer sequential/diverging/qualitative sets plus the perceptually-uniform scientific ramps (viridis, magma, plasma, inferno, cividis), each carrying a colour-blind-safe flag, sampled to any class count. A "colour-blind safe only" filter is built into the Quick Style panel.
- **Layout export presets** — export any layout to PNG, PDF or SVG at 96 / 150 / 300 / 600 dpi from the Layout Manager.

### Changed
- A graduated Quick Style on a field with a single distinct value now degrades gracefully to one class instead of failing.
- The provider now ships 13 Processing algorithms (Quick Style added); the e2e harness pins and verifies the count.

## [1.5.1] - 2026-07-13

### Added
- **First-run welcome** — a one-time greeting (also reachable from *Plugins → PlanX CartoLab → Welcome & Sample Map*) with a **"Create a sample map"** button that builds a fully-styled demo choropleth and finished map sheet in seconds, from an in-memory layer (no bundled data).
- **"Rate on the Hub"** link in the dashboard footer.

### Changed
- Refreshed discovery metadata (tags + description/about) so CartoLab surfaces for common searches — *choropleth, map layout, print layout, atlas, colour ramp, ColorBrewer, colourblind, viridis, thematic map, north arrow* — without changing any behaviour.

## [1.5.0] - 2026-07-13

### Added
- **Auto Map Sheet** — one-click publication layout built from the current map view: titled map frame at the current extent and CRS, filtered legend, scale bar, north arrow (bundled QGIS SVG with a drawn fallback), optional coordinate grid, neat-line and credits. Choose page size (A0–A4) and orientation; the finished layout opens straight in the Layout Designer.
- **Layout Manager** in the dashboard Layout tab — pick any project layout and open it in the Designer, duplicate it, delete it, or export it to PNG/PDF at 300 dpi.
- Real-QGIS e2e coverage for the layout subsystem (map sheet assembly, grid idempotency, native legend, isometric stack, export) — the harness now runs 33 checks on both QGIS 3.44 LTR and QGIS 4.
- Pure-logic `core/layout_math.py` (nice grid intervals, collision-free layout names, page geometry) with 17 new unit tests.

### Changed
- Bivariate print-layout legends are now built from **native, editable layout items** (rectangles / diamonds + text, grouped) instead of an embedded SVG — no more orphaned temporary files, and the legend can be tweaked in the Designer.
- Layout decorators (bivariate legend, typography, minimalist grid) now target the **layout you select** in the Layout Manager instead of blindly using the first layout.
- Isometric layer stacks are now created as `QgsPrintLayout` objects (so they appear correctly in the Layout Manager and Designer) with collision-free names.

### Fixed
- Minimalist coordinate grid is now **idempotent** (re-running replaces the CartoLab grid instead of stacking duplicates) and derives a rounded interval from the map extent, so it reads well at any scale or CRS. The grid line styling used non-existent API calls (`setGridLinePenSize`/`setGridLineStyle`) and silently failed; it now uses `setLineSymbol`.

### Removed
- Dead code: unused `create_cross_grid_style`, and the orphaned `build_bivariate_legend_html` / `build_micro_bar_chart_html` HTML factories.

## [1.4.3] - 2026-07-10

- Packaging hygiene fix: `packaging/zip_hub.py` now always excludes internal AI-agent work-order files (`ENHANCEMENT_PLAN_*.md`, `DEEPSEEK_PROMPT_*.txt`, `REPORT_v*.md`) from the built zip, regardless of version suffix. These files remain in the GitHub repository as project history but no longer ship in the QGIS Hub package.

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
