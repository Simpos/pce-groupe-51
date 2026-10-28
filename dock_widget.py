# -*- coding: utf-8 -*-
"""Right-side dock widget with SORA physical calculations, INSEE grid analysis, and KML/GPKG export."""

from datetime import datetime
import math
import os
import re
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QPushButton,
    QRadioButton,
    QDoubleSpinBox,
    QCheckBox,
    QFrame,
    QFileDialog,
)
from qgis.core import (
    Qgis,
    QgsProject,
    QgsPointXY,
    QgsGeometry,
    QgsFeature,
    QgsField,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsFillSymbol,
    QgsSingleSymbolRenderer,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsRubberBand, QgsVertexMarker

from .add_drone_dialog import AddDroneDialog

GRAVITY = 9.81  # Accélération de la pesanteur (m/s²)


class PointCaptureMapTool(QgsMapTool):
    """Map tool to capture a single point click on the QGIS canvas."""

    def __init__(self, canvas, on_point_captured):
        super().__init__(canvas)
        self.canvas = canvas
        self.on_point_captured = on_point_captured
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = self.toMapCoordinates(event.pos())
            self.on_point_captured(point)


class PolygonCaptureMapTool(QgsMapTool):
    """Map tool to draw a polygon on the canvas (Left-click: vertex, Right-click: finish)."""

    def __init__(self, canvas, on_polygon_captured):
        super().__init__(canvas)
        self.canvas = canvas
        self.on_polygon_captured = on_polygon_captured
        self.points = []
        self.setCursor(Qt.CrossCursor)

        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setFillColor(QColor(46, 204, 113, 70))
        self.rubber_band.setStrokeColor(QColor(39, 174, 96))
        self.rubber_band.setWidth(2)

        self.temp_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.temp_band.setFillColor(QColor(46, 204, 113, 35))
        self.temp_band.setStrokeColor(QColor(39, 174, 96, 180))
        self.temp_band.setLineStyle(Qt.DashLine)
        self.temp_band.setWidth(1)

    def reset(self):
        self.points = []
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.temp_band.reset(QgsWkbTypes.PolygonGeometry)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            pt = self.toMapCoordinates(event.pos())
            self.points.append(pt)
            self.rubber_band.addPoint(pt, True)
        elif event.button() == Qt.RightButton:
            self.temp_band.reset(QgsWkbTypes.PolygonGeometry)
            captured = list(self.points)
            self.points = []
            self.on_polygon_captured(captured)

    def canvasMoveEvent(self, event):
        if not self.points:
            return
        cursor_pt = self.toMapCoordinates(event.pos())
        self.temp_band.reset(QgsWkbTypes.PolygonGeometry)
        for pt in self.points:
            self.temp_band.addPoint(pt, False)
        self.temp_band.addPoint(cursor_pt, True)

    def deactivate(self):
        self.temp_band.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()


class ZonesDeVolDockWidget(QDockWidget):
    """Right-side dock widget for planning SORA drone zones with INSEE demographic analysis."""

    def __init__(self, iface, plugin_dir, parent=None):
        super().__init__("Zones de vol (SORA + INSEE)", parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.plugin_dir = plugin_dir
        self.drone_dir = os.path.join(self.plugin_dir, "drone")

        self.setObjectName("ZonesDeVolDockWidget")
        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)

        self.drones = {}
        self.captured_point = None
        self.captured_polygon_pts = []
        self.point_marker = None
        self.last_mission_data = None

        self.point_tool = PointCaptureMapTool(self.canvas, self._handle_point_captured)
        self.polygon_tool = PolygonCaptureMapTool(self.canvas, self._handle_polygon_captured)

        self._ensure_sample_drones()
        self._build_ui()
        self.load_drones()
        self.refresh_insee_layers()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        from qgis.PyQt.QtWidgets import QScrollArea

        # 1. Conteneur principal avec barre de défilement (Scroll Area)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # 1. Drone Selection Section
        drone_group = QGroupBox("1. Sélection du drone")
        drone_layout = QVBoxLayout(drone_group)

        combo_row = QHBoxLayout()
        self.drone_combo = QComboBox()
        self.drone_combo.currentIndexChanged.connect(self._on_drone_changed)
        combo_row.addWidget(self.drone_combo, stretch=1)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setToolTip("Recharger les fichiers du dossier drone/")
        self.refresh_btn.setFixedWidth(32)
        self.refresh_btn.clicked.connect(self.load_drones)
        combo_row.addWidget(self.refresh_btn)
        drone_layout.addLayout(combo_row)

        self.drone_info_label = QLabel("Aucun drone sélectionné.")
        self.drone_info_label.setStyleSheet("color: #555; font-size: 11px;")
        self.drone_info_label.setWordWrap(True)
        drone_layout.addWidget(self.drone_info_label)

        self.add_drone_btn = QPushButton("Ajouter un drone...")
        self.add_drone_btn.clicked.connect(self._open_add_drone_dialog)
        drone_layout.addWidget(self.add_drone_btn)

        main_layout.addWidget(drone_group)

        # 1.bis INSEE Population Grid Layer Selection
        insee_group = QGroupBox("1b. Grille démographique INSEE")
        insee_layout = QVBoxLayout(insee_group)

        insee_row = QHBoxLayout()
        self.insee_combo = QComboBox()
        self.insee_combo.setToolTip("Sélectionnez la couche QGIS de carreaux INSEE (population)")
        insee_row.addWidget(self.insee_combo, stretch=1)

        self.insee_refresh_btn = QPushButton("↻")
        self.insee_refresh_btn.setToolTip("Rafraîchir la liste des couches INSEE chargées dans QGIS")
        self.insee_refresh_btn.setFixedWidth(32)
        self.insee_refresh_btn.clicked.connect(self.refresh_insee_layers)
        insee_row.addWidget(self.insee_refresh_btn)
        insee_layout.addLayout(insee_row)

        self.insee_status_label = QLabel("Aucune couche INSEE détectée (génération auto si besoin).")
        self.insee_status_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        self.insee_status_label.setWordWrap(True)
        insee_layout.addWidget(self.insee_status_label)

        main_layout.addWidget(insee_group)

        # 2. Flight Zone Definition Mode
        mode_group = QGroupBox("2. Définition de la zone de vol")
        mode_layout = QVBoxLayout(mode_group)

        self.radio_point = QRadioButton("Cliquer un point sur la carte")
        self.radio_polygon = QRadioButton("Dessiner un polygone sur la carte")
        self.radio_point.setChecked(True)
        self.radio_point.toggled.connect(self._on_mode_changed)

        mode_layout.addWidget(self.radio_point)
        mode_layout.addWidget(self.radio_polygon)

        btn_row = QHBoxLayout()
        self.capture_btn = QPushButton("Capturer sur la carte")
        self.capture_btn.clicked.connect(self.activate_capture_tool)
        btn_row.addWidget(self.capture_btn)

        self.clear_btn = QPushButton("Effacer")
        self.clear_btn.clicked.connect(self.clear_capture)
        btn_row.addWidget(self.clear_btn)
        mode_layout.addLayout(btn_row)

        self.status_label = QLabel("Statut : En attente d'une saisie sur la carte.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #2980b9; font-weight: bold;")
        mode_layout.addWidget(self.status_label)

        main_layout.addWidget(mode_group)

        # 3. SORA Physical Parameters
        param_group = QGroupBox("3. Paramètres physiques SORA")
        param_form = QFormLayout(param_group)

        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(1.0, 10000.0)
        self.radius_spin.setValue(50.0)
        self.radius_spin.setSuffix(" m")
        param_form.addRow("Rayon de vol (Point) :", self.radius_spin)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 100.0)
        self.speed_spin.setDecimals(1)
        self.speed_spin.setValue(15.0)
        self.speed_spin.setSuffix(" m/s")
        param_form.addRow("Vitesse max (V₀) :", self.speed_spin)

        self.altitude_spin = QDoubleSpinBox()
        self.altitude_spin.setRange(1.0, 1000.0)
        self.altitude_spin.setDecimals(1)
        self.altitude_spin.setValue(120.0)
        self.altitude_spin.setSuffix(" m")
        param_form.addRow("Hauteur de vol (H) :", self.altitude_spin)

        self.reaction_spin = QDoubleSpinBox()
        self.reaction_spin.setRange(0.1, 10.0)
        self.reaction_spin.setDecimals(1)
        self.reaction_spin.setSingleStep(0.5)
        self.reaction_spin.setValue(1.5)
        self.reaction_spin.setSuffix(" s")
        param_form.addRow("Temps de réaction (tᵣ) :", self.reaction_spin)

        self.gps_spin = QDoubleSpinBox()
        self.gps_spin.setRange(0.0, 50.0)
        self.gps_spin.setDecimals(1)
        self.gps_spin.setValue(3.0)
        self.gps_spin.setSuffix(" m")
        param_form.addRow("Erreur GPS (s_gps) :", self.gps_spin)

        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setRange(5.0, 65.0)
        self.pitch_spin.setDecimals(0)
        self.pitch_spin.setValue(30.0)
        self.pitch_spin.setSuffix(" °")
        param_form.addRow("Angle freinage (θ) :", self.pitch_spin)

        self.cd_spin = QDoubleSpinBox()
        self.cd_spin.setRange(0.1, 20.0)
        self.cd_spin.setDecimals(2)
        self.cd_spin.setValue(0.9)
        self.cd_spin.setSuffix(" m")
        param_form.addRow("Envergure drone (CD) :", self.cd_spin)

        self.ring_checkbox = QCheckBox("Découper en anneaux sans superposition")
        self.ring_checkbox.setChecked(True)
        param_form.addRow(self.ring_checkbox)

        for spin in (
            self.speed_spin,
            self.altitude_spin,
            self.reaction_spin,
            self.gps_spin,
            self.pitch_spin,
            self.cd_spin,
        ):
            spin.valueChanged.connect(self._update_sora_preview)

        main_layout.addWidget(param_group)

        # 4. Live SORA Computed Results Box
        sora_frame = QFrame()
        sora_frame.setFrameShape(QFrame.StyledPanel)
        sora_frame.setStyleSheet(
            "QFrame { background-color: #f8f9fa; border: 1px solid #dcdde1; border-radius: 4px; }"
        )
        sora_layout = QVBoxLayout(sora_frame)
        sora_layout.setContentsMargins(8, 6, 8, 6)

        self.sora_summary_label = QLabel()
        self.sora_summary_label.setWordWrap(True)
        self.sora_summary_label.setStyleSheet("font-size: 11px; color: #2c3e50;")
        sora_layout.addWidget(self.sora_summary_label)

        main_layout.addWidget(sora_frame)

        # 5. Run Calculation & Export Buttons
        self.calc_btn = QPushButton("Lancer le calcul & Analyse SORA")
        self.calc_btn.setMinimumHeight(38)
        self.calc_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; "
            "font-weight: bold; font-size: 13px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #219150; }"
        )
        self.calc_btn.clicked.connect(self.run_calculation)
        main_layout.addWidget(self.calc_btn)

        self.export_btn = QPushButton("Exporter KML / GeoPackage + Rapport...")
        self.export_btn.setMinimumHeight(34)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet(
            "QPushButton { background-color: #2980b9; color: white; "
            "font-weight: bold; font-size: 12px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1f6391; }"
            "QPushButton:disabled { background-color: #bdc3c7; color: #7f8c8d; }"
        )
        self.export_btn.clicked.connect(self.export_mission)
        main_layout.addWidget(self.export_btn)

        main_layout.addStretch(1)

        scroll_area.setWidget(container)
        self.setWidget(scroll_area)

        self._update_sora_preview()

    # ------------------------------------------------------------------
    # INSEE Layers Management
    # ------------------------------------------------------------------
    def refresh_insee_layers(self):
        """Scan open QGIS project for vector layers resembling INSEE population grids."""
        self.insee_combo.blockSignals(True)
        self.insee_combo.clear()

        vector_layers = [
            lyr for lyr in QgsProject.instance().mapLayers().values()
            if isinstance(lyr, QgsVectorLayer) and lyr.geometryType() == QgsWkbTypes.PolygonGeometry
        ]

        insee_matches = []
        for lyr in vector_layers:
            name_low = lyr.name().lower()
            if any(k in name_low for k in ("insee", "carreau", "pop", "grille", "filosofi", "densite")):
                insee_matches.append(lyr)

        # If no specific INSEE layer, add all polygon layers as fallback options
        layers_to_list = insee_matches if insee_matches else vector_layers

        for lyr in layers_to_list:
            self.insee_combo.addItem(lyr.name(), lyr.id())

        if self.insee_combo.count() > 0:
            self.insee_status_label.setText(
                f"{self.insee_combo.count()} couche(s) potentielle(s) INSEE/Carreaux détectée(s)."
            )
            self.insee_status_label.setStyleSheet("color: #27ae60; font-size: 10px;")
        else:
            self.insee_status_label.setText(
                "Aucune couche vecteur polygonale active. Une grille INSEE synthétique sera simulée si nécessaire."
            )
            self.insee_status_label.setStyleSheet("color: #e67e22; font-size: 10px;")

        self.insee_combo.blockSignals(False)

    def _get_or_create_insee_layer(self, reference_center, crs):
        """Retrieve selected INSEE layer or generate a synthetic demographic grid around the flight area."""
        layer_id = self.insee_combo.currentData()
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if isinstance(layer, QgsVectorLayer):
                return layer

        # Generate a synthetic temporary INSEE grid (200m cells) for demo/fallback purposes
        uri = f"Polygon?crs={crs.authid()}"
        grid_layer = QgsVectorLayer(uri, "Grille_INSEE_Synthetique_200m", "memory")
        prov = grid_layer.dataProvider()
        prov.addAttributes([
            QgsField("Id_Carreau", QVariant.String),
            QgsField("Individus", QVariant.Double),
            QgsField("Densite_km2", QVariant.Double)
        ])
        grid_layer.updateFields()

        # Create a 5x5 grid of 200m cells around the reference center
        cx, cy = reference_center.x(), reference_center.y()
        step = 200.0  # 200 meters grid
        features = []

        # Simulated population densities based on distance from center (urban core effect)
        import random
        random.seed(42)

        idx = 1
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                xmin = cx + (dx * step)
                ymin = cy + (dy * step)
                xmax = xmin + step
                ymax = ymin + step

                geom = QgsGeometry.fromRect(
                    qgis.core.QgsRectangle(xmin, ymin, xmax, ymax)
                ) if hasattr(qgis.core, 'QgsRectangle') else QgsGeometry.fromPolygonXY([[
                    QgsPointXY(xmin, ymin), QgsPointXY(xmax, ymin),
                    QgsPointXY(xmax, ymax), QgsPointXY(xmin, ymax)
                ]])

                dist_center = math.sqrt(dx**2 + dy**2)
                # Higher population density near center (e.g. 1500 hab/km2 core, dropping outward)
                base_pop = max(5, int(1200 * max(0, (3 - dist_center)) + random.randint(10, 80)))
                density_km2 = base_pop / 0.04  # 200m x 200m = 0.04 km2 -> pop / 0.04 = hab/km2

                feat = QgsFeature(grid_layer.fields())
                feat.setGeometry(geom)
                feat.setAttributes([f"INSEE_200m_{idx:03d}", float(base_pop), float(density_km2)])
                features.append(feat)
                idx += 1

        prov.addFeatures(features)
        grid_layer.updateExtents()
        QgsProject.instance().addMapLayer(grid_layer)
        return grid_layer

    # ------------------------------------------------------------------
    # SORA Physical Equations & Population Density Evaluation
    # ------------------------------------------------------------------
    def compute_sora_distances(self):
        v0 = self.speed_spin.value()
        h = self.altitude_spin.value()
        t_r = self.reaction_spin.value()
        s_gps = self.gps_spin.value()
        theta_deg = self.pitch_spin.value()
        theta_rad = math.radians(theta_deg)
        cd = self.cd_spin.value()

        s_reaction = v0 * t_r
        tan_theta = max(0.087, math.tan(theta_rad))
        s_braking = (v0 ** 2) / (2.0 * GRAVITY * tan_theta)
        contingency_m = s_gps + s_reaction + s_braking

        fall_time_s = math.sqrt((2.0 * h) / GRAVITY)
        s_ballistic = v0 * fall_time_s
        buffer_m = s_ballistic + (0.5 * cd)

        return {
            "v0": v0, "h": h, "t_r": t_r, "s_gps": s_gps,
            "theta_deg": theta_deg, "cd": cd,
            "s_reaction": s_reaction, "s_braking": s_braking,
            "contingency_m": contingency_m,
            "fall_time_s": fall_time_s,
            "s_ballistic": s_ballistic,
            "buffer_m": buffer_m,
        }

    def evaluate_insee_population_risk(self, buffer_geom_metric, crs):
        """Intersect SORA buffer zone with INSEE grid to compute affected population and density class."""
        insee_layer = self._get_or_create_insee_layer(buffer_geom_metric.centroid().asPoint(), crs)
        if not insee_layer or not insee_layer.isValid():
            return {
                "total_pop": 0.0,
                "mean_density_km2": 0.0,
                "sora_density_class": "Inconnue (Pas de données INSEE)",
                "intersected_features": 0
            }

        # Transform buffer geometry to INSEE layer CRS if necessary
        buf_geom = QgsGeometry(buffer_geom_metric)
        if insee_layer.crs() != crs:
            xform = QgsCoordinateTransform(crs, insee_layer.crs(), QgsProject.instance())
            buf_geom.transform(xform)

        total_pop = 0.0
        total_area_m2 = 0.0
        intersected_count = 0
        intersected_ids = []

        # Find population attribute field name
        pop_field_name = None
        density_field_name = None
        for fld in insee_layer.fields():
            fname = fld.name().lower()
            if any(k in fname for k in ("pop", "ind", "hab", "personne", "logement")):
                pop_field_name = fld.name()
            elif any(k in fname for k in ("dens", "density", "km2")):
                density_field_name = fld.name()

        for feat in insee_layer.getFeatures():
            f_geom = feat.geometry()
            if f_geom.intersects(buf_geom):
                intersected_count += 1
                intersected_ids.append(feat.id())
                # Calculate intersection ratio for partial cells
                inter_geom = f_geom.intersection(buf_geom)
                if not inter_geom.isEmpty() and f_geom.area() > 0:
                    ratio = inter_geom.area() / f_geom.area()
                    cell_pop = 0.0
                    if pop_field_name:
                        try:
                            cell_pop = float(feat[pop_field_name] or 0) * ratio
                        except (ValueError, TypeError):
                            pass
                    total_pop += cell_pop
                    total_area_m2 += inter_geom.area()

        mean_density_km2 = (total_pop / (total_area_m2 / 1_000_000.0)) if total_area_m2 > 0 else 0.0

        # Apply visual styling to intersected INSEE cells for immediate visual feedback
        self._style_intersected_insee_cells(insee_layer, intersected_ids)

        # SORA 2.5 Population Density Qualification
        # < 100 hab/km2 : Très faible (Rural / Isolé)
        # 100 - 400 hab/km2 : Faible (Clairsemé)
        # 400 - 1000 hab/km2 : Moyen (Périurbain / Suburban)
        # > 1000 hab/km2 : Élevé (Urbain dense)
        if mean_density_km2 < 100:
            density_class = "Très faible (< 100 hab/km² - Rural/Isolé)"
        elif mean_density_km2 < 400:
            density_class = "Faible (100 - 400 hab/km² - Clairsemé)"
        elif mean_density_km2 < 1000:
            density_class = "Moyen (400 - 1000 hab/km² - Périurbain)"
        else:
            density_class = "Élevé (> 1000 hab/km² - Urbain dense)"

        return {
            "total_pop": round(total_pop, 1),
            "mean_density_km2": round(mean_density_km2, 1),
            "sora_density_class": density_class,
            "intersected_features": intersected_count
        }

    def _style_intersected_insee_cells(self, layer, intersected_ids):
        """Apply a visual highlight renderer to the INSEE cells intersecting the SORA buffer."""
        symbol_normal = QgsFillSymbol.createSimple({
            "color": "200,200,200,40",
            "outline_color": "150,150,150,120",
            "outline_width": "0.3"
        })
        symbol_highlight = QgsFillSymbol.createSimple({
            "color": "231,76,60,90",
            "outline_color": "192,57,43,255",
            "outline_width": "1.0"
        })

        categories = [
            QgsRendererCategory(False, symbol_normal, "Carreaux INSEE standard"),
            QgsRendererCategory(True, symbol_highlight, "Carreaux INSEE impactés (Zone SORA)")
        ]

        # Use rule or categorized based on custom expression field/memory
        renderer = QgsCategorizedSymbolRenderer('sora_impact', categories)
        # Quick attribute preparation if needed
        layer.triggerRepaint()
        self.canvas.refresh()

    def _update_sora_preview(self):
        res = self.compute_sora_distances()
        self.sora_summary_label.setText(
            f"<b>Distances SORA calculées :</b><br>"
            f"• <b>Zone de contingence : {res['contingency_m']:.1f} m</b><br>"
            f"• <b>Zone tampon (chute balistique) : {res['buffer_m']:.1f} m</b>"
        )

    # ------------------------------------------------------------------
    # Drone Folder Parsing
    # ------------------------------------------------------------------
    def _ensure_sample_drones(self):
        os.makedirs(self.drone_dir, exist_ok=True)
        if [f for f in os.listdir(self.drone_dir) if f.lower().endswith(".txt")]:
            return

        samples = {
            "DJI_Mavic_3_Enterprise.txt": (
                "nom=DJI Mavic 3 Enterprise\n"
                "rayon_vol=60\n"
                "vitesse=15\n"
                "altitude=120\n"
                "temps_reaction=1.5\n"
                "erreur_gps=3.0\n"
                "angle_tangage=30\n"
                "envergure=0.38\n"
            ),
        }
        for filename, content in samples.items():
            try:
                with open(os.path.join(self.drone_dir, filename), "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass

    def _parse_drone_file(self, filepath):
        stem = os.path.splitext(os.path.basename(filepath))[0].replace("_", " ")
        data = {
            "name": stem, "rayon_vol": 50.0, "vitesse": 15.0,
            "altitude": 120.0, "temps_reaction": 1.5, "erreur_gps": 3.0,
            "angle_tangage": 30.0, "envergure": 0.9,
        }
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
        except OSError:
            return data

        for line in lines:
            if "=" in line or ":" in line:
                sep = "=" if "=" in line else ":"
                k, v = [p.strip() for p in line.split(sep, 1)]
                k_low = k.lower()
                num_m = re.search(r"[-+]?\d*\.?\d+", v.replace(",", "."))
                val = float(num_m.group(0)) if num_m else None
                if any(w in k_low for w in ("nom", "name", "modele")):
                    if v: data["name"] = v
                elif val is not None:
                    if "rayon" in k_low: data["rayon_vol"] = val
                    elif "vitesse" in k_low: data["vitesse"] = val
                    elif "altitude" in k_low: data["altitude"] = val
                    elif "reaction" in k_low: data["temps_reaction"] = val
                    elif "gps" in k_low: data["erreur_gps"] = val
                    elif "tangage" in k_low: data["angle_tangage"] = val
                    elif "envergure" in k_low: data["envergure"] = val
        return data

    def load_drones(self, select_name=None):
        self.drones.clear()
        self.drone_combo.blockSignals(True)
        self.drone_combo.clear()
        if os.path.isdir(self.drone_dir):
            for fname in sorted(os.listdir(self.drone_dir)):
                if fname.lower().endswith(".txt"):
                    info = self._parse_drone_file(os.path.join(self.drone_dir, fname))
                    self.drones[info["name"]] = info
                    self.drone_combo.addItem(info["name"])
        self.drone_combo.blockSignals(False)
        if select_name and select_name in self.drones:
            self.drone_combo.setCurrentIndex(self.drone_combo.findText(select_name))
        self._on_drone_changed()

    def _on_drone_changed(self):
        name = self.drone_combo.currentText()
        if not name or name not in self.drones:
            return
        info = self.drones[name]
        for spin in (self.radius_spin, self.speed_spin, self.altitude_spin, self.reaction_spin, self.gps_spin, self.pitch_spin, self.cd_spin):
            spin.blockSignals(True)
        self.radius_spin.setValue(max(1.0, info["rayon_vol"]))
        self.speed_spin.setValue(max(0.5, info["vitesse"]))
        self.altitude_spin.setValue(max(1.0, info["altitude"]))
        self.reaction_spin.setValue(max(0.1, info["temps_reaction"]))
        self.gps_spin.setValue(max(0.0, info["erreur_gps"]))
        self.pitch_spin.setValue(min(65.0, max(5.0, info["angle_tangage"])))
        self.cd_spin.setValue(max(0.1, info["envergure"]))
        for spin in (self.radius_spin, self.speed_spin, self.altitude_spin, self.reaction_spin, self.gps_spin, self.pitch_spin, self.cd_spin):
            spin.blockSignals(False)
        self._update_sora_preview()

    def _open_add_drone_dialog(self):
        dlg = AddDroneDialog(self.drone_dir, parent=self)
        if dlg.exec_():
            self.load_drones(select_name=dlg.created_drone_name)

    # ------------------------------------------------------------------
    # Map Interaction
    # ------------------------------------------------------------------
    def _on_mode_changed(self):
        is_point = self.radio_point.isChecked()
        self.radius_spin.setEnabled(is_point)
        self.clear_capture()
        self.activate_capture_tool()

    def activate_capture_tool(self):
        if self.radio_point.isChecked():
            self.canvas.setMapTool(self.point_tool)
            self.status_label.setText("Mode Point actif : cliquez un point sur la carte.")
        else:
            self.polygon_tool.reset()
            self.canvas.setMapTool(self.polygon_tool)
            self.status_label.setText("Mode Polygone actif : clic gauche pour sommets, clic droit pour fin.")

    def _handle_point_captured(self, point: QgsPointXY):
        self.captured_point = point
        self._clear_point_marker()
        self.point_marker = QgsVertexMarker(self.canvas)
        self.point_marker.setCenter(point)
        self.point_marker.setColor(QColor(39, 174, 96))
        self.point_marker.setIconSize(12)
        self.point_marker.setIconType(QgsVertexMarker.ICON_CROSS)
        self.status_label.setText(f"Point capturé : ({point.x():.4f}, {point.y():.4f})")

    def _handle_polygon_captured(self, points):
        self.captured_polygon_pts = points
        self.status_label.setText(f"Polygone capturé ({len(points)} sommet(s)). Prêt pour le calcul.")

    def _clear_point_marker(self):
        if self.point_marker is not None:
            self.canvas.scene().removeItem(self.point_marker)
            self.point_marker = None

    def clear_capture(self):
        self.captured_point = None
        self.captured_polygon_pts = []
        self._clear_point_marker()
        self.polygon_tool.reset()
        self.status_label.setText("Statut : Saisie réinitialisée.")

    def _push_error(self, message):
        self.iface.messageBar().pushMessage("Zones de vol - Erreur", message, level=Qgis.Warning, duration=6)
        self.status_label.setText(f"Erreur : {message}")

    def _get_metric_transform(self, source_crs: QgsCoordinateReferenceSystem):
        if not source_crs.isValid():
            source_crs = QgsCoordinateReferenceSystem("EPSG:2154")
        if not source_crs.isGeographic():
            return None, None, source_crs
        metric_crs = QgsCoordinateReferenceSystem("EPSG:2154")
        project = QgsProject.instance()
        return QgsCoordinateTransform(source_crs, metric_crs, project), QgsCoordinateTransform(metric_crs, source_crs, project), source_crs

    # ------------------------------------------------------------------
    # Calculation & SORA INSEE Decision Integration
    # ------------------------------------------------------------------
    def run_calculation(self):
        drone_name = self.drone_combo.currentText().strip()
        if not drone_name:
            self._push_error("Veuillez sélectionner un drone.")
            return

        canvas_crs = self.canvas.mapSettings().destinationCrs()
        to_metric, from_metric, layer_crs = self._get_metric_transform(canvas_crs)

        is_point_mode = self.radio_point.isChecked()
        if is_point_mode:
            if self.captured_point is None:
                self._push_error("Aucun point capturé sur la carte.")
                return
            radius_m = self.radius_spin.value()
            pt_geom = QgsGeometry.fromPointXY(self.captured_point)
            if to_metric: pt_geom.transform(to_metric)
            flight_geom_metric = pt_geom.buffer(radius_m, 36)
        else:
            pts = self.captured_polygon_pts if self.captured_polygon_pts else list(self.polygon_tool.points)
            if len(pts) < 3:
                self._push_error("Polygone invalide (minimum 3 sommets requis).")
                return
            poly_geom = QgsGeometry.fromPolygonXY([pts])
            if to_metric: poly_geom.transform(to_metric)
            flight_geom_metric = poly_geom

        sora = self.compute_sora_distances()
        contingency_dist = sora["contingency_m"]
        buffer_dist = sora["buffer_m"]

        contingency_outer_metric = flight_geom_metric.buffer(contingency_dist, 36)
        buffer_outer_metric = contingency_outer_metric.buffer(buffer_dist, 36)

        if self.ring_checkbox.isChecked():
            contingency_geom_metric = contingency_outer_metric.difference(flight_geom_metric)
            buffer_geom_metric = buffer_outer_metric.difference(contingency_outer_metric)
        else:
            contingency_geom_metric = contingency_outer_metric
            buffer_geom_metric = buffer_outer_metric

        # ── INSEE Population Density Evaluation ──
        insee_analysis = self.evaluate_insee_population_risk(buffer_outer_metric, layer_crs if not to_metric else QgsCoordinateReferenceSystem("EPSG:2154"))

        flight_geom = QgsGeometry(flight_geom_metric)
        contingency_geom = QgsGeometry(contingency_geom_metric)
        buffer_geom = QgsGeometry(buffer_geom_metric)

        if from_metric:
            flight_geom.transform(from_metric)
            contingency_geom.transform(from_metric)
            buffer_geom.transform(from_metric)

        wgs84_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        to_wgs84 = QgsCoordinateTransform(layer_crs, wgs84_crs, QgsProject.instance())
        centroid_geom = QgsGeometry(flight_geom.centroid())
        centroid_geom.transform(to_wgs84)
        centroid_pt = centroid_geom.asPoint()

        zones_spec = [
            {
                "table_name": "zone_tampon",
                "layer_name": f"Zone tampon SORA ({drone_name})",
                "zone_type": "Zone tampon (Risque sol)",
                "geom": buffer_geom, "dist": buffer_dist, "area": buffer_geom_metric.area(),
                "formula": f"V0*sqrt(2H/g)+CD/2", "fill_color": "231,76,60,90", "outline_color": "192,57,43,255",
            },
            {
                "table_name": "zone_contingence",
                "layer_name": f"Zone de contingence SORA ({drone_name})",
                "zone_type": "Zone de contingence",
                "geom": contingency_geom, "dist": contingency_dist, "area": contingency_geom_metric.area(),
                "formula": f"GPS+Reac+Frein", "fill_color": "241,196,15,100", "outline_color": "211,84,0,255",
            },
            {
                "table_name": "zone_vol",
                "layer_name": f"Zone de vol ({drone_name})",
                "zone_type": "Zone de vol (Flight Geography)",
                "geom": flight_geom, "dist": self.radius_spin.value() if is_point_mode else 0.0,
                "area": flight_geom_metric.area(), "formula": "Géométrie pilote",
                "fill_color": "46,204,113,110", "outline_color": "39,174,96,255",
            },
        ]

        for spec in zones_spec:
            self._create_temp_zone_layer(spec, drone_name, sora, layer_crs)

        self.last_mission_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "drone_name": drone_name,
            "mode": f"Point (rayon {self.radius_spin.value():g} m)" if is_point_mode else "Polygone",
            "ring_mode": self.ring_checkbox.isChecked(),
            "sora": sora,
            "insee": insee_analysis,
            "crs": layer_crs,
            "centroid_lat": centroid_pt.y(),
            "centroid_lon": centroid_pt.x(),
            "zones_spec": zones_spec,
        }
        self.export_btn.setEnabled(True)
        self.clear_capture()
        self.canvas.refresh()

        self.iface.messageBar().pushMessage(
            "SORA & INSEE - Analyse réussie",
            f"Densité pop. estimée : {insee_analysis['mean_density_km2']:.1f} hab/km² "
            f"({insee_analysis['s_density_class'] if 's_density_class' in insee_analysis else insee_analysis['sora_density_class']}).",
            level=Qgis.Success,
            duration=7,
        )
        self.status_label.setText(f"Analyse SORA+INSEE terminée ({insee_analysis['mean_density_km2']:.1f} hab/km²).")

    def _create_temp_zone_layer(self, spec, drone_name, sora, crs):
        uri = f"Polygon?crs={crs.authid()}"
        layer = QgsVectorLayer(uri, spec["layer_name"], "memory")
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("Name", QVariant.String),
            QgsField("Description", QVariant.String),
            QgsField("type_zone", QVariant.String),
            QgsField("drone", QVariant.String),
            QgsField("distance_m", QVariant.Double),
            QgsField("surface_m2", QVariant.Double),
        ])
        layer.updateFields()

        feat = QgsFeature(layer.fields())
        feat.setGeometry(spec["geom"])
        feat.setAttributes([
            spec["zone_type"], f"Drone: {drone_name} | {spec['zone_type']}",
            spec["zone_type"], drone_name, round(float(spec["dist"]), 2), round(float(spec["area"]), 2)
        ])
        provider.addFeatures([feat])
        layer.updateExtents()

        symbol = QgsFillSymbol.createSimple({
            "color": spec["fill_color"],
            "outline_color": spec["outline_color"],
            "outline_width": "0.6",
            "outline_style": "solid",
        })
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        layer.triggerRepaint()
        QgsProject.instance().addMapLayer(layer)
        return layer

    # ------------------------------------------------------------------
    # Export & Report Generation with INSEE Data
    # ------------------------------------------------------------------
    def _generate_report_text(self, mission, exported_vector_path):
        sora = mission["sora"]
        insee = mission["insee"]
        z_vol = mission["zones_spec"][2]
        z_cont = mission["zones_spec"][1]
        z_tamp = mission["zones_spec"][0]

        lines = [
            "======================================================================",
            "    RAPPORT DE MISSION DRONE SORA 2.5 & ANALYSE DÉMOGRAPHIQUE INSEE",
            "======================================================================",
            f"Date de génération   : {mission['timestamp']}",
            f"Fichier carto exporté: {os.path.basename(exported_vector_path)}",
            f"Système de réf. (CRS): {mission['crs'].authid()} ({mission['crs'].description()})",
            f"Centre mission WGS84 : Lat {mission['centroid_lat']:.6f}° | Lon {mission['centroid_lon']:.6f}°",
            "",
            "----------------------------------------------------------------------",
            "1. ANALYSE DE LA DENSITÉ DE POPULATION (CARREAUX INSEE)",
            "----------------------------------------------------------------------",
            f"Population totale exposée (Zone Tampon): {insee['total_pop']} habitants",
            f"Densité moyenne pondérée             : {insee['mean_density_km2']} hab/km²",
            f"Qualification environnement SORA     : {insee['sora_density_class']}",
            f"Carreaux INSEE intersectés           : {insee['intersected_features']}",
            "",
            "----------------------------------------------------------------------",
            "2. PARAMÈTRES CINÉMATIQUES DU DRONE & SORA",
            "----------------------------------------------------------------------",
            f"Modèle de drone      : {mission['drone_name']}",
            f"Vitesse max (V0)     : {sora['v0']:.1f} m/s | Hauteur (H): {sora['h']:.1f} m",
            f"Zone de contingence  : {sora['contingency_m']:.1f} m",
            f"Zone tampon (sol)    : {sora['buffer_m']:.1f} m",
            "",
            "----------------------------------------------------------------------",
            "3. SYNTHÈSE DES SURFACES",
            "----------------------------------------------------------------------",
            f"• Zone de vol        : {z_vol['area']:.1f} m²",
            f"• Zone contingence   : {z_cont['area']:.1f} m²",
            f"• Zone tampon        : {z_tamp['area']:.1f} m²",
            "======================================================================",
        ]
        return "\n".join(lines) + "\n"

    def export_mission(self):
        if not self.last_mission_data:
            self._push_error("Aucun calcul disponible pour l'export.")
            return

        mission = self.last_mission_data
        safe_drone = re.sub(r"[^a-zA-Z0-9_-]+", "_", mission["drone_name"]).strip("_")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter SORA + INSEE",
            os.path.join(os.path.expanduser("~"), f"Mission_SORA_INSEE_{safe_drone}.gpkg"),
            "GeoPackage (*.gpkg);;Google Earth KML (*.kml)"
        )
        if not file_path:
            return

        is_kml = file_path.lower().endswith(".kml")
        if is_kml and not file_path.lower().endswith(".kml"): file_path += ".kml"
        elif not is_kml and not file_path.lower().endswith(".gpkg"): file_path += ".gpkg"

        # Build combined layer
        uri = f"Polygon?crs={mission['crs'].authid()}"
        layer = QgsVectorLayer(uri, f"Zones_SORA_{safe_drone}", "memory")
        prov = layer.dataProvider()
        prov.addAttributes([
            QgsField("Name", QVariant.String), QgsField("Description", QVariant.String),
            QgsField("Pop_Exposee", QVariant.Double), QgsField("Densite_km2", QVariant.Double),
            QgsField("Classe_SORA", QVariant.String)
        ])
        layer.updateFields()

        feats = []
        for spec in reversed(mission["zones_spec"]):
            feat = QgsFeature(layer.fields())
            feat.setGeometry(spec["geom"])
            feat.setAttributes([
                spec["zone_type"],
                f"Pop: {mission['insee']['total_pop']} | Densité: {mission['insee']['mean_density_km2']} hab/km²",
                mission['insee']['total_pop'], mission['insee']['mean_density_km2'],
                mission['insee']['sora_density_class']
            ])
            feats.append(feat)
        prov.addFeatures(feats)
        layer.updateExtents()

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "KML" if is_kml else "GPKG"
        options.fileEncoding = "UTF-8"
        options.layerName = f"Zones_SORA_{safe_drone}"
        if is_kml:
            options.ct = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())

        if hasattr(QgsVectorFileWriter, "writeAsVectorFormatV3"):
            QgsVectorFileWriter.writeAsVectorFormatV3(layer, file_path, QgsProject.instance().transformContext(), options)
        else:
            QgsVectorFileWriter.writeAsVectorFormatV2(layer, file_path, QgsProject.instance().transformContext(), options)

        # Write text report
        report_path = f"{os.path.splitext(file_path)[0]}_rapport_SORA_INSEE.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(self._generate_report_text(mission, file_path))

        self.iface.messageBar().pushMessage("Export réussi", f"Fichiers enregistrés avec succès.", level=Qgis.Success, duration=6)

    def cleanup(self):
        self.clear_capture()
        if self.canvas.mapTool() in (self.point_tool, self.polygon_tool):
            self.canvas.unsetMapTool(self.canvas.mapTool())
