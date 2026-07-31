from math import atan, sin, cos, sqrt, atan2, radians, acos, asin, tan, degrees
import ppigrf
from datetime import date, datetime
import numpy as np


class Geodezy:
    """
    Геодезические расчеты
    """
    def __init__(self):
        pass

    @staticmethod
    def convergence_meridians(B: float, L: float, L0: float, a: float, b: float):
        """
        Расчет сближения меридианов по формуле Морозова.

        Параметры
        ----------
        B : float
            Геодезическая широта, радианы    
        L : float
            Геодезическая долгота точки, радианы    
        L0 : float
            Долгота осевого меридиана зоны, радианы    
        a : float
            Большая полуось эллипсоида, м    
        b : float
            Малая полуось эллипсоида, м
            
        Возвращает
        ----------
        float
            Сближение меридианов, радианы
        """
        # Разность долгот
        l = L - L0

        # Первый эксцентриситет²
        #e2 = (a**2 - b**2) / (a**2)
        # Второй эксцентриситет²
        es2 = (a**2 - b**2) / (b**2)
        # η²
        eta2 = es2 * cos(B) ** 2

        # Формула Морозова
        tg_gamma = (sin(B) * tan(l) + (eta2 * sin(B) * cos(B)**2 * l**3* (1 + (2/3)*eta2 + cos(B)**2 * l**2)))
        gamma = atan(tg_gamma)

        return gamma

    @staticmethod
    def azimuth_true_2_grid(azimiuth_true: float, convergence_meridians: float) -> float:
        """
        Расчет дирекционного угла по магнитному азимуту и сближению меридианов

        Параметры
        ----------
        azimiuth_true : float
            Истинный азимут, радианы
        convergence_meridians : float
            Сближение меридианов, радианы
        lon0_deg : float
            Долгота осевого меридиана зоны, радианы
        
        Возвращает
        ----------
        float
            Дирекционный угол, радианы
        """

    @staticmethod
    def magnetic_declination(lat_deg: float, lon_deg: float, alt_m: float, dt: datetime) -> float:
        """
        Расчет магнитного склонения по модели IGRF.

        Параметры
        ----------
        lat_deg : float
            Геодезическая широта, градусы
        lon_deg : float
            Геодезическая долгота точки, градусы
        alt_m : float
            Альтитуда точки, м
        dt : datetime
            Дата
        
        Возвращает
        ----------
        float
            Магнитное склонение, радианы
        """
        # Расчет компонентов напряженности магнитного поля Восток, Север, Нормальное (вверх)
        Be, Bn, Bu = ppigrf.igrf(lon=lon_deg, lat=lat_deg, h=alt_m, date=dt)

        # Полная напряженность
        total = np.sqrt(Bn**2 + Be**2 + Bu**2)

        # Магнитное склонение (в радианах)
        declination_rad = np.arctan2(Be, Bn)    # arctan2(Восток, Север)
        declination_deg = np.degrees(declination_rad)

        # Магнитное наклонение
        horizontal = np.sqrt(Bn**2 + Be**2)
        inclination_rad = np.arctan2(Bu, horizontal)
        inclination_deg = np.degrees(inclination_rad)

        # Вычисление изменения магнитного склонения в год
        date_old = datetime(dt.year - 1, dt.month, dt.day)
        Be_old, Bn_old, Bu_old = ppigrf.igrf(lon=lon_deg, lat=lat_deg, h=alt_m, date=date_old)
        declination_rad_old = np.arctan2(Be_old, Bn_old)
        declination_deg_old = np.degrees(declination_rad_old)
        change_per_year = declination_deg_old - declination_deg
        
        return declination_rad