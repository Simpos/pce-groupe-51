# -*- coding: utf-8 -*-
"""Secondary window for adding a new drone definition."""

import os
import re
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QLabel,
    QDialogButtonBox,
    QMessageBox,
)


class AddDroneDialog(QDialog):
    """Secondary window allowing the user to add a new drone to the drone/ folder."""

    def __init__(self, drone_dir, parent=None):
        super().__init__(parent)
        self.drone_dir = drone_dir
        self.created_drone_name = None

        self.setWindowTitle("Ajouter un drone")
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Renseignez les caractéristiques du drone pour l'ajouter au dossier "
            "<b>drone/</b> (ou utilisez cette fenêtre comme base d'édition)."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ex: DJI Air 3S")
        form.addRow("Nom du drone :", self.name_edit)

        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(5.0, 10000.0)
        self.radius_spin.setValue(50.0)
        self.radius_spin.setSuffix(" m")
        form.addRow("Rayon de vol (mode point) :", self.radius_spin)

        self.contingency_spin = QDoubleSpinBox()
        self.contingency_spin.setRange(1.0, 5000.0)
        self.contingency_spin.setValue(30.0)
        self.contingency_spin.setSuffix(" m")
        form.addRow("Zone de contingence :", self.contingency_spin)

        self.buffer_spin = QDoubleSpinBox()
        self.buffer_spin.setRange(1.0, 5000.0)
        self.buffer_spin.setValue(50.0)
        self.buffer_spin.setSuffix(" m")
        form.addRow("Zone tampon :", self.buffer_spin)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(1.0, 100.0)
        self.speed_spin.setValue(15.0)
        self.speed_spin.setSuffix(" m/s")
        form.addRow("Vitesse max :", self.speed_spin)

        self.altitude_spin = QDoubleSpinBox()
        self.altitude_spin.setRange(1.0, 500.0)
        self.altitude_spin.setValue(120.0)
        self.altitude_spin.setSuffix(" m")
        form.addRow("Hauteur max :", self.altitude_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Save).setText("Enregistrer")
        buttons.button(QDialogButtonBox.Cancel).setText("Fermer")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                "Nom manquant",
                "Veuillez saisir un nom pour le drone avant d'enregistrer.",
            )
            return

        os.makedirs(self.drone_dir, exist_ok=True)
        safe_filename = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_") or "drone"
        file_path = os.path.join(self.drone_dir, f"{safe_filename}.txt")

        content = (
            f"nom={name}\n"
            f"rayon_vol={self.radius_spin.value():.1f}\n"
            f"contingence={self.contingency_spin.value():.1f}\n"
            f"tampon={self.buffer_spin.value():.1f}\n"
            f"vitesse={self.speed_spin.value():.1f}\n"
            f"altitude={self.altitude_spin.value():.1f}\n"
        )

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Erreur d'écriture",
                f"Impossible d'enregistrer le fichier drone :\n{exc}",
            )
            return

        self.created_drone_name = name
        self.accept()
