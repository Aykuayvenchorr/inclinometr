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
    }

    targets = {
        "ID": 0,
        "NORTH": 1,
        "EAST": 2,
        "TVD": 3,
    }

