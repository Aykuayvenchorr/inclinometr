import os
import json
from datetime import datetime

from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    QgsCoordinateReferenceSystem,
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
from ..settings.TableColumns import TableColumns
from ..modules.excel_reader import ExcelReader
from ..modules.geodezy import Geodezy
from ..modules.inclinometry import Inclinometry

IncCol = TableColumns.inclinometry


class TabInclinometry:
    """Вкладка 'Инклинометрия'"""

    def __init__(self, dialog):
        self.tab = dialog
        self.north_p = 0.0
        self.east_p = 0.0
        self.north_g = 0.0
        self.east_g = 0.0
        self.alt = 0.0
        self.gamma = 0.0
        self.rows = 0
        self.inclinometry = Inclinometry()

        # Загрузка инклинометрии из Excel
        self.excel = ExcelReader()
        self.tab.btnLoadInclinometry.clicked.connect(self.load_inclinometry)

        # Настройка выпадающего списка выбора типа азимута
        self.tab.cmbAzimuthType.addItems([
                "Магнитный",
                "Истинный",
                "Дирекционный угол"
            ])
        
        # По умолчанию магнитный
        self.tab.cmbAzimuthType.setCurrentIndex(0)
        self.AzimuthType = self.tab.cmbAzimuthType.currentIndex()
        # Переключение типа азимута
        self.tab.cmbAzimuthType.currentIndexChanged.connect(self.onAzimuthTypeChanged)
        # Кнопка расчета инклинометрии
        self.tab.btnCalculateInclinometry.clicked.connect(self.calculateInclinometryAndDeviation)

    

    def load_inclinometry(self):
        """Загрузка данных инклинометрии из Excel"""

        # Открытие диалога выбора файла
        filename = self.excel.open_file()
        if not filename:
            return

        # Чтение данных из Excel
        self.excel.read_inclinometry(filename)

        # Отображение данных в таблице
        self.tab.tableInclinometry.setRowCount(len(self.excel.data))
        self.crs = self.tab.mQgsProjectionSelectionWidgetWellHead.crs()
        
        # Цикл чтения данных из Excel и заполнения таблицы
        for row, item in enumerate(self.excel.data):
            self.tab.tableInclinometry.setItem(row, IncCol["DEPTH"], QtWidgets.QTableWidgetItem(str(item["depth"])))
            self.tab.tableInclinometry.setItem(row, IncCol["ZENITH"], QtWidgets.QTableWidgetItem(str(item["zenith"])))
            self.tab.tableInclinometry.setItem(row, IncCol["AZIMUTH"], QtWidgets.QTableWidgetItem(str(item["azimuth"])))
            self.rows = row + 1
            if row == 0:
                self.tab.tableInclinometry.setItem(row, IncCol["DATE"], QtWidgets.QTableWidgetItem(str(datetime.now().strftime("%Y-%m-%d"))))
                self.tab.tableInclinometry.setItem(row, IncCol["NORTH"], QtWidgets.QTableWidgetItem(self.tab.txtWellHeadNorth.text()))
                self.north_p = float(self.tab.txtWellHeadNorth.text())
                self.tab.tableInclinometry.setItem(row, IncCol["EAST"], QtWidgets.QTableWidgetItem(self.tab.txtWellHeadEast.text()))
                self.east_p = float(self.tab.txtWellHeadEast.text())
                self.tab.tableInclinometry.setItem(row, IncCol["ALTITUDE"], QtWidgets.QTableWidgetItem(self.tab.txtWellHeadRotor.text()))
                self.alt = float(self.tab.txtWellHeadRotor.text())


            # # Исходная точка
            # sourcePoint = QgsPointXY(self.east_p, self.north_p)
            # # Пересчет
            # geographicPoint = self.transform.transform(sourcePoint)
            # if self.AzimuthType == 0:  # Магнитный                    
            #     self.gamma = Geodezy.convergence_meridians(
            #         Geodezy.deg2rad(geographicPoint.y()),
            #         Geodezy.deg2rad(geographicPoint.x()),
            #         Geodezy.getZoneNumberFromEast(self.east_p)
            #     )
            # self.tab.tableInclinometry.setItem(row, IncCol["CONVERGENCE"], QtWidgets.QTableWidgetItem(str(Geodezy.rad2deg(self.gamma))))


    # Меняет переменную AzimuthType в зависимости от выбранного типа азимута в выпадающем списке
    def onAzimuthTypeChanged(self, index):
        self.AzimuthType = index

    def getPointPulkovo42(self, north: float, east: float) -> QgsPointXY:
        """
        Получение точки в системе координат Pulkovo 1942 по координатам в текущей системе координат

        Параметры
        ----------
        north : float
            Координата Север, м
        east : float
            Координата Восток, м
        
        Возвращает
        ----------
        QgsPointXY
            Точка в системе координат Pulkovo 1942
        """
        targetCrs = QgsCoordinateReferenceSystem("EPSG:4284") # Pulkovo 1942
        transform = QgsCoordinateTransform(
            self.crs,
            targetCrs,
            QgsProject.instance()
        )
        # Исходная точка
        sourcePoint = QgsPointXY(east, north)
        # Пересчет
        geographicPoint = transform.transform(sourcePoint)
        return geographicPoint

    def getPointWGS84(self, north: float, east: float) -> QgsPointXY:
        """
        Получение точки в системе координат WGS 84 по координатам в текущей системе координат

        Параметры
        ----------
        north : float
            Координата Север, м
        east : float
            Координата Восток, м
        
        Возвращает
        ----------
        QgsPointXY
            Точка в системе координат WGS 84
        """
        targetCrs = QgsCoordinateReferenceSystem("EPSG:4326") # WGS 84
        transform = QgsCoordinateTransform(
            self.crs,
            targetCrs,
            QgsProject.instance()
        )
        # Исходная точка
        sourcePoint = QgsPointXY(east, north)
        # Пересчет
        geographicPoint = transform.transform(sourcePoint)
        return geographicPoint

    def calculateInclinometry(
            self,
            zenith_error,
            magnetic_azimuth_error,
            azimuth_error,
            north_col,
            east_col,
            alt_col,
            switch # если 1 - будет выводить в таблицу промежуточные результаты и координаты (основная траектория)
                   # если 0 - будет выводить в таблицу только координаты (крайние траектории)
    ):
        # Актуальная дата для расчета магнитного склонения
        dt: datetime = datetime.now()
        magnetic_declination: float = 0.0
        gamma: float = 0.0
        north_p: float = float(self.tab.tableInclinometry.item(0, IncCol["NORTH"]).text())
        east_p: float = float(self.tab.tableInclinometry.item(0, IncCol["EAST"]).text())
        alt: float = float(self.tab.tableInclinometry.item(0, IncCol["ALTITUDE"]).text())

        depth_prev: float = 0.0
        zenith_prev: float = 0.0
        azimuth_grid_prev: float = 0.0

        for i in range(self.rows):
            depth = float(self.tab.tableInclinometry.item(i, IncCol["DEPTH"]).text())
            zenith = Geodezy.deg2rad(float(self.tab.tableInclinometry.item(i, IncCol["ZENITH"]).text())) + zenith_error
            azimuth = Geodezy.deg2rad(float(self.tab.tableInclinometry.item(i, IncCol["AZIMUTH"]).text())) 
            if self.tab.tableInclinometry.item(0, IncCol["DATE"]).text() != "":
                dt = datetime.strptime(self.tab.tableInclinometry.item(0, IncCol["DATE"]).text(), "%Y-%m-%d")

            # Магнитное склонение
            if self.AzimuthType < 1:
                pointWGS84 = self.getPointWGS84(north_p, east_p)
                magnetic_declination = Geodezy.magnetic_declination(
                    Geodezy.deg2rad(pointWGS84.y()),
                    Geodezy.deg2rad(pointWGS84.x()),
                    alt,
                    dt
                )[0]
            

            # Сближение меридианов
            if self.AzimuthType < 2:
                pointPulkovo42 = self.getPointPulkovo42(north_p, east_p)
                gamma = Geodezy.convergence_meridians(
                    Geodezy.deg2rad(pointPulkovo42.y()),
                    Geodezy.deg2rad(pointPulkovo42.x()),
                    Geodezy.getZoneNumberFromEast(east_p)
                )
            

            # Дирекционный угол
            azimuth_grid = azimuth + magnetic_declination + gamma + azimuth_error + magnetic_azimuth_error
            

            # РАСЧЕТ
            if i > 0:
                dl = depth - depth_prev
                dNorth, dEast, dZ = self.inclinometry.inclinometry_step(
                    dl,
                    azimuth_grid_prev,
                    azimuth_grid,
                    zenith_prev,
                    zenith
                )
                if switch == 1:
                    self.tab.tableInclinometry.setItem(i, IncCol["DELTA_NORTH"], QtWidgets.QTableWidgetItem(str(dNorth)))
                    self.tab.tableInclinometry.setItem(i, IncCol["DELTA_EAST"], QtWidgets.QTableWidgetItem(str(dEast)))
                    self.tab.tableInclinometry.setItem(i, IncCol["DELTA_Z"], QtWidgets.QTableWidgetItem(str(dZ)))
                north_p += dNorth
                east_p += dEast
                alt -= dZ
                self.tab.tableInclinometry.setItem(i, north_col, QtWidgets.QTableWidgetItem(str(north_p)))
                self.tab.tableInclinometry.setItem(i, east_col, QtWidgets.QTableWidgetItem(str(east_p)))
                self.tab.tableInclinometry.setItem(i, alt_col, QtWidgets.QTableWidgetItem(str(alt)))

                depth_prev = depth
                zenith_prev = zenith
                azimuth_grid_prev = azimuth_grid

            #Вывод промежуточных результатов в таблицу
            if switch == 1:
                self.tab.tableInclinometry.setItem(i, IncCol["DECLINATION"], QtWidgets.QTableWidgetItem(str(Geodezy.rad2deg(magnetic_declination))))
                self.tab.tableInclinometry.setItem(i, IncCol["CONVERGENCE"], QtWidgets.QTableWidgetItem(str(Geodezy.rad2deg(gamma))))
                self.tab.tableInclinometry.setItem(i, IncCol["GRID_AZIMUTH"], QtWidgets.QTableWidgetItem(str(Geodezy.rad2deg(azimuth_grid))))

    def calculateInclinometryAndDeviation(self):
        self.calculateInclinometry(
            zenith_error=0.0,
            magnetic_azimuth_error=0.0,
            azimuth_error=0.0,
            north_col=IncCol["NORTH"],
            east_col=IncCol["EAST"],
            alt_col=IncCol["ALTITUDE"],
            switch=1
        )
        # Верхняя траектория с учетом погрешностей
        self.calculateInclinometry(
            zenith_error = Geodezy.deg2rad(float(self.tab.txtErrZenith.text())),
            magnetic_azimuth_error= 0,
            azimuth_error= 0,
            north_col=IncCol["NORTH_TOP"],
            east_col=IncCol["EAST_TOP"],
            alt_col=IncCol["ALTITUDE_TOP"],
            switch=0
        )
        # левая траектория с учетом погрешностей
        self.calculateInclinometry(
            zenith_error = 0,
            magnetic_azimuth_error= - Geodezy.deg2rad(float(self.tab.txtErrMagneticAzimuth.text())),
            azimuth_error= - Geodezy.deg2rad(float(self.tab.txtErrAzimuth.text())),
            north_col=IncCol["NORTH_LEFT"],
            east_col=IncCol["EAST_LEFT"],
            alt_col=IncCol["ALTITUDE_LEFT"],
            switch=0
        )
        # нижняя траектория с учетом погрешностей
        self.calculateInclinometry(
            zenith_error = - Geodezy.deg2rad(float(self.tab.txtErrZenith.text())),
            magnetic_azimuth_error= 0,
            azimuth_error= 0,
            north_col=IncCol["NORTH_BOTTOM"],
            east_col=IncCol["EAST_BOTTOM"],
            alt_col=IncCol["ALTITUDE_BOTTOM"],
            switch=0
        )
        # правая траектория с учетом погрешностей
        self.calculateInclinometry(
            zenith_error = 0,
            magnetic_azimuth_error= Geodezy.deg2rad(float(self.tab.txtErrMagneticAzimuth.text())),
            azimuth_error= Geodezy.deg2rad(float(self.tab.txtErrAzimuth.text())),
            north_col=IncCol["NORTH_RIGHT"],
            east_col=IncCol["EAST_RIGHT"],
            alt_col=IncCol["ALTITUDE_RIGHT"],
            switch=0
        )