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
        self.currentDate = ''
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
        self.tab.btnCalculateInclinometry.setEnabled(False)
        self.tab.tabInclTargetGoBtn.setEnabled(False)
    

    def load_inclinometry(self):
        """Загрузка данных инклинометрии из Excel"""

        # Открытие диалога выбора файла
        filename = self.excel.open_file()
        if not filename:
            return

        # Очищаем таблицу перед загрузкой
        table = self.tab.tableInclinometry
        table.clearContents()
        table.setRowCount(0)
        self.excel.data.clear()
        # table.update()
        # table.viewport().update()
        # QtWidgets.QApplication.processEvents()
        # for i in range(table.rowCount()):
        #     table.removeRow(0)
        
        # Чтение данных из Excel
        self.excel.read_inclinometry(filename)

        # Отображение данных в таблице
        self.tab.tableInclinometry.setRowCount(len(self.excel.data))
        self.crs = self.tab.mQgsProjectionSelectionWidgetWellHead.crs()
        
        # Цикл чтения данных из Excel и заполнения таблицы
        for row, item in enumerate(self.excel.data):
            self.tab.tableInclinometry.setItem(row, IncCol["MD"], QtWidgets.QTableWidgetItem(str(item["md"])))
            self.tab.tableInclinometry.setItem(row, IncCol["ZENITH"], QtWidgets.QTableWidgetItem(str(item["zenith"])))
            self.tab.tableInclinometry.setItem(row, IncCol["AZIMUTH"], QtWidgets.QTableWidgetItem(str(item["azimuth"])))
            self.rows = row + 1
            if row == 0:
                self.tab.tableInclinometry.setItem(row, IncCol["DATE"], QtWidgets.QTableWidgetItem(str(datetime.now().strftime("%Y-%m-%d"))))
                self.tab.tableInclinometry.setItem(row, IncCol["NORTH"], QtWidgets.QTableWidgetItem(self.tab.txtWellHeadNorth.text()))
                self.north_p = float(self.tab.txtWellHeadNorth.text())
                self.tab.tableInclinometry.setItem(row, IncCol["EAST"], QtWidgets.QTableWidgetItem(self.tab.txtWellHeadEast.text()))
                self.east_p = float(self.tab.txtWellHeadEast.text())
                self.tab.tableInclinometry.setItem(row, IncCol["TVDSS"], QtWidgets.QTableWidgetItem(self.tab.txtWellHeadRotor.text()))
                self.alt = float(self.tab.txtWellHeadRotor.text())

                # ===============================================
                # Указание погрешности модели IGRF
                # ===============================================
                if self.tab.cmbAzimuthType.currentIndex() == 0:  # Магнитный
                    self.tab.txtErrMagneticAzimuth.setText("0.5/1.0/1.5")
                    self.tab.txtErrZenith.setText("0.5")
                    self.tab.txtErrAzimuth.setText("0.5")

        self.tab.btnCalculateInclinometry.setEnabled(True)
        self.tab.tabInclTargetGoBtn.setEnabled(False)
        


            # # Исходная точка
            # sourcePoint = QgsPointXY(self.east_p, self.north_p)
            # # Пересчет
            # geographicPoint = self.transform.transform(sourcePoint)
            # if self.AzimuthType == 0:  # Магнитный                    
            #     self.gamma = Geodezy.convergence_meridians(self.tab.tableInclinometry.setItem(
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


    def calculateInclinometry(
            self,
            zenith_error,
            magnetic_azimuth_error,
            azimuth_error,
            north_col,
            east_col,
            tvdss_col,
            switch # если 1 - будет выводить в таблицу промежуточные результаты и координаты (основная траектория)
                   # если 0 - будет выводить в таблицу только координаты (крайние траектории) 
                   # Это было нужно когда функция повторялась 5 раз для расчета крайних траекторий
                   # сейчас она запускается 1 раз с switch = 1)
    ):
        """
        Расчет траектории скважины методом минимальной кривизны.

        Функция последовательно обрабатывает точки инклинометрии,
        рассчитывает дирекционный угол с учетом магнитного склонения
        и сближения меридианов, а затем определяет приращения
        координат Север, Восток и TVDSS для каждого интервала.

        Расчет каждой траектории начинается заново от координат устья,
        указанных в первой строке таблицы. Приращения координат
        последовательно накапливаются вдоль ствола скважины.

        Все угловые параметры внутри функции используются в радианах.
        Значения зенитного угла и азимута, полученные из таблицы,
        перед расчетом преобразуются из градусов в радианы.

        Параметры
        ----------
        zenith_error : float
            Поправка на ошибку зенитного угла, рад.

        magnetic_azimuth_error : float
            Поправка на ошибку магнитного азимута, рад.

        azimuth_error : float
            Поправка на ошибку азимута, рад.

        north_col : int
            Индекс столбца таблицы, в который записывается
            рассчитанная координата Север, м.

        east_col : int
            Индекс столбца таблицы, в который записывается
            рассчитанная координата Восток, м.

        tvdss_col : int
            Индекс столбца таблицы, в который записывается
            рассчитанная координата TVDSS, м.

        switch : int
            Управляет выводом промежуточных результатов в таблицу.
            
            1 :
                записывать приращения координат, магнитное склонение,
                сближение меридианов и дирекционный угол.

            0 :
                записывать только рассчитанные координаты Север,
                Восток и TVDSS.

        Возвращает
        ----------
        None
            Результаты расчета непосредственно записываются
            в таблицу tableInclinometry.
        """
        # Актуальная дата для расчета магнитного склонения
        dt: datetime = datetime.now()
        magnetic_declination: float = 0.0
        gamma: float = 0.0
        north_p: float = float(self.tab.tableInclinometry.item(0, IncCol["NORTH"]).text())
        east_p: float = float(self.tab.tableInclinometry.item(0, IncCol["EAST"]).text())
        alt: float = float(self.tab.tableInclinometry.item(0, IncCol["TVDSS"]).text())
        # alt: float = 0.0

        depth_prev: float = 0.0
        zenith_prev: float = 0.0
        azimuth_grid_prev: float = 0.0
        self.currentDate = datetime.strptime(self.tab.tableInclinometry.item(0, IncCol["DATE"]).text(), "%Y-%m-%d")

        for i in range(self.rows):
            depth = float(self.tab.tableInclinometry.item(i, IncCol["MD"]).text())
            zenith = Geodezy.deg2rad(float(self.tab.tableInclinometry.item(i, IncCol["ZENITH"]).text())) + zenith_error
            azimuth = Geodezy.deg2rad(float(self.tab.tableInclinometry.item(i, IncCol["AZIMUTH"]).text())) 
            dt = self.getRowDate(i)
            # if self.tab.tableInclinometry.item(0, IncCol["DATE"]).text() != "":
            #     dt = datetime.strptime(self.tab.tableInclinometry.item(0, IncCol["DATE"]).text(), "%Y-%m-%d")
            if i > 0:
                # dt = self.getRowDate(i)
                alt = float(self.tab.tableInclinometry.item(i-1, IncCol["TVDSS"]).text())
                # alt = 0.0 

            # Магнитное склонение
            if self.AzimuthType < 1:
                pointWGS84 = self.getPointWGS84(north_p, east_p)
                magnetic_declination = Geodezy.magnetic_declination(
                    Geodezy.deg2rad(pointWGS84.y()),
                    Geodezy.deg2rad(pointWGS84.x()),
                    alt/1000.0,
                    dt,
                    self.tab.cmbAzimuthType.currentIndex()
                )[0]
                # print(f'Широта: {pointWGS84.y():.7f} / Долгота: {pointWGS84.x():.7f} / Дата: {dt} / Альтитуда: {alt:.3f} / CurrentIndex: {self.tab.cmbAzimuthType.currentIndex()} / Магскл: {magnetic_declination}')
            

            # Сближение меридианов
            if self.AzimuthType < 2:
                pointPulkovo42 = self.getPointPulkovo42(north_p, east_p)
                gamma = Geodezy.convergence_meridians(
                    Geodezy.deg2rad(pointPulkovo42.y()),
                    Geodezy.deg2rad(pointPulkovo42.x()),
                    Geodezy.getZoneNumberFromEast(east_p),
                    self.tab.cmbAzimuthType.currentIndex()
                )
            

            # Дирекционный угол
            azimuth_grid = azimuth + magnetic_declination + gamma # + azimuth_error + magnetic_azimuth_error
            

            # РАСЧЕТ
            if i > 0:
                dl = depth - depth_prev
                dNorth, dEast, dTVDSS = self.inclinometry.inclinometry_step(
                    dl,
                    azimuth_grid_prev,
                    azimuth_grid,
                    zenith_prev,
                    zenith
                )
                if switch == 1:
                    self.tab.tableInclinometry.setItem(i, IncCol["DELTA_NORTH"], QtWidgets.QTableWidgetItem(f'{dNorth:.3f}'))
                    self.tab.tableInclinometry.setItem(i, IncCol["DELTA_EAST"], QtWidgets.QTableWidgetItem(f'{dEast:.3f}'))
                    self.tab.tableInclinometry.setItem(i, IncCol["DELTA_TVDSS"], QtWidgets.QTableWidgetItem(f'{dTVDSS:.3f}'))
                north_p += dNorth
                east_p += dEast
                alt -= dTVDSS
                self.tab.tableInclinometry.setItem(i, north_col, QtWidgets.QTableWidgetItem(str(f"{north_p:.3f}")))
                self.tab.tableInclinometry.setItem(i, east_col, QtWidgets.QTableWidgetItem(str(f"{east_p:.3f}")))
                self.tab.tableInclinometry.setItem(i, tvdss_col, QtWidgets.QTableWidgetItem(str(f"{alt:.3f}")))

                depth_prev = depth
                zenith_prev = zenith
                azimuth_grid_prev = azimuth_grid

            #Вывод промежуточных результатов в таблицу
            if switch == 1:
                self.tab.tableInclinometry.setItem(i, IncCol["DECLINATION"], QtWidgets.QTableWidgetItem(f'{Geodezy.rad2deg(magnetic_declination):.7f}'))
                self.tab.tableInclinometry.setItem(i, IncCol["CONVERGENCE"], QtWidgets.QTableWidgetItem(f'{Geodezy.rad2deg(gamma):.7f}'))
                self.tab.tableInclinometry.setItem(i, IncCol["GRID_AZIMUTH"], QtWidgets.QTableWidgetItem(str(f'{Geodezy.rad2deg(azimuth_grid) % 360.0:.7f}')))

        self.tab.tabInclTargetGoBtn.setEnabled(True)

    def calculateErrorPoints(
        self,
        zenith_error: float,
        # magnetic_azimuth_error: float,
        azimuth_error: float
    ):
        """
        Расчет эллипса неопределенности и четырех крайних точек
        для каждой точки ствола, начиная со второй строки.

        Для ErrorEllipse():
            используется полная длина ствола от первой точки
            до текущей точки.

        Для perpendicular_points():
            используется текущий участок между предыдущей
            и текущей точкой.

        Результаты записываются в текущую строку таблицы.
        """

        # Для построения первого эллипса нужны минимум две точки
        if self.rows < 2:
            return

        # Начинаем со второй строки
        for i in range(1, self.rows):

            dt = self.getRowDate(i)
            # =========================================================
            # Погрешность магнитного склонения
            # =========================================================

            magnetic_azimuth_error = Geodezy.deg2rad(
                self.currentErrorDeclination(dt)
            )

            # =========================================================
            # Предыдущая точка
            # =========================================================

            north1 = float(
                self.tab.tableInclinometry
                .item(i - 1, IncCol["NORTH"])
                .text()
            )

            east1 = float(
                self.tab.tableInclinometry
                .item(i - 1, IncCol["EAST"])
                .text()
            )

            md1 = float(
                self.tab.tableInclinometry
                .item(i - 1, IncCol["MD"])
                .text()
            )

            # =========================================================
            # Текущая точка
            # =========================================================

            north2 = float(
                self.tab.tableInclinometry
                .item(i, IncCol["NORTH"])
                .text()
            )

            east2 = float(
                self.tab.tableInclinometry
                .item(i, IncCol["EAST"])
                .text()
            )

            md2 = float(
                self.tab.tableInclinometry
                .item(i, IncCol["MD"])
                .text()
            )

            # =========================================================
            # Полная длина ствола от начала до текущей точки
            # =========================================================

            md_current = float(
                self.tab.tableInclinometry
                .item(i, IncCol["MD"])
                .text()
            )


            l = md_current

            # =========================================================
            # Расчет a, b и четырех крайних точек
            # =========================================================

            a, b, points = self.inclinometry.calculate_error_points(
                north1,
                east1,
                md1,

                north2,
                east2,
                md2,

                l,

                azimuth_error,
                zenith_error,
                magnetic_azimuth_error
            )
           
            # =========================================================
            # Распаковка результата
            # =========================================================

            (
                north_left,
                east_left,
                tvdss_left,

                north_right,
                east_right,
                tvdss_right,

                north_up,
                east_up,
                tvdss_up,

                north_down,
                east_down,
                tvdss_down
            ) = points

            # =========================================================
            # Полуоси эллипса
            # =========================================================

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["a"],
                QtWidgets.QTableWidgetItem(f"{a:.3f}")
            )

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["b"],
                QtWidgets.QTableWidgetItem(f"{b:.3f}")
            )

            # =========================================================
            # LEFT
            # =========================================================

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["NORTH_LEFT"],
                QtWidgets.QTableWidgetItem(f"{north_left:.3f}")
            )


            self.tab.tableInclinometry.setItem(
                i,
                IncCol["EAST_LEFT"],
                QtWidgets.QTableWidgetItem(f"{east_left:.3f}")
            )

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["TVDSS_LEFT"],
                QtWidgets.QTableWidgetItem(f"{tvdss_left:.3f}")
            )

            # =========================================================
            # RIGHT
            # =========================================================

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["NORTH_RIGHT"],
                QtWidgets.QTableWidgetItem(f"{north_right:.3f}")
            )

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["EAST_RIGHT"],
                QtWidgets.QTableWidgetItem(f"{east_right:.3f}")
            )

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["TVDSS_RIGHT"],
                QtWidgets.QTableWidgetItem(f"{tvdss_right:.3f}")
            )

            # =========================================================
            # TOP
            # =========================================================

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["NORTH_TOP"],
                QtWidgets.QTableWidgetItem(f"{north_up:.3f}")
            )

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["EAST_TOP"],
                QtWidgets.QTableWidgetItem(f"{east_up:.3f}")
            )

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["TVDSS_TOP"],
                QtWidgets.QTableWidgetItem(f"{tvdss_up:.3f}")
            )

            # =========================================================
            # DOWN
            # =========================================================

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["NORTH_DOWN"],
                QtWidgets.QTableWidgetItem(f"{north_down:.3f}")
            )

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["EAST_DOWN"],
                QtWidgets.QTableWidgetItem(f"{east_down:.3f}")
            )

            self.tab.tableInclinometry.setItem(
                i,
                IncCol["TVDSS_DOWN"],
                QtWidgets.QTableWidgetItem(f"{tvdss_down:.3f}")
            )
            # print("ROW:", i)
            # print("P1:", north1, east1, md1)
            # print("P2:", north2, east2, md2)
            # print("L:", l)
            # print("ERR_A:", azimuth_error)
            # print("ERR_I:", zenith_error)
            # print("ERR_M:", magnetic_azimuth_error)

    def calculateInclinometryAndDeviation(self):
        """Расчет траектории скважины и эллипса неопределенности
        с последующим заполнением таблицы tableInclinometry."""
        # Система координат на устье, принимаемая для расчета, прямоугольная
        if self.tab.mQgsProjectionSelectionWidgetWellHead.crs().isGeographic():
            QMessageBox.warning(
                self.tab,
                "Ошибка",
                "Система координат на вкладке Позиции/Устья должна быть прямоугольной.\nТакже необходимо перезагрузить инклинометрию."
            )
            return

        self.calculateInclinometry(
            zenith_error=0.0,
            magnetic_azimuth_error=0.0,
            azimuth_error=0.0,
            north_col=IncCol["NORTH"],
            east_col=IncCol["EAST"],
            tvdss_col=IncCol["TVDSS"],
            switch=1
        )
        self.calculateErrorPoints(
            zenith_error=Geodezy.deg2rad(float(self.tab.txtErrZenith.text())),
            # magnetic_azimuth_error=Geodezy.deg2rad(self.currentErrorDeclination(dt)),
            azimuth_error=Geodezy.deg2rad(float(self.tab.txtErrAzimuth.text()))
        )

        # # Верхняя траектория с учетом погрешностей
        # self.calculateInclinometry(
        #     zenith_error = Geodezy.deg2rad(float(self.tab.txtErrZenith.text())),
        #     magnetic_azimuth_error= 0,
        #     azimuth_error= 0,
        #     north_col=IncCol["NORTH_TOP"],
        #     east_col=IncCol["EAST_TOP"],
        #     tvdss_col=IncCol["TVDSS_TOP"],
        #     switch=0
        # )
        # # левая траектория с учетом погрешностей
        # self.calculateInclinometry(
        #     zenith_error = 0,
        #     magnetic_azimuth_error= - Geodezy.deg2rad(float(self.tab.txtErrMagneticAzimuth.text())),
        #     azimuth_error= - Geodezy.deg2rad(float(self.tab.txtErrAzimuth.text())),
        #     north_col=IncCol["NORTH_LEFT"],
        #     east_col=IncCol["EAST_LEFT"],
        #     tvdss_col=IncCol["TVDSS_LEFT"],
        #     switch=0
        # )
        # # нижняя траектория с учетом погрешностей
        # self.calculateInclinometry(
        #     zenith_error = - Geodezy.deg2rad(float(self.tab.txtErrZenith.text())),
        #     magnetic_azimuth_error= 0,
        #     azimuth_error= 0,
        #     north_col=IncCol["NORTH_DOWN"],
        #     east_col=IncCol["EAST_DOWN"],
        #     tvdss_col=IncCol["TVDSS_DOWN"],
        #     switch=0
        # )
        # # правая траектория с учетом погрешностей
        # self.calculateInclinometry(
        #     zenith_error = 0,
        #     magnetic_azimuth_error= Geodezy.deg2rad(float(self.tab.txtErrMagneticAzimuth.text())),
        #     azimuth_error= Geodezy.deg2rad(float(self.tab.txtErrAzimuth.text())),
        #     north_col=IncCol["NORTH_RIGHT"],
        #     east_col=IncCol["EAST_RIGHT"],
        #     tvdss_col=IncCol["TVDSS_RIGHT"],
        #     switch=0
        # )
    def targetTabActivate(self):
        # Нужна проверка на то что инклинометрия посчитана??  
        targets_index = self.tab.tabWidget.indexOf(self.tab.tabTargets)
        self.tab.tabWidget.setTabEnabled(targets_index, True)
        self.tab.tabWidget.setCurrentWidget(self.tab.tabTargets)

    def currentErrorDeclination(self, dt: datetime) -> float:
        """
        Возвращает принятую погрешность магнитного склонения
        в градусах в зависимости от даты.

        Значения берутся из txtErrMagneticAzimuth:
            до 2025 года       → первое значение
            2025–2030          → второе значение
            после 2030 года    → третье значение
        """

        errors = self.tab.txtErrMagneticAzimuth.text().strip()

        error_values = [
            float(value.strip())
            for value in errors.split("/")
        ]

        if dt < datetime(2025, 1, 1):
            return error_values[0]

        if dt < datetime(2030, 1, 1):
            return error_values[1]

        return error_values[2]

    def getRowDate(self, row: int) -> datetime:
        """
        Возвращает дату, действующую для указанной строки.

        Логика:
        - если в текущей строке есть дата — она становится текущей;
        - если дата пустая — используется последняя найденная дата выше;
        - новая дата действует для всех следующих строк,
        пока не встретится следующая дата.
        """

        table = self.tab.tableInclinometry

        for current_row in range(row, -1, -1):
            item = table.item(current_row, IncCol["DATE"])

            if item is None:
                continue

            date_text = item.text().strip()

            if not date_text:
                continue

            self.currentDate = datetime.strptime(
                date_text,
                "%Y-%m-%d"
            )

            # ВАЖНО:
            # нашли ближайшую дату — дальше вверх не идём
            break

        return self.currentDate
