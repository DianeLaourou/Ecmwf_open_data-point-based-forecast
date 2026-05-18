# 🌊 Dashboard Marine — Sème (METEO-BENIN)

**Auteur :** LAOUROU MAKONDJOU DIANE  
**Structure :** METEO-BENIN / DPROM / SPAM  
**Point :** Sème — 6.22°N, 2.63°E, Golfe de Guinée, Bénin

---

## 📦 Fichiers à ajouter à votre dépôt GitHub

```
Ecmwf_open_data-point-based-forecast/
├── dashboard.py          ← Application Streamlit  ✅ NOUVEAU
├── requirements.txt      ← Dépendances Python     ✅ NOUVEAU
├── .streamlit/
│   └── config.toml       ← Thème & config         ✅ NOUVEAU
├── config.py             (existant)
├── extractor.py          (existant)
├── exporter.py           (existant)
├── word_exporter.py      (existant)
├── run_pipeline.py       (existant)
└── ...
```

---

## 🚀 Déploiement sur Streamlit Cloud

### Étape 1 — Pousser les fichiers sur GitHub
```bash
git add dashboard.py requirements.txt .streamlit/config.toml
git commit -m "feat: ajout dashboard Streamlit interactif"
git push origin main
```

### Étape 2 — Créer l'application sur Streamlit Cloud
1. Aller sur **https://share.streamlit.io**
2. Cliquer **"New app"**
3. Sélectionner votre dépôt : `DianeLaourou/Ecmwf_open_data-point-based-forecast`
4. Branch : `main`
5. Main file path : `dashboard.py`
6. Cliquer **"Deploy!"**

### Étape 3 — Secrets Streamlit (si mode Pipeline live)
Dans Streamlit Cloud → Settings → Secrets :
```toml
# Copernicus Marine (si utilisé)
COPERNICUSMARINE_SERVICE_USERNAME = "votre_username"
COPERNICUSMARINE_SERVICE_PASSWORD = "votre_password"

# WorldTides API (optionnel)
WORLDTIDES_API_KEY = "votre_clé"
```

---

## 💻 Lancement local

```bash
conda activate marine_pipeline
pip install streamlit plotly kaleido
streamlit run dashboard.py
```

Ouvre automatiquement : **http://localhost:8501**

---

## 🎛️ Fonctionnalités du dashboard

| Fonctionnalité | Description |
|---|---|
| **Modes données** | Démo (synthétique) ou Pipeline live (ECMWF + Copernicus) |
| **Sélection variables** | Checkbox par groupe : Vagues, Vent, Pression, Autres |
| **Filtre temporel** | Slider 0–120h |
| **Séries temporelles** | Subplots interactifs, seuils d'alerte colorés |
| **Rose des vents** | Barpolar par classe de vitesse |
| **Boussole swell** | Scatterpolar direction/hauteur Swell 1 & 2 |
| **Matrice corrélation** | Heatmap + scatter personnalisé |
| **KPI header** | SWH max, vent max, rafale, MSLP, SST, précip |
| **Warning automatique** | 🟢 Normal / 🟡 Prudence / 🔴 Danger |
| **Export CSV** | Délimiteur point-virgule, encodage UTF-8 BOM |
| **Export Excel** | `.xlsx` via openpyxl |
| **Export JSON** | Format records avec timestamps ISO |
| **Export PNG** | Via kaleido (à activer dans requirements.txt) |
| **Bulletin texte** | Synthèse téléchargeable `.txt` |

---

## ⚠️ Note sur l'export PNG

Pour activer l'export PNG des graphiques Plotly, décommenter dans `requirements.txt` :
```
kaleido>=0.2.1
```
Kaleido est parfois instable sur Streamlit Cloud ; si des erreurs apparaissent, le bouton sera simplement désactivé.

---

## 📊 Colonnes DataFrame supportées

| Colonne | Description | Unité |
|---|---|---|
| `valid_local` | Heure locale de validité | — |
| `wind10_dir` | Direction vent 10m | ° |
| `wind10_spd_kt` | Vitesse vent 10m | kt |
| `wind10_gust_kt` | Rafales 10m | kt |
| `wind100_dir` | Direction vent 100m | ° |
| `wind100_spd_kt` | Vitesse vent 100m | kt |
| `mslp_hpa` | Pression mer | hPa |
| `vis_km` | Visibilité | km |
| `t2m_c` | Température 2m | °C |
| `rain_pct` | Probabilité précip. | % |
| `sst_c` | Température surface mer | °C |
| `sw1_dir` | Direction swell 1 | ° |
| `sw1_period_s` | Période swell 1 | s |
| `sw1_ht_m` | Hauteur swell 1 | m |
| `sw2_dir` | Direction swell 2 | ° |
| `sw2_period_s` | Période swell 2 | s |
| `sw2_ht_m` | Hauteur swell 2 | m |
| `swh_m` | Hauteur significative vagues | m |
| `cur_dir` | Direction courant | ° |
| `cur_spd_kt` | Vitesse courant | kt |

---

*© 2026 LAOUROU MAKONDJOU DIANE — METEO-BENIN / DPROM / SPAM*
