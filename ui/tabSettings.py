import os
import json

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    QgsGeometry,
    QgsMapLayerProxyModel,
    QgsCoordinateTransform,
    QgsProject,
    QgsPointXY,
    QgsVectorLayer,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsWkbTypes,
    QgsCoordinateTransformContext
)
from PyQt5.QtCore import QVariant
from qgis.utils import iface
from qgis.gui import QgsMapToolIdentifyFeature


class TabSettings:
    """Вкладка 'Рабочие слои'"""

    def __init__(self, dialog):
        self.tab = dialog
        self.gpkg_path = ''


    def pathTodDB(self, workdir):
        """
        Формирует путь к GeoPackage.
        """

        self.gpkg_path = os.path.join(
            workdir,
            "InclinometryCalc.gpkg"
        )

        if os.path.isfile(self.gpkg_path):
            print("База существует:", self.gpkg_path)
        else:
            print("База будет создана:", self.gpkg_path)

        return self.gpkg_path


    def getWellheadLayer(self):
        """
        Проверяет, загружен ли слой wellhead
        из текущего GeoPackage в проект QGIS.

        Возвращает слой, если он уже загружен.
        Иначе возвращает None.
        """

        for layer in QgsProject.instance().mapLayers().values():

            if (
                layer.name() == "wellhead"
                and layer.source().startswith(self.gpkg_path)
            ):
                return layer

        return None


    def wellheadLayerAdd(self):
        """
        Создание базы данных (если отсутствует)
        и создание слоя wellhead (если отсутствует).

        Логика:

        1. Если wellhead уже загружен в проект -
           ничего не делаем.

        2. Если GeoPackage существует:
           - если wellhead есть в БД -> загружаем его;
           - если wellhead нет в БД -> создаём его.

        3. Если GeoPackage не существует:
           - создаём GeoPackage;
           - создаём wellhead;
           - загружаем его в QGIS.
        """

        # ==========================================
        # 1. Проверяем рабочую папку
        # ==========================================

        workdir = self.tab.tabSettingsWorkdir.filePath()

        if not os.path.isdir(workdir):
            QMessageBox.critical(
                self.tab,
                "Рабочая папка",
                "Не указана рабочая папка!"
            )
            return


        # ==========================================
        # 2. Получаем путь к GeoPackage
        # ==========================================

        self.gpkg_path = self.pathTodDB(workdir)

        # ==========================================
        # 3. Проверяем, не загружен ли уже
        #    wellhead в проект QGIS
        # ==========================================

        loaded_layer = self.getWellheadLayer()

        if loaded_layer is not None:
            print("wellhead уже загружен в проект.")
            QMessageBox.information(
                self.tab,
                "Слой wellhead",
                "Слой wellhead уже загружен в проект."
            )
            return

        # ==========================================
        # 4. Если GeoPackage существует,
        #    проверяем наличие wellhead внутри БД
        # ==========================================

        if os.path.isfile(self.gpkg_path):
            existing_layer = QgsVectorLayer(
                f"{self.gpkg_path}|layername=wellhead",
                "wellhead",
                "ogr"
            )

            # ------------------------------------------
            # wellhead существует в БД
            # ------------------------------------------

            if existing_layer.isValid():

                print(
                    "wellhead существует в БД, "
                    "но ещё не загружен в проект."
                )

                QgsProject.instance().addMapLayer(
                    existing_layer
                )

                QMessageBox.information(
                    self.tab,
                    "Слой wellhead",
                    "Существующий слой wellhead "
                    "загружен из базы данных."
                )

                return


        # ==========================================
        # 5. Если дошли сюда:
        #
        # - БД не существует
        # ИЛИ
        # - БД существует, но wellhead в ней нет
        #
        # Значит, создаём новый слой
        # ==========================================

        print("wellhead отсутствует в БД.")
        print("Создаём новый слой.")


        # ==========================================
        # 6. Поля слоя wellhead
        # ==========================================

        fields = QgsFields()

        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("type", QVariant.Int))
        fields.append(QgsField("lic", QVariant.String))
        fields.append(QgsField("field", QVariant.String))
        fields.append(QgsField("pad", QVariant.String))
        fields.append(QgsField("name",QVariant.String,len=100))
        fields.append(QgsField("rel", QVariant.Bool))
        fields.append(QgsField("north", QVariant.Double))
        fields.append(QgsField("east", QVariant.Double))
        fields.append(QgsField("alt_ground", QVariant.Double))
        fields.append(QgsField("alt_rotor", QVariant.Double))
        fields.append(QgsField("alt", QVariant.Double))
        fields.append(QgsField("alt_note", QVariant.String))
        fields.append(QgsField("crs_param", QVariant.String))
        fields.append(QgsField("crs_text", QVariant.String))
        fields.append(QgsField("path", QVariant.String))
        fields.append(QgsField("note", QVariant.String))

        # ==========================================
        # 7. Тип геометрии и CRS
        # ==========================================

        geometry_type = QgsWkbTypes.Point

        crs = QgsCoordinateReferenceSystem("EPSG:4326")

        # ==========================================
        # 8. Настройки создания GeoPackage
        # ==========================================

        options = QgsVectorFileWriter.SaveVectorOptions()

        options.driverName = "GPKG"
        options.layerName = "wellhead"

        # ==========================================
        # 9. Если GeoPackage уже существует,
        #    создаём слой внутри существующей БД
        # ==========================================

        if os.path.isfile(self.gpkg_path):
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        # ==========================================
        # 10. Контекст преобразования координат
        # ==========================================

        transform_context = QgsProject.instance().transformContext()

        # ==========================================
        # 11. Создаём GeoPackage / слой
        # ==========================================

        writer = QgsVectorFileWriter.create(
            self.gpkg_path,
            fields,
            geometry_type,
            crs,
            transform_context,
            options
        )

        # ==========================================
        # 12. Проверяем результат создания
        # ==========================================

        if writer.hasError() != (QgsVectorFileWriter.NoError):
            QMessageBox.critical(
                self.tab,
                "Ошибка создания слоя",
                f"Не удалось создать слой wellhead:\n"
                f"{writer.errorMessage()}"
            )
            del writer
            return

        # ==========================================
        # 13. Закрываем writer
        # ==========================================

        del writer

        # ==========================================
        # 14. Загружаем созданный слой
        # ==========================================

        layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=wellhead",
            "wellhead",
            "ogr"
        )

        # ==========================================
        # 15. Проверяем загрузку
        # ==========================================

        print("Файл:", self.gpkg_path)
        print("Файл существует:", os.path.exists(self.gpkg_path))
        print("Слой valid:", layer.isValid())
        print("Слой name:", layer.name())
        print("Ошибка:", layer.error().message())

        if not layer.isValid():

            QMessageBox.critical(
                self.tab,
                "Ошибка",
                "Слой wellhead создан, "
                "но не удалось его загрузить.\n\n"
                f"Ошибка: {layer.error().message()}"
            )

            return


        # ==========================================
        # 16. Добавляем слой в проект QGIS
        # ==========================================

        QgsProject.instance().addMapLayer(layer)

        # ==========================================
        # 17. Сообщение
        # ==========================================

        QMessageBox.information(
            self.tab,
            "Готово",
            "Новый слой wellhead создан "
            "и добавлен в QGIS."
        )

