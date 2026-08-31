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
    QgsCoordinateTransformContext,
    QgsRelation,
    QgsEditorWidgetSetup,
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


    def getTargetsLayer(self):
        """
        Проверяет, загружен ли слой targets
        из текущего GeoPackage в проект QGIS.

        Возвращает слой, если он уже загружен.
        Иначе возвращает None.
        """

        for layer in QgsProject.instance().mapLayers().values():

            if (
                layer.name() == "targets"
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

        # ==========================================================
        # 4. Проверяем, существует ли type_wellhead в GeoPackage
        # ==========================================================

        type_wellhead_uri = (
            f"{self.gpkg_path}|layername=type_wellhead"
        )

        type_wellhead_layer = QgsVectorLayer(
            type_wellhead_uri,
            "type_wellhead",
            "ogr"
        )

        # ==========================================================
        # 2. Если type_wellhead отсутствует — создаём его
        # ==========================================================

        if not type_wellhead_layer.isValid():

            print("type_wellhead отсутствует.")
            print("Создаём слой type_wellhead.")

            type_fields = QgsFields()

            type_fields.append(
                QgsField("id", QVariant.Int)
            )

            type_fields.append(
                QgsField("name", QVariant.String)
            )

            type_options = (
                QgsVectorFileWriter.SaveVectorOptions()
            )

            type_options.driverName = "GPKG"
            type_options.layerName = "type_wellhead"

            # Если GeoPackage уже существует,
            # создаём новый слой внутри него
            if os.path.isfile(self.gpkg_path):

                type_options.actionOnExistingFile = (
                    QgsVectorFileWriter.CreateOrOverwriteLayer
                )

            transform_context = (
                QgsProject.instance().transformContext()
            )

            type_writer = QgsVectorFileWriter.create(
                self.gpkg_path,
                type_fields,
                QgsWkbTypes.NoGeometry,
                QgsCoordinateReferenceSystem(),
                transform_context,
                type_options
            )

            if type_writer.hasError() != (
                QgsVectorFileWriter.NoError
            ):

                QMessageBox.critical(
                    self.tab,
                    "Ошибка создания type_wellhead",
                    type_writer.errorMessage()
                )

                del type_writer
                return

            del type_writer

            # ------------------------------------------------------
            # Загружаем созданный type_wellhead
            # ------------------------------------------------------

            type_wellhead_layer = QgsVectorLayer(
                type_wellhead_uri,
                "type_wellhead",
                "ogr"
            )

            if not type_wellhead_layer.isValid():

                QMessageBox.critical(
                    self.tab,
                    "Ошибка",
                    "Слой type_wellhead создан, "
                    "но не удалось его загрузить."
                )

                return

            # ------------------------------------------------------
            # Заполняем справочник
            # ------------------------------------------------------

            type_wellhead_layer.startEditing()

            feature = QgsFeature(
                type_wellhead_layer.fields()
            )

            feature["id"] = 0
            feature["name"] = "Позиция"

            type_wellhead_layer.addFeature(feature)

            feature = QgsFeature(
                type_wellhead_layer.fields()
            )

            feature["id"] = 1
            feature["name"] = "Устье"

            type_wellhead_layer.addFeature(feature)

            type_wellhead_layer.commitChanges()

            print("type_wellhead создан и заполнен.")


        else:

            print("type_wellhead уже существует в БД.")
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

                 # Сначала добавляем слой в проект
                QgsProject.instance().addMapLayer(
                    existing_layer
                )

                # Затем настраиваем поле type
                self.setupWellheadTypeField(
                    existing_layer
                )
                self.tab.tabSettingsWellheadMLCBox.setLayer(existing_layer)
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
        self.tab.tabSettingsWellheadMLCBox.setLayer(layer)

        # ==========================================================
        # 12. Настраиваем поле type
        #
        # В выпадающем списке:
        #
        # Позиция -> 0
        # Устье   -> 1
        #
        # В БД сохраняется именно id.
        # ==========================================================

        self.setupWellheadTypeField(layer)
        # ==========================================
        # 17. Сообщение
        # ==========================================

        QMessageBox.information(
            self.tab,
            "Готово",
            "Новый слой wellhead создан "
            "и добавлен в QGIS."
        )


    def setupWellheadTypeField(self, layer):
        """
        Настраивает поле type слоя wellhead
        как выпадающий список ValueMap.

        Отображаемое значение:
        Позиция
        Устье

        В поле type записывается:
            0
            1
        """

        # ==========================================================
        # 1. Ищем поле type
        # ==========================================================

        type_field_index = layer.fields().indexOf("type")

        if type_field_index == -1:
            print("Поле type отсутствует в wellhead.")
            return

        # ==========================================================
        # 2. Открываем type_wellhead из БД
        #
        # ВАЖНО:
        # этот слой НЕ добавляется в проект
        # ==========================================================

        type_wellhead_uri = (
            f"{self.gpkg_path}|layername=type_wellhead"
        )

        type_layer = QgsVectorLayer(
            type_wellhead_uri,
            "type_wellhead",
            "ogr"
        )

        if not type_layer.isValid():

            print(
                "type_wellhead отсутствует или "
                "не удалось его открыть."
            )

            return

        # ==========================================================
        # 3. Формируем ValueMap
        # ==========================================================

        value_map = []

        for feature in type_layer.getFeatures():

            type_id = feature["id"]
            type_name = feature["name"]

            if type_id is None or type_name is None:
                continue

            value_map.append({
                str(type_name): type_id
            })

        # ==========================================================
        # 4. Проверяем справочник
        # ==========================================================

        if not value_map:

            print(
                "В type_wellhead нет записей."
            )

            return

        print(
            "ValueMap для type:",
            value_map
        )

        # ==========================================================
        # 5. Создаём настройку ValueMap
        # ==========================================================

        widget_setup = QgsEditorWidgetSetup(
            "ValueMap",
            {
                "map": value_map
            }
        )

        # ==========================================================
        # 6. Устанавливаем настройку на поле type
        # ==========================================================

        layer.setEditorWidgetSetup(
            type_field_index,
            widget_setup
        )

        # ==========================================================
        # 7. Проверяем, что настройка действительно установилась
        # ==========================================================

        current_setup = layer.editorWidgetSetup(
            type_field_index
        )

        print(
            "Тип виджета:",
            current_setup.type()
        )

        print(
            "Конфигурация:",
            current_setup.config()
        )

    def selectWellheadInComboBox(self):
        """
        Если слой wellhead уже есть в проекте,
        выбирает его в ComboBox.
        """

        wellhead_layer = self.getWellheadLayer()

        if wellhead_layer is not None:
            self.tab.tabSettingsWellheadMLCBox.setLayer(
                wellhead_layer
            )

    def selectTargetsInComboBox(self):
        """
        Если слой targets уже есть в проекте,
        выбирает его в ComboBox.
        """

        targets_layer = self.getTargetsLayer()

        if targets_layer is not None:
            self.tab.tabSettingsTargetsMLCBox.setLayer(
                targets_layer
            )

    def filterWellheadLayers(self):
        """
        Фильтрует слои для ComboBox wellhead.

        В список попадают только:
        - точечные слои;
        - слои со всеми 17 полями wellhead.
        """

        combo = self.tab.tabSettingsWellheadMLCBox

        required_fields = {
            "id",
            "type",
            "lic",
            "field",
            "pad",
            "name",
            "rel",
            "north",
            "east",
            "alt_ground",
            "alt_rotor",
            "alt",
            "alt_note",
            "crs_param",
            "crs_text",
            "path",
            "note",
        }

        excepted_layers = []

        for layer in QgsProject.instance().mapLayers().values():

            # ======================================================
            # Только точечные слои
            # ======================================================

            if not isinstance(layer, QgsVectorLayer):
                excepted_layers.append(layer)
                continue

            if layer.geometryType() != QgsWkbTypes.PointGeometry:
                excepted_layers.append(layer)
                continue

            # ======================================================
            # Получаем поля слоя
            # ======================================================

            layer_fields = {
                field.name()
                for field in layer.fields()
            }

            # ======================================================
            # Проверяем наличие всех 17 полей
            # ======================================================

            if not required_fields.issubset(layer_fields):
                excepted_layers.append(layer)

        # ==========================================================
        # Передаём ComboBox список слоёв, которые нужно исключить
        # ==========================================================

        combo.setExceptedLayerList(
            excepted_layers
        )

    def filterTargetsLayers(self):
        """
        Фильтрует слои для ComboBox targets.

        В список попадают только:
        - точечные слои;
        - слои со всеми 17 полями targets.
        """

        combo = self.tab.tabSettingsTargetsMLCBox

        required_fields = {
            "id",
            "type",
            "lic",
            "field",
            "pad",
            "name",
            "num_txt",
            "num_int",
            "rel",
            "north",
            "east",
            "alt_ground",
            "alt_rotor",
            "alt",
            "alt_note",
            "crs_param",
            "crs_text",
            "path",
            "note",
        }

        excepted_layers = []

        for layer in QgsProject.instance().mapLayers().values():

            # ======================================================
            # Только точечные слои
            # ======================================================

            if not isinstance(layer, QgsVectorLayer):
                excepted_layers.append(layer)
                continue

            if layer.geometryType() != QgsWkbTypes.PointGeometry:
                excepted_layers.append(layer)
                continue

            # ======================================================
            # Получаем поля слоя
            # ======================================================

            layer_fields = {
                field.name()
                for field in layer.fields()
            }

            # ======================================================
            # Проверяем наличие всех 17 полей
            # ======================================================

            if not required_fields.issubset(layer_fields):
                excepted_layers.append(layer)

        # ==========================================================
        # Передаём ComboBox список слоёв, которые нужно исключить
        # ==========================================================

        combo.setExceptedLayerList(
            excepted_layers
        )

    def targetsLayerAdd(self):
        """
        Создание базы данных (если отсутствует)
        и создание слоя targets (если отсутствует).

        Логика:

        1. Если targets уже загружен в проект -
           ничего не делаем.

        2. Если GeoPackage существует:
           - если targets есть в БД -> загружаем его;
           - если targets нет в БД -> создаём его.

        3. Если GeoPackage не существует:
           - создаём GeoPackage;
           - создаём targets;
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

        # ==========================================================
        # 4. Проверяем, существует ли type_wellhead в GeoPackage
        # ==========================================================

        type_wellhead_uri = (
            f"{self.gpkg_path}|layername=type_wellhead"
        )

        type_wellhead_layer = QgsVectorLayer(
            type_wellhead_uri,
            "type_wellhead",
            "ogr"
        )

        # ==========================================================
        # 2. Если type_wellhead отсутствует — создаём его
        # ==========================================================

        if not type_wellhead_layer.isValid():

            print("type_wellhead отсутствует.")
            print("Создаём слой type_wellhead.")

            type_fields = QgsFields()

            type_fields.append(
                QgsField("id", QVariant.Int)
            )

            type_fields.append(
                QgsField("name", QVariant.String)
            )

            type_options = (
                QgsVectorFileWriter.SaveVectorOptions()
            )

            type_options.driverName = "GPKG"
            type_options.layerName = "type_wellhead"

            # Если GeoPackage уже существует,
            # создаём новый слой внутри него
            if os.path.isfile(self.gpkg_path):

                type_options.actionOnExistingFile = (
                    QgsVectorFileWriter.CreateOrOverwriteLayer
                )

            transform_context = (
                QgsProject.instance().transformContext()
            )

            type_writer = QgsVectorFileWriter.create(
                self.gpkg_path,
                type_fields,
                QgsWkbTypes.NoGeometry,
                QgsCoordinateReferenceSystem(),
                transform_context,
                type_options
            )

            if type_writer.hasError() != (
                QgsVectorFileWriter.NoError
            ):

                QMessageBox.critical(
                    self.tab,
                    "Ошибка создания type_wellhead",
                    type_writer.errorMessage()
                )

                del type_writer
                return

            del type_writer

            # ------------------------------------------------------
            # Загружаем созданный type_wellhead
            # ------------------------------------------------------

            type_wellhead_layer = QgsVectorLayer(
                type_wellhead_uri,
                "type_wellhead",
                "ogr"
            )

            if not type_wellhead_layer.isValid():

                QMessageBox.critical(
                    self.tab,
                    "Ошибка",
                    "Слой type_wellhead создан, "
                    "но не удалось его загрузить."
                )

                return

            # ------------------------------------------------------
            # Заполняем справочник
            # ------------------------------------------------------

            type_wellhead_layer.startEditing()

            feature = QgsFeature(
                type_wellhead_layer.fields()
            )

            feature["id"] = 0
            feature["name"] = "Позиция"

            type_wellhead_layer.addFeature(feature)

            feature = QgsFeature(
                type_wellhead_layer.fields()
            )

            feature["id"] = 1
            feature["name"] = "Устье"

            type_wellhead_layer.addFeature(feature)

            type_wellhead_layer.commitChanges()

            print("type_wellhead создан и заполнен.")


        else:

            print("type_wellhead уже существует в БД.")
        # ==========================================
        # 3. Проверяем, не загружен ли уже
        #    targets в проект QGIS
        # ==========================================

        loaded_layer = self.getTargetsLayer()

        if loaded_layer is not None:
            print("targets уже загружен в проект.")
            QMessageBox.information(
                self.tab,
                "Слой targets",
                "Слой targets уже загружен в проект."
            )
            return

        # ==========================================
        # 4. Если GeoPackage существует,
        #    проверяем наличие targets внутри БД
        # ==========================================

        if os.path.isfile(self.gpkg_path):
            existing_layer = QgsVectorLayer(
                f"{self.gpkg_path}|layername=targets",
                "targets",
                "ogr"
            )

            # ------------------------------------------
            # targets существует в БД
            # ------------------------------------------

            if existing_layer.isValid():

                print(
                    "targets существует в БД, "
                    "но ещё не загружен в проект."
                )

                 # Сначала добавляем слой в проект
                QgsProject.instance().addMapLayer(
                    existing_layer
                )

                # Затем настраиваем поле type
                self.setupWellheadTypeField(
                    existing_layer
                )
                self.tab.tabSettingsTargetsMLCBox.setLayer(existing_layer)
                QMessageBox.information(
                    self.tab,
                    "Слой targets",
                    "Существующий слой targets "
                    "загружен из базы данных."
                )

                return

        # ==========================================
        # 5. Если дошли сюда:
        #
        # - БД не существует
        # ИЛИ
        # - БД существует, но targets в ней нет
        #
        # Значит, создаём новый слой
        # ==========================================

        print("targets отсутствует в БД.")
        print("Создаём новый слой.")


        # ==========================================
        # 6. Поля слоя targets
        # ==========================================

        fields = QgsFields()

        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("type", QVariant.Int))
        fields.append(QgsField("lic", QVariant.String))
        fields.append(QgsField("field", QVariant.String))
        fields.append(QgsField("pad", QVariant.String))
        fields.append(QgsField("name",QVariant.String,len=100))
        fields.append(QgsField("num_txt",QVariant.String,len=100))
        fields.append(QgsField("num_int",QVariant.Int,len=100))
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
        options.layerName = "targets"

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
                f"Не удалось создать слой targets:\n"
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
            f"{self.gpkg_path}|layername=targets",
            "targets",
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
                "Слой targets создан, "
                "но не удалось его загрузить.\n\n"
                f"Ошибка: {layer.error().message()}"
            )

            return


        # ==========================================
        # 16. Добавляем слой в проект QGIS
        # ==========================================

        QgsProject.instance().addMapLayer(layer)
        self.tab.tabSettingsTargetsMLCBox.setLayer(layer)

        # ==========================================================
        # 12. Настраиваем поле type
        #
        # В выпадающем списке:
        #
        # Позиция -> 0
        # Устье   -> 1
        #
        # В БД сохраняется именно id.
        # ==========================================================

        self.setupWellheadTypeField(layer)
        # ==========================================
        # 17. Сообщение
        # ==========================================

        QMessageBox.information(
            self.tab,
            "Готово",
            "Новый слой targets создан "
            "и добавлен в QGIS."
        )





    