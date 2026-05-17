# 🌊 Pipeline de Prévision Marine Automatisé — Sème (Bénin)

**Agence Nationale de la Météorologie du Bénin**  
Direction de la Prévision et du Réseau d'Observation Météorologique

---

## Auteur

**LAOUROU MAKONDJOU DIANE**  
Météorologiste & Data Scientist  
METEO-BENIN / DPROM / SPAM  
Mai 2026

---

## Description

Pipeline Python automatisé pour la génération du bulletin de prévision marine au point **Sème (6.22°N, 2.63°E)**, Golfe de Guinée, Bénin.

Génère automatiquement :
- 📊 **Fichier Excel** (4 feuilles : données + graphique + ENSgram + probabilités)
- 📝 **Bulletin Word** (7 pages : en-tête + tableau + figures + marées)

---

## Sources de données

| Source | Variables | Accès |
|--------|-----------|-------|
| [ECMWF Open Data](https://www.ecmwf.int/en/forecasts/datasets/open-data) | Vent 10m/100m, Rafale, MSLP, T°C, SWH | Gratuit |
| [Copernicus Marine](https://marine.copernicus.eu) | Swell1/2, Courants, SST | Gratuit (inscription) |
| [WorldTides API](https://www.worldtides.info) | Marées hautes/basses | Gratuit (clé API) |

---

## Structure du projet

```
D:\pipeline\
├── config.py               # Paramètres (point, seuils, clés API)
├── extractor.py            # Extraction ECMWF + Copernicus
├── exporter.py             # Génération Excel
├── word_exporter.py        # Génération bulletin Word
├── run_pipeline.py         # Script principal
├── tides.py                # Marées automatiques
├── gdrive.py               # Upload Google Drive (optionnel)
├── install_deps.py         # Vérification dépendances
├── check_variables.py      # Diagnostic variables GRIB2
├── run_marine_pipeline.bat # Automatisation Windows
├── logo_republique.png     # Logo République du Bénin
└── logo_meteo_oval.png     # Logo Météo Bénin
```

---

## Installation

### 1. Créer l'environnement conda
```cmd
conda create -n marine_pipeline python=3.11
conda activate marine_pipeline
```

### 2. Installer les packages (tout via conda pour éviter les erreurs DLL Windows)
```cmd
conda install -c conda-forge pandas openpyxl cfgrib eccodes xarray numpy matplotlib Pillow requests python-docx
pip install ecmwf-opendata copernicusmarine
```

### 3. Authentification Copernicus Marine
```cmd
copernicusmarine login
```

### 4. Vérification
```cmd
python install_deps.py
```

---

## Utilisation

```cmd
conda activate marine_pipeline
cd D:\pipeline

# Run automatique (run la plus récente)
python run_pipeline.py --swh ecmwf

# Run spécifique
python run_pipeline.py --date 2026-05-16 --hour 12 --swh ecmwf
```

---

## Automatisation Windows

Planifier `run_marine_pipeline.bat` via le Planificateur de tâches Windows à **15h00** heure locale.

---

## Configuration

Éditer `config.py` pour adapter le point de prévision :

```python
POINT = {"name": "Sème", "lat": 6.22, "lon": 2.63}
UTC_OFFSET = 1  # UTC+1 pour le Bénin
```

---

## Système d'alertes

| Condition | Couleur | Warning |
|-----------|---------|---------|
| SWH < 1.6m | Normal | Warning: None |
| 1.6m ≤ SWH < 2.0m | 🟡 Jaune | Warning: None + prudence |
| SWH ≥ 2.0m | 🔴 Rouge | Warning: activé |
| Vent ≥ 15 kts | 🟡 Jaune | — |
| Vent ≥ 20 kts | 🔴 Rouge | Warning: activé |

---

## Licence

Usage interne — Agence Nationale de la Météorologie du Bénin  
© 2026 LAOUROU MAKONDJOU DIANE — Tous droits réservés
