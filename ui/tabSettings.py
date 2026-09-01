import os
import json
from pathlib import Path

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
    QgsDefaultValue,
)
from PyQt5.QtCore import QVariant
from qgis.utils import iface
from qgis.gui import QgsMapToolIdentifyFeature


class TabSettings:
    """Вкладка 'Рабочие слои'"""

    def __init__(self, dialog):
        self.tab = dialog
        self.gpkg_path = ''
        self.wellhead_name = ''
        self.welltarget_name = ''
        self.wellbore_name = ''
        self.read_settings()

    def read_settings(self):
        # Получаем абсолютный путь к папке, где лежит этот скрипт
        BASE_DIR = Path(__file__).resolve().parent.parent
        config_path = os.path.join(BASE_DIR, "settings", "config.json")
        
        print(f'BASE_DIR: {config_path}')
        # Открываем файл с указанием кодировки utf-8
        with open(config_path, "r", encoding="utf-8") as file:
            config = json.load(file)

        self.wellhead_name = config["wellhead"]
        self.welltarget_name = config["welltarget"]
        self.wellbore_name = config["wellbore"]


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
                layer.name() == self.wellhead_name
                and layer.source().startswith(self.gpkg_path)
            ):
                return layer

        return None


    def getWelltargetLayer(self):
        """
        Проверяет, загружен ли слой welltarget
        из текущего GeoPackage в проект QGIS.

        Возвращает слой, если он уже загружен.
        Иначе возвращает None.
        """

        for layer in QgsProject.instance().mapLayers().values():

            if (
                layer.name() == self.welltarget_name
                and layer.source().startswith(self.gpkg_path)
            ):
                return layer

        return None


    def getWellboreLayer(self):
        """
        Проверяет, загружен ли слой wellbore
        из текущего GeoPackage в проект QGIS.

        Возвращает слой, если он уже загружен.
        Иначе возвращает None.
        """

        for layer in QgsProject.instance().mapLayers().values():

            if (
                layer.name() == self.wellbore_name
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
        # 4. Проверяем, существует ли wellhead_type в GeoPackage
        # ==========================================================

        wellhead_type_uri = (
            f"{self.gpkg_path}|layername=wellhead_type"
        )

        wellhead_type_layer = QgsVectorLayer(
            wellhead_type_uri,
            "wellhead_type",
            "ogr"
        )

        # ==========================================================
        # 2. Если wellhead_type отсутствует — создаём его
        # ==========================================================

        if not wellhead_type_layer.isValid():

            print("wellhead_type отсутствует.")
            print("Создаём слой wellhead_type.")

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
            type_options.layerName = "wellhead_type"

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
                    "Ошибка создания wellhead_type",
                    type_writer.errorMessage()
                )

                del type_writer
                return

            del type_writer

            # ------------------------------------------------------
            # Загружаем созданный wellhead_type
            # ------------------------------------------------------

            wellhead_type_layer = QgsVectorLayer(
                wellhead_type_uri,
                "wellhead_type",
                "ogr"
            )

            if not wellhead_type_layer.isValid():

                QMessageBox.critical(
                    self.tab,
                    "Ошибка",
                    "Слой wellhead_type создан, "
                    "но не удалось его загрузить."
                )

                return

            # ------------------------------------------------------
            # Заполняем справочник
            # ------------------------------------------------------

            wellhead_type_layer.startEditing()

            feature = QgsFeature(
                wellhead_type_layer.fields()
            )

            feature["id"] = 0
            feature["name"] = "Позиция"

            wellhead_type_layer.addFeature(feature)

            feature = QgsFeature(
                wellhead_type_layer.fields()
            )

            feature["id"] = 1
            feature["name"] = "Устье"

            wellhead_type_layer.addFeature(feature)

            wellhead_type_layer.commitChanges()

            print("wellhead_type создан и заполнен.")


        else:

            print("wellhead_type уже существует в БД.")
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
                f"{self.gpkg_path}|layername={self.wellhead_name}",
                f"{self.wellhead_name}",
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
        fields.append(QgsField("rig", QVariant.String))
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
        options.layerName = self.wellhead_name

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
            f"{self.gpkg_path}|layername={self.wellhead_name}",
            f"{self.wellhead_name}",
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
        # После загрузки wellhead
        self.connectWellheadSignals()

        # И сразу обновляем wellbore,
        # если он уже загружен
        self.updateWellboreWellheadField()

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
        # 2. Открываем wellhead_type из БД
        #
        # ВАЖНО:
        # этот слой НЕ добавляется в проект
        # ==========================================================

        wellhead_type_uri = (
            f"{self.gpkg_path}|layername=wellhead_type"
        )

        type_layer = QgsVectorLayer(
            wellhead_type_uri,
            "wellhead_type",
            "ogr"
        )

        if not type_layer.isValid():

            print(
                "wellhead_type отсутствует или "
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
                "В wellhead_type нет записей."
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
        # 7. Устанавливаем значение по умолчанию
        # Позиция = id 0
        # ==========================================================

        layer.setDefaultValueDefinition(
            type_field_index,
            QgsDefaultValue("0")
        )

        # ==========================================================
        # 8. Проверяем, что настройка действительно установилась
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
    def setupWelltargetTypeField(self, layer):
        """
        Настраивает поле type слоя welltarget
        как выпадающий список ValueMap.

        Отображаемое значение:
        Кровля 
        Подошва

        В поле type записывается:
            0
            1
        """

        # ==========================================================
        # 1. Ищем поле type
        # ==========================================================

        type_field_index = layer.fields().indexOf("type")

        if type_field_index == -1:
            print("Поле type отсутствует в welltarget.")
            return

        # ==========================================================
        # 2. Открываем welltarget_type из БД
        #
        # ВАЖНО:
        # этот слой НЕ добавляется в проект
        # ==========================================================

        welltarget_type_uri = (
            f"{self.gpkg_path}|layername=welltarget_type"
        )

        type_layer = QgsVectorLayer(
            welltarget_type_uri,
            "welltarget_type",
            "ogr"
        )

        if not type_layer.isValid():

            print(
                "welltarget_type отсутствует или "
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
                "В welltarget_type нет записей."
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

        layer.setDefaultValueDefinition(
                    type_field_index,
                    QgsDefaultValue("0")
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



    def setupWellboreTypeField(self, layer):
        """
        Настраивает поле type слоя wellbore
        как выпадающий список ValueMap.

        Отображаемое значение:
        Кровля 
        Подошва

        В поле type записывается:
            0
            1
        """

        # ==========================================================
        # 1. Ищем поле type
        # ==========================================================

        type_field_index = layer.fields().indexOf("type")

        if type_field_index == -1:
            print("Поле type отсутствует в wellbore.")
            return

        # ==========================================================
        # 2. Открываем wellbore_type из БД
        #
        # ВАЖНО:
        # этот слой НЕ добавляется в проект
        # ==========================================================

        wellbore_type_uri = (
            f"{self.gpkg_path}|layername=wellbore_type"
        )

        type_layer = QgsVectorLayer(
            wellbore_type_uri,
            "wellbore_type",
            "ogr"
        )

        if not type_layer.isValid():

            print(
                "wellbore_type отсутствует или "
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
                "В wellbore_type нет записей."
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

        layer.setDefaultValueDefinition(
                    type_field_index,
                    QgsDefaultValue("0")
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

    def selectWelltargetInComboBox(self):
        """
        Если слой welltarget уже есть в проекте,
        выбирает его в ComboBox.
        """

        welltarget_layer = self.getWelltargetLayer()

        if welltarget_layer is not None:
            self.tab.tabSettingsTargetsMLCBox.setLayer(
                welltarget_layer
            )

    def selectWellboreInComboBox(self):
        """
        Если слой wellbore уже есть в проекте,
        выбирает его в ComboBox.
        """

        wellbore_layer = self.getWellboreLayer()

        if wellbore_layer is not None:
            self.tab.tabSettingsBoresMLCBox.setLayer(
                wellbore_layer
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
            "rig",
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

        print(
            "EXCEPTED:",
            [layer.name() for layer in excepted_layers]
        )

    def filterWelltargetLayers(self):
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
            "stratum",
            "pad",
            "name",
            "num_txt",
            "num_int",
            "rel",
            "north",
            "east",
            "depth",
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

    def filterWellboreLayers(self):
        """
        Фильтрует слои для ComboBox bores.

        В список попадают только:
        - точечные слои;
        - слои со всеми 17 полями bores.
        """

        combo = self.tab.tabSettingsBoresMLCBox

        required_fields = {
            "id",
            "type",
            "lic",
            "field",
            "pad",
            "name",
            "wellhead_id",
            "welltarget",
            "rel",
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

            if layer.geometryType() != QgsWkbTypes.NullGeometry:
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

    def welltargetLayerAdd(self):
        """
        Создание базы данных (если отсутствует)
        и создание слоя welltarget (если отсутствует).

        Логика:

        1. Если welltarget уже загружен в проект -
           ничего не делаем.

        2. Если GeoPackage существует:
           - если welltarget есть в БД -> загружаем его;
           - если welltarget нет в БД -> создаём его.

        3. Если GeoPackage не существует:
           - создаём GeoPackage;
           - создаём welltarget;
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
        # 4. Проверяем, существует ли welltarget_type в GeoPackage
        # ==========================================================

        welltarget_type_uri = (
            f"{self.gpkg_path}|layername=welltarget_type"
        )

        welltarget_type_layer = QgsVectorLayer(
            welltarget_type_uri,
            "welltarget_type",
            "ogr"
        )

        # ==========================================================
        # 2. Если welltarget_type отсутствует — создаём его
        # ==========================================================

        if not welltarget_type_layer.isValid():

            print("welltarget_type отсутствует.")
            print("Создаём слой welltarget_type.")

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
            type_options.layerName = "welltarget_type"

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
                    "Ошибка создания welltarget_type",
                    type_writer.errorMessage()
                )

                del type_writer
                return

            del type_writer

            # ------------------------------------------------------
            # Загружаем созданный welltarget_type
            # ------------------------------------------------------

            welltarget_type_layer = QgsVectorLayer(
                welltarget_type_uri,
                "welltarget_type",
                "ogr"
            )

            if not welltarget_type_layer.isValid():

                QMessageBox.critical(
                    self.tab,
                    "Ошибка",
                    "Слой welltarget_type создан, "
                    "но не удалось его загрузить."
                )

                return

            # ------------------------------------------------------
            # Заполняем справочник
            # ------------------------------------------------------

            welltarget_type_layer.startEditing()

            feature = QgsFeature(
                welltarget_type_layer.fields()
            )

            feature["id"] = 0
            feature["name"] = "Кровля"

            welltarget_type_layer.addFeature(feature)

            feature = QgsFeature(
                welltarget_type_layer.fields()
            )

            feature["id"] = 1
            feature["name"] = "Подошва"

            welltarget_type_layer.addFeature(feature)

            welltarget_type_layer.commitChanges()

            print("welltarget_type создан и заполнен.")


        else:

            print("welltarget_type уже существует в БД.")
        # ==========================================
        # 3. Проверяем, не загружен ли уже
        #    welltarget в проект QGIS
        # ==========================================

        loaded_layer = self.getWelltargetLayer()

        if loaded_layer is not None:
            print("welltarget уже загружен в проект.")
            QMessageBox.information(
                self.tab,
                "Слой welltarget",
                "Слой welltarget уже загружен в проект."
            )
            return

        # ==========================================
        # 4. Если GeoPackage существует,
        #    проверяем наличие welltarget внутри БД
        # ==========================================

        if os.path.isfile(self.gpkg_path):
            existing_layer = QgsVectorLayer(
                f"{self.gpkg_path}|layername={self.welltarget_name}",
                f"{self.welltarget_name}",
                "ogr"
            )

            # ------------------------------------------
            # welltarget существует в БД
            # ------------------------------------------

            if existing_layer.isValid():

                print(
                    "welltarget существует в БД, "
                    "но ещё не загружен в проект."
                )

                 # Сначала добавляем слой в проект
                QgsProject.instance().addMapLayer(
                    existing_layer
                )

                # Затем настраиваем поле type
                self.setupWelltargetTypeField(
                    existing_layer
                )
                self.tab.tabSettingsTargetsMLCBox.setLayer(existing_layer)
                QMessageBox.information(
                    self.tab,
                    "Слой welltarget",
                    "Существующий слой welltarget "
                    "загружен из базы данных."
                )

                return

        # ==========================================
        # 5. Если дошли сюда:
        #
        # - БД не существует
        # ИЛИ
        # - БД существует, но welltarget в ней нет
        #
        # Значит, создаём новый слой
        # ==========================================

        print("welltarget отсутствует в БД.")
        print("Создаём новый слой.")


        # ==========================================
        # 6. Поля слоя welltarget
        # ==========================================

        fields = QgsFields()

        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("type", QVariant.Int))
        fields.append(QgsField("lic", QVariant.String))
        fields.append(QgsField("field", QVariant.String))
        fields.append(QgsField("stratum", QVariant.String))
        fields.append(QgsField("pad", QVariant.String))
        fields.append(QgsField("name",QVariant.String,len=100))
        fields.append(QgsField("num_txt",QVariant.String,len=100))
        fields.append(QgsField("num_int",QVariant.Int))
        fields.append(QgsField("rel", QVariant.Bool))
        fields.append(QgsField("north", QVariant.Double))
        fields.append(QgsField("east", QVariant.Double))
        fields.append(QgsField("depth", QVariant.Double))
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
        options.layerName = self.welltarget_name

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
                f"Не удалось создать слой welltarget:\n"
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
            f"{self.gpkg_path}|layername={self.welltarget_name}",
            f"{self.welltarget_name}",
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
                "Слой welltarget создан, "
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
        # Кровля -> 0
        # Подошва   -> 1
        #
        # В БД сохраняется именно id.
        # ==========================================================

        self.setupWelltargetTypeField(layer)
        # ==========================================
        # 17. Сообщение
        # ==========================================

        QMessageBox.information(
            self.tab,
            "Готово",
            "Новый слой welltarget создан "
            "и добавлен в QGIS."
        )


    def wellboreLayerAdd(self):
        """
        Создание базы данных (если отсутствует)
        и создание слоя wellbore (если отсутствует).

        Логика:

        1. Если wellbore уже загружен в проект -
           ничего не делаем.

        2. Если GeoPackage существует:
           - если wellbore есть в БД -> загружаем его;
           - если wellbore нет в БД -> создаём его.

        3. Если GeoPackage не существует:
           - создаём GeoPackage;
           - создаём wellbore;
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
        # 4. Проверяем, существует ли wellbore_type в GeoPackage
        # ==========================================================

        wellbore_type_uri = (
            f"{self.gpkg_path}|layername=wellbore_type"
        )

        wellbore_type_layer = QgsVectorLayer(
            wellbore_type_uri,
            "wellbore_type",
            "ogr"
        )

        # ==========================================================
        # 2. Если wellbore_type отсутствует — создаём его
        # ==========================================================

        if not wellbore_type_layer.isValid():

            print("wellbore_type отсутствует.")
            print("Создаём слой wellbore_type.")

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
            type_options.layerName = "wellbore_type"

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
                    "Ошибка создания wellbore_type",
                    type_writer.errorMessage()
                )

                del type_writer
                return

            del type_writer

            # ------------------------------------------------------
            # Загружаем созданный wellbore_type
            # ------------------------------------------------------

            wellbore_type_layer = QgsVectorLayer(
                wellbore_type_uri,
                "wellbore_type",
                "ogr"
            )

            if not wellbore_type_layer.isValid():

                QMessageBox.critical(
                    self.tab,
                    "Ошибка",
                    "Слой wellbore_type создан, "
                    "но не удалось его загрузить."
                )

                return

            # ------------------------------------------------------
            # Заполняем справочник
            # ------------------------------------------------------

            wellbore_type_layer.startEditing()

            feature = QgsFeature(wellbore_type_layer.fields())
            feature["id"] = 0
            feature["name"] = "Основной проектный"
            wellbore_type_layer.addFeature(feature)

            feature = QgsFeature(wellbore_type_layer.fields())
            feature["id"] = 1
            feature["name"] = "Основной фактический"
            wellbore_type_layer.addFeature(feature)

            feature = QgsFeature(wellbore_type_layer.fields())
            feature["id"] = 2
            feature["name"] = "Вероятный верх"
            wellbore_type_layer.addFeature(feature)

            feature = QgsFeature(wellbore_type_layer.fields())
            feature["id"] = 3
            feature["name"] = "Вероятный запад"
            wellbore_type_layer.addFeature(feature)

            feature = QgsFeature(wellbore_type_layer.fields())
            feature["id"] = 4
            feature["name"] = "Вероятный низ"
            wellbore_type_layer.addFeature(feature)

            feature = QgsFeature(wellbore_type_layer.fields())
            feature["id"] = 5
            feature["name"] = "Вероятный восток"
            wellbore_type_layer.addFeature(feature)

            wellbore_type_layer.commitChanges()

            print("wellbore_type создан и заполнен.")


        else:

            print("wellbore_type уже существует в БД.")
        # ==========================================
        # 3. Проверяем, не загружен ли уже
        #    welltarget в проект QGIS
        # ==========================================

        loaded_layer = self.getWellboreLayer()

        if loaded_layer is not None:
            print("wellbore already загружен в проект.")
            QMessageBox.information(
                self.tab,
                "Слой wellbore",
                "Слой wellbore уже загружен в проект."
            )
            return

        # ==========================================
        # 4. Если GeoPackage существует,
        #    проверяем наличие welltarget внутри БД
        # ==========================================

        if os.path.isfile(self.gpkg_path):
            existing_layer = QgsVectorLayer(
                f"{self.gpkg_path}|layername={self.wellbore_name}",
                f"{self.wellbore_name}",
                "ogr"
            )

            # ------------------------------------------
            # wellbore существует в БД
            # ------------------------------------------

            if existing_layer.isValid():

                print(
                    "wellbore существует в БД, "
                    "но ещё не загружен в проект."
                )

                 # Сначала добавляем слой в проект
                QgsProject.instance().addMapLayer(
                    existing_layer
                )

                # Затем настраиваем поле type
                self.setupWellboreTypeField(
                    existing_layer
                )
                self.setupWellboreWellheadField(existing_layer)
                self.connectWellheadSignals()

                self.tab.tabSettingsBoresMLCBox.setLayer(existing_layer)
                QMessageBox.information(
                    self.tab,
                    "Слой wellbore",
                    "Существующий слой wellbore "
                    "загружен из базы данных."
                )

                return

        # ==========================================
        # 5. Если дошли сюда:
        #
        # - БД не существует
        # ИЛИ
        # - БД существует, но wellbore в ней нет
        #
        # Значит, создаём новый слой
        # ==========================================

        print("wellbore отсутствует в БД.")
        print("Создаём новый слой.")


        # ==========================================
        # 6. Поля слоя wellbore
        # ==========================================

        fields = QgsFields()

        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("type", QVariant.Int))
        fields.append(QgsField("lic", QVariant.String))
        fields.append(QgsField("field", QVariant.String))
        fields.append(QgsField("pad", QVariant.String))
        fields.append(QgsField("name",QVariant.String,len=100))
        fields.append(QgsField("wellhead_id",QVariant.Int))
        fields.append(QgsField("welltarget",QVariant.String,len=100))
        fields.append(QgsField("rel", QVariant.Bool))
        fields.append(QgsField("note", QVariant.String))

        # ==========================================
        # 7. Тип геометрии и CRS
        # ==========================================

        geometry_type = QgsWkbTypes.NoGeometry

        crs = QgsCoordinateReferenceSystem()

        # ==========================================
        # 8. Настройки создания GeoPackage
        # ==========================================

        options = QgsVectorFileWriter.SaveVectorOptions()

        options.driverName = "GPKG"
        options.layerName = self.wellbore_name

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
                f"Не удалось создать слой welltarget:\n"
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
            f"{self.gpkg_path}|layername={self.wellbore_name}",
            f"{self.wellbore_name}",
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
                "Слой welltarget создан, "
                "но не удалось его загрузить.\n\n"
                f"Ошибка: {layer.error().message()}"
            )

            return


        # ==========================================
        # 16. Добавляем слой в проект QGIS
        # ==========================================

        QgsProject.instance().addMapLayer(layer)
        self.tab.tabSettingsBoresMLCBox.setLayer(layer)

        # ==========================================================
        # 12. Настраиваем поле type
        #
        # В выпадающем списке:
        #
        # Кровля -> 0
        # Подошва   -> 1
        #
        # В БД сохраняется именно id.
        # ==========================================================

        self.setupWellboreTypeField(layer)
        self.setupWellboreWellheadField(layer)
        self.connectWellheadSignals()
        # ==========================================
        # 17. Сообщение
        # ==========================================

        QMessageBox.information(
            self.tab,
            "Готово",
            "Новый слой wellbore создан "
            "и добавлен в QGIS."
        )


    def setupWellboreWellheadField(self, layer):
        """
        Настраивает wellhead_id как выпадающий список.

        Список формируется из слоя wellhead.

        Отображение:
            Устье (1)
            Позиция (2)

        В БД сохраняется только id.
        """

        field_index = layer.fields().indexOf("wellhead_id")

        if field_index == -1:
            print("Поле wellhead_id отсутствует.")
            return

        # Получаем wellhead
        wellhead_layer = self.getWellheadLayer()

        value_map = []

        # Если wellhead уже существует и содержит объекты —
        # формируем список
        if wellhead_layer is not None and wellhead_layer.isValid():

            if (
                wellhead_layer.fields().indexOf("id") != -1
                and wellhead_layer.fields().indexOf("name") != -1
            ):

                for feature in wellhead_layer.getFeatures():

                    wellhead_id = feature["id"]
                    wellhead_name = feature["name"]

                    if wellhead_id is None:
                        continue

                    if wellhead_name is None:
                        wellhead_name = ""

                    display_name = (
                        f"{wellhead_name} ({wellhead_id})"
                    )

                    value_map.append({
                        display_name: wellhead_id
                    })

        # ==========================================================
        # ВАЖНО:
        # ValueMap устанавливаем ВСЕГДА.
        #
        # Даже если value_map пока пустой.
        # ==========================================================

        widget_setup = QgsEditorWidgetSetup(
            "ValueMap",
            {
                "map": value_map
            }
        )

        layer.setEditorWidgetSetup(
            field_index,
            widget_setup
        )

        layer.updateFields()

        print(
            "wellhead_id настроен как ValueMap:",
            value_map
        )

    def updateWellboreWellheadField(self):
        """
        Обновляет список значений wellhead_id.
        """

        wellbore_layer = self.getWellboreLayer()

        if wellbore_layer is None:
            return

        self.setupWellboreWellheadField(
            wellbore_layer
        )

    def connectWellheadSignals(self):
        """
        Подключает сигналы слоя wellhead только один раз.
        """

        wellhead_layer = self.getWellheadLayer()

        if wellhead_layer is None:
            print("wellhead не найден.")
            return

        # Если сигналы уже подключены,
        # повторно ничего не делаем
        if getattr(self, "_wellhead_signals_connected", False):
            print("Сигналы wellhead уже подключены.")
            return

        # ==========================================
        # Добавление объекта
        # ==========================================

        wellhead_layer.featureAdded.connect(
            self._onWellheadChanged
        )

        # ==========================================
        # Удаление объекта
        # ==========================================

        wellhead_layer.featureDeleted.connect(
            self._onWellheadChanged
        )

        # ==========================================
        # Изменение атрибутов
        # ==========================================

        wellhead_layer.attributeValueChanged.connect(
            self._onWellheadAttributeChanged
        )

        self._wellhead_signals_connected = True

        print("Сигналы wellhead подключены.")

    def _onWellheadChanged(self, fid):
        """
        Вызывается при добавлении или удалении
        объекта wellhead.
        """

        self.updateWellboreWellheadField()

    def _onWellheadAttributeChanged(self, fid, field, value):
        """
        Вызывается при изменении атрибута wellhead.
        """

        self.updateWellboreWellheadField()

    def _onLayersChanged(self, *args):
        """Обновляет фильтрацию ComboBox после изменения проекта."""

        self.filterWellheadLayers()
        self.filterWelltargetLayers()
        self.filterWellboreLayers()

    