import os
import json
import random

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFields,
    QgsFeature
)

from PyQt5.QtCore import QVariant


class LayerManager:


    def __init__(self, dialog):

        # ссылка на главное окно
        self.dialog = dialog
        # ======================================================
    # Работа с исходными слоями
    # ======================================================


    # Добавление исходного слоя позиций

    def addPositionLayer(self):

        layer = self.dialog.mMapLayerComboBoxPositions.currentLayer()
    
        if layer is None:
            return
    
        if layer not in self.dialog.positionLayers:

            self.dialog.positionLayers.append(layer)

            self.dialog.listWidgetPositionLayers.addItem(
                layer.name()
            )


    # Удаление исходного слоя позиций

    def removePositionLayer(self):

        selected = self.dialog.listWidgetPositionLayers.currentRow()
    
        if selected >= 0:

            self.dialog.listWidgetPositionLayers.takeItem(
                selected
            )

            del self.dialog.positionLayers[selected]



    # Добавление исходного слоя целей

    def addTargetLayer(self):

        layer = self.dialog.mMapLayerComboBoxTargets.currentLayer()
    
        if layer is None:
            return
    
        if layer not in self.dialog.targetLayers:

            self.dialog.targetLayers.append(layer)

            self.dialog.listWidgetTargetLayers.addItem(
                layer.name()
            )



    # Удаление исходного слоя целей

    def removeTargetLayer(self):

        selected = self.dialog.listWidgetTargetLayers.currentRow()
    
        if selected >= 0:

            self.dialog.listWidgetTargetLayers.takeItem(
                selected
            )

            del self.dialog.targetLayers[selected]

        # Создание рабочего слоя позиций

    def createPositionsLayer(self):

        # удалить старый рабочий слой если есть
        if self.dialog.layerPositions:
            QgsProject.instance().removeMapLayer(self.dialog.layerPositions.id())
            self.dialog.layerPositions = None
    
        # создать новый слой
        self.dialog.layerPositions = QgsVectorLayer(
            "Point?crs=EPSG:4284",
            "Positions_WORK",
            "memory"
        )
        
        # Добавление атрибутов в новый слой
        dp = self.dialog.layerPositions.dataProvider()
    
        fields = QgsFields()
        fields.append(QgsField("name", QVariant.String))
        fields.append(QgsField("pos", QVariant.String))
        fields.append(QgsField("ground", QVariant.String))
        fields.append(QgsField("rotor", QVariant.String))
        fields.append(QgsField("tfield", QVariant.String))
        fields.append(QgsField("oilfield", QVariant.String))
        fields.append(QgsField("oilfield_name", QVariant.String))
        fields.append(QgsField("source", QVariant.String))

        dp.addAttributes(fields)
        self.dialog.layerPositions.updateFields()
    
        QgsProject.instance().addMapLayer(self.dialog.layerPositions)

        self.importPositions()

     # Создание рабочего слоя целей

    def createTargetsLayer(self):

        # удалить старый слой если есть
        if self.dialog.layerTargets:
            QgsProject.instance().removeMapLayer(self.dialog.layerTargets.id())
            self.dialog.layerTargets = None
    
        # создать новый слой
        self.dialog.layerTargets = QgsVectorLayer(
            "Point?crs=EPSG:4284",
            "Targets_WORK",
            "memory"
        )
    
        dp = self.dialog.layerTargets.dataProvider()
    
        fields = QgsFields()

        fields.append(QgsField("tid", QVariant.String))
        fields.append(QgsField("oilfield", QVariant.String))
        fields.append(QgsField("source", QVariant.String))
        fields.append(QgsField("ttvd", QVariant.String))
    
        dp.addAttributes(fields)

        self.dialog.layerTargets.updateFields()
    
        QgsProject.instance().addMapLayer(self.dialog.layerTargets)

        self.importTargets()

    # Создание рабочего слоя месторождений
    
    def createOilFieldsLayer(self):

        # удалить старый слой
        if self.dialog.layerOilfields:
            QgsProject.instance().removeMapLayer(
                self.dialog.layerOilfields.id()
            )

            self.dialog.layerOilfields = None
    
        # негеометрический memory-слой
        self.dialog.layerOilfields = QgsVectorLayer(
            "None",
            "Oilfields_WORK",
            "memory"
        )
    
        dp = self.dialog.layerOilfields.dataProvider()
    
        fields = QgsFields()

        fields.append(QgsField("oilfield", QVariant.String))
        fields.append(QgsField("name", QVariant.String))
    
        dp.addAttributes(fields)

        self.dialog.layerOilfields.updateFields()
    
        QgsProject.instance().addMapLayer(
            self.dialog.layerOilfields
        )
    
        self.importOilfields()

    # Импорт позиций в Positions_WORK
    
    def importPositions(self):

        if self.dialog.layerPositions is None:
            return
    
        dp = self.dialog.layerPositions.dataProvider()
    
        features_to_add = []
    
        for layer in self.dialog.positionLayers:
    
            mapping = self.getPositionMapping(layer)

            if mapping is None:
                continue
    
            for feature in layer.getFeatures():

                newFeature = QgsFeature(self.dialog.layerPositions.fields())
                newFeature.setGeometry(feature.geometry())
            
            
                newFeature["name"] = self.getMappedValue(feature, mapping, "name")
                newFeature["pos"] = self.getMappedValue(feature, mapping, "pos")
                newFeature["ground"] = self.getMappedValue(feature, mapping, "ground")
                newFeature["rotor"] = self.getMappedValue(feature, mapping, "rotor")
                newFeature["tfield"] = self.getMappedValue(feature, mapping, "lic")
                newFeature["oilfield"] = self.getMappedValue(feature, mapping, "oilfield").split("_")[0]
                newFeature["oilfield_name"] = self.getMappedValue(feature, mapping, "oilfield_name").strip().title()
                newFeature["source"] = layer.name()
            
                features_to_add.append(newFeature)
    
        dp.addFeatures(features_to_add)

        print("Добавлено:", len(features_to_add))
        print("В рабочем слое:", self.dialog.layerPositions.featureCount())
    
        self.dialog.layerPositions.updateExtents()
        self.dialog.layerPositions.triggerRepaint()

# Заполнение рабочего слоя целей

    def importTargets(self):
    
        if self.dialog.layerTargets is None:
            return
            
        plugin_dir = os.path.dirname(__file__)

        settings_path = os.path.join(
            plugin_dir,
            "settings",
            "settings.json"
        )
        
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
        
        mapping = settings["Target"]["Layers"]["default"]

        dp = self.dialog.layerTargets.dataProvider()
    
        features_to_add = []
    
        for layer in self.dialog.targetLayers:
    
            if mapping is None:
                continue
    
            for feature in layer.getFeatures():
    
                newFeature = QgsFeature(self.dialog.layerTargets.fields())

                newFeature.setGeometry(feature.geometry())

                newFeature["tid"] = self.getMappedValue(
                    feature,
                    mapping,
                    "tid"
                )

                newFeature["oilfield"] = self.getMappedValue(
                    feature,
                    mapping,
                    "oilfield"
                ).split("_")[0]

                newFeature["source"] = layer.name()


                # ======================================================
                # Временное тестовое значение ttvd
                # Используется для проверки расчета отклонений
                # Позже удалить
                # ======================================================

                ttvd = self.getMappedValue(
                    feature,
                    mapping,
                    "ttvd"
                )

                if str(ttvd).strip() in ("", "NULL", "None"):
                    ttvd = random.randint(-2000, -100)

                
                newFeature["ttvd"] = str(ttvd)

                features_to_add.append(newFeature)
    
        dp.addFeatures(features_to_add)

        self.dialog.layerTargets.updateExtents()
        self.dialog.layerTargets.triggerRepaint()

# Заполнение OilFields_WORK

    def importOilfields(self):
    
        if self.dialog.layerOilfields is None:
            return
    
    
        dp = self.dialog.layerOilfields.dataProvider()
    
        features_to_add = []
    
        # словарь для удаления дублей
        oilfields = {}
    
    
        # ============================
        # 1. Сначала берем из Positions_WORK
        # ============================
    
        if self.dialog.layerPositions is not None:
    
            for feature in self.dialog.layerPositions.getFeatures():
    
                code = str(feature["oilfield"])

                name = str(feature["oilfield_name"]).upper()
    
    
                if code not in oilfields:

                    oilfields[code] = name
    
    
    
        # ============================
        # 2. Добавляем коды из Targets_WORK,
        #    если их еще нет
        # ============================
    
        if self.dialog.layerTargets is not None:
    
            for feature in self.dialog.layerTargets.getFeatures():
    
                code = str(feature["oilfield"])
    
    
                if code not in oilfields:

                    oilfields[code] = ""
    
    
    
        # ============================
        # Запись в OilFields_WORK
        # ============================
    
        for code, name in oilfields.items():
    
            newFeature = QgsFeature(
                self.dialog.layerOilfields.fields()
            )
    
    
            newFeature["oilfield"] = code

            newFeature["name"] = name
    
    
            features_to_add.append(newFeature)
    

        dp.addFeatures(features_to_add)
    
    
        self.dialog.layerOilfields.updateExtents()

        self.dialog.layerOilfields.triggerRepaint()

    # Определение соответствия полей источника

    def getPositionMapping(self, layer):
        """
        Определяет тип слоя (ARMM / GeoBD)
        и возвращает соответствующий mapping из settings.json
        """
    
        plugin_dir = os.path.dirname(__file__)
        settings_path = os.path.join(
            plugin_dir,
            "settings",
            "settings.json"
        )
    
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
    
        # проверка что слой существует
        if layer is None:
            return None

        # -----------------------------
        # 1. Определяем тип слоя
        # -----------------------------
    
        fields = layer.fields()
    
        # GeoBD признак 
        if fields.indexOf("license_area") != -1:
            return settings["WellHead"]["Layers"]["geobd"]
    
        # иначе считаем ARMM
        else:
            return settings["WellHead"]["Layers"]["armm"]



    # Получение значения поля с учетом mapping

    def getMappedValue(self, feature, mapping, key):

        field = mapping.get(key)
    
        if field is None:
            return ""
    
        if field == "none":
            return ""
    
        if feature.fields().indexOf(field) == -1:
            return ""
    
        value = feature[field]
    
        if value is None:
            return ""
    
        return str(value)



    

