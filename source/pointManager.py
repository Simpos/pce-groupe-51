from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer
)
from qgis.gui import QgsMapTool, QgsMapToolPan
from qgis.PyQt.QtCore import Qt


class PointManager(QgsMapTool):
    """
    Outil de carte à deux comportements :
    - Ctrl + clic gauche : ajoute un point à la couche mémoire ;
    - clic gauche glissé sans Ctrl : déplace la carte (pan) ;
    - clic droit : désactive l'outil sur le canevas.
    Les points sont stockés dans le CRS cible (Lambert-93 par défaut), comme les zones.
    """

    NOM_COUCHE = "Points posés"

    def __init__(self, canvas, context: int = 0 ,crs_cible: str = "EPSG:2154"):
        super().__init__(canvas)
        self.canvas = canvas
        self.crs_cible = QgsCoordinateReferenceSystem(crs_cible)
        self.couche = None
        self.couche_id = None
        self.points: list[QgsPointXY] = []  # points cliqués, dans le CRS cible
        # Outil de déplacement standard de QGIS, utilisé en interne pour le pan
        self.pan_tool = QgsMapToolPan(canvas)
        # Vrai pendant qu'un glissement de carte est en cours
        self.is_panning = False
        self.context = context

    # --- Cycle de vie ---

    def activer(self) -> None:
        """Crée la couche si besoin et active l'outil sur le canevas."""
        if not self._couche_presente():
            self.create_point_layer()
        self.canvas.setMapTool(self)

    def desactiver(self) -> None:
        """Désactive l'outil et supprime la couche du projet."""
        self.canvas.unsetMapTool(self)
        if self._couche_presente():
            QgsProject.instance().removeMapLayer(self.couche_id)
        self.couche = None
        self.couche_id = None
        self.points.clear()
        self.is_panning = False

    def create_point_layer(self) -> QgsVectorLayer:
        self.couche = QgsVectorLayer(
            f"Point?crs={self.crs_cible.authid()}", self.NOM_COUCHE, "memory"
        )
        self.couche_id = self.couche.id()
        QgsProject.instance().addMapLayer(self.couche)
        return self.couche

    def _couche_presente(self) -> bool:
        return self.couche_id is not None and QgsProject.instance().mapLayer(self.couche_id) is not None

    # --- Saisie et déplacement à la souris ---

    def canvasPressEvent(self, event):
        # Sans Ctrl, un clic gauche démarre un déplacement de carte
        if event.button() == Qt.LeftButton and not self._is_ctrl_pressed(event):
            self.is_panning = True
            self.pan_tool.canvasPressEvent(event)

    def canvasMoveEvent(self, event):
        # Pendant le glissement, la carte suit la souris
        if self.is_panning:
            self.pan_tool.canvasMoveEvent(event)

    def canvasReleaseEvent(self, event):
        if self.is_panning and event.button() == Qt.LeftButton:
            # Fin du glissement de carte
            self.pan_tool.canvasReleaseEvent(event)
            self.is_panning = False
        elif event.button() == Qt.LeftButton and self._is_ctrl_pressed(event):
            # Ctrl + clic gauche : ajout d'un point
            point_canevas = self.toMapCoordinates(event.pos())
            
            if self.context == 0:
                self.clear_couche()
            self.ajouter_point(self._vers_crs_cible(point_canevas))
        elif event.button() == Qt.RightButton:
            # Clic droit : désactive l'outil
            self.canvas.unsetMapTool(self)

    def ajouter_point(self, point: QgsPointXY) -> None:
        if not self._couche_presente():
            self.create_point_layer()

        feature = QgsFeature(self.couche.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        self.couche.dataProvider().addFeatures([feature])
        self.couche.updateExtents()
        self.couche.triggerRepaint()
        self.points.append(point)

    def clear_couche(self) -> None:
        self.vider()
        if self._couche_presente():
            QgsProject.instance().removeMapLayer(self.couche_id)
        self.couche = None
        self.couche_id = None

    def vider(self) -> None:
        """Vide la liste des points. La couche reste affichée."""
        self.points.clear()


    # --- Utilitaires ---

    @staticmethod
    def _is_ctrl_pressed(event) -> bool:
        # Vrai si la touche Ctrl est enfoncée pendant l'événement souris
        return bool(event.modifiers() & Qt.ControlModifier)

    def _vers_crs_cible(self, point: QgsPointXY) -> QgsPointXY:
        # Convertit un point du CRS du canevas vers le CRS cible
        transformation = QgsCoordinateTransform(
            self.canvas.mapSettings().destinationCrs(),
            self.crs_cible,
            QgsProject.instance().transformContext(),
        )
        return transformation.transform(point)
