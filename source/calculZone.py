from dataclasses import dataclass, field

from qgis.PyQt.QtGui import QColor

from .drone import Drone
from .zone import Zone


@dataclass
class ZoneCalculateur:
    flying_area: Zone = field(default_factory=lambda: Zone([], QColor("red"), 3, "fly"))
    buffering_area: Zone = field(default_factory=lambda: Zone([], QColor("blue"), 1, "buffer"))
    contingency_area: Zone = field(default_factory=lambda: Zone([], QColor("green"), 2, "cont"))
    restricted_area: list[Zone] = field(default_factory=lambda: [Zone([], QColor("black"), 4, "ban")])
    param: float = 0.0
    ITER_LIMIT: int = 10

    def calculate_areas(self, drone: Drone) -> None:
        """
        Calcule les zones de contingence et de buffer autour de la zone de vol.

        - contingence : expansion égale à la portée radio du drone
          (hypothèse à valider, voir la réponse)
        - buffer : expansion égale à la distance tampon du drone

        Lève ValueError si l'une de ces deux valeurs est absente du fichier du drone.
        """
        distance_contingence = drone.get_radio_dist()
        distance_buffer = drone.get_buffer_dist()

        if distance_contingence is None or distance_buffer is None:
            raise ValueError(
                f"Données du drone '{drone.get_name()}' incomplètes : "
                "radio_dist et buffer_dist sont requis."
            )

        #FIXME: Les zones de contingences semblent être vraiment trop grande
        self.contingency_area.offset_self(self.flying_area,distance_contingence)
        self.buffering_area.offset_self(self.contingency_area,distance_buffer)
        #self.contingency_area.expand_self(self.flying_area, distance_contingence)
        #self.buffering_area.expand_self(self.contingency_area, distance_buffer)

    def expansion_algorithm(self) -> None:
        for _ in range(self.ITER_LIMIT):
            self.flying_area.offset_self(self.flying_area.copy(), 10)
            self.contingency_area.offset_self(self.flying_area, 10)
            self.buffering_area.offset_self(self.contingency_area, 10)
