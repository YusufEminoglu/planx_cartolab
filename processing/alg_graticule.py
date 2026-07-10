# -*- coding: utf-8 -*-
"""Graticule / Reference Grid — Processing algorithm."""
from __future__ import annotations

from qgis.core import (
    QgsFeature, QgsFeatureSink, QgsField, QgsFields, QgsGeometry, QgsPointXY,
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterExtent, QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber, QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from ..core.graticule import nice_interval, graticule_lines
from ._help_mixin import CartoLabHelpMixin


class GraticuleAlgorithm(QgsProcessingAlgorithm, CartoLabHelpMixin):
    EXTENT = "EXTENT"
    X_INTERVAL = "X_INTERVAL"
    Y_INTERVAL = "Y_INTERVAL"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        return "graticule_grid"

    def displayName(self) -> str:
        return "Graticule / Reference Grid"

    def group(self) -> str:
        return "Map Reference"

    def groupId(self) -> str:
        return "map_reference"

    def createInstance(self):
        return GraticuleAlgorithm()

    def shortHelpString(self) -> str:
        return (
            "Generate a line layer of meridians and parallels across an extent, on "
            "'nice' round coordinate intervals. Each line carries its orientation, "
            "constant coordinate and a formatted label (label it with the 'label' "
            "field).\n\n"
            "Leave an interval at 0 to auto-pick a round step (~8 lines across the "
            "extent). The output uses the extent's CRS — set the extent in the CRS "
            "you want the grid drawn in."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, "Grid extent"))
        self.addParameter(QgsProcessingParameterNumber(
            self.X_INTERVAL, "Vertical line (meridian) interval, 0 = auto",
            type=QgsProcessingParameterNumber.Double, defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.Y_INTERVAL, "Horizontal line (parallel) interval, 0 = auto",
            type=QgsProcessingParameterNumber.Double, defaultValue=0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Graticule output", QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback):
        rect = self.parameterAsExtent(parameters, self.EXTENT, context)
        crs = self.parameterAsExtentCrs(parameters, self.EXTENT, context)
        if rect.isEmpty():
            raise QgsProcessingException("The supplied extent is empty.")
        x_interval = self.parameterAsDouble(parameters, self.X_INTERVAL, context)
        y_interval = self.parameterAsDouble(parameters, self.Y_INTERVAL, context)

        xmin, ymin = rect.xMinimum(), rect.yMinimum()
        xmax, ymax = rect.xMaximum(), rect.yMaximum()
        x_step = x_interval if x_interval > 0 else nice_interval(xmax - xmin)
        y_step = y_interval if y_interval > 0 else nice_interval(ymax - ymin)

        out_fields = QgsFields()
        out_fields.append(QgsField("orientation", QVariant.String))
        out_fields.append(QgsField("coord", QVariant.Double))
        out_fields.append(QgsField("label", QVariant.String))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, QgsWkbTypes.LineString, crs,
        )

        lines = graticule_lines(xmin, ymin, xmax, ymax, x_step, y_step)
        for ln in lines:
            if feedback.isCanceled():
                break
            pts = [QgsPointXY(x, y) for (x, y) in ln["points"]]
            nf = QgsFeature(out_fields)
            nf.setGeometry(QgsGeometry.fromPolylineXY(pts))
            nf.setAttributes([ln["orientation"], ln["coord"], ln["label"]])
            sink.addFeature(nf, QgsFeatureSink.FastInsert)

        feedback.pushInfo(
            f"Graticule: {len(lines)} lines (x step {x_step:g}, y step {y_step:g})."
        )
        return {self.OUTPUT: dest_id}
