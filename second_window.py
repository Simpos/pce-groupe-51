import os
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt import uic

# On charge le fichier .ui spécifique à cette seconde fenêtre
SECOND_FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), 'second_window.ui')
)

class SecondWindow(QDockWidget, SECOND_FORM_CLASS):
    def __init__(self, parent=None):
        super(SecondWindow, self).__init__(parent)
        self.setupUi(self)

    def accept(self):
        """Évite l'erreur si un bouton Valider est présent."""
        self.close()

    def reject(self):
        """Évite l'erreur si un bouton Annuler est présent."""
        self.close()