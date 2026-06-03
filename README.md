# PlanX CartoLab

> Publication-grade cartography for QGIS: native 2.5D building styling, bivariate maps, cartograms, ridge maps, Value-by-Alpha uncertainty, and layout automation.

[![QGIS](https://img.shields.io/badge/QGIS-3.28%20to%204.99-589632?style=for-the-badge&logo=qgis&logoColor=white)](https://qgis.org)
[![Version](https://img.shields.io/badge/version-1.2.3-1f6f8b?style=for-the-badge)](metadata.txt)
[![License](https://img.shields.io/badge/license-GPL--3.0-111827?style=for-the-badge)](LICENSE)
[![PlanX](https://img.shields.io/badge/PlanX-CartoLab-c47a3b?style=for-the-badge)](docs/index.html)

PlanX CartoLab turns ordinary GIS layers into polished analytical maps. It is built for planners, urban researchers, studios, and academic cartography workflows that need strong visual output without leaving QGIS.

## Showcase

Open the GitHub Pages-ready showcase from [docs/index.html](docs/index.html). It includes an interactive 2.5D canvas scene, feature map, workflow narrative, and publication-oriented positioning for the plugin.

Recommended GitHub Pages source:

```text
Branch: master
Folder: /docs
```

## What It Does

| Area | Capability |
|------|------------|
| 2.5D styling | Native QGIS `25dRenderer`, sample-QML-style per-floor colour bands, height-field extrusion, material presets, shadows, wall shading, optional stepped floors, QML export. |
| Classification | Adaptive Geometric Interval Classification, Fisher-Jenks, and Head/Tail Breaks for skewed urban indicators. |
| Thematic mapping | Bivariate choropleths and Value-by-Alpha maps for dual variables and reliability-aware visualisation. |
| Distortion | Continuous-area cartograms for value-proportional polygon geometry. |
| Raster expression | Ridge-line maps from raster surfaces such as DEM, heat, density, or accessibility grids. |
| Layout polish | Isometric layer stacks, minimalist grids, typography hierarchy, and bivariate legends. |
| Inspection | Floating HTML feature cards with radar-style attribute charts. |

## Fast Start

1. Install `QGIS_Plugin_Releases/planx_cartolab.zip` from **Plugins > Manage and Install Plugins > Install from ZIP**.
2. Open **Plugins > PlanX CartoLab > CartoLab Dashboard**.
3. For buildings, open **2.5D Styling**, choose a polygon layer and a height field such as `Hmax`, then apply a preset.
4. For thematic maps, run tools from **Processing Toolbox > PlanX CartoLab** or the dashboard module cards.

## 2.5D Building Styling

The 2.5D panel is designed as a better, reusable version of ad hoc QML extrusion styles:

- Native QGIS renderer rather than a fragile pasted QML block.
- Clean English labels and stable presets.
- Height expression generated from the selected height or floor-count field.
- Floor-count mode for fields such as `Kat_Sayisi`: rendered height = floor count x floor height.
- Per-floor colour bands for `Kat_Sayisi`-style layers, with selectable palettes and maximum floor-band control.
- Optional floor-step snapping for planning-height layers.
- Soft shadow and directional wall shading controls.
- One-click QML export for reuse across projects.

For floor-count data, select `Kat_Sayisi` as the height field, set **Height source** to **Floor count field**, and keep **Floor height** at `3.5` map units unless your project uses another floor height. Enable **Colour each floor separately** to generate the rule-based geometry-generator renderer where every floor band receives its own colour.

## Repository Structure

```text
planx_cartolab/
  core/        # Symbology engines, 2.5D renderer helpers, math logic
  processing/  # QGIS Processing algorithms
  layout/      # Print Layout automation
  ui/          # Dashboard, 2.5D panel, feature inspector
  docs/        # GitHub Pages showcase and technical docs
```

## Documentation

- [Showcase](docs/index.html)
- [Documentation index](docs/README.md)
- [Feature showcase](docs/SHOWCASE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Publishing notes](docs/PUBLISHING.md)
- [Changelog](CHANGELOG.md)

## Compatibility

| Requirement | Value |
|-------------|-------|
| QGIS minimum | 3.28 |
| QGIS maximum | 4.99 |
| Python | 3.9+ |
| External pip dependencies | None required for core plugin operation |
| License | GPL-3.0 |

## Author

**Yusuf Eminoglu**

Department of City and Regional Planning

GitHub: [YusufEminoglu](https://github.com/YusufEminoglu)

Email: yusuf.eminoglu@deu.edu.tr
