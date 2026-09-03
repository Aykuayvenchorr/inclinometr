from math import sqrt
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
from ..settings.TableColumns import TableColumns

IncCol = TableColumns.inclinometry


class TabTarget:

    def __init__(self, dialog):
        """
        Класс для работы со вкладкой Targets.
        """

        # ======================================================
        # СВОЙСТВА
        # ======================================================

        # Диалоговое окно
        self.tab = dialog

        # Выбранная цель
        # self.selectedTarget = None

        # Слой целей
        self.layerTarget = None

        # CRS исходного слоя
        self.crsLayerTarget = None

        # CRS, выбранная пользователем
        self.crsOutputTarget = None

        # CRS, в которой сейчас находятся координаты в таблице
        self.crsTableTarget = None

        self.crsCurrentTarget = None

        # Инструмент выбора
        self.targetIdentifyTool = None

        # ======================================================
        # МЕТОДЫ
        # ======================================================

        # Изменение системы координат
        self.tab.mQgsProjectionSelectionWidgetTarget.crsChanged.connect(self.targetCrsChanged)
        self.tab.btnCalculateDeviations.setEnabled(False)
        # Удалить цель из списка
        self.tab.btnRemoveTarget.clicked.connect(self.deleteTarget)
        self.tab.btnCalculateDeviations.clicked.connect(self.calculateDeviations)


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

        QMessageBox.warning(self.tab, "Внимание", "Не выбран способ получения координат.")

        return None

    # ==========================================================
    # ВКЛЮЧАЕМ ИНСТРУМЕНТ ВЫБОРА ЦЕЛИ НА КАРТЕ
    # ==========================================================

    def selectTarget(self):
        """
        Включает режим выбора целей на карте.
        """

        # Определяем переменную для слоя целей
        combo = self.tab.tabSettingsTargetsMLCBox
        self.layerTarget = combo.currentLayer()

        if self.layerTarget is None:
            QtWidgets.QMessageBox.warning(self.tab, "Внимание", "Сначала выберите слой целей.")
            return

        if not self.layerTarget.isValid():
            QtWidgets.QMessageBox.warning(self.tab, "Внимание", "Выбранный слой целей недействителен.")
            return

        # CRS слоя
        self.crsLayerTarget = self.layerTarget.crs()
        if self.crsLayerTarget is None or not self.crsLayerTarget.isValid():
            QMessageBox.warning(self.tab, "Ошибка", "Не определена система координат слоя целей.")
            return

        # Если текущая и целевая crs еще не установлены, тогда они примут crs слоя
        # if self.crsOutputTarget is None:
        #     self.crsOutputTarget = self.crsLayerTarget
        # if self.crsCurrentTarget is None:
        #     self.crsCurrentTarget = self.crsLayerTarget

        # Показываем CRS слоя
        # self.tab.mQgsProjectionSelectionWidgetTarget.setCrs(self.crsLayerTarget)

        # Если инструмент уже существует, повторно создавать его не нужно
        if self.targetIdentifyTool is None:
            self.targetIdentifyTool = QgsMapToolIdentifyFeature(iface.mapCanvas())
            self.targetIdentifyTool.setLayer(self.layerTarget)
            self.targetIdentifyTool.featureIdentified.connect(self.targetSelected)

        # Включаем инструмент выбора
        iface.mapCanvas().setMapTool(self.targetIdentifyTool)

    # ==========================================================
    # ПРОИЗОШЕЛ ВЫБОР ОБЪЕКТА
    # ==========================================================

    def targetSelected(self, feature):
        """
        Обрабатывает выбранный объект цели.
        """
        # Сохраняем в переменную выбранную цель
        # self.selectedTarget = feature

        # Добавляем выбранную цель в таблицу
        self.addTargetToTable(feature)

        # Инструмент выбора НЕ выключаем. Поэтому можно сразу выбрать следующую цель.

    # ==========================================================
    # ДОБАВЛЕНИЕ ЦЕЛИ В ТАБЛИЦУ
    # ==========================================================


    def addTargetToTable(self, feature):
        """
        Добавляет выбранную цель в tableTargets.

        Колонки:
        0 — id
        1 - stratum
        2 - name
        3 — north
        4 — east
        5 — tvd
        6 - tvdss
        7 - md
        8 - north_f
        9 - east_f
        10 - r_f

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

        # Если режим координат из геометрии
        if coordinates_source == "map":
            # Читаем геометрию выбранной цели
            geometry = feature.geometry()

            # Нахер пошли отсюда, если геометрия выбранной цели отсутствует
            if geometry is None or geometry.isEmpty():
                QMessageBox.warning(self.tab, "Ошибка", "У выбранной цели отсутствует геометрия.")
                return

            point = geometry.asPoint()
            self.crsCurrentTarget = self.crsLayerTarget

            east = point.x()
            north = point.y()

        # Если режим координат из атрибутов
        elif coordinates_source == "value":
            east = feature["east"]
            north = feature["north"]

            # Проверяем, что координаты в атрибутах есть
            if east is None or north is None:
                QMessageBox.warning(self.tab, "Ошибка", "В атрибутах выбранной цели отсутствуют координаты east/north.")
                return

            # Проверяем, что координаты, корректные числа
            try:
                east = float(east)
                north = float(north)

            except (TypeError, ValueError):
                QMessageBox.warning(self.tab, "Ошибка", "Значения полей east и north должны быть числовыми.")
                return

            # CRS из crs_text, проверка наличия записи о системе коодинат и ее корректность
            crs_text = feature["crs_text"]
            if crs_text is None or str(crs_text).strip() == "":
                QMessageBox.warning(self.tab, "Ошибка", "В атрибутах выбранной цели не указана система координат в поле crs_text.")
                return
            crs_text = str(crs_text).strip()
            self.crsCurrentTarget = QgsCoordinateReferenceSystem(crs_text)
            # if crs_text.isdigit():
            #     self.crsCurrentTarget = QgsCoordinateReferenceSystem(f"EPSG:{crs_text}")
            # else:
            #     self.crsCurrentTarget = QgsCoordinateReferenceSystem(crs_text)
            if not self.crsCurrentTarget.isValid():
                QMessageBox.warning(self.tab, "Ошибка", f"Не удалось определить систему координат:\n{crs_text}")
                return


        # Если в таблице уже есть цели
        if self.tab.tableTargets.rowCount() > 0:
            # Пересчитываем коодинаты в таблице
            self.transformCoordinatesInTable()

        self.tab.mQgsProjectionSelectionWidgetTarget.blockSignals(True)        
        try:
            self.tab.mQgsProjectionSelectionWidgetTarget.setCrs(self.crsCurrentTarget)
            self.pointAddToTable(QgsPointXY(east, north), feature)

        finally:
            self.tab.mQgsProjectionSelectionWidgetTarget.blockSignals(False)
        self.crsTableTarget = self.crsCurrentTarget
        QTimer.singleShot(0, self.tab.mQgsProjectionSelectionWidgetTarget.update)
        QTimer.singleShot(0, self.tab.mQgsProjectionSelectionWidgetTarget.repaint)
        self.tab.btnCalculateDeviations.setEnabled(True)

        """
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

        """


    def formatTargetCoordinates(self, point):
        """
        Форматирует координаты в зависимости от CRS.
        """

        if self.crsCurrentTarget.isGeographic():
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
        Пересчитывает координаты уже добавленных целей из предыдущей CRS в новую.
        """

        if crs is None or not crs.isValid():
            return
        
        # Если CRS ещё не была установлена
        # if self.crsCurrentTarget is None:
        #     self.crsOutputTarget = crs
        #     self.crsCurrentTarget = crs
        #     return

        # Если CRS не изменилась
        if crs == self.crsCurrentTarget:
            return

        # # Сохраняем старую CRS
        # oldCrs = self.crsOutputTarget

        # # Новая CRS
        # newCrs = crs

        # # Если таблица пустая — пересчитывать нечего
        # if self.tab.tableTargets.rowCount() == 0:
        #     self.crsOutputTarget = newCrs
        #     return

        # self.crsCurrentTarget = self.tab.mQgsProjectionSelectionWidgetTarget.crs()
        self.crsCurrentTarget = crs
        self.transformCoordinatesInTable()


        # # Пересчитываем все строки таблицы
        # for row in range(self.tab.tableTargets.rowCount()):
        #     northItem = self.tab.tableTargets.item(row, 1)
        #     eastItem = self.tab.tableTargets.item(row, 2)
        #     if northItem is None or eastItem is None:
        #         continue

        #     try:
        #         north = float(northItem.text())
        #         east = float(eastItem.text())
        #     except (TypeError, ValueError):
        #         continue

        #     # Записываем обратно
        #     northItem.setText(northText)
        #     eastItem.setText(eastText)

        # # Запоминаем CRS, в которой теперь находятся координаты таблицы
        # self.crsOutputTarget = newCrs


    def transformCoordinatesInTable(self):
        """Пересчет координат в таблице"""
        # QMessageBox.warning(self.tab, "Системы координат", f"Current {self.crsCurrentTarget},\nTable {self.crsTableTarget}")
        # Преобразование
        # print(self.crsTableTarget)
        # print(self.crsCurrentTarget)
        transform = QgsCoordinateTransform(self.crsTableTarget, self.crsCurrentTarget, QgsProject.instance())

        # Пересчитываем все строки таблицы
        for row in range(self.tab.tableTargets.rowCount()):
            northItem = self.tab.tableTargets.item(row, 3)
            eastItem = self.tab.tableTargets.item(row, 4)
            if northItem is None or eastItem is None:
                continue

            try:
                north = float(northItem.text())
                east = float(eastItem.text())
            except (TypeError, ValueError):
                continue

            targetPoint = transform.transform(QgsPointXY(east, north))
            northText, eastText = self.formatTargetCoordinates(targetPoint)

            # Записываем обратно
            northItem.setText(northText)
            eastItem.setText(eastText)

        # Новая система координат в таблице соответствует текущей
        self.crsTableTarget = self.crsCurrentTarget

    def pointAddToTable(self, point, feature):
        """Добавление точки в таблицу"""
        # Добавляем строку
        row = self.tab.tableTargets.rowCount()
        self.tab.tableTargets.insertRow(row)
        stratum = feature["stratum"]
        # ID
        self.tab.tableTargets.setItem(row, 0, QtWidgets.QTableWidgetItem(str(feature["id"])))
        self.tab.tableTargets.setItem(row, 1, QtWidgets.QTableWidgetItem("" if stratum is None else str(stratum)))
        self.tab.tableTargets.setItem(row, 2, QtWidgets.QTableWidgetItem(str(feature["name"])))
        # Добавление записи в таблицу
        northText, eastText = self.formatTargetCoordinates(point)
        self.tab.tableTargets.setItem(row, 3, QtWidgets.QTableWidgetItem(northText))
        self.tab.tableTargets.setItem(row, 4, QtWidgets.QTableWidgetItem(eastText))
        # TVD
        tvd = feature["tvd"]
        tvdss = feature["tvdss"]
        self.tab.tableTargets.setItem(row, 5, QtWidgets.QTableWidgetItem("" if tvd is None else str(tvd)))
        self.tab.tableTargets.setItem(row, 6, QtWidgets.QTableWidgetItem("" if tvdss is None else str(tvdss)))

        # Колонки:
        # 0 — id
        # 1 - stratum
        # 2 - name
        # 3 — north
        # 4 — east
        # 5 — tvd
        # 6 - tvdss
        # 7 - md
        # 8 - north_f
        # 9 - east_f
        # 10 - r_f
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
        if self.tab.tableTargets.rowCount() == 0:
            self.tab.btnCalculateDeviations.setEnabled(False)


    def calculateDeviations(self):
        if self.tab.mQgsProjectionSelectionWidgetTarget.crs() != self.tab.mQgsProjectionSelectionWidgetWellHead.crs():
            self.tab.mQgsProjectionSelectionWidgetTarget.blockSignals(True) 
            self.tab.mQgsProjectionSelectionWidgetTarget.setCrs(self.tab.mQgsProjectionSelectionWidgetWellHead.crs())
            self.targetCrsChanged(self.tab.mQgsProjectionSelectionWidgetTarget.crs())
            self.tab.mQgsProjectionSelectionWidgetTarget.blockSignals(False)
            self.crsTableTarget = self.crsCurrentTarget
            QTimer.singleShot(0, self.tab.mQgsProjectionSelectionWidgetTarget.update)
            QTimer.singleShot(0, self.tab.mQgsProjectionSelectionWidgetTarget.repaint)

        for rowTarget in range(self.tab.tableTargets.rowCount()):
            res = self.calculateCoordsTarget(rowTarget)
            if res:
                north_ft, east_ft = res
                # Фактический Север
                self.tab.tableTargets.setItem(rowTarget, 8, QtWidgets.QTableWidgetItem(f"{north_ft:.3f}"))
                # Фактический Восток
                self.tab.tableTargets.setItem(rowTarget, 9, QtWidgets.QTableWidgetItem(f"{east_ft:.3f}"))

                # Север цели
                north = float(self.tab.tableTargets.item(rowTarget, 3).text())
                # Восток цели
                east = float(self.tab.tableTargets.item(rowTarget, 4).text())
                # Отклонение
                deviation = self.calculateRfact(north, east, north_ft, east_ft)
                # Записываем отклонение
                self.tab.tableTargets.setItem(rowTarget, 10, QtWidgets.QTableWidgetItem(f"{deviation:.3f}"))


    def calculateCoordsTarget(self, rowTarget):
        """
        Вычисляет фактические координаты одной цели
        по таблице инклинометрии.

        rowTarget — номер строки цели в tableTargets.
        """

        tableTargets = self.tab.tableTargets
        tableInclin = self.tab.tableInclinometry

        # MD цели
        mdTargetItem = tableTargets.item(rowTarget, 7)

        if mdTargetItem is None:
            QMessageBox.warning(self.tab, "Внимание: введите MD цели в таблице целей.")
            return

        try:
            mdTarget = float(mdTargetItem.text())
        except (TypeError, ValueError):
            return

        # ----------------------------------------
        # Ищем MD больше или равный MD цели
        # ----------------------------------------

        rowAfter = None
        rowBefore = None
        # print('mdTarget', mdTarget)
        # print('tableInclin.rowCount()', tableInclin.rowCount())

        for row in range(tableInclin.rowCount()):
            mdItem = tableInclin.item(row, IncCol["MD"])
            md = float(mdItem.text())
            if md < mdTarget:
                continue
            if mdTarget == md:
                rowAfter = row
                rowBefore = row
                break
            # MD инклинометрии больше MD цели
            rowAfter = row
            rowBefore = row - 1
            # print('rowAfter', rowAfter, 'rowBefore', rowBefore)
            break

        # Не нашли точку с MD >= MD цели
        if rowAfter is None:
            QMessageBox.warning(self.tab, "Внимание", "MD цели больше, чем максимальный MD в таблице инклинометрии.")   
            return

        # Точное совпадение MD
        if rowBefore == rowAfter:

            north_ft = float(tableInclin.item(rowAfter, IncCol["NORTH"]).text())
            east_ft = float(tableInclin.item(rowAfter, IncCol["EAST"]).text())

        # Интерполяция между двумя точками
        else:
            mdBefore = float(tableInclin.item(rowBefore, IncCol["MD"]).text())
            northBefore = float(tableInclin.item(rowBefore, IncCol["NORTH"]).text())
            eastBefore = float(tableInclin.item(rowBefore, IncCol["EAST"]).text())

            mdAfter = float(tableInclin.item(rowAfter, IncCol["MD"]).text())
            northAfter = float(tableInclin.item(rowAfter, IncCol["NORTH"]).text())
            eastAfter = float(tableInclin.item(rowAfter, IncCol["EAST"]).text())

            k = ((mdTarget - mdBefore) / (mdAfter - mdBefore))
            north_ft = (northBefore + k * (northAfter - northBefore))
            east_ft = (eastBefore + k * (eastAfter - eastBefore))

        return north_ft, east_ft

    def calculateRfact(self, north_t, east_t, north_ft, east_ft):
        """
        Рассчитывает горизонтальное отклонение цели
        от фактической точки.

        north    — Север цели
        east     — Восток цели
        north_ft — фактический Север
        east_ft  — фактический Восток
        """

        deviation = sqrt((north_t - north_ft) ** 2 + (east_t - east_ft) ** 2)
        return deviation