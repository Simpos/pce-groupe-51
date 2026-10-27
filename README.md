# Zones de vol — Drone Flight-Zone Planner

> **Repository:** https://github.com/Simpos/pce-groupe-51  
> **Application type:** QGIS desktop plugin  
> **Purpose:** define a drone flight area and calculate surrounding contingency and buffer areas.

This README is also a reverse-engineering specification for GitReverse or another AI code-reconstruction tool. It documents observed behavior and highlights incomplete features so a reconstruction does not invent functionality.

## 1. Product overview

“Zones de vol” is a Python plugin for QGIS, built with PyQGIS and Qt widgets. It adds a **Zones de vol** action to the QGIS menu and toolbar. Activating it opens a dockable panel on the right side of QGIS.

The plugin lets a user define an initial drone flight area and visualize three zone types:

- **Flight area (`fly`)**: a user-defined polygon, or a polygon generated around one map point.
- **Contingency area (`cont`)**: an outward buffer of the flight area using the selected drone's radio range.
- **Buffer area (`buffer`)**: a further outward buffer around the contingency area using the drone's buffer distance.
- **Restricted area (`ban`)**: a zone type known to the zone manager, but official restricted-zone loading and end-to-end integration are not implemented in the current workflow.

A drone catalogue is stored as one text file per drone. The interface also includes altitude, speed, and accepted-population-density inputs; the current calculation service does not use those values. They must not be described as active calculation parameters unless implemented as a tested extension.

## 2. Main user workflow

1. Open QGIS and load the **Zones de vol** plugin.
2. Open it from the menu or toolbar; a right-side dock appears.
3. Select a drone. The panel displays name, type, radio range, air speed, and buffer distance.
4. Choose a starting mode:
   - **Point mode:** Ctrl + left-click a point on the map. A subsequent point replaces the previous point.
   - **Polygon mode:** Ctrl + left-click at least three points to define a polygon.
5. Click **Lancer le calcul**.
6. The plugin validates the input geometry and required drone distances, calculates the contingency and buffer geometries, and draws them on the map.
7. Input points are cleared after successful calculation; result polygons remain displayed.
8. Closing the dock or choosing **Arrêter le plug-in** triggers cleanup through the implemented lifecycle handlers.

Ordinary left-click-and-drag pans the map. Ctrl + left-click adds a point. Right-click unsets the custom map tool. Changing modes clears points collected in the previous mode.

## 3. User interface

The main dock is defined in `flying_areas_dialog_base.ui` and coordinated by `flying_areas_dialog.py`.

### Drone section
- Dropdown populated from `Base_drones/*.txt`.
- **Ajouter un drone** opens a secondary window.
- Labels show the selected drone's name, type, radio range, air speed, and buffer distance.

The secondary window (`second_window.ui` and `second_window.py`) is currently a placeholder, not a complete add/edit/save workflow.

### Flight parameters
- Starting mode dropdown: point or polygon.
- Relative altitude, in metres.
- Drone flight speed, in km/h.
- Accepted population density, in inhabitants/km².

The current code sets numeric widget ranges but does not pass these three values into `ZoneCalculateur.calculate_areas()`. Preserve that fact or explicitly document and test any extension.

### Actions and feedback
- **Lancer le calcul** validates input and generates zones.
- **Arrêter le plug-in** closes the dock and resets parameter widgets.
- Loading and validation problems are reported in the QGIS message bar under **Zones de vol**.

## 4. Calculation and geometry rules

The calculation service is in `source/calculZone.py`; polygon operations are in `source/zone.py`.

1. The initial polygon must have at least three vertices and pass QGIS geometry validity checks.
2. In point mode, the current implementation generates a polygon with 30 vertices. The current call uses a radius of **10 map units**; a constant elsewhere suggests 100 metres, but that constant is not used. Do not silently treat the actual radius as 100 metres.
3. Both `radio_dist` and `buffer_dist` must be present for the selected drone; otherwise calculation stops with a validation error.
4. The contingency polygon is a QGIS geometry buffer of the flight polygon by `radio_dist`.
5. The buffer polygon is a further buffer around the contingency polygon by `buffer_dist`.
6. Invalid geometries are repaired with `makeValid()` before buffering.
7. If buffering creates multiple polygons, the current helper keeps only the largest part and ignores other parts and holes.
8. Output is stored in a temporary polygon layer in **EPSG:2154 (Lambert-93)**. The point manager transforms canvas coordinates to this CRS.
9. Styling uses translucent categories: flight green, contingency orange, buffer red, and restricted area black.
10. Priority values are restricted (`ban`) 4, flight (`fly`) 3, contingency (`cont`) 2, and buffer (`buffer`) 1. The zone manager subtracts overlaps according to priority. The current calculation adds flight, buffer, and contingency zones in that order; review and test this interaction before changing it.

The current workflow does not load official no-fly-zone or population-density datasets. Do not claim regulatory compliance or flight authorization.

## 5. Drone catalogue format

Each UTF-8 `.txt` file in `Base_drones/` must contain exactly five lines:

1. Drone name
2. Radio range / contingency distance (number or `null`)
3. Air speed (number or `null`)
4. Drone type
5. Buffer distance (number or `null`)

Example:

```text
Example Drone
500
15
Multirotor
100
```

Numeric values are parsed as floating-point numbers; literal `null` becomes Python `None`. Radio range and buffer distance are required for calculations. Drone files are discovered in alphabetical filename order.

## 6. Architecture and key files

| Path | Responsibility |
| --- | --- |
| `__init__.py` | QGIS plugin entry point / factory. |
| `flying_areas.py` | Menu and toolbar registration, dock lifecycle, plugin unloading. |
| `flying_areas_dialog.py` | Main UI behavior, drone loading, validation, calculation orchestration, feedback. |
| `flying_areas_dialog_base.ui` | Qt Designer definition of the main dock. |
| `second_window.py`, `second_window.ui` | Secondary window; currently a placeholder. |
| `source/drone.py` | Drone domain model and creation/modification helpers. |
| `source/file_managing.py` | Reads and writes five-line drone files. |
| `source/zone.py` | Polygon model, validation, point-based polygon generation, buffering. |
| `source/calculZone.py` | Calculates flight, contingency, and buffer zones. |
| `source/pointManager.py` | Map tool for capturing points and managing the temporary point layer. |
| `source/zoneManager.py` | Temporary polygon layer, styling, overlap and priority management. |
| `Base_drones/` | Drone catalogue files. |
| `tests/` | Pytest coverage for geometry, calculations, file management, UI orchestration, and managers. |
| `metadata.txt` | QGIS plugin metadata. |
| `Makefile`, `pb_tool.cfg` | Development, testing, packaging, and deployment helpers. |

## 7. Technology and environment

- Python 3
- QGIS 3.x and PyQGIS
- Qt widgets through `qgis.PyQt`
- QGIS geometry APIs (`QgsGeometry`, `QgsPointXY`) and in-memory vector layers
- NumPy for point-based polygon construction
- pytest
- Plugin Builder / `pb_tool`

This is a **QGIS desktop plugin**, not a standalone web application. A faithful recreation should remain integrated with QGIS unless a different platform is explicitly requested.

## 8. Development and testing

Run from the repository root in an environment with QGIS/PyQGIS and project dependencies available:

```bash
python3 -m pytest tests -v
```

The Makefile defines:

```bash
make test      # run pytest tests
make compile   # pb_tool compile
make deploy    # compile, test, then deploy through pb_tool
make zip       # compile, test, then package the plugin
make doc       # generate plugin documentation through pb_tool
```

`make all` runs compile, test, and deploy. `pb_tool` requires Plugin Builder tooling and a correctly configured local QGIS profile.

## 9. Reconstruction prompt for GitReverse

Use the following prompt as the primary specification for reconstructing the application.

---

### Prompt: Recreate “Zones de vol” QGIS plugin

You are an expert Python, PyQGIS, and Qt desktop application engineer. Analyze the full repository and recreate **Zones de vol** as a working QGIS 3.x plugin. Inspect all relevant source files, UI definitions, drone data files, and tests before implementation. Treat the code as evidence of current behavior; do not invent features.

**Objective:** Build a QGIS plugin that lets a user select a drone, define a flight area from one map point or a polygon, and calculate/display flight, contingency, and buffer areas using drone radio-range and buffer-distance values.

**Platform and architecture**
- Use Python 3, PyQGIS, and `qgis.PyQt`.
- Preserve plugin lifecycle: factory entry point, initialization, menu/toolbar registration, dock display, and clean unloading.
- Use a dockable panel integrated with the QGIS map canvas.
- Keep responsibilities separated into plugin lifecycle/controller, UI controller, drone model and file persistence, map-point capture, zone geometry, calculation service, and zone-layer manager.
- Use the supplied Qt Designer `.ui` files and widget names as the UI source of truth unless making a deliberate, documented improvement.
- Preserve French-facing labels and QGIS message-bar feedback.

**Required behavior**
1. Register a QGIS menu entry and toolbar action named **Zones de vol**.
2. Open a right-docked panel.
3. Populate a drone dropdown from `Base_drones/*.txt`; display drone name, type, radio range, air speed, and buffer distance.
4. Provide point and polygon starting modes:
   - Point mode: Ctrl + left-click captures one point; the next replaces it.
   - Polygon mode: Ctrl + left-click captures vertices; require at least three.
   - Normal left-drag pans the map; right-click unsets the map tool.
   - Switching modes clears old points.
5. Provide numeric controls for altitude (m), speed (km/h), and accepted population density (inhabitants/km²), plus **Lancer le calcul** and **Arrêter le plug-in**.
6. Validate the selected drone, starting geometry, and required distances; show useful French messages in the QGIS message bar.
7. Generate a point-centered polygon or use the user-defined polygon. Buffer it by drone radio range for contingency, then buffer contingency by drone buffer distance for the buffer zone.
8. Display geometries in a temporary EPSG:2154 polygon layer with transparent categorized styling and deterministic overlap/priority handling. Clean up temporary layers and map tools appropriately.
9. Preserve the existing five-line UTF-8 drone-file format and handle malformed files or missing values safely.
10. Provide automated tests for geometry validity, buffer distances, drone parsing/writing, map point capture, zone priority/overlap, and UI orchestration.

**Fidelity and correctness constraints**
- Inspect code before coding and identify discrepancies instead of guessing.
- Current point mode uses radius **10 map units** and 30 vertices, despite a constant suggesting a different intended radius. Make the chosen behavior explicit and test it.
- Altitude, speed, and population-density inputs are not currently used in the calculation service. Do not imply they affect results unless implementing and testing a documented extension.
- Restricted-area support is incomplete: the `ban` type exists, but official restricted-area data is not loaded in the current workflow.
- The add-drone window is a placeholder. Do not claim complete drone management unless implementing and testing it.
- The geometry helper keeps only the largest part of multipart buffers and ignores holes. Preserve for strict compatibility or improve with tests and explicit documentation.
- Do not claim generated zones certify legal compliance or replace official aviation/geospatial data.
- Preserve French labels unless internationalization is requested.
- Follow PEP 8 where practical, add type hints, and keep geometry/calculation logic testable independently from UI code.

**Expected deliverables**
- Complete installable QGIS plugin source and UI definitions.
- No placeholder implementation for features declared complete.
- Automated tests for valid and invalid inputs.
- Installation/development instructions and documentation of architecture, file format, and limitations.
- A final report of implemented features, tests and results, known limitations, and deviations from source behavior.

**Acceptance criteria**
- Loads in supported QGIS 3.x without import or UI errors.
- Menu/toolbar action opens the dock and unloads cleanly.
- Drone files load deterministically; malformed files produce warnings without crashing.
- Point and polygon modes follow the specified mouse interactions and validation.
- Valid input produces three valid displayed zones with expected distances and styles.
- Missing drone distances and invalid geometry are handled safely.
- Overlap priority is deterministic and tested.
- Tests pass in the documented environment; incomplete features are clearly identified.

Before writing code, first produce a concise map of modules and tests, then implement incrementally. Do not replace QGIS/PyQGIS with a web stack or mock map unless a non-QGIS port is explicitly requested.

---

## 10. Known gaps for future development

- Decide and document the intended point-mode radius and its CRS/units.
- Connect altitude, speed, and population density to a defined model, or label them as future inputs.
- Implement drone creation/editing in the secondary window, including validation and persistence.
- Integrate official restricted/no-fly and population datasets only after defining sources, CRS, update strategy, and regulatory assumptions.
- Review overlap priority and subtraction order with geometry tests.
- Decide whether multipart buffer components and holes should be preserved.
- Verify cleanup on dock close, plugin unload, and repeated calculations.

## License

The repository includes a GNU General Public License (GPL) license file. See [LICENSE](LICENSE) for the exact terms.
