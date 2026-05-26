# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Advanced Disruptive Cartography Suite for QGIS.
Generative thematic mapping engine: bivariate rendering, Value-by-Alpha,
Ridge Maps, isometric layout stacking, cartogram distortion, and
HTML/Tailwind floating annotations.

classFactory returns the PlanXCartoLab instance.
"""


def classFactory(iface):
    from .main_plugin import PlanXCartoLab
    return PlanXCartoLab(iface)
