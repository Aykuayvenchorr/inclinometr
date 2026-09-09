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
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
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

        # Если CRS не изменилась
        if crs == self.crsCurrentTarget:
            return

        self.crsCurrentTarget = crs
        self.transformCoordinatesInTable()


    def transformCoordinatesInTable(self):
        """Пересчет координат в таблице"""
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
        self.layerTarget.updateFields()
        self.layerTarget.updateExtents()
        self.layerTarget.triggerRepaint()
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
                north_ft, east_ft, tvdss_ft = res
                # Фактический Север
                self.tab.tableTargets.setItem(rowTarget, 8, QtWidgets.QTableWidgetItem(f"{north_ft:.3f}"))
                # Фактический Восток
                self.tab.tableTargets.setItem(rowTarget, 9, QtWidgets.QTableWidgetItem(f"{east_ft:.3f}"))
                # Фактический TVDSS
                self.tab.tableTargets.setItem(rowTarget, 11, QtWidgets.QTableWidgetItem(f"{tvdss_ft:.3f}"))

                # Север цели
                north = float(self.tab.tableTargets.item(rowTarget, 3).text())
                # Восток цели
                east = float(self.tab.tableTargets.item(rowTarget, 4).text())
                # Отклонение
                deviation = self.calculateRfact(north, east, north_ft, east_ft)
                # Записываем отклонение
                self.tab.tableTargets.setItem(rowTarget, 10, QtWidgets.QTableWidgetItem(f"{deviation:.3f}"))
                self.addActualTargetToLayer(rowTarget, north_ft, east_ft, tvdss_ft)


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
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "Введите MD цели в таблице целей."
            )            
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
            tvdss_ft = float(tableInclin.item(rowAfter, IncCol["TVDSS"]).text())

        # Интерполяция между двумя точками
        else:
            mdBefore = float(tableInclin.item(rowBefore, IncCol["MD"]).text())
            northBefore = float(tableInclin.item(rowBefore, IncCol["NORTH"]).text())
            eastBefore = float(tableInclin.item(rowBefore, IncCol["EAST"]).text())
            tvdssBefore = float(tableInclin.item(rowBefore, IncCol["TVDSS"]).text())


            mdAfter = float(tableInclin.item(rowAfter, IncCol["MD"]).text())
            northAfter = float(tableInclin.item(rowAfter, IncCol["NORTH"]).text())
            eastAfter = float(tableInclin.item(rowAfter, IncCol["EAST"]).text())
            tvdssAfter = float(tableInclin.item(rowAfter, IncCol["TVDSS"]).text())

            k = ((mdTarget - mdBefore) / (mdAfter - mdBefore))
            north_ft = (northBefore + k * (northAfter - northBefore))
            east_ft = (eastBefore + k * (eastAfter - eastBefore))
            tvdss_ft = (tvdssBefore + k * (tvdssAfter - tvdssBefore))

        return north_ft, east_ft, tvdss_ft

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

    def addActualTargetToLayer(self, source_row, north_f, east_f, tvdss_f):
        """
        Добавляет рассчитанную фактическую цель
        в слой welltarget на основе проектной цели.

        ID исходной цели берётся из столбца 0 tableTargets.

        Типы:
            0 - Кровля проект -> 2 - Кровля факт
            1 - Подошва проект -> 3 - Подошва факт
        """

        tableTargets = self.tab.tableTargets
        layer_target = self.tab.tabSettingsTargetsMLCBox.currentLayer()
        layer_target.updateFields()
        layer_target.updateExtents()

        # ==========================================
        # 1. Получаем ID цели из tableTargets
        # ==========================================

        id_item = tableTargets.item(source_row, 0)

        if id_item is None or not id_item.text().strip():
            return

        try:
            target_id = int(id_item.text())
        except (TypeError, ValueError):
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "Некорректный ID цели."
            )
            return

        # ==========================================
        # 2. Проверяем слой welltarget
        # ==========================================

        if layer_target is None or not layer_target.isValid():
            QMessageBox.warning(
                self.tab,
                "Внимание",
                "Слой целей welltarget не найден."
            )
            return

        # ==========================================
        # 3. Ищем исходную цель по ID
        # ==========================================

        request = QgsFeatureRequest().setFilterExpression(
            f'"id" = {target_id} AND "type" IN (0, 1)'
        )

        source_target = next(
            layer_target.getFeatures(request),
            None
        )

        if source_target is None:
            QMessageBox.warning(
                self.tab,
                "Внимание",
                f"Цель с ID {target_id} не найдена "
                f"в слое welltarget."
            )
            return

        # ==========================================
        # 4. Получаем type из атрибутов объекта
        # ==========================================

        source_type = source_target["type"]

        if source_type is None:
            QMessageBox.warning(
                self.tab,
                "Внимание",
                f"У цели с ID {target_id} "
                f"не указан тип."
            )
            return

        try:
            source_type = int(source_type)
        except (TypeError, ValueError):
            QMessageBox.warning(
                self.tab,
                "Внимание",
                f"Некорректный тип цели с ID {target_id}."
            )
            return

        # ==========================================
        # 5. Проектный тип -> фактический тип
        # ==========================================

        project_to_fact_type = {
            0: 2,  # Кровля проект -> Кровля факт
            1: 3,  # Подошва проект -> Подошва факт
        }

        fact_type = project_to_fact_type.get(source_type)

        # Если исходная цель уже фактическая
        if fact_type is None:
            return

        # ==========================================
        # 6. Создаём новую feature
        # ==========================================

        actualTarget = QgsFeature(layer_target.fields())

        # Копируем все атрибуты исходной цели
        # кроме id и type
        for field in layer_target.fields():

            field_name = field.name()

            if field_name in ("fid", "id", "type"):
                continue

            actualTarget[field_name] = source_target[field_name]

        # ==========================================
        # 7. Получаем новый ID
        # ==========================================

        # max_id = 0

        # for feature in layer_target.getFeatures():

        #     try:
        #         feature_id = int(feature["id"])

        #         if feature_id > max_id:
        #             max_id = feature_id

        #     except (TypeError, ValueError):
        #         continue

        # actualTarget["id"] = max_id + 1
        actualTarget["id"] = (
        self.tab.tabSettings.idCounter.getNextId(
                "welltarget"
            )
        )

        # ==========================================
        # 8. Устанавливаем фактический тип
        # ==========================================

        actualTarget["type"] = fact_type

        # ==========================================
        # 9. Записываем рассчитанные координаты
        # ==========================================

        actualTarget["north"] = north_f
        actualTarget["east"] = east_f
        actualTarget["tvdss"] = tvdss_f

        # ==========================================
        # 10. Получаем MD из tableTargets
        # ==========================================

        # md_item = tableTargets.item(source_row, 7)

        # if md_item is not None and md_item.text().strip():

        #     try:
        #         md = float(
        #             md_item.text().replace(",", ".")
        #         )

        #         actualTarget["depth"] = md

        #     except (TypeError, ValueError):
        #         pass

        # ==========================================
        # 11. Формируем геометрию фактической цели
        # ==========================================

        point = QgsPointXY(
            east_f,
            north_f
        )

        # CRS, в котором были рассчитаны координаты
        crs_calculation = self.crsCurrentTarget

        # CRS слоя welltarget
        crs_layer = layer_target.crs()

        if crs_calculation.isValid() and crs_layer.isValid():

            if crs_calculation != crs_layer:

                transform = QgsCoordinateTransform(
                    crs_calculation,
                    crs_layer,
                    QgsProject.instance()
                )

                point = transform.transform(point)

        actualTarget.setGeometry(
            QgsGeometry.fromPointXY(point)
        )

        # ==========================================
        # 12. Добавляем фактическую цель в welltarget
        # ==========================================

        layer_target.startEditing()

        success = layer_target.addFeatures(
            [actualTarget]
        )

        if not success:

            provider_error = layer_target.dataProvider().error().message()

            print("========================================")
            print("ОШИБКА ДОБАВЛЕНИЯ ФАКТИЧЕСКОЙ ЦЕЛИ")
            print("Слой:", layer_target.name())
            print("ID:", actualTarget["id"])
            print("type:", actualTarget["type"])
            print("north:", actualTarget["north"])
            print("east:", actualTarget["east"])
            print("tvdss:", actualTarget["tvdss"])
            print("Геометрия:", actualTarget.geometry().asWkt())
            print("Ошибка provider:", provider_error)
            print("========================================")

            layer_target.rollBack()

            QMessageBox.warning(
                self.tab,
                "Ошибка",
                "Не удалось добавить фактическую цель "
                "в слой welltarget.\n\n"
                f"Ошибка:\n{provider_error}"
            )

            return False

        # ==========================================
        # 13. Сохраняем изменения
        # ==========================================

        if not layer_target.commitChanges():

            QMessageBox.warning(
                self.tab,
                "Ошибка",
                "Фактическая цель была добавлена, "
                "но не удалось сохранить изменения "
                "в слое welltarget."
            )

            return

        # ==========================================
        # 14. Обновляем слой
        # ==========================================

        layer_target.triggerRepaint()
