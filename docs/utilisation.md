# Manuel d'utilisation

Ce manuel explique comment installer et utiliser le plugin FlyingAreas dans QGIS.

<!-- À COMPLÉTER : les noms de boutons, champs et menus ci-dessous sont à vérifier
     par rapport à l'interface réelle. Ajouter les captures d'écran dans docs/img/ -->

## 1. Installation

### Depuis les sources (développeurs)

Avec [pb_tool](http://g-sherman.github.io/plugin_build_tool/) :

```bash
pb_tool deploy
```

Le plugin est copié dans le dossier des plugins du profil QGIS :

- Linux : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/flying_areas`
- Windows : `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\flying_areas`
- macOS : `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/flying_areas`

### Depuis une archive ZIP

1. Dans QGIS, ouvrir **Extensions → Installer/Gérer les extensions**.
2. Choisir l'onglet **Installer depuis un ZIP**.
3. Sélectionner l'archive du plugin, puis cliquer sur **Installer**.

### Activation

Dans **Extensions → Installer/Gérer les extensions → Installées**, cocher **FlyingAreas**. Une icône apparaît dans la barre d'outils et une entrée dans le menu **Extensions**.

<!-- capture : img/activation_plugin.png -->

## 2. Lancement

Cliquer sur l'icône FlyingAreas de la barre d'outils, ou ouvrir **Extensions → FlyingAreas**. La fenêtre principale s'affiche.

<!-- capture : img/fenetre_principale.png -->

## 3. Fenêtre principale

La fenêtre principale permet de paramétrer le calcul des zones de vol.

| Élément | Description |
|---|---|
| Choix du drone | Sélectionne un modèle dans la base de drones |
| Couche d'entrée | Couche QGIS servant de base au calcul |
| Paramètres de calcul | Valeurs numériques ajustables |
| Bouton de calcul | Lance le calcul des zones |
| Accès à la seconde fenêtre | Ouvre les options complémentaires |

<!-- À COMPLÉTER : remplacer ce tableau par les vrais éléments de flying_areas_dialog_base.ui -->

## 4. Seconde fenêtre

<!-- À COMPLÉTER : décrire le rôle de second_window.ui et comment l'ouvrir -->

<!-- capture : img/seconde_fenetre.png -->

## 5. Scénarios d'utilisation

### 5.1 Calculer une zone de vol

1. Charger dans QGIS la couche de travail.
2. Ouvrir FlyingAreas.
3. Sélectionner le drone dans la liste.
4. Renseigner les paramètres de calcul.
5. Cliquer sur le bouton de calcul.
6. La couche résultat est ajoutée au projet QGIS.

### 5.2 Utiliser le mode expansion

<!-- À COMPLÉTER : expliquer ce que fait l'expansion d'une zone, ses paramètres,
     et quand l'utiliser (voir source/modeExpansion.py) -->

### 5.3 Gérer les zones existantes

<!-- À COMPLÉTER : consulter, modifier ou supprimer des zones (voir source/zoneManager.py) -->

## 6. Résultats

Les zones calculées sont ajoutées sous forme de couches dans le panneau **Couches** de QGIS. Elles peuvent être stylisées, exportées (GeoPackage, Shapefile, GeoJSON…) ou utilisées dans d'autres traitements.

<!-- capture : img/resultat.png -->

## 7. Dépannage

| Problème | Cause probable | Solution |
|---|---|---|
| Le plugin n'apparaît pas dans QGIS | Plugin non activé ou mal déployé | Vérifier dans le gestionnaire d'extensions, relancer `pb_tool deploy` |
| Erreur au chargement du plugin | Fichier `.ui` ou module manquant | Consulter **Extensions → Console Python** ou le panneau **Messages du journal** |
| Aucun drone dans la liste | Dossier `Base_drones` absent du plugin | Vérifier qu'il est bien dans `extra_dirs` du `pb_tool.cfg` |
| Le calcul ne produit pas de couche | Couche d'entrée invalide ou vide | Vérifier la couche, son système de coordonnées et sa géométrie |

## 8. Aide et contact

Pour signaler un problème ou poser une question : <adrien.seminatore@imt-atlantique.net>.
