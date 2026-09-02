import os
import json

from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QMessageBox

from qgis.core import (
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
    QgsCoordinateReferenceSystem,
)

from qgis.gui import QgsMapToolIdentifyFeature
from qgis.utils import iface
from qgis.PyQt.QtCore import QTimer



class TabTarget:

    def __init__(self, dialog):
        """
        Класс для работы со вкладкой Targets.
        """

        self.tab = dialog

        # ======================================================
        # ВЫБРАННАЯ ЦЕЛЬ
        # ======================================================

        self.selectedTarget = None

        # ======================================================
        # СЛОЙ ЦЕЛЕЙ
        # ======================================================

        self.layerTarget = None

        # CRS исходного слоя
        self.crsLayerTarget = None

        # CRS, выбранная пользователем
        self.crsOutputTarget = None

        # CRS, в которой сейчас находятся координаты
        # в таблице
        self.crsCurrentTarget = None

        # ======================================================
        # ИНСТРУМЕНТ ВЫБОРА
        # ======================================================

        self.targetIdentifyTool = None

        # ======================================================
        # CRS WIDGET
        # ======================================================

        self.tab.mQgsProjectionSelectionWidgetTarget.crsChanged.connect(
            self.targetCrsChanged
        )

        self.tab.btnRemoveTarget.clicked.connect(
            self.deleteTarget
        )
    def checkCoordinateMethod(self):
        """
        Проверяет, выбран ли способ получения координат.

        Возвращает:
            "map"   — координаты из карты
            "value" — координаты из атрибутов
            None    — способ не выбран
        """

        if self.tab.tabTargetsCRSMapBtn.isChecked():
            return "map"

        if self.tab.tabTargetsCRSValueBtn.isChecked():
            return "value"

        QMessageBox.warning(
            self.tab,
            "Внимание",
            "Выберите способ получения координат"
        )

        return None

    def getCoordinatesSource(self):
            """
            Определяет способ получения координат позиции / устья.
    
            Возвращает:
                "map"   — координаты берутся из геометрии;
                "value" — координаты берутся из атрибутов north/east;
                None    — способ не выбран.
            """
    
            if self.tab.tabTargetsCRSMapBtn.isChecked():
                return "map"
    
            if self.tab.tabTargetsCRSValueBtn.isChecked():
                return "value"
    
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "Не выбран способ получения координат."
            )
    
            return None

    # ==========================================================
    # ВЫБОР ЦЕЛИ НА КАРТЕ
    # ==========================================================

    def selectTarget(self):
        """
        Включает режим выбора целей на карте.
        """

        combo = self.tab.tabSettingsTargetsMLCBox

        layer = combo.currentLayer()

        if layer is None:
            QtWidgets.QMessageBox.warning(
                self.tab,
                "Внимание",
                "Сначала выберите слой целей."
            )
            return

        if not layer.isValid():
            QtWidgets.QMessageBox.warning(
                self.tab,
                "Внимание",
                "Выбранный слой целей недействителен."
            )
            return

        # Сохраняем слой
        self.layerTarget = layer

        # CRS слоя
        self.crsLayerTarget = layer.crs()
        self.crsOutputTarget = layer.crs()
        self.crsCurrentTarget = layer.crs()

        # Показываем CRS слоя
        # self.tab.mQgsProjectionSelectionWidgetTarget.setCrs(
        #     self.crsLayerTarget
        # )

        # Если инструмент уже существует,
        # повторно создавать его не нужно
        if self.targetIdentifyTool is None:

            self.targetIdentifyTool = QgsMapToolIdentifyFeature(
                iface.mapCanvas()
            )

            self.targetIdentifyTool.setLayer(
                self.layerTarget
            )

            self.targetIdentifyTool.featureIdentified.connect(
                self.targetSelected
            )

        # Включаем инструмент выбора
        iface.mapCanvas().setMapTool(
            self.targetIdentifyTool
        )

    # ==========================================================
    # ВЫБОР ОБЪЕКТА
    # ==========================================================

    def targetSelected(self, feature):
        """
        Обрабатывает выбранный объект цели.
        """

        self.selectedTarget = feature

        # Добавляем выбранную цель в таблицу
        self.addTargetToTable(feature)

        # Инструмент выбора НЕ выключаем.
        # Поэтому можно сразу выбрать следующую цель.

    # ==========================================================
    # ДОБАВЛЕНИЕ ЦЕЛИ В ТАБЛИЦУ
    # ==========================================================
    def addTargetToTable(self, feature):
        """
        Добавляет выбранную цель в tableTargets.

        Колонки:
        0 — id
        1 — north
        2 — east
        3 — depth

        Источник координат определяется radio button:
        - map   — геометрия объекта;
        - value — поля east/north + crs_text.
        """

        # ======================================================
        # Проверяем способ получения координат
        # ======================================================

        coordinates_source = self.getCoordinatesSource()

        if coordinates_source is None:
            return

        # ======================================================
        # Получаем координаты
        # ======================================================

        if coordinates_source == "map":

            # ----------------------------------------------
            # Координаты из геометрии
            # ----------------------------------------------

            geometry = feature.geometry()

            if geometry is None or geometry.isEmpty():
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    "У выбранной цели отсутствует геометрия."
                )
                return

            point = geometry.asPoint()

            east = point.x()
            north = point.y()

            # CRS геометрии слоя
            crs_source = self.crsLayerTarget

            if crs_source is None or not crs_source.isValid():
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    "Не определена система координат слоя целей."
                )
                return

        elif coordinates_source == "value":

            # ----------------------------------------------
            # Координаты из атрибутов
            # ----------------------------------------------

            east = feature["east"]
            north = feature["north"]

            if east is None or north is None:
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    "В атрибутах выбранной цели отсутствуют "
                    "координаты east/north."
                )
                return

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

            # ----------------------------------------------
            # CRS из crs_text
            # ----------------------------------------------

            crs_text = feature["crs_text"]

            if crs_text is None or str(crs_text).strip() == "":
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    "В атрибутах выбранной цели не указана "
                    "система координат в поле crs_text."
                )
                return

            crs_text = str(crs_text).strip()

            if crs_text.isdigit():
                crs_source = QgsCoordinateReferenceSystem(
                    f"EPSG:{crs_text}"
                )
            else:
                crs_source = QgsCoordinateReferenceSystem(
                    crs_text
                )

            if not crs_source.isValid():
                QMessageBox.warning(
                    self.tab,
                    "Ошибка",
                    f"Не удалось определить систему координат:\n"
                    f"{crs_text}"
                )
                return

        # ======================================================
        # CRS, в которую переводим координаты
        # ======================================================

        if self.crsOutputTarget is None:
            self.crsOutputTarget = crs_source

        crs_output = self.crsOutputTarget

        # ======================================================
        # Устанавливаем CRS в ComboBox
        #
        # Только если это первая выбранная цель.
        #
        # При последующих целях не меняем CRS пользователя.
        # ======================================================

        if self.tab.tableTargets.rowCount() == 0:

            self.tab.mQgsProjectionSelectionWidgetTarget.blockSignals(
                True
            )

            try:
                self.tab.mQgsProjectionSelectionWidgetTarget.setCrs(
                    crs_source
                )
            finally:
                self.tab.mQgsProjectionSelectionWidgetTarget.blockSignals(
                    False
                )

            self.crsOutputTarget = crs_source
            crs_output = crs_source

            QTimer.singleShot(
                0,
                self.tab.mQgsProjectionSelectionWidgetTarget.update
            )

            QTimer.singleShot(
                0,
                self.tab.mQgsProjectionSelectionWidgetTarget.repaint
            )

        # ======================================================
        # Преобразуем координаты
        # ======================================================

        transform = QgsCoordinateTransform(
            crs_source,
            crs_output,
            QgsProject.instance()
        )

        try:

            target_point = transform.transform(
                QgsPointXY(
                    east,
                    north
                )
            )

        except Exception as e:

            QMessageBox.warning(
                self.tab,
                "Ошибка преобразования",
                f"Не удалось преобразовать координаты:\n{e}"
            )
            return

        # ======================================================
        # Добавляем строку
        # ======================================================

        row = self.tab.tableTargets.rowCount()

        self.tab.tableTargets.insertRow(row)

        # ======================================================
        # ID
        # ======================================================

        self.tab.tableTargets.setItem(
            row,
            0,
            QtWidgets.QTableWidgetItem(
                str(feature["id"])
            )
        )

        # ======================================================
        # Координаты
        # ======================================================

        northText, eastText = self.formatTargetCoordinates(
            target_point
        )

        self.tab.tableTargets.setItem(
            row,
            1,
            QtWidgets.QTableWidgetItem(
                northText
            )
        )

        self.tab.tableTargets.setItem(
            row,
            2,
            QtWidgets.QTableWidgetItem(
                eastText
            )
        )

        # ======================================================
        # Depth
        # ======================================================

        depth = feature["depth"]

        self.tab.tableTargets.setItem(
            row,
            3,
            QtWidgets.QTableWidgetItem(
                "" if depth is None else str(depth)
            )
        )

        # ======================================================
        # Запоминаем CRS координат таблицы
        # ======================================================

        self.crsCurrentTarget = crs_output
    # def addTargetToTable(self, feature):
    #     """
    #     Добавляет выбранную цель в tableTargets.

    #     Колонки:

    #     0 — id
    #     1 — north
    #     2 — east
    #     3 — depth
    #     """

    #     if self.crsLayerTarget is None:
    #         QtWidgets.QMessageBox.warning(
    #             self.tab,
    #             "Внимание",
    #             "Не определена CRS слоя цели."
    #         )
    #         return

    #     if self.crsOutputTarget is None:
    #         self.crsOutputTarget = self.crsLayerTarget

    #     # ------------------------------------------------------
    #     # Новая строка
    #     # ------------------------------------------------------

    #     row = self.tab.tableTargets.rowCount()

    #     self.tab.tableTargets.insertRow(row)

    #     # ------------------------------------------------------
    #     # ID
    #     # ------------------------------------------------------

    #     self.tab.tableTargets.setItem(
    #         row,
    #         0,
    #         QtWidgets.QTableWidgetItem(
    #             str(feature["id"])
    #         )
    #     )

    #     # ------------------------------------------------------
    #     # Геометрия
    #     # ------------------------------------------------------

    #     geometry = feature.geometry()

    #     if geometry is None or geometry.isEmpty():

    #         QtWidgets.QMessageBox.warning(
    #             self.tab,
    #             "Внимание",
    #             "У выбранной цели отсутствует геометрия."
    #         )

    #         self.tab.tableTargets.removeRow(row)

    #         return

    #     # ==========================================
    #     # Проверяем способ получения координат
    #     # ==========================================

    #     coordinates_source = self.getCoordinatesSource()
    #     if coordinates_source is None:
    #         return

    #     # ==========================================
    #     # Получаем координаты
    #     # ==========================================
        
    #     if coordinates_source == "map":
    #         # ------------------------------------------
    #         # Координаты из геометрии объекта
    #         # ------------------------------------------
    #         if (feature.geometry() is None
    #             or feature.geometry().isEmpty()):
    #             QMessageBox.warning(
    #                 self.tab,
    #                 "Ошибка",
    #                 "У выбранного объекта отсутствует геометрия."
    #             )
    #             return

    #         point = feature.geometry().asPoint()

    #         east = point.x()
    #         north = point.y()

    #         # CRS
    #         crs_l = self.crsLayerTarget
    #         self.tab.mQgsProjectionSelectionWidgetTarget.setCrs(
    #             self.crsLayerTarget
    #         )

    #     elif coordinates_source == "value":
    #         # ------------------------------------------
    #         # Координаты из атрибутов
    #         # ------------------------------------------

    #         east = feature["east"]
    #         north = feature["north"]


    #         # Проверяем заполненность
    #         if east is None or north is None:
    #             QMessageBox.warning(
    #                 self.tab,
    #                 "Ошибка",
    #                 "В атрибутах выбранного объекта отсутствуют "
    #                 "координаты east/north."
    #             )
    #             return

    #         # Проверяем, что значения можно преобразовать в число
    #         try:
    #             east = float(east)
    #             north = float(north)

    #         except (TypeError, ValueError):
    #             QMessageBox.warning(
    #                 self.tab,
    #                 "Ошибка",
    #                 "Значения полей east и north должны быть числовыми."
    #             )
    #             return
    #         # ------------------------------------------
    #         # CRS из поля crs_text
    #         # ------------------------------------------

    #         crs_text = feature["crs_text"]

    #         if crs_text is None or str(crs_text).strip() == "":
    #             QMessageBox.warning(
    #                 self.tab,
    #                 "Ошибка",
    #                 "В атрибутах выбранного объекта не указана "
    #                 "система координат в поле crs_text."
    #             )
    #             return

    #         crs_text = str(crs_text).strip()
    #         crs_l = QgsCoordinateReferenceSystem(crs_text)
            
    #         if not crs_l.isValid():
    #             QMessageBox.warning(
    #                 self.tab,
    #                 "Ошибка",
    #                 f"Не удалось определить систему координат:\n"
    #                 f"{crs_text}"
    #             )
    #             return

    #         self.crsLayerTarget = crs_l
    #         self.tab.mQgsProjectionSelectionWidgetTarget.setCrs(
    #             self.crsLayerTarget
    #         )
            

    #     # ------------------------------------------------------
    #     # Преобразование из CRS слоя в выходную CRS
    #     # ------------------------------------------------------

    #     transform = QgsCoordinateTransform(
    #         self.crsLayerTarget,
    #         self.crsOutputTarget,
    #         QgsProject.instance()
    #     )

    #     targetPoint = transform.transform(
    #         QgsPointXY(east, north)
    #     )

    #     # ------------------------------------------------------
    #     # Форматирование
    #     # ------------------------------------------------------

    #     northText, eastText = self.formatTargetCoordinates(
    #         targetPoint
    #     )

    #     # ------------------------------------------------------
    #     # Записываем координаты
    #     # ------------------------------------------------------

    #     self.tab.tableTargets.setItem(
    #         row,
    #         1,
    #         QtWidgets.QTableWidgetItem(
    #             northText
    #         )
    #     )

    #     self.tab.tableTargets.setItem(
    #         row,
    #         2,
    #         QtWidgets.QTableWidgetItem(
    #             eastText
    #         )
    #     )

    #     # ------------------------------------------------------
    #     # Depth
    #     # ------------------------------------------------------

    #     self.tab.tableTargets.setItem(
    #         row,
    #         3,
    #         QtWidgets.QTableWidgetItem(
    #             str(feature["depth"])
    #         )
    #     )

    #     # ------------------------------------------------------
    #     # Теперь координаты таблицы находятся в этой CRS
    #     # ------------------------------------------------------

    #     self.crsCurrentTarget = self.crsOutputTarget

    # ==========================================================
    # ФОРМАТИРОВАНИЕ КООРДИНАТ
    # ==========================================================

    def formatTargetCoordinates(self, point):
        """
        Форматирует координаты в зависимости от CRS.
        """

        if self.crsOutputTarget.isGeographic():

            northText = f"{point.y():.10f}"
            eastText = f"{point.x():.10f}"

        else:

            northText = f"{point.y():.3f}"
            eastText = f"{point.x():.3f}"

        return northText, eastText

    # ==========================================================
    # ИЗМЕНЕНИЕ CRS
    # ==========================================================

    def targetCrsChanged(self, crs):
        """
        Обрабатывает изменение CRS пользователем.

        Пересчитывает координаты уже добавленных целей
        из предыдущей CRS в новую.
        """

        if crs is None or not crs.isValid():
            return

        # ------------------------------------------------------
        # Если CRS ещё не была установлена
        # ------------------------------------------------------

        if self.crsCurrentTarget is None:

            self.crsOutputTarget = crs
            self.crsCurrentTarget = crs

            return

        # ------------------------------------------------------
        # Если CRS не изменилась
        # ------------------------------------------------------

        if crs == self.crsCurrentTarget:
            return

        # ------------------------------------------------------
        # Сохраняем старую CRS
        # ------------------------------------------------------

        oldCrs = self.crsCurrentTarget

        # Новая CRS
        newCrs = crs

        # ------------------------------------------------------
        # Обновляем текущую CRS
        # ------------------------------------------------------

        self.crsOutputTarget = newCrs

        # ------------------------------------------------------
        # Если таблица пустая — пересчитывать нечего
        # ------------------------------------------------------

        if self.tab.tableTargets.rowCount() == 0:

            self.crsCurrentTarget = newCrs

            return

        # ------------------------------------------------------
        # Создаём преобразование
        # ------------------------------------------------------

        transform = QgsCoordinateTransform(
            oldCrs,
            newCrs,
            QgsProject.instance()
        )

        # ------------------------------------------------------
        # Пересчитываем все строки таблицы
        # ------------------------------------------------------

        for row in range(
            self.tab.tableTargets.rowCount()
        ):

            northItem = self.tab.tableTargets.item(
                row,
                1
            )

            eastItem = self.tab.tableTargets.item(
                row,
                2
            )

            if northItem is None or eastItem is None:
                continue

            try:
                north = float(
                    northItem.text()
                )

                east = float(
                    eastItem.text()
                )

            except (TypeError, ValueError):
                continue

            # --------------------------------------------------
            # Преобразование
            # --------------------------------------------------

            sourcePoint = QgsPointXY(
                east,
                north
            )

            targetPoint = transform.transform(
                sourcePoint
            )

            # --------------------------------------------------
            # Форматирование
            # --------------------------------------------------

            if newCrs.isGeographic():

                northText = f"{targetPoint.y():.10f}"
                eastText = f"{targetPoint.x():.10f}"

            else:

                northText = f"{targetPoint.y():.3f}"
                eastText = f"{targetPoint.x():.3f}"

            # --------------------------------------------------
            # Записываем обратно
            # --------------------------------------------------

            northItem.setText(
                northText
            )

            eastItem.setText(
                eastText
            )

        # ------------------------------------------------------
        # Запоминаем CRS, в которой теперь находятся
        # координаты таблицы
        # ------------------------------------------------------

        self.crsCurrentTarget = newCrs

    # ==========================================================
    # ОЧИСТКА
    # ==========================================================

    def clearSelectedTarget(self):
        """
        Сбрасывает текущую выбранную цель.
        """

        self.selectedTarget = None

        if self.targetIdentifyTool is not None:

            iface.mapCanvas().unsetMapTool(
                self.targetIdentifyTool
            )

            self.targetIdentifyTool = None

    def deleteTarget(self):
        """
        Удаляет выбранную цель из таблицы tableTargets.
        """

        table = self.tab.tableTargets

        row = table.currentRow()

        if row < 0:
            QtWidgets.QMessageBox.warning(
                self.tab,
                "Внимание",
                "Выберите цель в таблице для удаления."
            )
            return

        # Удаляем строку
        table.removeRow(row)

        # Сбрасываем выбранную цель
        self.selectedTarget = None