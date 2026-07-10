# -*- coding: utf-8 -*-
"""Shared helpUrl() mixin for all PlanX CartoLab Processing algorithms."""


class CartoLabHelpMixin:
    """Mixin providing a default helpUrl() pointing to the repo's Module Catalog.

    Individual algorithms MAY override this to supply a more specific anchor
    (e.g. ``#bivariate-choropleth-map``).
    """

    _HELP_BASE = "https://github.com/YusufEminoglu/planx_cartolab#module-catalog"

    def helpUrl(self) -> str:
        return self._HELP_BASE
