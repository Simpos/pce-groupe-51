from pathlib import Path


class Drone:
    """Décrit un drone : portée radio, vitesse, type et distance tampon."""

    def __init__(self, name: str, radio_dist: float | None, air_speed: float | None,
                 drone_type: str, buffer_dist: float | None):
        self.name = name
        self.radio_dist = radio_dist
        self.air_speed = air_speed
        self.drone_type = drone_type
        self.buffer_dist = buffer_dist

    def get_name(self) -> str:
        return self.name

    def get_radio_dist(self) -> float | None:
        return self.radio_dist

    def get_air_speed(self) -> float | None:
        return self.air_speed

    def get_drone_type(self) -> str:
        return self.drone_type

    def get_buffer_dist(self) -> float | None:
        return self.buffer_dist

    def modify_drone(self, name: str, radio_dist: float | None, air_speed: float | None,
                     drone_type: str, buffer_dist: float | None) -> None:
        self.name = name
        self.radio_dist = radio_dist
        self.air_speed = air_speed
        self.drone_type = drone_type
        self.buffer_dist = buffer_dist

    @classmethod
    def nouveau_drone(
        cls,
        chemin: str,
        name: str,
        radio_dist: float,
        air_speed: float,
        drone_type: str,
        buffer_dist: float,
    ) -> "Drone":
        from .file_managing import File_managing  # import local : évite un import circulaire

        if Path(chemin).exists():
            raise FileExistsError(f"Le fichier existe déjà : {chemin}")

        drone = cls(
            name=name,
            radio_dist=radio_dist,
            air_speed=air_speed,
            drone_type=drone_type,
            buffer_dist=buffer_dist,
        )
        File_managing.write(drone, chemin)
        return drone

    def __repr__(self) -> str:
        return (
            f"Drone(name={self.name!r}, radio_dist={self.radio_dist!r}, "
            f"air_speed={self.air_speed!r}, drone_type={self.drone_type!r}, "
            f"buffer_dist={self.buffer_dist!r})"
        )
