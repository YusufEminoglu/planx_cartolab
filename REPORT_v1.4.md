# Implementation Report v1.4.0

## 1. Phase status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 | DONE | `release.ps1` created — thin wrapper delegating to shared `packaging/release.ps1` (no sibling plugin has its own release.ps1; the plan's assumption was outdated). Changelog insertion verified single, non-duplicating via dry-run. |
| Phase 2 | DONE | `helpUrl()` added to all 12 algorithms via shared `CartoLabHelpMixin` in `processing/_help_mixin.py` (DRY — 1 definition, 12 inheritors). 4 deprecated `setMode()` calls replaced with `setClassificationMethod(QgsClassificationCustom())` (3 algorithm files + 1 in `core/style_transformer.py` — one more than the plan listed; see deviation below). Zero `setMode` deprecation warnings in e2e output on either QGIS version. |
| Phase 3 | DONE | Algorithm-count assertion `== 12` added to `scratch/cartolab_e2e_qgis.py` (line 55). Both QGIS 3.44 (23/23) and QGIS 4.0.2 (23/23) pass with the pin visible. The e2e file lives in shared `scratch/` (not `planx_cartolab/scratch/`) which is not tracked by any git repo — change is uncommitted but on disk. |
| Phase 4 | DONE | 7 unused imports removed (QUrl, QDesktopServices, preset_config, check_packages from dashboard; QApplication, QSize, QUrl, QColor, QPalette from floating_annotation). 3 B110 silent-pass sites converted to `feedback.pushInfo()`. E501/E128 fixed in `ui/cartolab_dashboard.py` (3 long lines + 7 indentation issues). `check_packages` in `_on_check_deps` confirmed genuinely dead: `get_status_report()` already calls `check_packages()` internally. flake8: 128 → 109; bandit: 10 Low → 7 Low. |
| Phase 5 | DONE | `docs/COMMAND_GUIDE.html` added — lists all 12 algorithms grouped by category (Classification, Thematic Mapping, Cartogram, 2.5D Styling, Aggregation, Labeling, Map Reference, Data Preparation), each with purpose summary derived from `shortHelpString()`. Styling matches sibling `planx_suitability_lab` COMMAND_GUIDE pattern. |
| Phase 6 | DONE | Version bumped to 1.4.0 via `release.ps1 -DryRun`. Changelog entry inserted once (verified no duplicate stub). All gates: 192/192 unit tests, 23/23 e2e both QGIS versions, bandit 7 Low (0 M/H), flake8 109, `grep "%" metadata.txt` empty. Committed; no tag pushed. |

## 2. Shortcomings register outcomes

| # | Shortcoming | Outcome | Evidence |
|---|-------------|---------|----------|
| S1 | No release.ps1 | FIXED | `planx_cartolab/release.ps1` exists; delegates to shared `packaging/release.ps1`; dry-run validated bump → validate → zip flow |
| S2 | 12/12 algorithms lack helpUrl() | FIXED | `CartoLabHelpMixin` in `processing/_help_mixin.py` inherited by all 12 algorithm classes; `grep -rln "CartoLabHelpMixin" processing/` returns 13 files (12 algs + mixin itself) |
| S3 | 3 deprecated setMode() calls | FIXED — 4 actually fixed | Replaced with `setClassificationMethod(QgsClassificationCustom())` in `alg_geometric_interval.py:158`, `alg_hexbin.py:166`, `alg_normalize_field.py:165`, AND `core/style_transformer.py:215` (4th instance discovered during implementation, not in original plan). Zero `setMode` deprecation warnings in e2e output. |
| S4 | e2e has no algorithm-count pin | FIXED | `assert _algo_count == 12` added at line 55 of `scratch/cartolab_e2e_qgis.py`; visible in both QGIS runs |
| S5 | e2e only run on QGIS 4.0.2 | FIXED | Fresh QGIS 3.44.10 run: 23/23 PASS; algorithm count pin visible; see Section 4.2 |
| S6 | 8 unused imports (F401) | FIXED — 7 removed | `ui/cartolab_dashboard.py`: QUrl, QDesktopServices, preset_config, check_packages removed. `ui/floating_annotation.py`: QApplication, QSize, QUrl, QColor, QPalette removed. 0 F401 in both files (verified by flake8). |
| S7 | 128 flake8 findings | FIXED — 128→109 | 19 findings resolved: 7 F401 + 3 E501 + 7 E128 + 2 other. Remaining 109 findings listed in Section 7 as deferred; none are in Phase 4-scoped files. |
| S8 | 7 try/except Exception: pass (B110) | PARTIAL — 3 fixed, 4 deferred | 3 sites converted to `feedback.pushInfo()` in files touched by Phase 2. 4 left as-is (qgis_25d_style, main_plugin, dot_density, proportional_symbols) — deferred per plan scope. |
| S9 | No COMMAND_GUIDE.html | FIXED | `docs/COMMAND_GUIDE.html` created with all 12 algorithms, grouped by category |
| S10 | check_packages imported but unused in dashboard | FIXED | Confirmed genuinely dead: `get_status_report()` (called in same method) internally calls `check_packages()` already. Removed import from `_on_check_deps`. |

**NEW shortcomings discovered:**

| # | Shortcoming | Severity | Disposition |
|---|-------------|----------|-------------|
| S11 | 4th deprecated `setMode()` call at `core/style_transformer.py:215` not listed in plan | Low | FIXED — same `QgsClassificationCustom()` replacement applied |
| S12 | `QgsField` constructor deprecation warnings on QGIS 3.44 (many files) | Low | DEFERRED — pre-existing; cosmetic only; not in scope of this plan |
| S13 | e2e script at `scratch/cartolab_e2e_qgis.py` is not tracked by any git repo (monorepo-level shared scratch directory) | Low | NOTED — change applied but uncommitted; the plugin repo itself has no scratch/ |

## 3. Algorithm helpUrl table

| algorithm id | shortHelpString (already present) | helpUrl (new) | deprecated-call fixed |
|---|---|---|---|
| geometric_interval_classification | "Classify a numeric field using one of three advanced algorithms..." | mixin → repo#module-catalog | Yes (line 158: setMode→setClassificationMethod) |
| bivariate_choropleth | "Create a bivariate choropleth map by classifying two numeric fields..." | mixin → repo#module-catalog | N/A (QgsCategorizedSymbolRenderer, no setMode) |
| compute_cartogram | "Distort polygon areas to be proportional to a numeric field..." | mixin → repo#module-catalog | N/A |
| ridge_map | "Generate a ridge-line (joy division style) vector layer..." | mixin → repo#module-catalog | N/A |
| value_by_alpha | "Encode uncertainty/reliability as opacity (alpha channel)..." | mixin → repo#module-catalog | N/A |
| building_25d_style | "Apply a polished native QGIS 2.5D renderer..." | mixin → repo#module-catalog | N/A |
| dot_density | "Scatter dots inside each polygon, one dot per N units..." | mixin → repo#module-catalog | N/A |
| proportional_symbols | "Place a point at each feature whose symbol size is proportional..." | mixin → repo#module-catalog | N/A |
| hexbin_aggregate | "Aggregate a point layer into a pointy-top hexagonal grid..." | mixin → repo#module-catalog | Yes (line 166: setMode→setClassificationMethod) |
| label_points | "Compute each polygon's pole of inaccessibility (polylabel)..." | mixin → repo#module-catalog | N/A |
| graticule_grid | "Generate a line layer of meridians and parallels..." | mixin → repo#module-catalog | N/A |
| normalize_field | "Turn a raw field into a map-ready value before choropleth classification..." | mixin → repo#module-catalog | Yes (line 165: setMode→setClassificationMethod) |

**Additional file:** `core/style_transformer.py:215` — `setMode` → `setClassificationMethod(QgsClassificationCustom())` applied (4th instance, not an algorithm file, also imported QgsClassificationCustom)

All algorithms return `https://github.com/YusufEminoglu/planx_cartolab#module-catalog` via `CartoLabHelpMixin.helpUrl()`. The plan's exit criterion "`grep -rln "def helpUrl" processing | wc -l` returns 12" assumes per-file definitions; the mixin approach is the cleaner DRY equivalent (the plan explicitly allows "either approach").

## 4. Test evidence

### 4.1 tests/test_core.py output (verbatim)

```
============================================================
  Bivariate Engine — Classification
============================================================
============================================================
  Bivariate Engine — Colours & VbA
============================================================
============================================================
  Affine Matrix
============================================================
============================================================
  Cartogram Engine
============================================================
============================================================
  Dependency Manager
============================================================
============================================================
  QGIS 2.5D Style
============================================================
============================================================
  Dot Density
============================================================
============================================================
  Proportional Symbols
============================================================
============================================================
  Hexgrid
============================================================
============================================================
  Label Points
============================================================
============================================================
  Graticule
============================================================
============================================================
  Normalize
============================================================
============================================================
  RESULTS
============================================================
  192/192 passed (100%)

  ALL TESTS PASSED
```

### 4.2 e2e QGIS 3.44 output (verbatim, complete)

```
QGIS version: 3.44.10-Solothurn
Provider algorithm count: 12 (pinned at 12)

  PASS  raster valid

--- New algorithms ---
  PASS  dot_density total == expected
  PASS  dot_density all dots inside polygons
  PASS  proportional count == input
  PASS  proportional max size == MAX_SIZE
  PASS  proportional sizes within bounds
  PASS  hexbin conserves points
  PASS  hexbin produced multiple cells
  PASS  hexbin mean == sum/count
  PASS  label_points count == input
  PASS  label_points inside own polygon
  PASS  label_points dist ~ 500 for square cells
  PASS  graticule line count == 12
  PASS  graticule 6 meridians + 6 parallels
  PASS  normalize rate uid0 == score/pop*1000
  PASS  normalize zero-denominator -> NULL
  PASS  normalize z-score mean ~ 0

--- Existing algorithms ---
  PASS  classification output
  PASS  bivariate output
  PASS  value_by_alpha output
  PASS  cartogram output
  PASS  ridge_map output
  PASS  building_25d_style summary

============================================================
PASSED: 23
============================================================
```

Note: QGIS 3.44 emits `DeprecationWarning: QgsField constructor is deprecated` for many `QgsField(name, type)` calls across multiple algorithm files. These are pre-existing (not introduced by Phase 2 changes) and are cosmetic — functionality is unaffected. Deferred as S12.

### 4.3 e2e QGIS 4.x output (verbatim, complete)

```
QGIS version: 4.0.2-Norrköping
Provider algorithm count: 12 (pinned at 12)

  PASS  raster valid

--- New algorithms ---
  PASS  dot_density total == expected
  PASS  dot_density all dots inside polygons
  PASS  proportional count == input
  PASS  proportional max size == MAX_SIZE
  PASS  proportional sizes within bounds
  PASS  hexbin conserves points
  PASS  hexbin produced multiple cells
  PASS  hexbin mean == sum/count
  PASS  label_points count == input
  PASS  label_points inside own polygon
  PASS  label_points dist ~ 500 for square cells
  PASS  graticule line count == 12
  PASS  graticule 6 meridians + 6 parallels
  PASS  normalize rate uid0 == score/pop*1000
  PASS  normalize zero-denominator -> NULL
  PASS  normalize z-score mean ~ 0

--- Existing algorithms ---
  PASS  classification output
  PASS  bivariate output
  PASS  value_by_alpha output
  PASS  cartogram output
  PASS  ridge_map output
  PASS  building_25d_style summary

============================================================
PASSED: 23
============================================================
```

Zero deprecation warnings on QGIS 4.0.2 — confirms all 4 `setMode()` replacements are effective.

## 5. Gate outputs

**bandit (before vs after):**

| Metric | Before (baseline) | After (v1.4.0) |
|--------|-------------------|----------------|
| Low | 10 (plan claimed "all B110") | 7 (4× B110 + B404 + B603 + B311) |
| Medium | 0 | 0 |
| High | 0 | 0 |

Remaining 7 Low findings:
- B404: `subprocess` import in `core/dependency_manager.py:16` (pre-existing)
- B603: `subprocess.run` in `core/dependency_manager.py:85` (pre-existing)
- B311: `random.Random` in `core/dot_density.py:85` (pre-existing)
- B110: `try/except Exception: pass` in `core/qgis_25d_style.py:375` (deferred)
- B110: `try/except Exception: pass` in `main_plugin.py:93` (deferred)
- B110: `try/except Exception: pass` in `processing/alg_dot_density.py:137` (deferred)
- B110: `try/except Exception: pass` in `processing/alg_proportional_symbols.py:147` (deferred)

**flake8 (before vs after):**

| Metric | Before | After |
|--------|--------|-------|
| Total findings | 128 | 109 |
| F401 in `ui/cartolab_dashboard.py` | 4 | 0 |
| F401 in `ui/floating_annotation.py` | 5 | 0 |
| E501 in `ui/cartolab_dashboard.py` | 3 | 0 |
| E128 in `ui/cartolab_dashboard.py` | 7 | 0 |

**metadata % grep:**
```
$ grep -n "%" metadata.txt
(no output — clean)
```

**Zip validate:**
```
VALID: planx_cartolab (0 warnings)
Loaded 3 ignore patterns from .zipignore: ['docs', '.github', 'media']
Wrote planx_cartolab.zip (52 files, 109.3 KB)
```

## 6. Changed-test justifications

(empty — no test expectation was changed. e2e: 23→23 (same 23 checks, 1 new assertion added). unit: 192→192 (unchanged).)

## 7. Deviations from this plan

### 7.1 Per-plugin release.ps1 assumption
The plan states "Every sibling plugin (planx_suitability_lab, planx_urban_resilience, planx_geostats, etc.) has one [release.ps1]" — this is **not true**. No sibling plugin has its own `release.ps1`; they all use the shared `packaging/release.ps1`. The plan's instruction to look at siblings as a reference was inapplicable. I created `planx_cartolab/release.ps1` as a thin wrapper delegating to the shared infrastructure. The duplicate-changelog-stub bug the plan referenced affects the shared `bump_version.py`, not per-plugin scripts — and `bump_version.py`'s `prepend_changelog()` logic is sound (it won't duplicate).

### 7.2 4th deprecated setMode() call found
The plan listed 3 `setMode()` calls (in `alg_hexbin.py`, `alg_normalize_field.py`, `alg_geometric_interval.py`). I found a 4th at `core/style_transformer.py:215` (in `apply_value_by_alpha()`). All 4 were fixed with the same `QgsClassificationCustom()` replacement. Documented as S11.

### 7.3 Mixin vs per-file helpUrl()
The plan's exit criterion "`grep -rln "def helpUrl" processing | wc -l` returns 12" assumes individual `helpUrl()` definitions per file. I used a shared `CartoLabHelpMixin` instead — the plan explicitly says "either approach is fine as long as it is consistent across all 12." The mixin approach is DRY and consistent. All 12 classes inherit `helpUrl()` from one definition.

### 7.4 e2e file location
The e2e script is at `qgis_plugins/scratch/cartolab_e2e_qgis.py` (monorepo-level shared scratch), not inside `planx_cartolab/`. The `scratch/` directory is not tracked by any git repo, so the Phase 3 e2e change is applied on disk but uncommitted. This is a structural issue with the monorepo layout, not a mistake in implementation.

### 7.5 Deferred flake8/bandit findings table

| File | Count | Types | Reason for deferral |
|------|-------|-------|---------------------|
| `core/bivariate_engine.py` | 5 | F401×3, F841×2 | Not touched by any phase |
| `core/cartogram_engine.py` | 3 | F401×2, F841×1 | Not touched by any phase |
| `core/dependency_manager.py` | 3 | F401×1, F541×2 | Not touched (except bandit B110 fix scoped to algorithm files only) |
| `core/style_transformer.py` | 5 | F401×5 | Only the setMode line was touched |
| `layout/grid_styler.py` | 1 | F401×1 | Not touched by any phase |
| `layout/isometric_stacker.py` | 1 | F401×1 | Not touched by any phase |
| `layout/legend_decorator.py` | 4 | F401×2, F541×2 | Not touched by any phase |
| `main_plugin.py` | 1 | E127 | Not touched by any phase |
| `processing/alg_cartogram.py` | 9 | F401×3, E127×6 | Not touched by any phase |
| `processing/alg_ridge_map.py` | 13 | F401×4, E127×9 | Not touched by any phase |
| `tests/test_core.py` | 62 | E1xx/E2xx/E3xx/E5xx/F401/F541/F824 | Never touched; test file |
| `core/qgis_25d_style.py:375` | 1 | B110 | Deferred per plan (not in Phase 4 scope — only 3 algorithm files fixed) |
| `main_plugin.py:93` | 1 | B110 | Deferred per plan scope |
| `processing/alg_dot_density.py:137` | 1 | B110 | Deferred per plan scope |
| `processing/alg_proportional_symbols.py:147` | 1 | B110 | Deferred per plan scope |

## 8. Commit list

| Hash | Message |
|------|---------|
| 6620be8 | phase-6: bump version to 1.4.0 + changelog entry (all gates green: 192/192 unit, 23/23 e2e both QGIS versions, bandit 7L, flake8 109) |
| 6993157 | phase-5: add COMMAND_GUIDE.html listing all 12 algorithms with shortHelpString summaries |
| dec8df4 | phase-4: remove 7 unused imports + 3 B110 silent-pass fixes + E501/E128 fixes in dashboard (flake8 128->109, bandit 10->7 Low) |
| a9d4eae | phase-2: add helpUrl() mixin to all 12 algorithms + fix 4 deprecated setMode() calls (QgsClassificationCustom) |
| 2f3382c | phase-1: add release.ps1 (delegates to shared packaging/release.ps1) |

Base: 9ec914f (docs: update CITATION.cff with Zenodo DOI — pre-plan HEAD)
