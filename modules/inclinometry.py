from math import degrees, radians, sin, cos, tan, acos, sqrt


class Inclinometry:
    """
    Расчет инклинометрии
    """

    def cross360(azimuth_grid_start, azimuth_grid_end):
        # ======================================================
        # Переводим азимуты из радиан в градусы
        # ======================================================

        azimuth_start_deg = degrees(azimuth_grid_start)
        azimuth_end_deg = degrees(azimuth_grid_end)

        # Приводим азимуты к диапазону 0...360°
        azimuth_start_deg %= 360
        azimuth_end_deg %= 360

        # ======================================================
        # Определяем разницу между азимутами
        # ======================================================

        delta_azimuth_deg = (
            azimuth_end_deg - azimuth_start_deg
        )

        # ======================================================
        # Учитываем переход через 0°/360°
        # ======================================================

        if delta_azimuth_deg > 180:
            delta_azimuth_deg -= 360

        elif delta_azimuth_deg < -180:
            delta_azimuth_deg += 360

        # ======================================================
        # Средний азимут в градусах
        # ======================================================

        azimuth_mean_deg = (
            azimuth_start_deg
            + delta_azimuth_deg / 2
        )

        # Возвращаем средний азимут в диапазон 0...360°
        azimuth_mean_deg %= 360

        # ======================================================
        # Переводим средний азимут обратно в радианы
        # ======================================================

        azimuth_mean = radians(azimuth_mean_deg)
        return azimuth_mean


    def method_mean_angle(self, dl: float, azimuth_grid_start: float, azimuth_grid_end: float, zenith_start: float, zenith_end: float) -> tuple[float, float, float]:
        """
        Расчет приращений по методу средних углов.

        На вход углы поступают в радианах.
        Корректировка среднего азимута выполняется в градусах.
        """
        azimuth_mean = self.cross360(azimuth_grid_start, azimuth_grid_end)

        # ======================================================
        # Средний зенитный угол
        #
        # Он уже в радианах, поэтому здесь ничего
        # переводить не нужно.
        # ======================================================

        zenith_mean = (
            zenith_start + zenith_end
        ) / 2.0

        # ======================================================
        # Расчет приращений
        # ======================================================

        dNorth = (
            dl
            * sin(zenith_mean)
            * cos(azimuth_mean)
        )

        dEast = (
            dl
            * sin(zenith_mean)
            * sin(azimuth_mean)
        )

        dZ = (
            dl
            * cos(zenith_mean)
        )
        # print(f'Метод среднего угла: ср.азимут {azimuth_mean} / ср.зенит {zenith_mean}')
        return dNorth, dEast, dZ

    # def method_mean_angle(self, dl: float, azimuth_grid_start: float, azimuth_grid_end: float, zenith_start: float, zenith_end: float) -> tuple[float, float, float]:
    #     """
    #     Расчет приращений по методу средних углов

    #     Параметры
    #     ----------
    #     dl : float
    #         Приращение длины, м
    #     azimuth_grid_start : float
    #         Дирекционный угол начала интервала, радианы
    #     azimuth_grid_start : float
    #         Дирекционный угол конца интервала, радианы
    #     zenith_start : float
    #         Зенитный угол начала интервала, радианы
    #     zenith_end : float
    #         Зенитный угол конца интервала, радианы
            
    #     Возвращает
    #     ----------
    #     (dNorth: float, dEast: float, dZ: float)
    #         Кортеж приращений координат Север, Восток, Глубина
    #     """
    #     # Ошибка при переходе через 0 градусов
    #     # if abs(azimuth_grid_end - azimuth_grid_start) > 3.14159:
    #     #     if azimuth_grid_start > azimuth_grid_end:
    #     #         azimuth_grid_end += 2 * 3.14159
    #     #     else:
    #     #         azimuth_grid_start += 2 * 3.14159
    #     dNorth = dl * sin((zenith_start + zenith_end) / 2.0) * cos((azimuth_grid_start + azimuth_grid_end) / 2.0)
    #     dEast  = dl * sin((zenith_start + zenith_end) / 2.0) * sin((azimuth_grid_start + azimuth_grid_end) / 2.0)
    #     dZ     = dl * cos((zenith_start + zenith_end) / 2.0)

    #     return dNorth, dEast, dZ

    def method_minimum_curvature(self, dl: float, azimuth_grid_start: float, azimuth_grid_end: float, zenith_start: float, zenith_end: float) -> tuple[float, float, float]:
        """
        Расчет приращений по методу наименьшей кривизны

        Параметры
        ----------
        dl : float
            Приращение длины, м
        azimuth_grid_start : float
            Дирекционный угол начала интервала, радианы
        azimuth_grid_end : float
            Дирекционный угол конца интервала, радианы
        zenith_start : float
            Зенитный угол начала интервала, радианы
        zenith_end : float
            Зенитный угол конца интервала, радианы

        Возвращает
        ----------
        (dNorth: float, dEast: float, dZ: float)
            Кортеж приращений координат Север, Восток, Глубина
        """

        cos_beta = (cos(zenith_end - zenith_start) - sin(zenith_start) * sin(zenith_end) 
                    * (1 - cos(azimuth_grid_end - azimuth_grid_start)))
        
        # cos_beta = max(-1.0, min(1.0, cos_beta))
        beta = acos(cos_beta)

        RF = (2.0 / beta) * tan(beta / 2.0)

        dNorth = (dl / 2.0) * (sin(zenith_start) * cos(azimuth_grid_start) + sin(zenith_end) * cos(azimuth_grid_end)) * RF
        dEast = (dl / 2.0) * (sin(zenith_start) * sin(azimuth_grid_start) + sin(zenith_end) * sin(azimuth_grid_end)) * RF
        dZ = (dl / 2.0) * (cos(zenith_start) + cos(zenith_end)) * RF

        return dNorth, dEast, dZ

    def inclinometry_step(self, dl: float, azimuth_grid_start: float, azimuth_grid_end: float, zenith_start: float, zenith_end: float) -> tuple[float, float, float]:
        """
        Расчет приращений обоими методами в зависимости от условий

        Параметры
        ----------
        dl : float
            Приращение длины, м
        azimuth_grid_start : float
            Дирекционный угол начала интервала, радианы
        azimuth_grid_end : float
            Дирекционный угол конца интервала, радианы
        zenith_start : float
            Зенитный угол начала интервала, радианы
        zenith_end : float
            Зенитный угол конца интервала, радианы

        Возвращает
        ----------
        (dNorth: float, dEast: float, dZ: float)
            Кортеж приращений координат Север, Восток, Глубина
        """
        
        if (zenith_start == zenith_end) and (azimuth_grid_start == azimuth_grid_end):
            return self.method_mean_angle(dl, azimuth_grid_start, azimuth_grid_end, zenith_start, zenith_end)
        else:
            return self.method_minimum_curvature(dl, azimuth_grid_start, azimuth_grid_end, zenith_start, zenith_end)

    def inclinometry(self, wellhead: tuple[float, float, float], measure: list[list[float, float, float]], err_l: float = 0.0, err_a: float = 0.0, err_i: float = 0.0) -> list[tuple[float, float, float, float, float, float, float, float, float, float, float, float, float, float, float]]:
        """
        Расчет приращений обоими методами в зависимости от условий

        Параметры
        ----------
        wellhead : tuple[float, float, float]
            Координаты устья скважины (Север, Восток, Глубина)
        measure : list[list[float, float, float]]
            Список измерений, каждый элемент - [глубина по стволу, дирекционный угол, зенитный угол]
        err_l : float
            Погрешность измерения длины, м
        err_a : float
            Погрешность измерения дирекционного угла, радианы
        err_i : float
            Погрешность измерения зенитного угла, радианы

        Возвращает
        ----------
        list[tuple[float, float, float, float, float, float, float, float, float, float, float, float, float, float, float]]:
            Список кортежей координат:
             - Север, Восток, Глубина - основного ствола
             - Север, Восток, Глубина - крайне-верхнего вероятного положения ствола             
             - Север, Восток, Глубина - крайне-левого вероятного положения ствола
             - Север, Восток, Глубина - крайне-нижнего вероятного положения ствола
             - Север, Восток, Глубина - крайне-правого вероятного положения ствола
        """

        # Начальные координаты устья скважины (Север, Восток, Глубина) для всех вероятных положений ствола
        incl_calc = list(
            wellhead[0], wellhead[1], wellhead[2],
            wellhead[0], wellhead[1], wellhead[2],
            wellhead[0], wellhead[1], wellhead[2],
            wellhead[0], wellhead[1], wellhead[2],
            wellhead[0], wellhead[1], wellhead[2]
        )                    

        for i, measure_i in enumerate(measure):
            if i == 0:
                continue

            # Расчет приращений координат Север, Восток, Глубина наиболее вероятного положения ствола
            dNorth, dEast, dZ = self.inclinometry_step(
                measure_i[0] - measure[i - 1][0],       # dl - длина участка по стволу
                measure[i - 1][1],                      # azimuth_grid_start - дирекционный угол начала интервала, радианы
                measure_i[1],                           # azimuth_grid_end - дирекционный угол конца интервала, радианы
                measure[i - 1][2],                      # zenith_start - зенитный угол начала интервала, радианы
                measure_i[2]                            # zenith_end - зенитный угол конца интервала, радианы
            )

            # Расчет приращений координат Север, Восток, Глубина крайне-верхнего вероятного положения ствола
            dNorth_up, dEast_up, dZ_up = self.inclinometry_step(
                measure_i[0] - measure[i - 1][0],       # dl - длина участка по стволу
                measure[i - 1][1],                      # azimuth_grid_start - дирекционный угол начала интервала, радианы
                measure_i[1],                           # azimuth_grid_end - дирекционный угол конца интервала, радианы
                measure[i - 1][2] + err_i,              # zenith_start - зенитный угол начала интервала, радианы
                measure_i[2] + err_i                    # zenith_end - зенитный угол конца интервала, радианы
            )

            # Расчет приращений координат Север, Восток, Глубина крайне-левого вероятного положения ствола
            dNorth_left, dEast_left, dZ_left = self.inclinometry_step(
                measure_i[0] - measure[i - 1][0],       # dl - длина участка по стволу
                measure[i - 1][1] - err_a,              # azimuth_grid_start - дирекционный угол начала интервала, радианы
                measure_i[1] - err_a,                   # azimuth_grid_end - дирекционный угол конца интервала, радианы
                measure[i - 1][2],                      # zenith_start - зенитный угол начала интервала, радианы
                measure_i[2]                            # zenith_end - зенитный угол конца интервала, радианы
            )

            # Расчет приращений координат Север, Восток, Глубина крайне-нижнего вероятного положения ствола
            dNorth_down, dEast_down, dZ_down = self.inclinometry_step(
                measure_i[0] - measure[i - 1][0],       # dl - длина участка по стволу
                measure[i - 1][1],                      # azimuth_grid_start - дирекционный угол начала интервала, радианы
                measure_i[1],                           # azimuth_grid_end - дирекционный угол конца интервала, радианы
                measure[i - 1][2] - err_i,              # zenith_start - зенитный угол начала интервала, радианы
                measure_i[2] - err_i                    # zenith_end - зенитный угол конца интервала, радианы
            )

            # Расчет приращений координат Север, Восток, Глубина крайне-правого вероятного положения ствола
            dNorth_right, dEast_right, dZ_right = self.inclinometry_step(
                measure_i[0] - measure[i - 1][0],       # dl - длина участка по стволу
                measure[i - 1][1] + err_a,              # azimuth_grid_start - дирекционный угол начала интервала, радианы
                measure_i[1] + err_a,                   # azimuth_grid_end - дирекционный угол конца интервала, радианы
                measure[i - 1][2],                      # zenith_start - зенитный угол начала интервала, радианы
                measure_i[2]                            # zenith_end - зенитный угол конца интервала, радианы
            )

            incl_calc.append((
                    incl_calc[-1][0] + dNorth,
                    incl_calc[-1][1] + dEast,
                    incl_calc[-1][2] + dZ,
                    incl_calc[-1][3] + dNorth_up,
                    incl_calc[-1][4] + dEast_up,
                    incl_calc[-1][5] + dZ_up,
                    incl_calc[-1][6] + dNorth_left,
                    incl_calc[-1][7] + dEast_left,
                    incl_calc[-1][8] + dZ_left,
                    incl_calc[-1][9] + dNorth_down,
                    incl_calc[-1][10] + dEast_down,
                    incl_calc[-1][11] + dZ_down,
                    incl_calc[-1][12] + dNorth_right,
                    incl_calc[-1][13] + dEast_right,
                    incl_calc[-1][14] + dZ_right
                ))

        return incl_calc

    def ErrorEllipse(
        self,
        l: float,
        err_a: float,
        err_i: float,
        err_m: float
    ) -> tuple[float, float]:
        """
        Расчет размеров области ошибки.

        Параметры
        ----------
        l : float
            Длина участка, м.

        err_a : float
            Погрешность дирекционного угла, радианы.

        err_i : float
            Погрешность зенитного угла, радианы.

        err_m : float
            Погрешность магнитного азимута, радианы.

        Возвращает
        ----------
        (a, b)
            a - горизонтальный размер, м
            b - вертикальный размер, м
        """

        a = l * tan(abs(err_a) + abs(err_m))
        b = l * tan(abs(err_i))

        return a, b

        
    def perpendicular_points(
        self,
        north1: float,
        east1: float,
        md1: float,
        north2: float,
        east2: float,
        md2: float,
        a: float,
        b: float
        ) -> list[float]:
        """
        Расчет четырех точек относительно конца отрезка P2.

        Параметры
        ----------
        north1, east1, md1 : float
            Координаты начала отрезка.

        north2, east2, md2 : float
            Координаты конца отрезка.

        a : float
            Расстояние до точек Left и Right, м.

        b : float
            Расстояние до точек Up и Down, м.

        Возвращает
        ----------
        list[float]
            Один список из 12 координат:

            [
                north_left, east_left, md_left,
                north_right, east_right, md_left,
                north_up, east_up, md_up,
                north_down, east_down, md_down
            ]

        Примечание
        ----------
        depth положительная вниз.
        """

        # Вектор от начала к концу отрезка
        d_north = north2 - north1
        d_east = east2 - east1
        d_depth = md2 - md1

        # Горизонтальная длина проекции отрезка
        horizontal_length = sqrt(d_north**2 + d_east**2)

        # Полная длина отрезка
        length = sqrt(d_north**2 + d_east**2 + d_depth**2)

        # Отрезок нулевой длины
        if length == 0:
            raise ValueError("Начальная и конечная точки совпадают.")

        # Вертикальный отрезок
        if horizontal_length == 0:
            raise ValueError(
                "Горизонтальная проекция отрезка равна нулю. "
                "Невозможно однозначно определить Left и Right."
            )

        # ---------------------------------------------------------
        # LEFT
        # ---------------------------------------------------------

        north_left = (north2 - a * d_east / horizontal_length)

        east_left = (east2 + a * d_north / horizontal_length)

        md_left = md2

        # ---------------------------------------------------------
        # RIGHT
        # ---------------------------------------------------------

        north_right = (
            north2 +
            a * d_east / horizontal_length
        )

        east_right = (
            east2 -
            a * d_north / horizontal_length
        )

        md_left = md2

        # ---------------------------------------------------------
        # UP
        # ---------------------------------------------------------

        north_up = (
            north2 -
            b * d_north * d_depth /
            (length * horizontal_length)
        )

        east_up = (
            east2 -
            b * d_east * d_depth /
            (length * horizontal_length)
        )

        # depth направлена вниз,
        # поэтому движение вверх уменьшает depth
        md_up = (
            md2 -
            b * horizontal_length / length
        )

        # ---------------------------------------------------------
        # DOWN
        # ---------------------------------------------------------

        north_down = (
            north2 +
            b * d_north * d_depth /
            (length * horizontal_length)
        )

        east_down = (
            east2 +
            b * d_east * d_depth /
            (length * horizontal_length)
        )

        # depth направлена вниз,
        # поэтому движение вниз увеличивает depth
        md_down = (
            md2 +
            b * horizontal_length / length
        )

        # ---------------------------------------------------------
        # Результат
        # ---------------------------------------------------------

        return [
            north_left,
            east_left,
            md_left,

            north_right,
            east_right,
            md_left,

            north_up,
            east_up,
            md_up,

            north_down,
            east_down,
            md_down
        ]


    def calculate_error_points(
        self,
        north1: float,
        east1: float,
        md1: float,
        north2: float,
        east2: float,
        md2: float,
        l: float,
        err_a: float,
        err_i: float,
        err_m: float
    ) -> tuple[float, float, list[float]]:
        """
        Расчет a, b и координат четырех крайних точек.

        Параметры
        ----------
        north1, east1, md1 : float
            Координаты начала отрезка.

        north2, east2, md2 : float
            Координаты конца отрезка.

        l : float
            Длина участка по стволу, м.

        err_a : float
            Погрешность азимута, радианы.

        err_i : float
            Погрешность зенитного угла, радианы.

        err_m : float
            Погрешность магнитного азимута, радианы.

        Возвращает
        ----------
        tuple[float, float, list[float]]
            a, b и список из 12 координат:
            
            [
                north_left, east_left, md_left,
                north_right, east_right, md_left,
                north_up, east_up, md_up,
                north_down, east_down, md_down
            ]
        """

        # Расчет размеров области ошибки
        a, b = self.ErrorEllipse(
            l,
            err_a,
            err_i,
            err_m
        )

        # Расчет координат крайних точек
        points = self.perpendicular_points(
            north1,
            east1,
            md1,
            north2,
            east2,
            md2,
            a,
            b
        )



        return a, b, points