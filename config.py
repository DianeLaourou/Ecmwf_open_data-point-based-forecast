# =============================================================================
# config.py — Configuration du pipeline de prévision marine (Sème)
# =============================================================================

# --- Point de prévision ---
POINT = {
    "name": "Sème",
    "lat" :  6.22,
    "lon" :  2.63,
}

# --- Source du SWH total ---
# "ecmwf"      : Option A — SWH depuis ECMWF Open Data  (défaut)
# "copernicus" : Option B — SWH depuis Copernicus Marine (cohérence maximale)
SWH_SOURCE = "ecmwf"

# --- Fuseau horaire local (UTC+1 pour le Bénin) ---
UTC_OFFSET = 1

# --- Durée de prévision (heures) ---
# 84h pour couvrir J 19h → J+3 19h depuis n'importe quelle run (00Z, 06Z, 12Z, 18Z)
FORECAST_HOURS = 120  # 120h garantit J+3 19h depuis n'importe quelle run

# --- Seuils d'alerte ---
ALERT_SWH_WARNING = 1.6   # m → cellule jaune (entre 1.6 et 2.0m)
ALERT_SWH_DANGER  = 2.0   # m → cellule rouge (≥ 2.0m) + Warning activé
ALERT_WIND_WARNING = 15   # kts → cellule jaune
ALERT_WIND_DANGER  = 20   # kts → cellule rouge

# --- Datasets Copernicus Marine ---

# Vagues : Swell1, Swell2, SWH (prévisions anfc)
COPERNICUS_DATASET   = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
COPERNICUS_VARIABLES = [
    "VHM0",       # SWH total (option B)
    "VHM0_SW1",   # Hauteur houle 1
    "VMDR_SW1",   # Direction houle 1
    "VTM01_SW1",  # Période houle 1
    "VHM0_SW2",   # Hauteur houle 2
    "VMDR_SW2",   # Direction houle 2
    "VTM01_SW2",  # Période houle 2
]

# Physique océanique : courants (uo, vo) + SST (thetao) — prévisions anfc
COPERNICUS_PHY_DATASET   = "cmems_mod_glo_phy_anfc_0.083deg_PT1H-m"
COPERNICUS_PHY_VARIABLES = [
    "uo",      # composante U courant de surface (m/s)
    "vo",      # composante V courant de surface (m/s)
    "thetao",  # température potentielle surface = SST (°C)
]

# --- WorldTides API (marées automatiques) ---
# Inscription gratuite sur https://www.worldtides.info
# Remplacez "VOTRE_CLE_ICI" par votre clé API après inscription
WORLDTIDES_API_KEY = "b6f34de2-9b6f-4c52-ae06-98f6c4a78037"
OUTPUT_FILE = "D:/pipeline/bulletin_marine_seme.xlsx"