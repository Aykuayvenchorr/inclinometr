from math import sin, cos, tan, acos


class Inclinometry:
    """
    Расчет инклинометрии
    """

    def method_mean_angle(self, dl: float, azimuth_grid_start: float, azimuth_grid_end: float, zenith_start: float, zenith_end: float) -> tuple[float, float, float]:
        """
        Расчет приращений по методу средних углов

        Параметры
        ----------
        dl : float
            Приращение длины, м
        azimuth_grid_start : float
            Дирекционный угол начала интервала, радианы
        azimuth_grid_start : float
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

        dNorth = dl * sin((zenith_start + zenith_end) / 2.0) * cos((azimuth_grid_start + azimuth_grid_end) / 2.0)
        dEast  = dl * sin((zenith_start + zenith_end) / 2.0) * sin((azimuth_grid_start + azimuth_grid_end) / 2.0)
        dZ     = dl * cos((zenith_start + zenith_end) / 2.0)

        return dNorth, dEast, dZ

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