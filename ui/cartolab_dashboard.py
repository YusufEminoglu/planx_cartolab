# -*- coding: utf-8 -*-
"""
CartoLab Dashboard — Professional QDialog following PlanX Suitability Lab pattern.

Provides a production console for PlanX CartoLab with:
  - Hero header with gradient branding
  - Tabbed interface: Overview, Modules (card grid), Setup, Quick Actions
  - Processing algorithm cards with Run/Fav buttons
  - System health monitoring and dependency management
"""
from __future__ import annotations

import os
from datetime import datetime

try:
    import processing
except ImportError:
    processing = None
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QMessageBox,
    QAbstractItemView,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from qgis.core import Qgis, QgsApplication, QgsProject, QgsMapLayer

from ..core.qgis_25d_style import (
    FLOOR_BAND_PALETTES,
    HEIGHT_MODE_FLOOR_COUNT,
    HEIGHT_MODE_HEIGHT,
    RENDER_MODE_FLOOR_BANDS,
    RENDER_MODE_NATIVE,
    STYLE_25D_PRESETS,
    Style25DConfig,
    apply_25d_renderer,
    build_style_summary,
    field_is_numeric,
    looks_like_floor_count_field,
    normalise_hex_color,
)


IS_QGIS4 = int(getattr(Qgis, "QGIS_VERSION_INT", 0)) >= 40000
DASHBOARD_SIZE = (1100, 760) if IS_QGIS4 else (1180, 800)
DEFAULT_CARD_COLUMNS = 2 if IS_QGIS4 else 3

# ── Algorithm catalogue ─────────────────────────────────────────────

ALGO_GROUPS = [
    (
        "2.5D Styling",
        "#9b6b43",
        [
            ("Apply 2.5D Building Style", "planx_cartolab:building_25d_style",
             "Native QGIS 2.5D extrusion from a height field with CartoLab lighting presets and shadows."),
        ],
    ),
    (
        "Classification",
        "#2f7aa8",
        [
            ("Geometric Interval Classification", "planx_cartolab:geometric_interval_classification",
             "Adaptive GIC, Head/Tail Breaks, Fisher-Jenks - optimal for skewed and heavy-tailed distributions."),
        ],
    ),
    (
        "Thematic Mapping",
        "#357a5f",
        [
            ("Bivariate Choropleth Map", "planx_cartolab:bivariate_choropleth",
             "NxN colour matrix from two numeric fields with bilinear interpolation."),
            ("Value-by-Alpha (VbA) Map", "planx_cartolab:value_by_alpha",
             "Encode reliability/uncertainty as opacity - unreliable data fades into background."),
            ("Ridge Map (Joyplot)", "planx_cartolab:ridge_map",
             "Raster-to-vector scanline deformation - Joy Division style wave profiles."),
            ("Dot-Density Map", "planx_cartolab:dot_density",
             "Seeded, hole-aware dots inside polygons - one dot per N units of a count field."),
            ("Proportional Symbols (Flannery)", "planx_cartolab:proportional_symbols",
             "Perceptually compensated graduated point symbols with nested-legend values."),
        ],
    ),
    (
        "Cartogram",
        "#7359a8",
        [
            ("Continuous-Area Cartogram", "planx_cartolab:compute_cartogram",
             "Diffusion method (Gastner & Newman) - polygon areas proportional to field value."),
        ],
    ),
    (
        "Aggregation",
        "#b6772f",
        [
            ("Hexbin Aggregation", "planx_cartolab:hexbin_aggregate",
             "Bin a point layer into a pointy-top hex grid - count, sum or mean, overplot-free."),
        ],
    ),
    (
        "Labeling",
        "#3f8e8a",
        [
            ("Visual-Center Label Points", "planx_cartolab:label_points",
             "Pole of inaccessibility (polylabel) - label anchors that always sit inside the shape."),
        ],
    ),
    (
        "Map Reference",
        "#5a6f9b",
        [
            ("Graticule / Reference Grid", "planx_cartolab:graticule_grid",
             "Meridians and parallels on nice round intervals, each carrying a coordinate label."),
        ],
    ),
    (
        "Data Preparation",
        "#9b466e",
        [
            ("Choropleth Normalization & Rates", "planx_cartolab:normalize_field",
             "Rates, z-score, robust z, min-max, percentile rank and log - prep before classifying."),
        ],
    ),
]

REQUIRED_IDS = [aid for _, _, items in ALGO_GROUPS for _, aid, _ in items]

CATEGORY_GROUPS = {
    "2.5D Styling": [
        "planx_cartolab:building_25d_style",
    ],
    "Classification Engine": [
        "planx_cartolab:geometric_interval_classification",
    ],
    "Thematic Mapping": [
        "planx_cartolab:bivariate_choropleth",
        "planx_cartolab:value_by_alpha",
        "planx_cartolab:ridge_map",
        "planx_cartolab:dot_density",
        "planx_cartolab:proportional_symbols",
    ],
    "Cartogram Engine": [
        "planx_cartolab:compute_cartogram",
    ],
    "Aggregation": [
        "planx_cartolab:hexbin_aggregate",
    ],
    "Labeling": [
        "planx_cartolab:label_points",
    ],
    "Map Reference": [
        "planx_cartolab:graticule_grid",
    ],
    "Data Preparation": [
        "planx_cartolab:normalize_field",
    ],
}


class CartoLabDashboard(QDialog):
    """Production console for PlanX CartoLab."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.settings = QSettings()
        self.recent_runs: list[str] = []
        self.card_widgets: list[QFrame] = []
        self._current_card_columns = DEFAULT_CARD_COLUMNS
        self.favorites: set[str] = set(
            self.settings.value("planx_cartolab/favorites", [], type=list) or []
        )

        self.setWindowTitle("PlanX CartoLab - Advanced Cartography Suite")
        self.resize(*DASHBOARD_SIZE)
        self._apply_style()
        self._build_ui()
        self._refresh()

    # ── Styling ──────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        r = 10 if IS_QGIS4 else 13
        btn_r = 8 if IS_QGIS4 else 9
        title_sz = 22 if IS_QGIS4 else 24
        self.setStyleSheet(f"""
            QDialog {{ background: #ecf3f4; font-family: "Segoe UI", "Inter", sans-serif; }}
            QFrame#heroCard {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #1a1a2e, stop:0.45 #16213e, stop:1 #0f3460);
                border-radius: {r}px; border: 1px solid #1a3a5c;
            }}
            QLabel#heroTitle {{ color: #e94560; font-weight: 700; font-size: {title_sz}px; }}
            QLabel#heroSub {{ color: #a8c8e8; font-size: 12px; }}
            QLabel#statusChip {{
                color: #0f2d3a; background: #f8d37a; border: 1px solid #e8bf58;
                border-radius: 8px; padding: 4px 10px; font-weight: 700;
            }}
            QTabWidget::pane {{ border: 1px solid #cfdee2; border-radius: {r}px; background: #ffffff; }}
            QTabBar::tab {{
                background: #dce9ec; color: #183844; border: 1px solid #c4d6dc;
                padding: 8px 14px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px;
            }}
            QTabBar::tab:selected {{ background: #ffffff; font-weight: 700; border-color: #9bbac4; }}
            QTextBrowser {{
                background: #ffffff; border: 1px solid #d4e1e5; border-radius: {r}px;
                padding: 9px; color: #17313a;
            }}
            QPushButton {{
                background: #236e83; color: #ffffff; border: 1px solid #1b5c6e;
                border-radius: {btn_r}px; padding: 7px 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #2d819a; }}
            QPushButton#ghost {{
                background: #ffffff; color: #1f6074; border: 1px solid #b4ccd3;
            }}
            QPushButton#ghost:hover {{ background: #f2f8f9; }}
            QPushButton#favBtn {{
                background: #ffffff; color: #e94560; border: 1px solid #e0c0c8;
                border-radius: 8px; padding: 2px 8px; font-weight: 700;
            }}
            QPushButton#favBtn:checked {{
                background: #fde8ec; color: #c0392b; border: 1px solid #e94560;
            }}
            QLineEdit {{
                background: #ffffff; border: 1px solid #c9d9de; border-radius: 8px; padding: 6px; color: #17323a;
            }}
            QComboBox {{
                background: #ffffff; border: 1px solid #c9d9de; border-radius: 8px; padding: 6px; color: #17323a;
            }}
            QDoubleSpinBox, QSpinBox {{
                background: #ffffff; border: 1px solid #c9d9de; border-radius: 8px; padding: 5px; color: #17323a;
            }}
            QCheckBox {{ color: #17323a; padding: 3px; }}
            QFrame[classCard="true"] {{
                background: #fbfefe; border: 1px solid #d3e3e7; border-radius: {r}px;
            }}
            QFrame[classCard="true"]:hover {{ background: #f2fafc; border: 1px solid #a8cfdb; }}
            QLabel[classTitle="true"] {{ color: #173741; font-weight: 700; font-size: 13px; }}
            QLabel[classMeta="true"] {{ color: #4a6871; font-size: 11px; }}
            QLabel[classChip="ok"] {{
                color: #0d4430; background: #b8e9cf; border: 1px solid #92d8b1;
                border-radius: 8px; padding: 1px 7px; font-size: 10px; font-weight: 700;
            }}
            QLabel[classChip="warn"] {{
                color: #734700; background: #ffe2ab; border: 1px solid #f0cb86;
                border-radius: 8px; padding: 1px 7px; font-size: 10px; font-weight: 700;
            }}
            QLabel#cardCount {{ color: #2b4d57; font-size: 11px; padding: 0 4px; }}
        """)

    # ── Build UI ─────────────────────────────────────────────────────

    def _make_group(self, title: str) -> QGroupBox:
        gb = QGroupBox(title)
        gb.setFont(QFont("Inter, Segoe UI", 9, QFont.Weight.Bold))
        gb.setStyleSheet(
            "QGroupBox { border: 1px solid #ccc; border-radius: 6px; "
            "margin-top: 8px; padding: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; }"
        )
        return gb

    def _build_ui(self) -> None:
        m = 10 if IS_QGIS4 else 12
        root = QVBoxLayout(self)
        root.setContentsMargins(m, m, m, m)
        root.setSpacing(m)

        # ── Hero header ──
        hero = QFrame()
        hero.setObjectName("heroCard")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(14, 12, 14, 12)
        ttl = QVBoxLayout()
        title = QLabel("PlanX CartoLab")
        title.setObjectName("heroTitle")
        sub = QLabel(
            "Advanced cartography suite: 2.5D styling, bivariate maps, "
            "cartograms, ridge maps, Value-by-Alpha, and layout automation."
        )
        sub.setObjectName("heroSub")
        ttl.addWidget(title)
        ttl.addWidget(sub)
        hl.addLayout(ttl, 1)
        self.status_chip = QLabel("System Status: checking...")
        self.status_chip.setObjectName("statusChip")
        hl.addWidget(self.status_chip, 0, Qt.AlignmentFlag.AlignRight)
        root.addWidget(hero)

        # ── Tabs ──
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # Overview tab
        self.overview = QTextBrowser()
        self.tabs.addTab(self.overview, "Overview")

        # Modules tab (card grid)
        mod_tab = QWidget()
        ml = QVBoxLayout(mod_tab)
        ml.setContentsMargins(8, 8, 8, 8)

        filter_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter modules...")
        self.search.textChanged.connect(self._filter_cards)
        filter_row.addWidget(self.search, 1)
        self.group_filter = QComboBox()
        self.group_filter.addItem("All Groups", "")
        for g, _, _ in ALGO_GROUPS:
            self.group_filter.addItem(g, g)
        self.group_filter.currentIndexChanged.connect(self._filter_cards)
        filter_row.addWidget(self.group_filter)
        self.fav_only = QPushButton("Favorites")
        self.fav_only.setObjectName("ghost")
        self.fav_only.setCheckable(True)
        self.fav_only.toggled.connect(self._filter_cards)
        filter_row.addWidget(self.fav_only)
        self.card_count = QLabel("0/0")
        self.card_count.setObjectName("cardCount")
        filter_row.addWidget(self.card_count, 0, Qt.AlignmentFlag.AlignRight)
        ml.addLayout(filter_row)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        cards_host = QWidget()
        self.cards_grid = QGridLayout(cards_host)
        self.cards_grid.setContentsMargins(4, 4, 4, 4)
        self.cards_grid.setHorizontalSpacing(8)
        self.cards_grid.setVerticalSpacing(8)
        self.cards_scroll.setWidget(cards_host)
        ml.addWidget(self.cards_scroll, 1)
        self.tabs.addTab(mod_tab, "Modules")

        self._build_cards()

        # Setup tab
        setup_tab = QWidget()
        sl = QVBoxLayout(setup_tab)
        sl.setContentsMargins(12, 12, 12, 12)
        sl.addWidget(QLabel("Check and install required Python packages for full functionality."))
        self.setup_status = QTextBrowser()
        sl.addWidget(self.setup_status, 1)
        sr = QHBoxLayout()
        btn_check = QPushButton("Check Dependencies")
        btn_check.clicked.connect(self._on_check_deps)
        sr.addWidget(btn_check)
        btn_install = QPushButton("Install Missing (pip)")
        btn_install.clicked.connect(self._on_install_deps)
        sr.addWidget(btn_install)
        sr.addStretch()
        sl.addLayout(sr)
        self.tabs.addTab(setup_tab, "Setup")

        # Quick Actions tab
        qa_tab = QWidget()
        ql = QVBoxLayout(qa_tab)
        ql.setContentsMargins(12, 12, 12, 12)
        quick = [
            ("Open 2.5D Styling Panel", self.show_25d_panel),
            ("Inspect Features (Radar Chart on Click)", self._on_activate_annotation),
            ("Run 2.5D Building Style", lambda: self._run_algorithm("planx_cartolab:building_25d_style", "2.5D Building Style")),
            ("Run Bivariate Choropleth",
             lambda: self._run_algorithm("planx_cartolab:bivariate_choropleth", "Bivariate")),
            ("Run Geometric Interval Classification",
             lambda: self._run_algorithm("planx_cartolab:geometric_interval_classification", "GIC")),
            ("Run Cartogram",
             lambda: self._run_algorithm("planx_cartolab:compute_cartogram", "Cartogram")),
            ("Run Ridge Map",
             lambda: self._run_algorithm("planx_cartolab:ridge_map", "Ridge Map")),
            ("Run Value-by-Alpha",
             lambda: self._run_algorithm("planx_cartolab:value_by_alpha", "VbA")),
            ("Run Dot-Density Map", lambda: self._run_algorithm("planx_cartolab:dot_density", "Dot Density")),
            ("Run Proportional Symbols", lambda: self._run_algorithm("planx_cartolab:proportional_symbols", "Proportional Symbols")),
            ("Run Hexbin Aggregation", lambda: self._run_algorithm("planx_cartolab:hexbin_aggregate", "Hexbin")),
            ("Run Visual-Center Label Points", lambda: self._run_algorithm("planx_cartolab:label_points", "Label Points")),
            ("Run Graticule / Reference Grid", lambda: self._run_algorithm("planx_cartolab:graticule_grid", "Graticule")),
            ("Run Choropleth Normalization", lambda: self._run_algorithm("planx_cartolab:normalize_field", "Normalize")),
            ("Copy Project Diagnostics", self._on_copy_diagnostics),
        ]
        for label, fn in quick:
            b = QPushButton(label)
            b.clicked.connect(fn)
            ql.addWidget(b)
        ql.addStretch()
        self.tabs.addTab(qa_tab, "Quick Actions")

        # 2.5D Styling tab
        self._build_25d_tab()

        # Layout Tools tab
        self._build_layout_tab()

        # Recent Runs tab
        rl_tab = QWidget()
        rl = QVBoxLayout(rl_tab)
        rl.setContentsMargins(8, 8, 8, 8)
        self.runlog = QTextBrowser()
        rl.addWidget(self.runlog, 1)
        clear = QPushButton("Clear Log")
        clear.setObjectName("ghost")
        clear.clicked.connect(self._clear_runlog)
        rl.addWidget(clear, 0, Qt.AlignmentFlag.AlignRight)
        self.tabs.addTab(rl_tab, "Recent Runs")

        # User-facing readiness tab
        self.readiness = QTextBrowser()
        self.tabs.addTab(self.readiness, "Readiness")

        # Footer
        footer = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._refresh)
        footer.addWidget(refresh)
        hint = QLabel("Tip: Use Classification first to understand data distribution, then Bivariate/Cartogram for visualization.")
        hint.setStyleSheet("color:#35545f; font-size:11px;")
        footer.addWidget(hint, 1)
        root.addLayout(footer)

        self._on_check_deps()

    # ── Module cards ─────────────────────────────────────────────────

    def _build_cards(self) -> None:
        for w in self.card_widgets:
            w.setParent(None)
        self.card_widgets = []
        columns = self._cards_column_count()
        self._current_card_columns = columns
        idx = 0
        for group, accent, items in ALGO_GROUPS:
            for title_txt, aid, desc in items:
                card = QFrame()
                card.setProperty("classCard", "true")
                card.setStyleSheet(f"border-left: 3px solid {accent};")
                v = QVBoxLayout(card)
                v.setContentsMargins(10, 10, 10, 10)

                hdr = QHBoxLayout()
                t = QLabel(title_txt)
                t.setProperty("classTitle", "true")
                hdr.addWidget(t, 1)
                status_lbl = QLabel("Checking")
                status_lbl.setProperty("classChip", "warn")
                hdr.addWidget(status_lbl, 0, Qt.AlignmentFlag.AlignRight)
                v.addLayout(hdr)

                m = QLabel(f"{group}  |  {aid}")
                m.setProperty("classMeta", "true")
                d = QLabel(desc)
                d.setWordWrap(True)
                d.setStyleSheet("color:#294e58; font-size:12px;")
                v.addWidget(m)
                v.addWidget(d, 1)

                fav = QPushButton("Fav")
                fav.setObjectName("favBtn")
                fav.setCheckable(True)
                fav.setChecked(aid in self.favorites)
                fav.clicked.connect(lambda checked, x=aid: self._toggle_favorite(x, checked))

                run = QPushButton("Run")
                run.clicked.connect(lambda _, x=aid, n=title_txt: self._run_algorithm(x, n))

                br = QHBoxLayout()
                br.addWidget(fav, 0, Qt.AlignmentFlag.AlignLeft)
                br.addStretch()
                br.addWidget(run, 0, Qt.AlignmentFlag.AlignRight)
                v.addLayout(br)

                card.meta = (group.lower(), title_txt.lower(), aid.lower(), desc.lower())
                card.algo_id = aid
                card.status_lbl = status_lbl
                r, c = divmod(idx, columns)
                self.cards_grid.addWidget(card, r, c)
                self.card_widgets.append(card)
                idx += 1

    def _cards_column_count(self) -> int:
        if not hasattr(self, "cards_scroll"):
            return DEFAULT_CARD_COLUMNS
        vp = self.cards_scroll.viewport()
        width = vp.width() if vp else self.width() - 120
        if width <= 0:
            width = 1
        target = 420 if IS_QGIS4 else 380
        max_cols = 2 if IS_QGIS4 else 3
        return max(1, min(max_cols, width // target))

    def _filter_cards(self) -> None:
        q = (self.search.text() or "").strip().lower()
        grp = (self.group_filter.currentData() or "").lower()
        fav_only = self.fav_only.isChecked()
        for card in self.card_widgets:
            mg, mt, ma, md = card.meta
            ok_q = (q in mg or q in mt or q in ma or q in md) if q else True
            ok_g = (mg == grp) if grp else True
            ok_f = (card.algo_id in self.favorites) if fav_only else True
            card.setVisible(ok_q and ok_g and ok_f)
        visible = sum(1 for c in self.card_widgets if c.isVisible())
        self.card_count.setText(f"Visible: {visible}/{len(self.card_widgets)}")

    def _toggle_favorite(self, algo_id: str, checked: bool) -> None:
        if checked:
            self.favorites.add(algo_id)
        else:
            self.favorites.discard(algo_id)
        self.settings.setValue("planx_cartolab/favorites", sorted(self.favorites))
        self._filter_cards()

    # ── Algorithm execution ──────────────────────────────────────────

    def _run_algorithm(self, algo_id: str, label: str) -> None:
        if processing is None:
            QMessageBox.warning(
                self, "Processing Unavailable",
                "The QGIS Processing framework is not available in this session. "
                "Enable the Processing plugin and restart QGIS."
            )
            return
        reg = QgsApplication.processingRegistry()
        if reg.algorithmById(algo_id) is None:
            QMessageBox.warning(
                self, "Algorithm Not Found",
                f"The algorithm '{algo_id}' is not registered.\n\n"
                "The Processing provider may not have loaded correctly. "
                "Try restarting QGIS or reinstalling the plugin."
            )
            return
        try:
            processing.execAlgorithmDialog(algo_id)
        except Exception as exc:
            QMessageBox.critical(
                self, "Algorithm Error",
                f"Failed to open '{label}':\n{exc}"
            )
            return
        ts = datetime.now().strftime("%H:%M:%S")
        self.recent_runs.insert(0, f"[{ts}] {label} ({algo_id})")
        self.recent_runs = self.recent_runs[:30]
        self._refresh_runlog()

    def _refresh_runlog(self) -> None:
        if not self.recent_runs:
            self.runlog.setHtml("<h3>Recent Runs</h3><p>No runs yet.</p>")
            return
        html = "<h3>Recent Runs</h3><ul>" + "".join(f"<li>{r}</li>" for r in self.recent_runs) + "</ul>"
        self.runlog.setHtml(html)

    def _clear_runlog(self) -> None:
        self.recent_runs = []
        self._refresh_runlog()

    def _on_copy_diagnostics(self) -> None:
        """Copy project diagnostics to clipboard."""
        from ..core.dependency_manager import check_packages, CARTO_LAB_DEPS
        avail, miss_req, miss_opt = check_packages(CARTO_LAB_DEPS)
        layers = list(QgsProject.instance().mapLayers().values())
        reg = QgsApplication.processingRegistry()
        missing = [aid for aid in REQUIRED_IDS if reg.algorithmById(aid) is None]
        txt = (
            "PlanX CartoLab - Project Diagnostics\n"
            "=====================================\n"
            f"QGIS layers: {len(layers)}\n"
            f"Algorithms ready: {len(REQUIRED_IDS) - len(missing)}/{len(REQUIRED_IDS)}\n"
            f"Missing: {', '.join(missing) if missing else 'None'}\n"
            f"Packages OK: {', '.join(avail)}\n"
            f"Missing required: {', '.join(miss_req) if miss_req else 'None'}\n"
            f"Missing optional: {', '.join(miss_opt) if miss_opt else 'None'}\n"
        )
        QApplication.clipboard().setText(txt)
        self.iface.messageBar().pushSuccess("CartoLab", "Diagnostics copied to clipboard.")

    def _on_activate_annotation(self) -> None:
        """Activate the floating annotation map tool."""
        from ..ui.floating_annotation import FloatingAnnotationTool
        canvas = self.iface.mapCanvas()
        tool = FloatingAnnotationTool(self.iface, canvas)
        canvas.setMapTool(tool)
        self.iface.messageBar().pushInfo(
            "CartoLab", "Click any feature on the map to inspect its attributes."
        )

    # ── Layout Tools ──────────────────────────────────────────────────

    # 2.5D Styling

    def _build_25d_tab(self) -> None:
        self.tab_25d = QScrollArea()
        self.tab_25d.setWidgetResizable(True)
        self.tab_25d.setFrameShape(QFrame.Shape.NoFrame)
        tab_body = QWidget()
        self.tab_25d.setWidget(tab_body)
        lyt = QVBoxLayout(tab_body)
        lyt.setContentsMargins(12, 12, 12, 12)
        lyt.setSpacing(10)

        source_group = self._make_group("Layer and Height")
        source_layout = QGridLayout(source_group)
        source_layout.setColumnMinimumWidth(0, 150)
        source_layout.setColumnStretch(1, 1)
        source_layout.setColumnStretch(2, 0)
        source_layout.addWidget(QLabel("Polygon layer:"), 0, 0)
        self.layer25d_combo = QComboBox()
        self.layer25d_combo.currentIndexChanged.connect(self._refresh_25d_fields)
        source_layout.addWidget(self.layer25d_combo, 0, 1)
        refresh_layers = QPushButton("Refresh Layers")
        refresh_layers.setObjectName("ghost")
        refresh_layers.clicked.connect(self._refresh_25d_layers)
        source_layout.addWidget(refresh_layers, 0, 2)

        source_layout.addWidget(QLabel("Height field:"), 1, 0)
        self.height25d_combo = QComboBox()
        self.height25d_combo.currentIndexChanged.connect(self._on_25d_height_field_changed)
        source_layout.addWidget(self.height25d_combo, 1, 1, 1, 2)

        source_layout.addWidget(QLabel("Height source:"), 2, 0)
        self.mode25d_combo = QComboBox()
        self.mode25d_combo.addItem("Height field is already in metres/map units", HEIGHT_MODE_HEIGHT)
        self.mode25d_combo.addItem("Floor count field (floors x floor height)", HEIGHT_MODE_FLOOR_COUNT)
        self.mode25d_combo.currentIndexChanged.connect(self._on_25d_mode_changed)
        source_layout.addWidget(self.mode25d_combo, 2, 1, 1, 2)

        source_layout.addWidget(QLabel("Visual preset:"), 3, 0)
        self.preset25d_combo = QComboBox()
        for key, preset in STYLE_25D_PRESETS.items():
            self.preset25d_combo.addItem(preset["label"], key)
        self.preset25d_combo.currentIndexChanged.connect(self._on_25d_preset_changed)
        source_layout.addWidget(self.preset25d_combo, 3, 1, 1, 2)
        lyt.addWidget(source_group)

        geom_group = self._make_group("Extrusion Geometry")
        geom_layout = QGridLayout(geom_group)
        geom_layout.setColumnMinimumWidth(0, 125)
        geom_layout.setColumnMinimumWidth(2, 125)
        geom_layout.setColumnStretch(1, 1)
        geom_layout.setColumnStretch(3, 1)
        self.angle25d_spin = self._make_double_spin(0, 359, 110, 1, " degrees")
        self.scale25d_spin = self._make_double_spin(0.01, 100, 1, 0.1, "x")
        self.floor_height25d_spin = self._make_double_spin(0.01, 100, 3.5, 0.1, " map units/floor")
        self.max25d_spin = self._make_double_spin(0, 1000000, 0, 1, " map units")
        self.step25d_check = QCheckBox("Snap heights to stepped floors")
        self.step25d_spin = self._make_double_spin(0.01, 100000, 3.5, 0.1, " map units")

        geom_layout.addWidget(QLabel("Projection angle:"), 0, 0)
        geom_layout.addWidget(self.angle25d_spin, 0, 1)
        geom_layout.addWidget(QLabel("Vertical scale:"), 0, 2)
        geom_layout.addWidget(self.scale25d_spin, 0, 3)
        self.floor_height25d_label = QLabel("Floor height:")
        geom_layout.addWidget(self.floor_height25d_label, 1, 0)
        geom_layout.addWidget(self.floor_height25d_spin, 1, 1)
        geom_layout.addWidget(QLabel("Maximum height:"), 1, 2)
        geom_layout.addWidget(self.max25d_spin, 1, 3)
        geom_layout.addWidget(self.step25d_check, 2, 0, 1, 2)
        geom_layout.addWidget(self.step25d_spin, 2, 2, 1, 2)
        lyt.addWidget(geom_group)

        floor_group = self._make_group("Floor Colour Bands")
        floor_layout = QGridLayout(floor_group)
        floor_layout.setColumnMinimumWidth(0, 150)
        floor_layout.setColumnMinimumWidth(2, 150)
        floor_layout.setColumnStretch(1, 1)
        floor_layout.setColumnStretch(3, 1)
        self.floor_bands25d_check = QCheckBox("Colour each floor separately")
        self.floor_bands25d_check.toggled.connect(self._on_25d_floor_bands_changed)
        self.floor_palette25d_label = QLabel("Floor palette:")
        self.floor_palette25d_combo = QComboBox()
        for key, palette in FLOOR_BAND_PALETTES.items():
            self.floor_palette25d_combo.addItem(palette["label"], key)
        self.floor_palette25d_combo.currentIndexChanged.connect(self._update_25d_status_preview)
        self.max_floors25d_label = QLabel("Maximum floor bands:")
        self.max_floors25d_spin = QSpinBox()
        self.max_floors25d_spin.setRange(0, 80)
        self.max_floors25d_spin.setSpecialValueText("Auto from layer")
        self.max_floors25d_spin.setValue(0)
        self.max_floors25d_spin.setToolTip("Use 0 to scan the selected floor-count field and match the layer automatically.")
        self.max_floors25d_spin.valueChanged.connect(self._update_25d_status_preview)

        floor_layout.addWidget(self.floor_bands25d_check, 0, 0, 1, 2)
        floor_layout.addWidget(self.floor_palette25d_label, 1, 0)
        floor_layout.addWidget(self.floor_palette25d_combo, 1, 1)
        floor_layout.addWidget(self.max_floors25d_label, 1, 2)
        floor_layout.addWidget(self.max_floors25d_spin, 1, 3)
        lyt.addWidget(floor_group)

        light_group = self._make_group("Lighting and Materials")
        light_layout = QGridLayout(light_group)
        light_layout.setColumnMinimumWidth(0, 110)
        light_layout.setColumnMinimumWidth(2, 125)
        light_layout.setColumnStretch(1, 1)
        light_layout.setColumnStretch(3, 1)
        self.roof25d_btn = self._make_color_button("#f2cf96")
        self.wall25d_btn = self._make_color_button("#b36f43")
        self.shadow25d_btn = self._make_color_button("#202833")
        self.shadow25d_check = QCheckBox("Enable soft shadow")
        self.shadow25d_check.setChecked(True)
        self.wall_shading25d_check = QCheckBox("Enable directional wall shading")
        self.wall_shading25d_check.setChecked(True)
        self.shadow_spread25d_spin = self._make_double_spin(0, 100000, 3.5, 0.5, " map units")

        self.roof25d_btn.clicked.connect(lambda: self._pick_25d_color(self.roof25d_btn, "Roof Color"))
        self.wall25d_btn.clicked.connect(lambda: self._pick_25d_color(self.wall25d_btn, "Wall Color"))
        self.shadow25d_btn.clicked.connect(lambda: self._pick_25d_color(self.shadow25d_btn, "Shadow Color"))

        light_layout.addWidget(QLabel("Roof color:"), 0, 0)
        light_layout.addWidget(self.roof25d_btn, 0, 1)
        light_layout.addWidget(QLabel("Wall color:"), 0, 2)
        light_layout.addWidget(self.wall25d_btn, 0, 3)
        light_layout.addWidget(QLabel("Shadow color:"), 1, 0)
        light_layout.addWidget(self.shadow25d_btn, 1, 1)
        light_layout.addWidget(QLabel("Shadow spread:"), 1, 2)
        light_layout.addWidget(self.shadow_spread25d_spin, 1, 3)
        light_layout.addWidget(self.shadow25d_check, 2, 0, 1, 2)
        light_layout.addWidget(self.wall_shading25d_check, 2, 2, 1, 2)
        lyt.addWidget(light_group)

        action_row = QHBoxLayout()
        apply_btn = QPushButton("Apply 2.5D Style")
        apply_btn.clicked.connect(self._on_apply_25d_style)
        action_row.addWidget(apply_btn)
        save_btn = QPushButton("Save QML Style")
        save_btn.setObjectName("ghost")
        save_btn.clicked.connect(self._on_save_25d_qml)
        action_row.addWidget(save_btn)
        copy_btn = QPushButton("Copy Style Summary")
        copy_btn.setObjectName("ghost")
        copy_btn.clicked.connect(self._on_copy_25d_summary)
        action_row.addWidget(copy_btn)
        for button in (apply_btn, save_btn, copy_btn):
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        action_row.addStretch()
        lyt.addLayout(action_row)

        self.style25d_status = QTextBrowser()
        self.style25d_status.setMaximumHeight(150)
        lyt.addWidget(self.style25d_status)
        lyt.addStretch()

        self.tabs.addTab(self.tab_25d, "2.5D Styling")
        self._refresh_25d_layers()
        self._on_25d_preset_changed()
        self._on_25d_mode_changed()

    def _make_double_spin(self, minimum: float, maximum: float, value: float, step: float, suffix: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(2)
        spin.setSingleStep(step)
        spin.setValue(value)
        spin.setSuffix(suffix)
        spin.valueChanged.connect(self._update_25d_status_preview)
        return spin

    def _make_color_button(self, color: str) -> QPushButton:
        btn = QPushButton()
        btn.setMinimumWidth(118)
        self._set_color_button(btn, color)
        return btn

    def _set_color_button(self, button: QPushButton, color: str) -> None:
        color = normalise_hex_color(color, "#888888")
        qcolor = QColor(color)
        luminance = qcolor.red() * 0.299 + qcolor.green() * 0.587 + qcolor.blue() * 0.114
        text_color = "#ffffff" if luminance < 150 else "#17232a"
        button.setProperty("hexColor", color)
        button.setText(color.upper())
        button.setStyleSheet(
            f"background:{color}; color:{text_color}; border:1px solid #203040; border-radius:8px; padding:7px 12px;"
        )

    def _pick_25d_color(self, button: QPushButton, title: str) -> None:
        current = QColor(button.property("hexColor") or "#888888")
        color = QColorDialog.getColor(current, self, title)
        if color.isValid():
            self._set_color_button(button, color.name())

    def show_25d_panel(self) -> None:
        if hasattr(self, "tab_25d"):
            self.tabs.setCurrentWidget(self.tab_25d)
            self._refresh_25d_layers()

    def _polygon_layers(self):
        layers = []
        for layer in QgsProject.instance().mapLayers().values():
            if (layer.type() == QgsMapLayer.VectorLayer
                    and hasattr(layer, "geometryType")
                    and layer.geometryType() == 2):
                layers.append(layer)
        return layers

    def _layer_by_id(self, layer_id: str):
        if not layer_id:
            return None
        return QgsProject.instance().mapLayer(layer_id)

    def _selected_25d_layer(self):
        if not hasattr(self, "layer25d_combo"):
            return None
        return self._layer_by_id(self.layer25d_combo.currentData())

    def _refresh_25d_layers(self) -> None:
        if not hasattr(self, "layer25d_combo"):
            return
        current = self.layer25d_combo.currentData()
        self.layer25d_combo.blockSignals(True)
        self.layer25d_combo.clear()
        for layer in self._polygon_layers():
            self.layer25d_combo.addItem(layer.name(), layer.id())
        if current:
            idx = self.layer25d_combo.findData(current)
            if idx >= 0:
                self.layer25d_combo.setCurrentIndex(idx)
        self.layer25d_combo.blockSignals(False)
        self._refresh_25d_fields()

    def _refresh_25d_fields(self) -> None:
        if not hasattr(self, "height25d_combo"):
            return
        layer = self._selected_25d_layer()
        current = self.height25d_combo.currentData()
        self.height25d_combo.blockSignals(True)
        self.height25d_combo.clear()
        if layer:
            fields = list(layer.fields())
            numeric_fields = [f for f in fields if field_is_numeric(f)]
            floor_fields = [f for f in fields if looks_like_floor_count_field(f.name())]
            candidate_fields = []
            for field in numeric_fields + floor_fields:
                if field.name() not in [existing.name() for existing in candidate_fields]:
                    candidate_fields.append(field)
            for field in candidate_fields or fields:
                self.height25d_combo.addItem(field.name(), field.name())
            preferred = [
                "Kat_Sayisi", "KatSayisi", "kat_sayisi", "floors", "floor_count",
                "Hmax", "Height", "height", "Heights", "building_height", "Yukseklik",
            ]
            target = current if current else next((name for name in preferred if self.height25d_combo.findData(name) >= 0), None)
            if target:
                idx = self.height25d_combo.findData(target)
                if idx >= 0:
                    self.height25d_combo.setCurrentIndex(idx)
        self.height25d_combo.blockSignals(False)
        self._on_25d_height_field_changed()
        self._update_25d_status_preview()

    def _on_25d_height_field_changed(self) -> None:
        if not hasattr(self, "mode25d_combo"):
            return
        field_name = self.height25d_combo.currentData() or ""
        if looks_like_floor_count_field(field_name):
            idx = self.mode25d_combo.findData(HEIGHT_MODE_FLOOR_COUNT)
            if idx >= 0:
                self.mode25d_combo.setCurrentIndex(idx)
        self._update_25d_status_preview()

    def _on_25d_mode_changed(self) -> None:
        if not hasattr(self, "floor_height25d_label"):
            return
        is_floor_mode = self.mode25d_combo.currentData() == HEIGHT_MODE_FLOOR_COUNT
        self.floor_height25d_label.setVisible(is_floor_mode)
        self.floor_height25d_spin.setVisible(is_floor_mode)
        if hasattr(self, "floor_bands25d_check"):
            self.floor_bands25d_check.setEnabled(is_floor_mode)
            if not is_floor_mode:
                self.floor_bands25d_check.setChecked(False)
            self._on_25d_floor_bands_changed()
        if is_floor_mode:
            self.step25d_check.setChecked(False)
        self._update_25d_status_preview()

    def _on_25d_floor_bands_changed(self) -> None:
        if not hasattr(self, "floor_palette25d_combo"):
            return
        is_floor_mode = self.mode25d_combo.currentData() == HEIGHT_MODE_FLOOR_COUNT
        enabled = bool(self.floor_bands25d_check.isChecked() and is_floor_mode)
        self.floor_palette25d_label.setVisible(enabled)
        self.floor_palette25d_combo.setVisible(enabled)
        self.max_floors25d_label.setVisible(enabled)
        self.max_floors25d_spin.setVisible(enabled)
        self.step25d_check.setEnabled(not enabled)
        self.step25d_spin.setEnabled(not enabled)
        if enabled:
            self.step25d_check.setChecked(False)
        self._update_25d_status_preview()

    def _on_25d_preset_changed(self) -> None:
        if not hasattr(self, "preset25d_combo"):
            return
        preset_key = self.preset25d_combo.currentData() or "warm_civic"
        preset = STYLE_25D_PRESETS.get(preset_key, STYLE_25D_PRESETS["warm_civic"])
        self._set_color_button(self.roof25d_btn, preset["roof"])
        self._set_color_button(self.wall25d_btn, preset["wall"])
        self._set_color_button(self.shadow25d_btn, preset["shadow"])
        self.shadow_spread25d_spin.setValue(float(preset["shadow_spread"]))
        self._update_25d_status_preview()

    def _current_25d_config(self) -> Style25DConfig:
        height_field = self.height25d_combo.currentData()
        if not height_field:
            raise ValueError("Select a numeric height field.")
        return Style25DConfig(
            height_field=height_field,
            preset=self.preset25d_combo.currentData() or "warm_civic",
            roof_color=normalise_hex_color(self.roof25d_btn.property("hexColor"), "#f2cf96"),
            wall_color=normalise_hex_color(self.wall25d_btn.property("hexColor"), "#b36f43"),
            shadow_color=normalise_hex_color(self.shadow25d_btn.property("hexColor"), "#202833"),
            angle=self.angle25d_spin.value(),
            height_scale=self.scale25d_spin.value(),
            max_height=self.max25d_spin.value(),
            stepped=self.step25d_check.isChecked(),
            step_height=self.step25d_spin.value(),
            shadow_enabled=self.shadow25d_check.isChecked(),
            shadow_spread=self.shadow_spread25d_spin.value(),
            wall_shading=self.wall_shading25d_check.isChecked(),
            height_mode=self.mode25d_combo.currentData() or HEIGHT_MODE_HEIGHT,
            floor_height=self.floor_height25d_spin.value(),
            render_mode=RENDER_MODE_FLOOR_BANDS if self.floor_bands25d_check.isChecked() else RENDER_MODE_NATIVE,
            floor_palette=self.floor_palette25d_combo.currentData() or "civic_spectrum",
            max_floors=self.max_floors25d_spin.value(),
        )

    def _update_25d_status_preview(self) -> None:
        if not hasattr(self, "style25d_status"):
            return
        layer = self._selected_25d_layer()
        if not layer:
            self.style25d_status.setPlainText("Load or select a polygon layer to apply 2.5D styling.")
            return
        try:
            summary = build_style_summary(layer.name(), self._current_25d_config())
        except Exception as exc:
            summary = str(exc)
        self.style25d_status.setPlainText(summary)

    def _on_apply_25d_style(self) -> None:
        layer = self._selected_25d_layer()
        try:
            summary = apply_25d_renderer(layer, self._current_25d_config())
            if hasattr(self.iface, "layerTreeView"):
                self.iface.layerTreeView().refreshLayerSymbology(layer.id())
            self.style25d_status.setPlainText(summary)
            self.iface.messageBar().pushSuccess("CartoLab", f"2.5D style applied to {layer.name()}.")
        except Exception as exc:
            QMessageBox.critical(self, "2.5D Styling Error", str(exc))

    def _on_save_25d_qml(self) -> None:
        layer = self._selected_25d_layer()
        if not layer:
            QMessageBox.warning(self, "Save QML Style", "Select a polygon layer first.")
            return
        default_name = f"{layer.name()}_planx_25d.qml".replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save QGIS Layer Style",
            os.path.join(os.path.expanduser("~"), "Desktop", default_name),
            "QGIS Layer Style (*.qml)",
        )
        if not path:
            return
        if not path.lower().endswith(".qml"):
            path += ".qml"
        try:
            apply_25d_renderer(layer, self._current_25d_config())
            message, ok = layer.saveNamedStyle(path)
            if not ok:
                raise RuntimeError(message)
            self.iface.messageBar().pushSuccess("CartoLab", f"QML style saved: {path}")
            self.style25d_status.append(f"\nSaved QML style: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save QML Style", str(exc))

    def _on_copy_25d_summary(self) -> None:
        self._update_25d_status_preview()
        QApplication.clipboard().setText(self.style25d_status.toPlainText())
        self.iface.messageBar().pushSuccess("CartoLab", "2.5D style summary copied to clipboard.")

    def _build_layout_tab(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget()
        lyt = QVBoxLayout(w)
        lyt.setContentsMargins(12, 12, 12, 12)
        lyt.setSpacing(10)

        # ── Group 1: Auto Map Sheet ──────────────────────────────────
        gb_sheet = self._make_group("Auto Map Sheet — one-click publication layout")
        gs = QVBoxLayout(gb_sheet)
        intro = QLabel(
            "Build a finished print layout from the current map view: titled "
            "map frame at the current extent, legend, scale bar, north arrow, "
            "grid and credits. Opens straight in the Layout Designer."
        )
        intro.setWordWrap(True)
        gs.addWidget(intro)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(6)
        form.addWidget(QLabel("Title:"), 0, 0)
        self.mapsheet_title = QLineEdit()
        self.mapsheet_title.setPlaceholderText("(defaults to the project title)")
        form.addWidget(self.mapsheet_title, 0, 1, 1, 3)

        form.addWidget(QLabel("Credits:"), 1, 0)
        self.mapsheet_credits = QLineEdit()
        self.mapsheet_credits.setPlaceholderText("Data source, author, date…")
        form.addWidget(self.mapsheet_credits, 1, 1, 1, 3)

        form.addWidget(QLabel("Page:"), 2, 0)
        self.mapsheet_page_combo = QComboBox()
        self.mapsheet_page_combo.addItems(["A4", "A3", "A2", "A1", "A0"])
        form.addWidget(self.mapsheet_page_combo, 2, 1)
        form.addWidget(QLabel("Orientation:"), 2, 2)
        self.mapsheet_orient_combo = QComboBox()
        self.mapsheet_orient_combo.addItems(["Landscape", "Portrait"])
        form.addWidget(self.mapsheet_orient_combo, 2, 3)
        gs.addLayout(form)

        el_row = QHBoxLayout()
        el_row.addWidget(QLabel("Include:"))
        self.cb_title = QCheckBox("Title")
        self.cb_legend = QCheckBox("Legend")
        self.cb_scalebar = QCheckBox("Scale bar")
        self.cb_north = QCheckBox("North arrow")
        self.cb_grid = QCheckBox("Grid")
        for cb in (self.cb_title, self.cb_legend, self.cb_scalebar, self.cb_north):
            cb.setChecked(True)
            el_row.addWidget(cb)
        self.cb_grid.setChecked(False)
        el_row.addWidget(self.cb_grid)
        el_row.addStretch()
        gs.addLayout(el_row)

        btn_sheet = QPushButton("Create Map Sheet from Current View")
        btn_sheet.setToolTip("Assemble a complete print layout and open it in the designer")
        btn_sheet.clicked.connect(self._on_create_map_sheet)
        gs.addWidget(btn_sheet)
        lyt.addWidget(gb_sheet)

        # ── Group 2: Layout Manager ──────────────────────────────────
        gb_mgr = self._make_group("Layout Manager")
        gm = QVBoxLayout(gb_mgr)
        pick = QHBoxLayout()
        pick.addWidget(QLabel("Layout:"))
        self.layout_combo = QComboBox()
        self.layout_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        pick.addWidget(self.layout_combo, 1)
        btn_refresh_layouts = QPushButton("↻")
        btn_refresh_layouts.setToolTip("Refresh layout list")
        btn_refresh_layouts.setMaximumWidth(36)
        btn_refresh_layouts.clicked.connect(self._refresh_layout_combo)
        pick.addWidget(btn_refresh_layouts)
        gm.addLayout(pick)

        actions = QHBoxLayout()
        btn_open = QPushButton("Open in Designer")
        btn_open.clicked.connect(self._on_open_designer)
        btn_dup = QPushButton("Duplicate")
        btn_dup.clicked.connect(self._on_duplicate_layout)
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self._on_delete_layout)
        for b in (btn_open, btn_dup, btn_del):
            actions.addWidget(b)
        gm.addLayout(actions)

        exports = QHBoxLayout()
        btn_png = QPushButton("Export PNG…")
        btn_png.clicked.connect(lambda: self._on_export_layout("png"))
        btn_pdf = QPushButton("Export PDF…")
        btn_pdf.clicked.connect(lambda: self._on_export_layout("pdf"))
        exports.addWidget(btn_png)
        exports.addWidget(btn_pdf)
        gm.addLayout(exports)
        lyt.addWidget(gb_mgr)

        # ── Group 3: Decorators (apply to the selected layout) ───────
        gb_dec = self._make_group("Decorators — enhance the selected layout")
        gd = QVBoxLayout(gb_dec)

        gd.addWidget(QLabel("Isometric stack layers (select 2+ to build a new stack):"))
        self.iso_layer_list = QListWidget()
        self.iso_layer_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )
        self.iso_layer_list.setMinimumHeight(96)
        self.iso_layer_list.setMaximumHeight(150)
        gd.addWidget(self.iso_layer_list)
        btn_iso = QPushButton("Create Isometric Layer Stack")
        btn_iso.clicked.connect(self._on_isometric_stack)
        gd.addWidget(btn_iso)

        bivar_row = QHBoxLayout()
        bivar_row.addWidget(QLabel("Bivariate legend:"))
        self.bivar_palette_combo = QComboBox()
        self.bivar_palette_combo.addItem("Teal-Brown", "teal_brown")
        self.bivar_palette_combo.addItem("Purple-Green", "purple_green")
        self.bivar_palette_combo.addItem("Blue-Orange", "blue_orange")
        self.bivar_palette_combo.addItem("Pink-Green", "pink_green")
        bivar_row.addWidget(self.bivar_palette_combo, 1)
        self.bivar_legend_type_combo = QComboBox()
        self.bivar_legend_type_combo.addItem("Diamond", "diamond")
        self.bivar_legend_type_combo.addItem("Square", "square")
        bivar_row.addWidget(self.bivar_legend_type_combo, 1)
        gd.addLayout(bivar_row)
        btn_legend = QPushButton("Add Bivariate Legend to Selected Layout")
        btn_legend.clicked.connect(self._on_bivariate_legend)
        gd.addWidget(btn_legend)

        deco_row = QHBoxLayout()
        btn_typo = QPushButton("Apply Swiss Typography")
        btn_typo.clicked.connect(self._on_typography)
        btn_grid = QPushButton("Add / Refresh Minimalist Grid")
        btn_grid.clicked.connect(self._on_grid_style)
        deco_row.addWidget(btn_typo)
        deco_row.addWidget(btn_grid)
        gd.addLayout(deco_row)
        lyt.addWidget(gb_dec)

        for button in (btn_sheet, btn_iso, btn_legend, btn_typo, btn_grid):
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lyt.addStretch()
        scroll.setWidget(w)
        self.tabs.addTab(scroll, "Layout")
        self._refresh_layout_combo()

    # ── Layout Manager helpers ───────────────────────────────────────

    def _refresh_layout_combo(self) -> None:
        """Repopulate the layout picker, preserving the current selection."""
        if not hasattr(self, "layout_combo"):
            return
        current = self.layout_combo.currentText()
        self.layout_combo.blockSignals(True)
        self.layout_combo.clear()
        names = [lay.name() for lay in QgsProject.instance().layoutManager().layouts()]
        self.layout_combo.addItems(sorted(names))
        if current in names:
            self.layout_combo.setCurrentText(current)
        self.layout_combo.blockSignals(False)

    def _selected_layout(self):
        """Return the QgsPrintLayout chosen in the picker, or None."""
        if not hasattr(self, "layout_combo"):
            return None
        name = self.layout_combo.currentText()
        if not name:
            return None
        return QgsProject.instance().layoutManager().layoutByName(name)

    def _require_layout(self, title: str):
        """Return the selected layout or show a helpful message and return None."""
        layout = self._selected_layout()
        if layout is None:
            QMessageBox.information(
                self, title,
                "No layout selected. Create a Map Sheet above, or pick an "
                "existing layout in the Layout Manager list.",
            )
        return layout

    def _bivar_colors(self):
        preset = self.bivar_palette_combo.currentData()
        return {
            "teal_brown": ("#e8e8e8", "#5ab4ac", "#d8b365", "#8c510a"),
            "purple_green": ("#e8e8e8", "#7fbf7b", "#af8dc3", "#762a83"),
            "blue_orange": ("#e8e8e8", "#fdae61", "#abd9e9", "#2c7bb6"),
            "pink_green": ("#e8e8e8", "#a1d76a", "#e9a3c9", "#c51b7d"),
        }.get(preset, ("#e8e8e8", "#5ab4ac", "#d8b365", "#8c510a"))

    def _open_in_designer(self, layout) -> None:
        try:
            if hasattr(self.iface, "openLayoutDesigner"):
                self.iface.openLayoutDesigner(layout)
        except Exception:
            pass

    # ── Layout Studio actions ────────────────────────────────────────

    def _on_create_map_sheet(self) -> None:
        if not QgsProject.instance().mapLayers():
            QMessageBox.warning(
                self, "Auto Map Sheet",
                "No layers are loaded — the map frame would be empty. "
                "Load a layer first.",
            )
            return
        try:
            from ..layout.map_sheet import create_map_sheet
            layout = create_map_sheet(
                iface=self.iface,
                title=self.mapsheet_title.text().strip(),
                credits=self.mapsheet_credits.text().strip(),
                page_size=self.mapsheet_page_combo.currentText(),
                landscape=(self.mapsheet_orient_combo.currentText() == "Landscape"),
                add_title=self.cb_title.isChecked(),
                add_legend=self.cb_legend.isChecked(),
                add_scalebar=self.cb_scalebar.isChecked(),
                add_north_arrow=self.cb_north.isChecked(),
                add_grid=self.cb_grid.isChecked(),
            )
            self._refresh_layout_combo()
            self.layout_combo.setCurrentText(layout.name())
            self._open_in_designer(layout)
            self.iface.messageBar().pushSuccess(
                "CartoLab", f"Map sheet '{layout.name()}' created.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Map Sheet Error", str(exc))

    def _on_open_designer(self) -> None:
        layout = self._require_layout("Open in Designer")
        if layout is not None:
            self._open_in_designer(layout)

    def _on_duplicate_layout(self) -> None:
        layout = self._require_layout("Duplicate Layout")
        if layout is None:
            return
        manager = QgsProject.instance().layoutManager()
        new_name = manager.generateUniqueTitle()
        try:
            dup = manager.duplicateLayout(layout, new_name)
        except Exception as exc:
            QMessageBox.critical(self, "Duplicate Layout", str(exc))
            return
        self._refresh_layout_combo()
        if dup is not None:
            self.layout_combo.setCurrentText(dup.name())
        self.iface.messageBar().pushSuccess("CartoLab", f"Duplicated to '{new_name}'.")

    def _on_delete_layout(self) -> None:
        layout = self._require_layout("Delete Layout")
        if layout is None:
            return
        name = layout.name()
        if QMessageBox.question(
            self, "Delete Layout",
            f"Delete layout '{name}'? This cannot be undone.",
        ) != QMessageBox.StandardButton.Yes:
            return
        QgsProject.instance().layoutManager().removeLayout(layout)
        self._refresh_layout_combo()
        self.iface.messageBar().pushSuccess("CartoLab", f"Deleted layout '{name}'.")

    def _on_export_layout(self, fmt: str) -> None:
        layout = self._require_layout("Export Layout")
        if layout is None:
            return
        ext = "pdf" if fmt == "pdf" else "png"
        filt = "PDF document (*.pdf)" if ext == "pdf" else "PNG image (*.png)"
        safe = "".join(c if c.isalnum() else "_" for c in layout.name())
        default = os.path.join(
            os.path.expanduser("~"), f"{safe}.{ext}")
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export {ext.upper()}", default, filt)
        if not path:
            return
        if not path.lower().endswith("." + ext):
            path += "." + ext
        try:
            from ..layout.layout_utils import export_layout
            success = export_layout(layout, path, dpi=300)
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))
            return
        if success:
            self.iface.messageBar().pushSuccess("CartoLab", f"Exported: {path}")
        else:
            QMessageBox.warning(self, "Export", "Export did not complete successfully.")

    def _on_isometric_stack(self) -> None:
        selected_items = self.iso_layer_list.selectedItems()
        if len(selected_items) < 2:
            QMessageBox.warning(
                self, "Isometric Stack",
                "Select at least 2 layers from the list above.",
            )
            return
        selected_names = [item.text() for item in selected_items]
        all_layers = QgsProject.instance().mapLayers()
        layers = [lyr for name, lyr in all_layers.items() if lyr.name() in selected_names]
        try:
            from ..layout.isometric_stacker import create_isometric_stack_layout
            layout = create_isometric_stack_layout(layers[:8])
            self._refresh_layout_combo()
            self.layout_combo.setCurrentText(layout.name())
            self._open_in_designer(layout)
            self.iface.messageBar().pushSuccess(
                "CartoLab", f"Isometric stack '{layout.name()}' created.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Layout Error", str(exc))

    def _on_bivariate_legend(self) -> None:
        layout = self._require_layout("Bivariate Legend")
        if layout is None:
            return
        colors = self._bivar_colors()
        try:
            from ..layout.legend_decorator import add_bivariate_legend_to_layout
            add_bivariate_legend_to_layout(
                layout,
                color_ll=colors[0], color_lh=colors[1],
                color_hl=colors[2], color_hh=colors[3],
                legend_type=self.bivar_legend_type_combo.currentData(),
            )
            self.iface.messageBar().pushSuccess(
                "CartoLab", f"Bivariate legend added to '{layout.name()}'.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Legend Error", str(exc))

    def _on_typography(self) -> None:
        layout = self._require_layout("Typography")
        if layout is None:
            return
        try:
            from ..layout.typography_engine import apply_typography_hierarchy
            apply_typography_hierarchy(layout)
            self.iface.messageBar().pushSuccess(
                "CartoLab", f"Typography applied to '{layout.name()}'.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Typography Error", str(exc))

    def _on_grid_style(self) -> None:
        layout = self._require_layout("Minimalist Grid")
        if layout is None:
            return
        try:
            from ..layout.grid_styler import apply_minimalist_grid
            if apply_minimalist_grid(layout):
                self.iface.messageBar().pushSuccess(
                    "CartoLab", f"Minimalist grid applied to '{layout.name()}'.",
                )
            else:
                QMessageBox.information(
                    self, "Minimalist Grid",
                    f"Layout '{layout.name()}' has no map frame to grid.",
                )
        except Exception as exc:
            QMessageBox.critical(self, "Grid Error", str(exc))

    # ── System health / refresh ──────────────────────────────────────

    def _refresh(self) -> None:
        layers = list(QgsProject.instance().mapLayers().values())
        reg = QgsApplication.processingRegistry()
        missing = [aid for aid in REQUIRED_IDS if reg.algorithmById(aid) is None]

        # repopulate layer lists for style/layout tabs
        if hasattr(self, "layer25d_combo"):
            self._refresh_25d_layers()
        if hasattr(self, "iso_layer_list"):
            self.iso_layer_list.clear()
            for layer in layers:
                self.iso_layer_list.addItem(layer.name())
        if hasattr(self, "layout_combo"):
            self._refresh_layout_combo()

        for card in self.card_widgets:
            is_ready = reg.algorithmById(card.algo_id) is not None
            card.status_lbl.setText("Ready" if is_ready else "Missing")
            card.status_lbl.setProperty("classChip", "ok" if is_ready else "warn")
            card.status_lbl.style().unpolish(card.status_lbl)
            card.status_lbl.style().polish(card.status_lbl)

        ready = len(missing) == 0
        status = "ALL READY" if ready else f"MISSING: {len(missing)}"
        self.status_chip.setText(f"System: {status}")
        if ready:
            self.status_chip.setStyleSheet(
                "color:#0f2d3a;background:#9fdfbf;border:1px solid #6fc995;border-radius:8px;padding:4px 10px;font-weight:700;"
            )
        else:
            self.status_chip.setStyleSheet(
                "color:#0f2d3a;background:#f8d37a;border:1px solid #e8bf58;border-radius:8px;padding:4px 10px;font-weight:700;"
            )

        # Build category health table
        cat_rows = []
        cat_ok_total = 0
        cat_total = 0
        for gname, ids in CATEGORY_GROUPS.items():
            found = sum(1 for aid in ids if reg.algorithmById(aid) is not None)
            total = len(ids)
            cat_ok_total += found
            cat_total += total
            pct = 100 * found / total if total else 0
            cat_rows.append((gname, found, total, pct))
        score = 100 * cat_ok_total / cat_total if cat_total else 0

        # Layer type counts for compatibility hints
        polygons = sum(1 for lyr in layers
                       if lyr.type() == QgsMapLayer.VectorLayer
                       and hasattr(lyr, 'geometryType')
                       and lyr.geometryType() == 2)
        rasters = sum(1 for lyr in layers
                      if lyr.type() == QgsMapLayer.RasterLayer)
        vectors = sum(1 for lyr in layers
                      if lyr.type() == QgsMapLayer.VectorLayer)

        compat_lines = []
        if polygons:
            compat_lines.append(f"{polygons} polygon -> 2.5D Styling, Cartogram, Bivariate, Classification, VbA")
        if rasters:
            compat_lines.append(f"{rasters} raster -> Ridge Map")
        if vectors and not polygons:
            compat_lines.append(f"{vectors} vector -> Classification, Bivariate, VbA")
        if not compat_lines:
            compat_lines.append("No layers loaded - load data to use algorithms.")

        self.overview.setHtml(
            "<h2>PlanX CartoLab</h2>"
            "<p><b>Advanced cartography suite for QGIS.</b> 2.5D building styling, bivariate choropleth, "
            "continuous-area cartograms, ridge maps, Value-by-Alpha uncertainty "
            "visualisation, and isometric layout stacking.</p>"
            f"<p><b>Loaded layers:</b> {len(layers)} "
            f"(polygon: {polygons}, raster: {rasters}, vector: {vectors})</p>"
            "<p><b>Compatibility:</b><br>&nbsp;&nbsp;"
            + "<br>&nbsp;&nbsp;".join(compat_lines)
            + "</p>"
            f"<p><b>Readiness:</b> {score:.0f}% ({cat_ok_total}/{cat_total} algorithms)</p>"
            + (f"<p><b>Missing:</b> {', '.join(missing)}</p>" if missing else "<p>All modules ready.</p>")
            + "<p><b>Get started:</b> Open the <b>Modules</b> tab, pick an algorithm, and click <b>Run</b>.</p>"
        )

        cat_table = [
            "<table style='border-collapse:collapse;width:100%'>",
            "<tr><th style='text-align:left;border:1px solid #d7e3e6;padding:6px'>Category</th>"
            "<th style='text-align:right;border:1px solid #d7e3e6;padding:6px'>Coverage</th>"
            "<th style='text-align:right;border:1px solid #d7e3e6;padding:6px'>Score</th></tr>",
        ]
        for gname, found, total, pct in cat_rows:
            cat_table.append(
                f"<tr><td style='border:1px solid #d7e3e6;padding:6px'>{gname}</td>"
                f"<td style='text-align:right;border:1px solid #d7e3e6;padding:6px'>{found}/{total}</td>"
                f"<td style='text-align:right;border:1px solid #d7e3e6;padding:6px'>{pct:.0f}%</td></tr>"
            )
        cat_table.append("</table>")

        readiness_title = "Ready to use" if not missing else "Needs attention"
        readiness_note = ("All CartoLab tools are available in QGIS." if not missing
                          else "Some tools are unavailable. Review Setup, then refresh the dashboard.")
        self.readiness.setHtml(
            f"<h2>{readiness_title}</h2>"
            f"<p>{readiness_note}</p>"
            f"<p><b>Available tools:</b> {len(REQUIRED_IDS) - len(missing)}/{len(REQUIRED_IDS)}</p>"
            f"<p><b>Readiness score:</b> {score:.0f}%</p>"
            f"<p><b>Unavailable tools:</b> {len(missing)}</p>"
            "<h3>Tool coverage</h3>"
            + "".join(cat_table)
        )

        self._refresh_runlog()
        self._filter_cards()

    # ── Dependency management ────────────────────────────────────────

    def _on_check_deps(self) -> None:
        from ..core.dependency_manager import get_status_report, CARTO_LAB_DEPS
        report = get_status_report(CARTO_LAB_DEPS, "CartoLab Dependencies")
        self.setup_status.setPlainText(report)

    def _on_install_deps(self) -> None:
        from ..core.dependency_manager import check_packages, install_packages, CARTO_LAB_DEPS
        _, missing_req, missing_opt = check_packages(CARTO_LAB_DEPS)
        all_missing = missing_req + missing_opt
        if not all_missing:
            QMessageBox.information(self, "CartoLab Setup", "All dependencies already installed.")
            return
        msg = (
            "The following packages will be installed via pip:\n\n"
            + "\n".join(f"  - {p}" for p in all_missing)
            + "\n\nQGIS restart recommended afterwards.\n\nContinue?"
        )
        if QMessageBox.question(
            self,
            "Install Dependencies",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.setup_status.setPlainText("Installing... this may take a few minutes.\n")
        ok, output = install_packages(all_missing)
        self.setup_status.append(output)
        if ok:
            self.setup_status.append("\nDone. Restart QGIS for changes to take effect.")
            self.iface.messageBar().pushSuccess("CartoLab", "Dependencies installed. Restart QGIS recommended.")
        else:
            self.setup_status.append("\nErrors occurred. See output above.")
            self.iface.messageBar().pushCritical("CartoLab", "Installation failed.")

    # ── Resize / keyboard ────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not hasattr(self, "cards_grid"):
            return
        desired = self._cards_column_count()
        if desired != self._current_card_columns:
            self._build_cards()
            self._refresh()

    def keyPressEvent(self, event) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_R:
                self._refresh()
                return
            if event.key() == Qt.Key.Key_F:
                self.search.setFocus()
                return
        super().keyPressEvent(event)
