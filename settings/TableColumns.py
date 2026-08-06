# Словари для всех таблиц в проекте (не думаю что их нужно разделять на несколько классов
# так как их немного и вряд ли их будет много в будующем)

class TableColumns:

    inclinometry = {
        "DEPTH": 0,
        "ZENITH": 1,
        "AZIMUTH": 2,
        "DATE": 3,
        "NORTH": 4,
        "EAST": 5,
        "ALTITUDE": 6,
        "CONVERGENCE": 7,
        "DECLINATION": 8,
        "GRID_AZIMUTH": 9,
        "DELTA_NORTH": 10,
        "DELTA_EAST": 11,
        "DELTA_Z": 12,
        "NORTH_TOP": 13,
        "EAST_TOP": 14,
        "ALTITUDE_TOP": 15,
        "NORTH_LEFT": 16,
        "EAST_LEFT": 17,
        "ALTITUDE_LEFT": 18,
        "NORTH_BOTTOM": 19,
        "EAST_BOTTOM": 20,
        "ALTITUDE_BOTTOM": 21,
        "NORTH_RIGHT": 22,
        "EAST_RIGHT": 23,
        "ALTITUDE_RIGHT": 24
    }

    targets = {
        "ID": 0,
        "NORTH": 1,
        "EAST": 2,
        "TVD": 3,
    }

