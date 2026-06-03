# -*- coding: utf-8 -*-
"""Comprehensive unit tests for planx_cartolab core modules.

Tests every algorithm with normal, edge-case, and adversarial data.
Runs without QGIS — mocks qgis.* imports for pure-logic verification.
"""
from __future__ import annotations

import math
import os
import sys
import types
import traceback

# ---------------------------------------------------------------------------
# Mock qgis.* so we can import core modules outside QGIS
# ---------------------------------------------------------------------------

class FakeQColor:
    def __init__(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], str):
            h = args[0].lstrip("#")
            self._r = int(h[0:2], 16) if len(h) >= 2 else 0
            self._g = int(h[2:4], 16) if len(h) >= 4 else 0
            self._b = int(h[4:6], 16) if len(h) >= 6 else 0
        elif len(args) == 3:
            self._r, self._g, self._b = args
        else:
            self._r = self._g = self._b = 0
    def red(self):   return self._r
    def green(self): return self._g
    def blue(self):  return self._b
    def name(self):  return f"#{self._r:02x}{self._g:02x}{self._b:02x}"
    def __repr__(self): return f"QColor({self._r},{self._g},{self._b})"

def _make_mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m

qgis_core = _make_mod("qgis.core",
    QgsCoordinateReferenceSystem=_make_mod("CRS", fromProj=classmethod(lambda c, p: _make_mod("X", isGeographic=lambda s: False))),
    QgsCoordinateTransformContext=_make_mod("CTC"),
    QgsDistanceArea=_make_mod("DA",
        setSourceCrs=lambda s, *a: None,
        setEllipsoid=lambda s, *a: None,
        measureArea=lambda s, g: getattr(g, 'area', lambda: 100.0)() if callable(getattr(g, 'area', None)) else 100.0,
    ),
    QgsGeometry=_make_mod("Geom"),
    QgsVertexId=_make_mod("VID", IsValid=lambda s: True, VertexType=_make_mod("VT", SegmentVertex=0, CurveVertex=1)),
    QgsPoint=_make_mod("P"),
    QgsPointXY=_make_mod("PXY"),
    QgsFeature=_make_mod("F"),
    QgsField=_make_mod("Field"),
    QgsFields=_make_mod("Fields"),
    QgsVectorLayer=_make_mod("VL"),
    QgsWkbTypes=_make_mod("Wkb"),
    QgsFeatureSink=_make_mod("FS", Flag=_make_mod("Flag", FastInsert=1)),
    QgsProcessingFeedback=_make_mod("PF"),
    QgsProcessingException=Exception,
    QgsRasterLayer=_make_mod("RL"),
    QgsRectangle=_make_mod("Rect"),
    QgsProcessing=_make_mod("Proc", SourceType=_make_mod("ST", TypeVectorPolygon=0, TypeVectorAnyGeometry=1)),
)
qgis_qtgui = _make_mod("qgis.PyQt.QtGui", QColor=FakeQColor)
qgis_qtcore = _make_mod("qgis.PyQt.QtCore", QVariant=lambda v=None: v)

# Wire package hierarchy
qgis_mod = _make_mod("qgis", core=qgis_core)
qgis_pyqt = _make_mod("qgis.PyQt", QtGui=qgis_qtgui, QtCore=qgis_qtcore)

sys.modules["qgis"] = qgis_mod
sys.modules["qgis.core"] = qgis_core
sys.modules["qgis.PyQt"] = qgis_pyqt
sys.modules["qgis.PyQt.QtGui"] = qgis_qtgui
sys.modules["qgis.PyQt.QtCore"] = qgis_qtcore

# Patch qgis.core.QgsGeometry inline for cartogram_engine
class FakeCentroid:
    def asPoint(self):
        class P: x = lambda s: 0.0; y = lambda s: 0.0
        return P()

class FakeGeometry:
    def __init__(self, wkt_or_obj=None):
        self._wkt = wkt_or_obj if isinstance(wkt_or_obj, str) else "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"
    def asWkt(self): return self._wkt
    def fromWkt(self, wkt):
        self._wkt = wkt
        return self
    def area(self): return 100.0
    def centroid(self): return FakeCentroid()
    def isEmpty(self): return False
    def isNull(self): return False
    def constParts(self): return []
    def buffer(self, dist, segs): return FakeGeometry()

qgis_core.QgsGeometry = FakeGeometry

# ---------------------------------------------------------------------------
# Add project root to path
# ---------------------------------------------------------------------------
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(PROJ))

from planx_cartolab.core import bivariate_engine as be
from planx_cartolab.core import dependency_manager as dm
from planx_cartolab.core import affine_matrix as am
from planx_cartolab.core import cartogram_engine as ce
from planx_cartolab.core import qgis_25d_style as s25d

# ---------------------------------------------------------------------------
# Test framework
# ---------------------------------------------------------------------------
passed = 0
failed = 0
errors = []

def check(name, cond, detail=""):
    global passed, failed, errors
    if cond:
        passed += 1
    else:
        failed += 1
        msg = f"FAIL [{name}]: {detail}"
        errors.append(msg)
        print(f"  {msg}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ===================================================================
# 1. BIVARIATE ENGINE — Classification
# ===================================================================
section("Bivariate Engine — Classification")

# Test data
NORMAL   = [10, 15, 22, 25, 30, 35, 40, 55, 60, 70, 85, 100, 120, 150, 200]
SKEWED   = [1]*30 + [2]*15 + [5]*8 + [10]*4 + [50]*2 + [100, 200, 500]
NEGATIVE = [-50, -30, -10, 0, 10, 20, 30, 50, 80, 120]
UNIFORM  = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# -- Geometric Interval --
breaks = be.geometric_interval_breaks(NORMAL, 5)
check("GIC returns n_classes+1 breaks", len(breaks) == 6, str(breaks))
check("GIC first break is min", abs(breaks[0] - min(NORMAL)) < 1, f"{breaks[0]} vs {min(NORMAL)}")
check("GIC last break >= max", breaks[-1] >= max(NORMAL), f"{breaks[-1]} vs {max(NORMAL)}")
check("GIC monotonic increasing", all(breaks[i] < breaks[i+1] for i in range(len(breaks)-1)))

breaks_neg = be.geometric_interval_breaks(NEGATIVE, 4)
check("GIC handles negative values", len(breaks_neg) == 5 and abs(breaks_neg[0] - min(NEGATIVE)) < 1)

breaks_skew = be.geometric_interval_breaks(SKEWED, 5)
check("GIC handles skewed data", len(breaks_skew) == 6)

breaks_two = be.geometric_interval_breaks([1, 100], 3)
check("GIC handles 2 values", len(breaks_two) == 4 and breaks_two[0] <= 1 and breaks_two[-1] >= 100)

breaks_same = be.geometric_interval_breaks([5, 5, 5, 5, 5], 3)
check("GIC handles identical values", len(breaks_same) == 4)

breaks_many = be.geometric_interval_breaks([1, 2, 3], 10)
check("GIC more classes than values", len(breaks_many) == 11)

# -- Head/Tail Breaks --
ht = be.head_tail_breaks(NORMAL)
check("Head/Tail returns >= 2 breaks", len(ht) >= 2, str(ht))
check("Head/Tail monotonic", all(ht[i] < ht[i+1] for i in range(len(ht)-1)))

ht_power = be.head_tail_breaks(SKEWED)
check("Head/Tail skewed data", len(ht_power) >= 2)

ht_small = be.head_tail_breaks([1, 2, 3])
check("Head/Tail handles tiny data", len(ht_small) >= 2)

# -- Fisher-Jenks --
fj = be.fisher_jenks_breaks(NORMAL, 5)
check("Fisher-Jenks returns n+1 breaks", len(fj) == 6)
check("Fisher-Jenks monotonic", all(fj[i] < fj[i+1] for i in range(len(fj)-1)))
check("Fisher-Jenks covers data", fj[0] <= min(NORMAL) and fj[-1] >= max(NORMAL))

fj_skew = be.fisher_jenks_breaks(SKEWED, 4)
check("Fisher-Jenks skewed ok", len(fj_skew) == 5)

fj_many_classes = be.fisher_jenks_breaks(NORMAL, len(NORMAL) - 1)
check("Fisher-Jenks many classes ok", len(fj_many_classes) == len(NORMAL))

# -- _validate_values --
try:
    be._validate_values([])
    check("_validate_values raises ValueError on empty", False)
except ValueError:
    check("_validate_values raises ValueError on empty", True)

vals = be._validate_values([None, math.nan, 5, float('inf'), 10, -float('inf'), 15])
check("_validate_values filters garbage", vals == [5, 10, 15], str(vals))

# ===================================================================
# 2. BIVARIATE ENGINE — Colours & VbA
# ===================================================================
section("Bivariate Engine — Colours & VbA")

matrix = be.bivariate_colour_matrix(4)
check("Colour matrix 4 rows", len(matrix) == 4)
check("Colour matrix each 4 cols", all(len(r) == 4 for r in matrix))
for row in matrix:
    for c in row:
        check("Colour matrix valid RGB", 0 <= c.red() <= 255 and 0 <= c.green() <= 255 and 0 <= c.blue() <= 255)

m2 = be.bivariate_colour_matrix(7)
check("Colour matrix 7x7", len(m2) == 7 and len(m2[0]) == 7)

m1 = be.bivariate_colour_matrix(2)
check("Colour matrix 2x2", len(m1) == 2 and len(m1[0]) == 2)

# -- Value-by-Alpha --
p_vals = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
r_vals = [90, 80, 70, 60, 50, 40, 30, 20, 10, 5]
alphas = be.compute_alpha_values(p_vals, r_vals, 30, 255)
check("VbA len matches input", len(alphas) == 10)
check("VbA values in alpha range", all(30 <= a <= 255 for a in alphas))

alphas2 = be.compute_alpha_values(p_vals[:5], p_vals[:5], 10, 200)
check("VbA small set ok", len(alphas2) == 5)
check("VbA small set range ok", all(10 <= a <= 200 for a in alphas2))

# Identical reliability — all max alpha
alphas3 = be.compute_alpha_values([10, 20, 30], [50, 50, 50], 0, 255)
check("VbA identical reliability", len(set(alphas3)) == 1, str(alphas3))

# ===================================================================
# 3. AFFINE MATRIX
# ===================================================================
section("Affine Matrix")

ident = am.AffineMatrix.identity()
check("identity a,b,c,d,tx,ty", (ident.a, ident.b, ident.c, ident.d, ident.tx, ident.ty) == (1, 0, 0, 1, 0, 0))
check("identity transform preserves x", ident.transform_point(5, 10)[0] == 5)
check("identity transform preserves y", ident.transform_point(5, 10)[1] == 10)

iso = am.AffineMatrix.from_isometric_angles(30, 100, math.degrees(math.atan(1 / math.sqrt(2))))
check("isometric a nonzero", iso.a != 0 or iso.b != 0)

tx, ty = iso.transform_point(100, 200)
check("isometric transform returns 2-tuple", isinstance(tx, float) and isinstance(ty, float))

comp = ident.compose(iso)
check("compose with identity a", abs(comp.a - iso.a) < 1e-9)
check("compose with identity d", abs(comp.d - iso.d) < 1e-9)

tr = ident.translate(15, 25)
check("translate origin", tr.transform_point(0, 0) == (15, 25))

sc = ident.scale(2, 3)
check("scale apply", sc.transform_point(10, 10) == (20, 30))

offsets = am.compute_isometric_layer_offsets(5, 50, 30, 35.264)
check("iso offsets len", len(offsets) == 5)
check("iso offsets dy ascending", all(offsets[i][1] < offsets[i+1][1] for i in range(4)))
check("iso offsets dx zero", all(dx == 0.0 for dx, _ in offsets))

# ===================================================================
# 4. CARTOGRAM ENGINE
# ===================================================================
section("Cartogram Engine")

# Create mock geometry for CartogramFeature
mock_geom = FakeGeometry("POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))")
cf = ce.CartogramFeature(1, mock_geom, 25.0)
check("CartogramFeature created", cf.id == 1)
check("CartogramFeature value", cf.value == 25.0)
check("CartogramFeature has WKT", cf.wkt_str is not None and "POLYGON" in cf.wkt_str)

# Edge: zero value
cf_zero = ce.CartogramFeature(2, mock_geom, 0.0)
check("CartogramFeature zero value clamped", cf_zero.value == 1e-12)

# Edge: None value
cf_none = ce.CartogramFeature(3, mock_geom, None)
check("CartogramFeature None value clamped", cf_none.value == 1e-12)

# Edge: null geometry raises
try:
    ce.CartogramFeature(4, None, 10.0)
    check("CartogramFeature rejects null geometry", False)
except ValueError:
    check("CartogramFeature rejects null geometry", True)

# ===================================================================
# 5. DEPENDENCY MANAGER
# ===================================================================
section("Dependency Manager")

avail, miss_req, miss_opt = dm.check_packages(dm.CARTO_LAB_DEPS)
check("check_packages returns 3 lists", all(isinstance(x, list) for x in [avail, miss_req, miss_opt]))
check("numpy tracked", "numpy" in avail or "numpy" in miss_req)
check("matplotlib tracked", "matplotlib" in avail or "matplotlib" in miss_opt)

report = dm.get_status_report(dm.CARTO_LAB_DEPS, "TEST")
check("status report non-empty string", isinstance(report, str) and len(report) > 50)
check("status report title present", "TEST" in report)
check("status report has OK marker", "[OK]" in report or "[!!]" in report)

ok, msg = dm.install_packages([])
check("install_packages empty list succeeds", ok and "No packages" in msg)

result = dm.ensure_required(dm.CARTO_LAB_DEPS, auto_install=False)
check("ensure_required returns bool", isinstance(result, bool))

# ===================================================================
# 6. QGIS 2.5D STYLE
# ===================================================================
section("QGIS 2.5D Style")

cfg = s25d.Style25DConfig(
    height_field="Hmax",
    height_scale=1.5,
    max_height=60,
    stepped=True,
    step_height=3.5,
)
expr = s25d.build_height_expression(cfg)
check("25D expression quotes field", '"Hmax"' in expr, expr)
check("25D expression scales height", "* 1.5" in expr, expr)
check("25D expression steps height", "round(" in expr and "/ 3.5" in expr, expr)
check("25D expression clamps height", "least(60" in expr and "greatest(0" in expr, expr)

summary = s25d.build_style_summary("Buildings", cfg)
check("25D summary names layer", "Buildings" in summary)
check("25D summary names field", "Hmax" in summary)

order_expr = s25d.build_order_by_expression()
check("25D order expression uses map extent", "@map_extent_center" in order_expr)
check("25D presets exist", len(s25d.STYLE_25D_PRESETS) >= 4)
check("25D preset colours are valid", all(
    s25d.HEX_COLOR_RE.match(p["roof"]) and s25d.HEX_COLOR_RE.match(p["wall"]) and s25d.HEX_COLOR_RE.match(p["shadow"])
    for p in s25d.STYLE_25D_PRESETS.values()
))
check("25D colour fallback", s25d.normalise_hex_color("bad", "#123456") == "#123456")

# ===================================================================
# SUMMARY
# ===================================================================
section("RESULTS")
total = passed + failed
print(f"  {passed}/{total} passed ({100*passed/total:.0f}%)")
if failed:
    print(f"\n  FAILURES:")
    for e in errors:
        print(f"    {e}")
    sys.exit(1)
else:
    print("\n  ALL TESTS PASSED")
    sys.exit(0)
