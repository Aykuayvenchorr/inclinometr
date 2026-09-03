from math import atan, sin, cos, sqrt, atan2, radians, acos, asin, tan, degrees

from .excel_reader import ExcelReader
from qgis.PyQt import QtWidgets
from qgis.core import QgsPoint

class Mathematics:

    def __init__(self, dialog):
        self.dialog = dialog
        self.excel = ExcelReader(dialog)
        # ==========================================================
        # tableTargets
        # ==========================================================

        self.COL_TARGET_ID =    0
        self.COL_TARGET_NORTH = 1
        self.COL_TARGET_EAST =  2
        self.COL_TARGET_TVD =   3

        # ==========================================================
        # tableInclinometry
        # ==========================================================

        self.COL_INCLIN_DEPTH =         0
        self.COL_INCLIN_ZENITH =        1
        self.COL_INCLIN_AZIMUTH =       2
        self.COL_INCLIN_DIRECTIONAL =   3
        self.COL_INCLIN_DATA =          4 
        self.COL_INCLIN_NORTH =         5
        self.COL_INCLIN_EAST =          6
        self.COL_INCLIN_TVD =           7

        # ==========================================================
        # tableCalculationDeviation
        # ==========================================================

        self.COL_RESULT_TVD =       0
        self.COL_RESULT_ID =        1
        self.COL_RESULT_NORTH =     2
        self.COL_RESULT_EAST =      3
        self.COL_RESULT_DEVIATION = 4

        self.c = QgsPoint(77, 550, 17)
        # print(f"Point: {self.c.x()}, {self.c.y()}, {self.c.z()}")
    from math import sin, cos, tan, atan, radians, degrees


    def convergence_meridians(lat_deg, lon_deg, lon0_deg, a, b):
        """
        Расчет сближения меридианов по формуле Морозова.

        Параметры
        ----------
        lat_deg : float
            Геодезическая широта, градусы.

        lon_deg : float
            Геодезическая долгота точки, градусы.

        lon0_deg : float
            Долгота осевого меридиана зоны, градусы.

        a : float
            Большая полуось эллипсоида, м.

        b : float
            Малая полуось эллипсоида, м.

        Возвращает
        ----------
        float
            Сближение меридианов, градусы.
        """

        # Перевод координат в радианы
        B = radians(lat_deg)
        L = radians(lon_deg)
        L0 = radians(lon0_deg)

        # Разность долгот
        l = L - L0

        # Первый эксцентриситет²
        #e2 = (a**2 - b**2) / (a**2)

        # Второй эксцентриситет²
        e2_second = (a**2 - b**2) / (b**2)

        # η²
        eta2 = e2_second * cos(B) ** 2

        # Формула Морозова
        tg_gamma = (sin(B) * tan(l) + (eta2 * sin(B) * cos(B)**2 * l**3* (1+ (2/3)*eta2 + cos(B)**2 * l**2)))

        gamma = atan(tg_gamma)

        return degrees(gamma)
    
    def loadInclinometry(self):

        filename = self.excel.open_file()

        if filename is None:
            return

        data = self.excel.read_inclinometry(filename)

        print("Прочитано:")
        print(data)
        data = self.excel.read_inclinometry(filename)
        self.excel.fill_table()
        
    def calculateInclinometry(self):
        """
        Расчет траектории методом минимальной кривизны.
        Формулы используются согласно методическому пособию.
        """

        # Таблица инклинометрии
        data = self.excel.data
    
        # Если таблица пустая — ничего не считаем
        if len(data) == 0:
            return
        # Угол сближения меридианов (градусы)
        try:
            convergence = float(self.dialog.txtConvergenceMeridian.text())
        except ValueError:
            convergence = 0.0
        # Таблица результатов
        table = self.dialog.tableInclinometry
        # ==========================================================
        # Координаты устья из интерфейса
        # ==========================================================
        
        north = float(self.dialog.txtWellHeadNorth.text())
        east = float(self.dialog.txtWellHeadEast.text())
    
        # Начальная вертикальная отметка
        tvd = 0.0
    
        # ==========================================================
        # Результирующая таблица
        # ==========================================================
    
        result = []
    
        # ==========================================================
        # Первая точка
        # ==========================================================
    
        first = {}
    
        first["depth"] = data[0]["depth"]
        first["zenith"] = data[0]["zenith"]
        first["azimuth"] = data[0]["azimuth"]
        first["directional"] = first["azimuth"] + convergence
        # чтобы угол был в диапазоне 0...360
        first["directional"] %= 360
        first["north"] = north
        first["east"] = east
        first["tvd"] = tvd
    
        result.append(first)
        
        # Записываем первую строку в таблицу
        table.setItem(
            0,
            self.COL_INCLIN_NORTH,
            QtWidgets.QTableWidgetItem(f"{north:.3f}")
        )
        
        table.setItem(
            0,
            self.COL_INCLIN_EAST,
            QtWidgets.QTableWidgetItem(f"{east:.3f}")
        )
        
        table.setItem(
            0,
            self.COL_INCLIN_TVD,
            QtWidgets.QTableWidgetItem(f"{tvd:.3f}")
        )
        table.setItem(
            0,
            self.COL_INCLIN_DIRECTIONAL,
            QtWidgets.QTableWidgetItem(f"{first['directional']:.3f}")
        )
        # ==========================================================
        # Расчет остальных точек
        # ==========================================================
    
        for i in range(1, len(data)):
    
            # -------------------------------
            # Верхняя точка интервала
            # -------------------------------
    
            p1 = data[i - 1]
    
            # -------------------------------
            # Нижняя точка интервала
            # -------------------------------
    
            p2 = data[i]
    
            # -------------------------------
            # Длина интервала
            # -------------------------------
    
            dMD = p2["depth"] - p1["depth"]
    
            # -------------------------------
            # Углы переводим в радианы
            # -------------------------------
    
            I1 = radians(p1["zenith"])
            I2 = radians(p2["zenith"])
    
            A1 = radians(p1["azimuth"])
            A2 = radians(p2["azimuth"])

            dir1 = radians((p1["azimuth"] + convergence) % 360)
            dir2 = radians((p2["azimuth"] + convergence) % 360)
    
            # =====================================================
            # Угол β между двумя измерениями
            # =====================================================
    
            cos_beta = cos(I2-I1) - sin(I1) * sin(I2) * (1-cos(dir2-dir1))

    
            # Из-за ошибок округления значение может выйти
            # немного больше 1 или меньше -1.
            cos_beta = max(-1.0, min(1.0, cos_beta))
    
            beta = acos(cos_beta)
    
            # =====================================================
            # Условие если угол β = 0 (радиус кривизны бесконечен) то используется метод средних углов
            # Иначе используется метод наименьшей кривизны
            # =====================================================
            if abs(beta) < 1e-10:
                # =====================================================
                # Приращения координат методом средних углов
                # =====================================================
                dNorth = dMD * sin((I1+I2) /2) * cos((dir1+dir2) /2)
                dEast = dMD * sin((I1+I2) /2) * sin((dir1+dir2) /2)
                dTVD = dMD * cos((I1+I2) /2)
            else:
                RF = (2 / beta) * tan(beta / 2)
    
                # =====================================================
                # Приращения координат методом наименьшей кривизны
                # =====================================================
        
                dNorth = (dMD / 2) * (sin(I1) * cos(dir1)+ sin(I2) * cos(dir2)) * RF
                dEast  = (dMD / 2) * (sin(I1) * sin(dir1)+ sin(I2) * sin(dir2)) * RF
                dTVD   = (dMD / 2  * (cos(I1) + cos(I2)) * RF )
    
            # =====================================================
            # Новые координаты
            # =====================================================
    
            north += dNorth
            east += dEast
            tvd += dTVD

            # =====================================================
            # Запись строки результата
            # =====================================================
    
            newRow = {}
    
            newRow["depth"] = p2["depth"]
            newRow["zenith"] = p2["zenith"]
            newRow["azimuth"] = p2["azimuth"]
    
            newRow["north"] = north
            newRow["east"] = east
            newRow["tvd"] = tvd
    
            result.append(newRow)

            # Записываем рассчитанные координаты в таблицу
            table.setItem(
                i,
                self.COL_INCLIN_NORTH,
                QtWidgets.QTableWidgetItem(f"{north:.3f}")
            )
            
            table.setItem(
                i,
                self.COL_INCLIN_EAST,
                QtWidgets.QTableWidgetItem(f"{east:.3f}")
            )
            
            table.setItem(
                i,
                self.COL_INCLIN_TVD,
                QtWidgets.QTableWidgetItem(f"{tvd:.3f}")
            )
            table.setItem(
                i,
                self.COL_INCLIN_DIRECTIONAL,
                QtWidgets.QTableWidgetItem(f"{degrees(dir2):.3f}")
            )

        # ==========================================================
        # Вывод результата
        # ==========================================================
    
        # print()

        # print(
        #     "Depth\tZenith\tAzimuth\tNorth\tEast\tTVD"
        # )

        # for row in result:

        #     print(
        #         f"{row['depth']:8.2f}\t"
        #         f"{row['zenith']:7.2f}\t"
        #         f"{row['azimuth']:8.2f}\t"
        #         f"{row['north']:12.3f}\t"
        #         f"{row['east']:12.3f}\t"
        #         f"{row['tvd']:12.3f}"
        #     )



    def calculationDeviation(self):
        """
        Расчет координат траектории на глубине целей.
        """
        # ==========================
        # Номера столбцов
        # ==========================

        sourceTable = self.dialog.tableTargets
        resultTable = self.dialog.tableCalculationDeviation

        # Очистить старые результаты
        resultTable.setRowCount(0)

        # Количество целей
        rows = sourceTable.rowCount()

        for row in range(rows):

            # Добавляем новую строку
            resultTable.insertRow(row)

            # ID цели (0 столбец таблицы целей)
            idItem = sourceTable.item(row, self.COL_TARGET_ID)

            # TVD (3 столбец таблицы целей)
            tvdItem = sourceTable.item(row, self.COL_TARGET_TVD)

            if tvdItem:
                resultTable.setItem(
                    row,
                    self.COL_RESULT_TVD,
                    QtWidgets.QTableWidgetItem(tvdItem.text())
                )

            if idItem:
                resultTable.setItem(
                    row,
                    self.COL_RESULT_ID,
                    QtWidgets.QTableWidgetItem(idItem.text())
                )

        # первые строки таблицы записаны , начинаем расчет координат и отклонений

        tableTargets = self.dialog.tableCalculationDeviation
        tableInclin = self.dialog.tableInclinometry

        # Проходим по всем целям
        for rowTarget in range(tableTargets.rowCount()):

            # Глубина цели
            targetTVD = float(
                tableTargets.item(rowTarget, self.COL_RESULT_TVD).text()
            )

            # ----------------------------------------
            # Ищем две соседние строки
            # ----------------------------------------

            for row in range(tableInclin.rowCount() - 1):

                tvd1 = float(tableInclin.item(row, self.COL_INCLIN_TVD).text())
                tvd2 = float(tableInclin.item(row + 1, self.COL_INCLIN_TVD).text())

                if tvd1 <= targetTVD <= tvd2:

                    north1 = float(tableInclin.item(row, self.COL_INCLIN_NORTH).text())
                    east1  = float(tableInclin.item(row, self.COL_INCLIN_EAST).text())

                    north2 = float(tableInclin.item(row + 1, self.COL_INCLIN_NORTH).text())
                    east2  = float(tableInclin.item(row + 1, self.COL_INCLIN_EAST).text())

                    # ----------------------------------------
                    # Коэффициент интерполяции
                    # ----------------------------------------

                    k = (targetTVD - tvd1) / (tvd2 - tvd1)

                    # ----------------------------------------
                    # Интерполяция координат
                    # ----------------------------------------

                    north = north1 + k * (north2 - north1)
                    east  = east1 + k * (east2 - east1)

                    targetNorth = float(
                        sourceTable.item(rowTarget, self.COL_TARGET_NORTH).text()
                    )

                    targetEast = float(
                        sourceTable.item(rowTarget, self.COL_TARGET_EAST).text()
                    )
                    deviation = sqrt(
                        (targetNorth - north) ** 2 +
                        (targetEast - east) ** 2
                    )
                    # ----------------------------------------
                    # Запись в таблицу
                    # ----------------------------------------

                    tableTargets.setItem(
                        rowTarget,
                        self.COL_RESULT_NORTH,
                        QtWidgets.QTableWidgetItem(f"{north:.3f}")
                    )

                    tableTargets.setItem(
                        rowTarget,
                        self.COL_RESULT_EAST,
                        QtWidgets.QTableWidgetItem(f"{east:.3f}")
                    )
                    tableTargets.setItem(
                        rowTarget,
                        self.COL_RESULT_DEVIATION,
                        QtWidgets.QTableWidgetItem(f"{deviation:.3f}")
                    )
                    break

if __name__ == "__main__":
    gg = Mathematics(None)