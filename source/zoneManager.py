from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsProject,
    QgsRendererCategory,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from .zone import Zone

COUCHE_NOM = "Zones de Vol (Gestion)"


class ZoneManager:
    """
    Gère la couche mémoire des zones. Une zone de priorité supérieure ou égale
    découpe les zones existantes ; une zone de priorité inférieure est découpée par elles.
    """

    def __init__(self):
        self.priorities = {"ban": 4, "fly": 3, "buffer": 1, "cont": 2}
        self.layer: QgsVectorLayer | None = None
        self.layer_id: str | None = None
        self.creer_couche()

    def _couche_presente(self) -> bool:
        return self.layer_id is not None and QgsProject.instance().mapLayer(self.layer_id) is not None

    def creer_couche(self) -> None:
        """Crée (ou recrée) la couche mémoire en Lambert-93 (EPSG:2154) avec son style."""
        self.supprimer_couche()

        self.layer = QgsVectorLayer("Polygon?crs=EPSG:2154", COUCHE_NOM, "memory")
        self.layer_id = self.layer.id()
        self.layer.dataProvider().addAttributes([
            QgsField("id", QVariant.Int),
            QgsField("type", QVariant.String),
            QgsField("priority", QVariant.Int),
        ])
        self.layer.updateFields()
        self.appliquer_style()
        QgsProject.instance().addMapLayer(self.layer)

    def appliquer_style(self) -> None:
        """Définit des couleurs fixes et transparentes pour chaque type de zone."""
        couleurs = {
            "ban": QColor(0, 0, 0, 100),         # noir semi-transparent
            "fly": QColor(0, 191, 99, 100),      # vert semi-transparent
            "buffer": QColor(255, 79, 79, 100),  # rouge semi-transparent
            "cont": QColor(255, 145, 77, 100),   # orange semi-transparent
        }

        categories = []
        for zone_type, color in couleurs.items():
            symbol = QgsFillSymbol.createSimple({
                "color": color.name(),
                "color_alpha": str(color.alpha() / 255.0),
                "outline_color": "black",
                "outline_width": "0.25",
            })
            categories.append(QgsRendererCategory(zone_type, symbol, zone_type.upper()))

        self.layer.setRenderer(QgsCategorizedSymbolRenderer("type", categories))

    def supprimer_couche(self) -> None:
        """Supprime proprement la couche du projet QGIS."""
        if self._couche_presente():
            QgsProject.instance().removeMapLayer(self.layer_id)
        self.layer = None
        self.layer_id = None

    def ajouter_zone(self, zone: Zone) -> None:
        if zone.type not in self.priorities:
            print(f"ERREUR : type de zone invalide '{zone.type}'")
            return
        if not zone.is_valid():
            print(f"ERREUR : géométrie invalide pour la zone '{zone.type}'")
            return
        if not self._couche_presente():
            self.creer_couche()

        priorite = self.priorities[zone.type]
        geom_nouvelle = zone.geometrie()

        a_supprimer = []
        a_modifier = []  # liste de (id, nouvelle géométrie)

        for feat in self.layer.getFeatures():
            geom_existante = feat.geometry()
            if not geom_nouvelle.intersects(geom_existante):
                continue

            if priorite >= feat["priority"]:
                reste = geom_existante.difference(geom_nouvelle)
                if reste.isEmpty():
                    a_supprimer.append(feat.id())
                else:
                    a_modifier.append((feat.id(), reste))
            else:
                geom_nouvelle = geom_nouvelle.difference(geom_existante)
                if geom_nouvelle.isEmpty():
                    return  # la zone entière est recouverte par une zone prioritaire

        self.layer.startEditing()
        if a_supprimer:
            self.layer.deleteFeatures(a_supprimer)
        for fid, geom in a_modifier:
            self.layer.changeGeometry(fid, geom)

        nouvelle = QgsFeature(self.layer.fields())
        nouvelle.setGeometry(geom_nouvelle)
        nouvelle.setAttributes([self.layer.featureCount() + 1, zone.type, priorite])
        self.layer.addFeature(nouvelle)
        self.layer.commitChanges()
        self.layer.triggerRepaint()
