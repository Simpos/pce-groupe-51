from .drone import Drone
from pathlib import Path

class File_managing:
    @staticmethod
    def read(chemin):
        with open(chemin, "r", encoding="utf-8") as f:
            lignes = f.read().splitlines()

        if len(lignes) != 5:
            raise ValueError(
                f"{chemin} : 5 lignes attendues, {len(lignes)} trouvées"
            )

        def convertir_nombre(valeur):
            if valeur.strip() == "null":
                return None
            return float(valeur)

        return Drone(
            name=lignes[0],
            radio_dist=convertir_nombre(lignes[1]),
            air_speed=convertir_nombre(lignes[2]),
            drone_type=lignes[3],
            buffer_dist=convertir_nombre(lignes[4]),
        )
    @staticmethod
    def delete(chemin: str):
        Path(chemin).unlink()
    @staticmethod
    def write(drone: Drone, chemin: str):
        def convertir_texte(valeur):
            return "null" if valeur is None else str(valeur)

        with open(chemin, "w", encoding="utf-8") as f:
            f.write(
                f"{drone.name}\n"
                f"{convertir_texte(drone.radio_dist)}\n"
                f"{convertir_texte(drone.air_speed)}\n"
                f"{drone.drone_type}\n"
                f"{convertir_texte(drone.buffer_dist)}"
            )
    @staticmethod
    def modify_air_speed(drone: Drone, air_speed: float, chemin: str):
        drone.air_speed = air_speed
        File_managing.write(drone, chemin)

    @staticmethod
    def modify_radio_dist(drone: Drone, radio_dist: float, chemin: str):
        drone.radio_dist = radio_dist
        File_managing.write(drone, chemin)

    @staticmethod
    def modify_drone_type(drone: Drone, drone_type: str, chemin: str):
        drone.drone_type = drone_type
        File_managing.write(drone, chemin)

    @staticmethod
    def modify_buffer_dist(drone: Drone, buffer_dist: float, chemin: str):
        drone.buffer_dist = buffer_dist
        File_managing.write(drone, chemin)
