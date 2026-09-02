import os
import json

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    QgsProject,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
)
from qgis.gui import QgsMapToolIdentifyFeature
from qgis.utils import iface
from qgis.PyQt.QtCore import QTimer


class TabWellhead:
    """Вкладка 'Устье'"""

    def __init__(self, dialog):
        self.tab = dialog

        self.crsLayerWellHead = None
        self.crsOutputWellHead = None
        self.layerWellHead = None
        self.tab.selectedWellHead = None

        self.wellHeadIdentifyTool = None

    def checkCoordinateMethod(self):
        """
        Проверяет, выбран ли способ получения координат.

        Возвращает:
            "map"   — координаты из карты
            "value" — координаты из атрибутов
            None    — способ не выбран
        """

        if self.tab.tabWellheadsCRSMapBtn.isChecked():
            return "map"

        if self.tab.tabWellheadsCRSValueBtn.isChecked():
            return "value"

        QMessageBox.warning(
            self.tab,
            "Внимание",
            "Выберите способ получения координат"
        )

        return None

    def selectWellHead(self):
        """
        Запускает выбор объекта wellhead на карте.

        Слой берётся из:
        tabSettingsWellheadMLCBox
        """
        # Проверяем способ получения координат
        coordinate_method = self.checkCoordinateMethod()

        if coordinate_method is None:
            return

        # Получаем выбранный слой из ComboBox
        layer = self.tab.tabSettingsWellheadMLCBox.currentLayer()

        if layer is None:
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "Сначала выберите слой wellhead в настройках."
            )
            return

        if not layer.isValid():
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "Выбранный слой недействителен."
            )
            return

        # Сохраняем выбранный слой
        self.layerWellHead = layer

        # CRS слоя
        self.crsLayerWellHead = layer.crs()
        self.crsOutputWellHead = layer.crs()

        # # Показываем CRS слоя
        # self.tab.mQgsProjectionSelectionWidgetWellHead.setCrs(
        #     self.crsLayerWellHead
        # )

        # Создаём инструмент выбора объекта
        self.wellHeadIdentifyTool = QgsMapToolIdentifyFeature(
            iface.mapCanvas()
        )

        self.wellHeadIdentifyTool.setLayer(layer)

        self.wellHeadIdentifyTool.featureIdentified.connect(
            self.wellHeadSelected
        )

        # Включаем инструмент на карте
        iface.mapCanvas().setMapTool(
            self.wellHeadIdentifyTool
        )

    def getCoordinatesSource(self):
        """
        Определяет способ получения координат позиции / устья.

        Возвращает:
            "map"   — координаты берутся из геометрии;
            "value" — координаты берутся из атрибутов north/east;
            None    — способ не выбран.
        """

        if self.tab.tabWellheadsCRSMapBtn.isChecked():
            return "map"

        if self.tab.tabWellheadsCRSValueBtn.isChecked():
            return "value"

        QMessageBox.warning(
            self.tab,
            "Внимание",
            "Не выбран способ получения координат позиции / устья.\n\n"
            "Выберите способ получения координат."
        )

        return None

    def wellHeadSelected(self, feature):
        """
        Обрабатывает выбранный объект wellhead.
        """

        # Сохраняем выбранный объект
        self.tab.selectedWellHead = feature

        layer = self.layerWellHead

        if layer is None:
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "Слой wellhead не определён."
            )
            return

        # Проверяем необходимые поля
        required_fields = {
            "name",
            "alt_ground",
            "alt_rotor",
            "lic",
        }

        layer_fields = {
            field.name()
            for field in layer.fields()
        }

        missing_fields = required_fields - layer_fields

        if missing_fields:
            QMessageBox.warning(
                self.tab,
                "Ошибка",
                "В слое wellhead отсутствуют поля:\n"
                + "\n".join(sorted(missing_fields))
            )
            return

        # Заполняем информацию об устье
        self.tab.txtWellHeadName.setText(
            str(feature["name"] or "")
        )

        self.tab.txtWellHeadGround.setText(
            str(feature["alt_ground"] or "")
        )

        self.tab.txtWellHeadRotor.setText(
            str(feature["alt_rotor"] or "")
        )

        self.tab.txtWellHeadLicense.setText(
            str(feature["lic"] or "")
        )

        # Проверяем альтитуды
        self.checkWellHeadAltitudes()

        # Проверяем геометрию
        if (
            feature.geometry() is None
            or feature.geometry().isEmpty()
        ):
            QMessageBox.warning(
                self.tab,
                "Ошибка",
                "У выбранного объекта отсутствует геометрия."
            )
            return

        # ==========================================
        # Проверяем способ получения координат
        # ==========================================

        coordinates_source = self.getCoordinatesSource()
        if coordinates_source is None:
            return

        # ==========================================
        # Получаем координаты
        # ==========================================

        if coordinates_source == "map":
            # ------------------------------------------
            # Координаты из геометрии объекта
            # ------------------------------------------
            if (feature.geometry() is None
                or feature.geometry().isEmpty()):
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    "У выбранного объекта отсутствует геометрия."
                )
                return

            point = feature.geometry().asPoint()

            east = point.x()
            north = point.y()

            # CRS
            crs_l = self.crsLayerWellHead
            # Показываем CRS слоя
            self.tab.mQgsProjectionSelectionWidgetWellHead.setCrs(
                self.crsLayerWellHead
            )

        elif coordinates_source == "value":
            # ------------------------------------------
            # Координаты из атрибутов
            # ------------------------------------------

            east = feature["east"]
            north = feature["north"]


            # Проверяем заполненность
            if east is None or north is None:
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    "В атрибутах выбранного объекта отсутствуют "
                    "координаты east/north."
                )
                return

            # Проверяем, что значения можно преобразовать в число
            try:
                east = float(east)
                north = float(north)

            except (TypeError, ValueError):
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    "Значения полей east и north должны быть числовыми."
                )
                return

            # ------------------------------------------
            # CRS из поля crs_text
            # ------------------------------------------

            crs_text = feature["crs_text"]

            if crs_text is None or str(crs_text).strip() == "":
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    "В атрибутах выбранного объекта не указана "
                    "система координат в поле crs_text."
                )
                return

            crs_text = str(crs_text).strip()

            # Например: 4326
            # if crs_text.isdigit():
            #     crs_l = QgsCoordinateReferenceSystem(
            #         f"EPSG:{crs_text}"
            #     )

            # Например: EPSG:4326
            # else:
            #     crs_l = QgsCoordinateReferenceSystem(
            #         crs_text
            #     )
            crs_l = QgsCoordinateReferenceSystem(crs_text)

            if not crs_l.isValid():
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    f"Не удалось определить систему координат:\n"
                    f"{crs_text}"
                )
                return

            self.crsLayerWellHead = crs_l
            self.tab.mQgsProjectionSelectionWidgetWellHead.setCrs(
                self.crsLayerWellHead
            )
            

        # CRS в которой планируем вести рассчет (выбор в comboBox)
        crs_t = self.crsOutputWellHead        

        # Преобразование координат
        transform = QgsCoordinateTransform(
            crs_l,
            crs_t,
            QgsProject.instance()
        )

        source_point = QgsPointXY(
            east,
            north
        )

        target_point = transform.transform(
            source_point
        )

        # Записываем координаты
        if self.crsOutputWellHead.isGeographic():

            self.tab.txtWellHeadNorth.setText(
                f"{target_point.y():.10f}"
            )

            self.tab.txtWellHeadEast.setText(
                f"{target_point.x():.10f}"
            )

        else:

            self.tab.txtWellHeadNorth.setText(
                f"{target_point.y():.3f}"
            )

            self.tab.txtWellHeadEast.setText(
                f"{target_point.x():.3f}"
            )

        # Выключаем инструмент выбора
        if self.wellHeadIdentifyTool is not None:
            iface.mapCanvas().unsetMapTool(
                self.wellHeadIdentifyTool
            )

        # Разрешаем изменение CRS
        self.tab.mQgsProjectionSelectionWidgetWellHead.setEnabled(
            True
        )

    def checkWellHeadAltitudes(self):
        """
        Проверяет наличие альтитуд земли и ротора.
        """

        if self.tab.txtWellHeadGround.text() == "":
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "В данных позиции / устья "
                "отсутствует альтитуда земли."
            )

            self.tab.txtWellHeadGround.setText("0.0")

            return False

        if self.tab.txtWellHeadRotor.text() == "":
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "В данных позиции / устья "
                "отсутствует альтитуда ротора."
            )

            self.tab.txtWellHeadRotor.setText("0.0")

            return False

        return True

    def wellHeadCrsChanged(self, crs):
        """
        Обрабатывает изменение системы координат.
        """

        self.crsLayerWellHead = self.crsOutputWellHead
        self.crsOutputWellHead = crs

        # Если координаты ещё не выбраны,
        # ничего не преобразуем
        if (
            self.tab.txtWellHeadNorth.text() == ""
            or self.tab.txtWellHeadEast.text() == ""
        ):
            return

        north = float(
            self.tab.txtWellHeadNorth.text()
        )

        east = float(
            self.tab.txtWellHeadEast.text()
        )

        # Создаём преобразование
        transform = QgsCoordinateTransform(
            self.crsLayerWellHead,
            self.crsOutputWellHead,
            QgsProject.instance()
        )

        source_point = QgsPointXY(
            east,
            north
        )

        target_point = transform.transform(
            source_point
        )

        # Записываем координаты
        if self.crsOutputWellHead.isGeographic():

            self.tab.txtWellHeadNorth.setText(
                f"{target_point.y():.10f}"
            )

            self.tab.txtWellHeadEast.setText(
                f"{target_point.x():.10f}"
            )

        else:

            self.tab.txtWellHeadNorth.setText(
                f"{target_point.y():.3f}"
            )

            self.tab.txtWellHeadEast.setText(
                f"{target_point.x():.3f}"
            )

        # Разрешаем вкладку инклинометрии
        self.tab.tabWidget.setTabEnabled(
            1,
            True
        )

    def getCurrentCrs(self):
        """
        Возвращает текущую систему координат
        для расчёта.
        """

        return self.crsOutputWellHead

    def inclTabActivate(self):
        if self.tab.selectedWellHead:
            incls_index = self.tab.tabWidget.indexOf(self.tab.tabIncls)
            self.tab.tabWidget.setTabEnabled(incls_index, True)
            self.tab.tabWidget.setCurrentWidget(self.tab.tabIncls)
        else:
            QMessageBox.warning(
                    self.tab,
                    "Внимание",
                    "Выберите позицию"
                )