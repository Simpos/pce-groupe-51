from dataclasses import dataclass, field
from math import hypot

import numpy as np
from qgis.core import QgsGeometry, QgsPointXY
from qgis.PyQt.QtGui import QColor


@dataclass
class Zone:
    """Zone décrite par une liste de sommets (anneau extérieur)."""
    points: list[QgsPointXY] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor("red"))
    priority: int = -1
    type: str = "default_type"

    def add_point(self, p: QgsPointXY) -> None:
        self.points.append(p)

    def geometrie(self) -> QgsGeometry | None:
        """Renvoie le polygone, ou None s'il n'a pas assez de sommets.
        L'anneau est fermé explicitement (premier sommet répété en fin de liste)."""
        if len(self.points) < 3:
            return None
        anneau = list(self.points)
        premier, dernier = anneau[0], anneau[-1]
        if premier.x() != dernier.x() or premier.y() != dernier.y():
            anneau.append(QgsPointXY(premier.x(), premier.y()))
        return QgsGeometry.fromPolygonXY([anneau])

    def is_valid(self) -> bool:
        geom = self.geometrie()
        return geom is not None and geom.isGeosValid()

    def intersect(self, other: "Zone") -> bool:
        a, b = self.geometrie(), other.geometrie()
        return a is not None and b is not None and a.intersects(b)

    def __repr__(self) -> str:
        coords = ", ".join(f"({p.x():.2f}, {p.y():.2f})" for p in self.points)
        return f"Zone([{coords}])"

    def barycenter(self) -> QgsPointXY:
        """Retourne le barycentre de la liste de points."""
        if len(self.points) < 1:
            return QgsPointXY(0, 0)
        x_total = sum(p.x() for p in self.points)
        y_total = sum(p.y() for p in self.points)
        return QgsPointXY(x_total / len(self.points), y_total / len(self.points))

    def normalize(self, point: QgsPointXY):
        point.multiply(1 / point.distance(QgsPointXY(0, 0)))

    def expand_zone(self, expand: float) -> "Zone":
        """
        Renvoie une nouvelle zone agrandie : chaque sommet est repoussé
        de `expand` unités le long de la direction barycentre -> sommet.
        """
        center = self.barycenter()
        new_points = []

        for p in self.points:
            vx = p.x() - center.x()
            vy = p.y() - center.y()
            dist = hypot(vx, vy)

            if dist == 0:  # sommet confondu avec le barycentre : pas de direction
                new_points.append(QgsPointXY(p.x(), p.y()))
                continue

            factor = (dist + expand) / dist
            new_points.append(QgsPointXY(
                center.x() + vx * factor,
                center.y() + vy * factor,
            ))

        return Zone(new_points)

    def create_zone_from_point(self, center: QgsPointXY, radius: float, n_verteces: int = 4) -> None:
        """
        Modifie la zone pour en faire une zone « circulaire » de rayon `radius`,
        centrée sur `center`, avec `n_verteces` sommets.
        """
        angle = 2 * np.pi / n_verteces
        rotation = np.array([
            [np.cos(angle), -np.sin(angle)],
            [np.sin(angle),  np.cos(angle)],
        ])
        center_xy = np.array([center.x(), center.y()])
        offset = np.array([-radius, radius])

        self.points = []
        for _ in range(n_verteces):
            x, y = np.round(center_xy + offset, 4)
            self.points.append(QgsPointXY(float(x), float(y)))
            offset = rotation @ offset

    def expand_self(self, other_zone: "Zone", expand: float) -> None:
        """Même fonctionnement que expand_zone, mais la zone se modifie elle-même."""
        self.points = other_zone.expand_zone(expand).points

    def copy(self) -> "Zone":
        return Zone(list(self.points), self.color, self.priority, self.type)

    def offset_zone(self, distance: float, segments: int = 16) -> "Zone":
        """
        Renvoie une nouvelle zone élargie de `distance` vers l'extérieur.
        Utilise le buffer géométrique de QGIS, qui fonctionne pour les formes non convexes.
        `segments` : nombre de segments par quart de cercle dans les angles arrondis.
        """
        geom = self.geometrie()
        if geom is None:
            return Zone([], self.color, self.priority, self.type)

        # Un polygone auto-croisé (sommets cliqués dans le désordre) est réparé d'abord
        if not geom.isGeosValid():
            geom = geom.makeValid()

        buffered = geom.buffer(distance, segments)
        points = self._points_plus_grande_partie(buffered)
        return Zone(points, self.color, self.priority, self.type)

    def offset_self(self, other_zone: "Zone", distance: float) -> None:
        """Même fonctionnement que offset_zone, mais la zone se modifie elle-même."""
        self.points = other_zone.offset_zone(distance).points

    @staticmethod
    def _points_plus_grande_partie(geom: QgsGeometry) -> list[QgsPointXY]:
        """
        Renvoie les sommets de l'anneau extérieur de la plus grande partie du polygone,
        sans le point de fermeture. Les autres parties et les trous sont ignorés.
        """
        if geom.isEmpty():
            return []

        if geom.isMultipart():
            polygones = geom.asMultiPolygon()
        else:
            polygones = [geom.asPolygon()]

        polygones = [p for p in polygones if p]  # ignore les polygones vides
        if not polygones:
            return []

        # Un élargissement peut couper la forme en plusieurs morceaux : on garde le plus grand
        plus_grand = max(polygones, key=lambda p: QgsGeometry.fromPolygonXY(p).area())
        anneau = plus_grand[0]
        return anneau[:-1]  # retire le dernier point, qui répète le premier
