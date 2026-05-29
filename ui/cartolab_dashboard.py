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

import processing
from qgis.PyQt.QtCore import QSettings, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QFont
from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
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
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from qgis.core import Qgis, QgsApplication, QgsProject, QgsMapLayer


IS_QGIS4 = int(getattr(Qgis, "QGIS_VERSION_INT", 0)) >= 40000
DASHBOARD_SIZE = (1100, 760) if IS_QGIS4 else (1180, 800)
DEFAULT_CARD_COLUMNS = 2 if IS_QGIS4 else 3

# ── Algorithm catalogue ─────────────────────────────────────────────

ALGO_GROUPS = [
    (
        "Classification",
        "#2f7aa8",
        [
            ("Geometric Interval Classification", "planx_cartolab:geometric_interval_classification",
             "Adaptive GIC, Head/Tail Breaks, Fisher-Jenks — optimal for skewed and heavy-tailed distributions."),
        ],
    ),
    (
        "Thematic Mapping",
        "#357a5f",
        [
            ("Bivariate Choropleth Map", "planx_cartolab:bivariate_choropleth",
             "N×N colour matrix from two numeric fields with bilinear interpolation."),
            ("Value-by-Alpha (VbA) Map", "planx_cartolab:value_by_alpha",
             "Encode reliability/uncertainty as opacity — unreliable data fades into background."),
            ("Ridge Map (Joyplot)", "planx_cartolab:ridge_map",
             "Raster-to-vector scanline deformation — Joy Division style wave profiles."),
        ],
    ),
    (
        "Cartogram",
        "#7359a8",
        [
            ("Continuous-Area Cartogram", "planx_cartolab:compute_cartogram",
             "Diffusion method (Gastner & Newman) — polygon areas proportional to field value."),
        ],
    ),
]

REQUIRED_IDS = [aid for _, _, items in ALGO_GROUPS for _, aid, _ in items]

CATEGORY_GROUPS = {
    "Classification Engine": [
        "planx_cartolab:geometric_interval_classification",
    ],
    "Thematic Mapping": [
        "planx_cartolab:bivariate_choropleth",
        "planx_cartolab:value_by_alpha",
        "planx_cartolab:ridge_map",
    ],
    "Cartogram Engine": [
        "planx_cartolab:compute_cartogram",
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

        self.setWindowTitle("PlanX CartoLab — Advanced Cartography Suite")
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
        sub = QLabel("Advanced cartography suite: bivariate, cartogram, ridge maps, Value-by-Alpha, isometric stacking | Ilieri haritacilik: bivariate, cartogram, ridge, VbA")
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
        self.search.setPlaceholderText("Filter modules / Modulleri filtrele...")
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
            ("Inspect Features (Radar Chart on Click)", self._on_activate_annotation),
            ("Run Bivariate Choropleth", lambda: self._run_algorithm("planx_cartolab:bivariate_choropleth", "Bivariate")),
            ("Run Geometric Interval Classification", lambda: self._run_algorithm("planx_cartolab:geometric_interval_classification", "GIC")),
            ("Run Cartogram", lambda: self._run_algorithm("planx_cartolab:compute_cartogram", "Cartogram")),
            ("Run Ridge Map", lambda: self._run_algorithm("planx_cartolab:ridge_map", "Ridge Map")),
            ("Run Value-by-Alpha", lambda: self._run_algorithm("planx_cartolab:value_by_alpha", "VbA")),
            ("Copy Project Diagnostics", self._on_copy_diagnostics),
        ]
        for label, fn in quick:
            b = QPushButton(label)
            b.clicked.connect(fn)
            ql.addWidget(b)
        ql.addStretch()
        self.tabs.addTab(qa_tab, "Quick Actions")

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

        # System Health tab
        self.readiness = QTextBrowser()
        self.tabs.addTab(self.readiness, "System Health")

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
            "PlanX CartoLab — Project Diagnostics\n"
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

    def _build_layout_tab(self) -> None:
        w = QWidget()
        lyt = QVBoxLayout(w)
        lyt.setContentsMargins(12, 12, 12, 12)

        gb = self._make_group("Print Layout Automation")
        gl = QVBoxLayout(gb)

        gl.addWidget(QLabel(
            "Create publication-ready print layouts with one click."))

        gl.addWidget(QLabel("Isometric stack layers (check to include):"))
        self.iso_layer_list = QListWidget()
        self.iso_layer_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )
        self.iso_layer_list.setMaximumHeight(120)
        gl.addWidget(self.iso_layer_list)

        btn_iso = QPushButton("Create Isometric Layer Stack")
        btn_iso.clicked.connect(self._on_isometric_stack)
        gl.addWidget(btn_iso)

        gl.addWidget(QLabel("Bivariate Legend Palette:"))
        self.bivar_palette_combo = QComboBox()
        self.bivar_palette_combo.addItem("Teal-Brown (Default)", "teal_brown")
        self.bivar_palette_combo.addItem("Purple-Green", "purple_green")
        self.bivar_palette_combo.addItem("Blue-Orange", "blue_orange")
        self.bivar_palette_combo.addItem("Pink-Green", "pink_green")
        gl.addWidget(self.bivar_palette_combo)

        btn_legend = QPushButton("Add Bivariate Legend to Layout")
        btn_legend.setToolTip("Add a colour-matrix legend to the first print layout")
        btn_legend.clicked.connect(self._on_bivariate_legend)
        gl.addWidget(btn_legend)

        btn_typo = QPushButton("Apply Swiss Typography")
        btn_typo.clicked.connect(self._on_typography)
        gl.addWidget(btn_typo)

        btn_grid = QPushButton("Add Minimalist Grid")
        btn_grid.clicked.connect(self._on_grid_style)
        gl.addWidget(btn_grid)

        lyt.addWidget(gb)
        lyt.addStretch()
        self.tabs.addTab(w, "Layout")

    def _on_isometric_stack(self) -> None:
        selected_items = self.iso_layer_list.selectedItems()
        if len(selected_items) < 2:
            QMessageBox.warning(self, "Isometric Stack",
                                "Select at least 2 layers from the list above.")
            return
        selected_names = [item.text() for item in selected_items]
        all_layers = QgsProject.instance().mapLayers()
        layers = [lyr for name, lyr in all_layers.items() if lyr.name() in selected_names]
        try:
            from ..layout.isometric_stacker import create_isometric_stack_layout
            create_isometric_stack_layout(layers[:8])
            self.iface.messageBar().pushSuccess("CartoLab",
                "Isometric layout created. Open Layout Manager to view.")
        except Exception as exc:
            QMessageBox.critical(self, "Layout Error", str(exc))

    def _on_bivariate_legend(self) -> None:
        project = QgsProject.instance()
        manager = project.layoutManager()
        layouts = manager.layouts()
        if not layouts:
            QMessageBox.information(self, "Bivariate Legend",
                "No print layouts found. Create one first in Project → Layout Manager.")
            return

        # Determine colors from selected preset
        preset = self.bivar_palette_combo.currentData()
        colors = {
            "teal_brown": ("#e8e8e8", "#5ab4ac", "#d8b365", "#8c510a"),
            "purple_green": ("#e8e8e8", "#7fbf7b", "#af8dc3", "#762a83"),
            "blue_orange": ("#e8e8e8", "#fdae61", "#abd9e9", "#2c7bb6"),
            "pink_green": ("#e8e8e8", "#a1d76a", "#e9a3c9", "#c51b7d"),
        }.get(preset, ("#e8e8e8", "#5ab4ac", "#d8b365", "#8c510a"))

        try:
            from ..layout.legend_decorator import add_bivariate_legend_to_layout
            add_bivariate_legend_to_layout(
                layouts[0],
                color_ll=colors[0],
                color_lh=colors[1],
                color_hl=colors[2],
                color_hh=colors[3]
            )
            self.iface.messageBar().pushSuccess("CartoLab",
                "Bivariate legend added to layout.")
        except Exception as exc:
            QMessageBox.critical(self, "Legend Error", str(exc))

    def _on_typography(self) -> None:
        project = QgsProject.instance()
        manager = project.layoutManager()
        count = 0
        try:
            from ..layout.typography_engine import apply_typography_hierarchy
            for layout in manager.layouts():
                apply_typography_hierarchy(layout)
                count += 1
            if count:
                self.iface.messageBar().pushSuccess("CartoLab",
                    f"Typography applied to {count} layout(s).")
            else:
                QMessageBox.information(self, "Typography",
                    "No print layouts found. Create one first in Project → Layout Manager.")
        except Exception as exc:
            QMessageBox.critical(self, "Typography Error", str(exc))

    def _on_grid_style(self) -> None:
        project = QgsProject.instance()
        manager = project.layoutManager()
        count = 0
        try:
            from ..layout.grid_styler import apply_minimalist_grid
            for layout in manager.layouts():
                apply_minimalist_grid(layout)
                count += 1
            if count:
                self.iface.messageBar().pushSuccess("CartoLab",
                    f"Minimalist grid added to {count} layout(s).")
            else:
                QMessageBox.information(self, "Grid Style",
                    "No print layouts found. Create one first.")
        except Exception as exc:
            QMessageBox.critical(self, "Grid Error", str(exc))

    # ── System health / refresh ──────────────────────────────────────

    def _refresh(self) -> None:
        layers = list(QgsProject.instance().mapLayers().values())
        reg = QgsApplication.processingRegistry()
        missing = [aid for aid in REQUIRED_IDS if reg.algorithmById(aid) is None]

        # repopulate layer list for layout tab
        if hasattr(self, "iso_layer_list"):
            self.iso_layer_list.clear()
            for layer in layers:
                self.iso_layer_list.addItem(layer.name())

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
            compat_lines.append(f"{polygons} polygon → Cartogram, Bivariate, Classification, VbA")
        if rasters:
            compat_lines.append(f"{rasters} raster → Ridge Map")
        if vectors and not polygons:
            compat_lines.append(f"{vectors} vector → Classification, Bivariate, VbA")
        if not compat_lines:
            compat_lines.append("No layers loaded — load data to use algorithms.")

        self.overview.setHtml(
            "<h2>PlanX CartoLab</h2>"
            "<p><b>Advanced cartography suite for QGIS.</b> Bivariate choropleth, "
            "continuous-area cartograms, ridge maps, Value-by-Alpha uncertainty "
            "visualisation, and isometric layout stacking.</p>"
            f"<p><b>Loaded layers:</b> {len(layers)} "
            f"(polygon: {polygons}, raster: {rasters}, vector: {vectors})</p>"
            "<p><b>Compatibility:</b><br>&nbsp;&nbsp;"
            + "<br>&nbsp;&nbsp;".join(compat_lines)
            + "</p>"
            f"<p><b>System health:</b> {score:.0f}% ({cat_ok_total}/{cat_total} algorithms)</p>"
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

        self.readiness.setHtml(
            "<h2>System Health</h2>"
            f"<p><b>Available algorithms:</b> {len(REQUIRED_IDS) - len(missing)}/{len(REQUIRED_IDS)}</p>"
            f"<p><b>Coverage score:</b> {score:.0f}%</p>"
            f"<p><b>Missing:</b> {', '.join(missing) if missing else 'None'}</p>"
            "<h3>Category Coverage</h3>"
            + "".join(cat_table)
        )

        self._refresh_runlog()
        self._filter_cards()

    # ── Dependency management ────────────────────────────────────────

    def _on_check_deps(self) -> None:
        from ..core.dependency_manager import check_packages, get_status_report, CARTO_LAB_DEPS
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
