import os
import json

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsCoordinateTransform,
    QgsProject,
    QgsPointXY,
    QgsVectorLayer,
    QgsField,
    QgsFields,
    QgsFeature
)
from qgis.utils import iface
from qgis.gui import QgsMapToolIdentifyFeature

class TabInclinometry:
    """Вкладка 'Инклинометрия'"""

    def __init__(self, dialog):
        self.tab = dialog