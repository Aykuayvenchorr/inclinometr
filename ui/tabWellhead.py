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


class TabWellhead:
    """Вкладка 'Устье'"""

    def __init__(self, dialog):
        self.tab = dialog

        self.crsLayerWellHead = None
        self.crsOutputWellHead = None
        self.layerWellHead = None

        # Блокирую кнопку выбора системы координат
        self.tab.mQgsProjectionSelectionWidgetWellHead.setEnabled(False)

    def selectWellHead(self):
        layers = QgsProject.instance().mapLayersByName("Positions_WORK")
        layer = layers[0] if layers else None

        self.crsLayerWellHead = layer.crs()
        self.crsOutputWellHead = layer.crs()
        self.layerWellHead = layer
        # Укажу систему координат слоя позиции / устья в виджете выбора системы координат
        self.tab.mQgsProjectionSelectionWidgetWellHead.setCrs( self.crsLayerWellHead )

        if layer is None:
            QMessageBox.warning( self.tab, "Внимание", "Сначала выберите слой." )
            return

        self.wellHeadIdentifyTool = QgsMapToolIdentifyFeature( iface.mapCanvas() )
        self.wellHeadIdentifyTool.setLayer(layer)
        self.wellHeadIdentifyTool.featureIdentified.connect( self.wellHeadSelected )
        iface.mapCanvas().setMapTool( self.wellHeadIdentifyTool )

    def wellHeadSelected(self, feature):
        # Сохраняем выбранный объект
        self.tab.selectedWellHead = feature
        
        plugin_dir = os.path.dirname(os.path.dirname(__file__))
        settings_path = os.path.join(
            plugin_dir,
            "settings",
            "settings.json"
        )
        # print(f"plugin_dir: {plugin_dir}")
        # print(f"settings_path: {settings_path}")
        
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
            
    
            # QMessageBox.information(self, "Слой", "Это устья ГеоБД")
            self.tab.txtWellHeadName.setText(
                str(feature[settings["WellHead"]["Layers"]["Position_WORK"]["name"]])
            )
            self.tab.txtWellHeadGround.setText(
                str(feature[settings["WellHead"]["Layers"]["Position_WORK"]["ground"]])
            )
            self.tab.txtWellHeadRotor.setText(
                str(feature[settings["WellHead"]["Layers"]["Position_WORK"]["rotor"]])
            )
            self.tab.txtWellHeadLicense.setText(
                str(feature[settings["WellHead"]["Layers"]["Position_WORK"]["lic"]])
            )

            self.checkWellHeadAltitudes()

            north = feature.geometry().asPoint().y()
            east = feature.geometry().asPoint().x()
            
            crs_l = self.crsLayerWellHead
            crs_t = self.crsOutputWellHead
            
            # Создаем преобразование координат
            transform = QgsCoordinateTransform(crs_l, crs_t, QgsProject.instance())
            
            # Исходная точка
            sourcePoint = QgsPointXY(east, north)
    
            # Пересчет
            targetPoint = transform.transform(sourcePoint)
            
            if self.crsOutputWellHead.isGeographic():
                self.tab.txtWellHeadNorth.setText(f"{targetPoint.y():.10f}")
                self.tab.txtWellHeadEast.setText(f"{targetPoint.x():.10f}")
            else:
                self.tab.txtWellHeadNorth.setText(f"{targetPoint.y():.3f}")
                self.tab.txtWellHeadEast.setText(f"{targetPoint.x():.3f}")
            
        # Выключаем инструмент выбора
        iface.mapCanvas().unsetMapTool( self.tab.wellHeadIdentifyTool )

        # Разблокирую кнопку выбора системы координат после чтения позиции / устья
        self.tab.mQgsProjectionSelectionWidgetWellHead.setEnabled(True)

    def checkWellHeadAltitudes(self):
        """Проверка наличия альтитуд устья и грунта"""
        
        if self.tab.txtWellHeadGround.text() == '':
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "В данных позиции / устья отсутствует альтитуда земли."
            )
            self.tab.txtWellHeadGround.setText("0.0")
            return False

        if self.tab.txtWellHeadRotor.text() == '':
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "В данных позиции / устья отсутствует альтитуда ротора."
            )
            self.tab.txtWellHeadRotor.setText("0.0")
            return False

        return True

    def wellHeadCrsChanged(self, crs):
        """Смена системы координат устья"""
        
        self.crsLayerWellHead = self.crsOutputWellHead
        self.crsOutputWellHead = crs
        
        if self.tab.txtWellHeadNorth.text() != '' and self.tab.txtWellHeadEast.text() != '':
            north = float(self.tab.txtWellHeadNorth.text())
            east = float(self.tab.txtWellHeadEast.text())
            
            # Создаем преобразование координат
            transform = QgsCoordinateTransform(
                self.crsLayerWellHead,
                self.crsOutputWellHead,
                QgsProject.instance()
            )
            
            # Исходная точка
            sourcePoint = QgsPointXY(east, north)
    
            # Пересчет
            targetPoint = transform.transform(sourcePoint)
            
            if self.crsOutputWellHead.isGeographic():
                self.tab.txtWellHeadNorth.setText(f"{targetPoint.y():.10f}")
                self.tab.txtWellHeadEast.setText(f"{targetPoint.x():.10f}")
            else:
                self.tab.txtWellHeadNorth.setText(f"{targetPoint.y():.3f}")
                self.tab.txtWellHeadEast.setText(f"{targetPoint.x():.3f}")
                self.tab.tabWidget.setTabEnabled(1, True)

    def getCurrentCrs(self):
        """Текущая система координат для расчета"""
        return self.crsOutputWellHead