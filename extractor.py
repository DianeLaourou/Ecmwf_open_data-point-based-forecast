# =============================================================================
# extractor.py — Extraction ECMWF Open Data + Copernicus Marine
# Sans Google Earth Engine
# =============================================================================

import math
import numpy as np
import pandas as pd
import xarray as xr
import copernicusmarine
from ecmwf.opendata import Client
from datetime import datetime, timedelta
from pathlib import Path
import config

# ---------------------------------------------------------------------------
# Utilitaires de conversion
# ---------------------------------------------------------------------------

def ms_to_knots(ms):
    return round(float(ms) * 1.94384) if ms is not None and not np.isnan(ms) else None

def pa_to_hpa(pa):
    return round(float(pa) / 100.0) if pa is not None and not np.isnan(pa) else None

def kelvin_to_celsius(k):
    return round(float(k) - 273.15) if k is not None and not np.isnan(k) else None

def uv_to_dir_speed(u, v):
    """
    Composantes U/V → direction météo FROM (°) et vitesse (m/s).
    Convention météo : direction d'où VIENT le vent (FROM).
    Utilisé pour le vent uniquement.
    """
    if u is None or v is None:
        return None, None
    speed = math.sqrt(float(u)**2 + float(v)**2)
    direction = (270 - math.degrees(math.atan2(float(v), float(u)))) % 360
    return round(direction, 1), round(speed, 2)

def uv_to_current_dir_speed(u, v):
    """
    Composantes U/V → direction océanographique TO (°) et vitesse (m/s).
    Convention océano : direction vers où VA le courant (TO).
    Utilisé pour les courants marins.
    """
    if u is None or v is None:
        return None, None
    speed = math.sqrt(float(u)**2 + float(v)**2)
    direction = (90 - math.degrees(math.atan2(float(v), float(u)))) % 360
    return round(direction, 1), round(speed, 2)


def calc_visibility(t2m_k, td2m_k, tcc):
    """
    Calcule la visibilité (km) :
      1. Humidité relative via formule de Magnus
      2. Visibilité de base via Kunkel (1984)
      3. Correction par couverture nuageuse
    Résultat clampé entre 0.1 et 10 km.
    """
    if t2m_k is None or td2m_k is None:
        return None
    try:
        T  = float(t2m_k)  - 273.15
        Td = float(td2m_k) - 273.15
        rh = 100.0 * (
            math.exp(17.625 * Td / (243.04 + Td)) /
            math.exp(17.625 * T  / (243.04 + T))
        )
        rh  = min(rh, 99.9)
        vis = -math.log(1.0 - rh / 100.0) / 0.135
        if tcc is not None:
            vis = vis * (1.0 - 0.4 * float(tcc))
        return round(max(0.1, min(10.0, vis)), 1)
    except Exception:
        return None


def calc_rain_chance(tp_current_m, tp_prev_m):
    """
    Probabilité de pluie (%) sur 3h via sigmoïde tropicale.
      tp en mètres (cumul ECMWF) → différence → mm → sigmoïde.
    """
    if tp_current_m is None:
        return 0
    try:
        tp_prev  = float(tp_prev_m) if tp_prev_m is not None else 0.0
        tp_3h_mm = max(0.0, (float(tp_current_m) - tp_prev) * 1000.0)
        prob     = 1.0 / (1.0 + math.exp(-4.0 * (tp_3h_mm - 0.5)))
        return int(max(0, min(100, round(prob * 100 / 10) * 10)))
    except Exception:
        return 0

def degrees_to_cardinal(deg):
    """Angle → direction cardinale (N, NE, E, ...)."""
    if deg is None or np.isnan(deg):
        return "—"
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
            "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(float(deg) / 22.5) % 16]

def nearest(ds, lat, lon):
    """Sélectionne le point de grille le plus proche."""
    return ds.sel(latitude=lat, longitude=lon, method="nearest")

# ---------------------------------------------------------------------------
# ECMWF Open Data — paramètres météo + SWH
# ---------------------------------------------------------------------------

def extract_ecmwf(run_datetime: datetime) -> pd.DataFrame:
    """
    Télécharge et extrait depuis ECMWF Open Data :
      - Vent 10m  (u10, v10, fg10) → direction + vitesse + rafale en noeuds
      - Vent 100m (u100, v100)     → direction + vitesse en noeuds
      - MSLP (hPa), T 2m (°C)
      - SWH total (m)

    Retry automatique sur les 3 miroirs (aws → azure → google) en cas d'erreur.
    """
    import time

    tmp_dir = Path("tmp_ecmwf")
    tmp_dir.mkdir(exist_ok=True)
    steps   = list(range(0, 121, 3))  # 0 à 120h, pas de 3h — garantit J+3 19h

    # ── Fonction de téléchargement avec retry sur les miroirs ─────────────
    MIRRORS = ["azure", "google", "aws"]
    MAX_RETRY = 3

    def download(params, target, label):
        """Tente le téléchargement sur les miroirs disponibles avec retry."""
        for mirror in MIRRORS:
            for attempt in range(1, MAX_RETRY + 1):
                try:
                    # Client() à l'intérieur du try pour capturer le 429 SAS token Azure
                    client = Client(source=mirror)
                    client.retrieve(**params, target=str(target))
                    print(f"  ✅ {label} (source: {mirror})")
                    return True
                except Exception as e:
                    err = str(e)
                    if any(x in err for x in ["503","SlowDown","429","Too Many"]):
                        wait = 30 * attempt
                        print(f"  ⏳ {mirror} saturé — attente {wait}s (tentative {attempt}/{MAX_RETRY})...")
                        time.sleep(wait)
                    elif "404" in err or "Not Found" in err:
                        print(f"  ⚠️  {label} non disponible sur {mirror} — miroir suivant.")
                        break
                    else:
                        print(f"  ⚠️  {mirror} : {err[:80]} — miroir suivant.")
                        break
        print(f"  ❌ {label} : tous les miroirs ont échoué.")
        return False

    print("  📡 Téléchargement ECMWF Open Data...")

    # ── Fichier atmosphérique ──────────────────────────────────────────────
    atm_file = tmp_dir / "ecmwf_atm.grib2"
    ok_atm = download(
        params={
            "date": run_datetime.strftime("%Y-%m-%d"),
            "time": run_datetime.hour,
            "step": steps, "stream": "oper", "type": "fc",
            "param": ["10u", "10v", "10fg", "100u", "100v", "msl", "2t",
                      "2d",   # point de rosée → visibilité
                      "tcc",  # couverture nuageuse totale → visibilité
                      "tp",   # précipitation totale → chance de pluie
                      ],
        },
        target=atm_file,
        label="Paramètres atmosphériques"
    )
    if not ok_atm:
        raise RuntimeError("Impossible de télécharger les paramètres atmosphériques ECMWF.")

    # ── SWH (stream wave) ─────────────────────────────────────────────────
    wav_file = tmp_dir / "ecmwf_wav.grib2"
    ok_wav = download(
        params={
            "date": run_datetime.strftime("%Y-%m-%d"),
            "time": run_datetime.hour,
            "step": steps, "stream": "wave", "type": "fc",
            "param": ["swh"],
        },
        target=wav_file,
        label="SWH"
    )

    # ── Ouverture des datasets cfgrib ──────────────────────────────────────
    import cfgrib
    def open_ds(filepath):
        """Ouvre tous les datasets d'un fichier GRIB2, retourne un dict var→ds."""
        result = {}
        try:
            datasets = cfgrib.open_datasets(
                str(filepath),
                backend_kwargs={"indexpath": ""}
            )
            for ds in datasets:
                for var in ds.data_vars:
                    result[var] = ds
        except Exception as e:
            print(f"  ⚠️  Erreur ouverture {filepath.name} : {e}")
        return result

    ds_atm = open_ds(atm_file)
    ds_wav = open_ds(wav_file) if ok_wav else {}
    ds_sst = {}

    # Noms réels confirmés par diagnostic :
    # u10, v10, fg10  → vent 10m + rafale
    # u100, v100      → vent 100m
    # t2m             → température 2m
    # msl             → pression mer
    # swh             → hauteur vagues significative
    # sst             → SST (analyse)

    def get_val(ds_dict, var, step_idx):
        """Extrait la valeur au point Sème pour un step donné."""
        ds = ds_dict.get(var)
        if ds is None:
            return None
        try:
            da = ds[var]
            # Sélection du step
            if "step" in da.dims:
                da = da.isel(step=step_idx)
            elif "valid_time" in da.dims:
                da = da.isel(valid_time=step_idx)
            # Sélection du point géographique
            da = da.sel(latitude=config.POINT["lat"],
                        longitude=config.POINT["lon"],
                        method="nearest")
            val = float(da.values)
            return None if (val != val) else val  # NaN check
        except Exception:
            return None

    def get_sst(ds_dict):
        """SST est une analyse (step=0 unique) — pas de dimension step."""
        ds = ds_dict.get("sst")
        if ds is None:
            return None
        try:
            da = ds["sst"]
            da = da.sel(latitude=config.POINT["lat"],
                        longitude=config.POINT["lon"],
                        method="nearest")
            val = float(da.values)
            return None if (val != val) else val
        except Exception:
            return None

    sst_val = get_sst(ds_sst)

    # ── Construction du DataFrame ──────────────────────────────────────────
    rows    = []
    tp_prev = None   # précipitation cumul du step précédent

    for i, step_h in enumerate(steps):
        valid_utc   = run_datetime + timedelta(hours=step_h)
        valid_local = valid_utc + timedelta(hours=config.UTC_OFFSET)

        u10  = get_val(ds_atm, "u10",  i)
        v10  = get_val(ds_atm, "v10",  i)
        fg10 = get_val(ds_atm, "fg10", i)
        u100 = get_val(ds_atm, "u100", i)
        v100 = get_val(ds_atm, "v100", i)
        msl  = get_val(ds_atm, "msl",  i)
        t2m  = get_val(ds_atm, "t2m",  i)
        d2m  = get_val(ds_atm, "d2m",  i)
        tcc  = get_val(ds_atm, "tcc",  i)
        tp   = get_val(ds_atm, "tp",   i)
        swh  = get_val(ds_wav, "swh",  i)

        wind10_dir,  wind10_spd  = uv_to_dir_speed(u10,  v10)
        wind100_dir, wind100_spd = uv_to_dir_speed(u100, v100)

        # Calcul visibilité (km)
        vis = calc_visibility(t2m, d2m, tcc)

        # Calcul chance de pluie (%)
        rain_pct = calc_rain_chance(tp, tp_prev)
        tp_prev  = tp

        rows.append({
            "valid_utc"      : valid_utc,
            "valid_local"    : valid_local,
            "step_h"         : step_h,
            # Vent 10m
            "wind10_dir_deg" : wind10_dir,
            "wind10_dir"     : degrees_to_cardinal(wind10_dir),
            "wind10_spd_kt"  : ms_to_knots(wind10_spd),
            "wind10_gust_kt" : ms_to_knots(fg10),
            # Vent 100m
            "wind100_dir_deg": wind100_dir,
            "wind100_dir"    : degrees_to_cardinal(wind100_dir),
            "wind100_spd_kt" : ms_to_knots(wind100_spd),
            # Paramètres météo — ordre bulletin
            "mslp_hpa"       : pa_to_hpa(msl),
            "vis_km"         : vis,
            "t2m_c"          : kelvin_to_celsius(t2m),
            "rain_pct"       : rain_pct,
            "sst_c"          : None,      # SST viendra de Copernicus
            "swh_ecmwf_m"    : round(swh, 2) if swh else None,
        })

    # Fermeture des datasets — sans set() pour éviter l'erreur unhashable
    for ds_dict in [ds_atm, ds_wav, ds_sst]:
        seen = []
        for ds in ds_dict.values():
            if ds not in seen:
                seen.append(ds)
                try:
                    ds.close()
                except Exception:
                    pass

    # Nettoyage fichiers temporaires
    for f in tmp_dir.glob("*"):
        try:
            f.unlink()
        except Exception:
            pass
    try:
        tmp_dir.rmdir()
    except Exception:
        pass

    df = pd.DataFrame(rows)
    print(f"  → {len(df)} pas de temps ECMWF extraits.")
    return df


def _read_grib_eccodes(atm_file, wav_file, run_datetime):
    """Fallback lecture GRIB via eccodes si cfgrib non disponible."""
    import eccodes
    rows_dict = {}

    def read_grib(filepath, shortName_filter):
        data = {}
        with open(filepath, "rb") as f:
            while True:
                msg = eccodes.codes_grib_new_from_file(f)
                if msg is None:
                    break
                try:
                    sn  = eccodes.codes_get(msg, "shortName")
                    step = eccodes.codes_get(msg, "stepRange")
                    if sn in shortName_filter:
                        step_h = int(step.split("-")[-1]) if "-" in str(step) else int(step)
                        lats   = eccodes.codes_get_array(msg, "latitudes")
                        lons   = eccodes.codes_get_array(msg, "longitudes")
                        vals   = eccodes.codes_get_array(msg, "values")
                        idx    = np.argmin((lats - config.POINT["lat"])**2 +
                                           (lons - config.POINT["lon"])**2)
                        data.setdefault(step_h, {})[sn] = vals[idx]
                finally:
                    eccodes.codes_release(msg)
        return data

    atm = read_grib(atm_file, ["10u", "10v", "10fg", "100u", "100v", "msl", "2t", "sst"])
    wav = read_grib(wav_file,  ["swh"])

    rows = []
    for step_h in range(0, 73, 3):
        a = atm.get(step_h, {})
        w = wav.get(step_h, {})
        valid_utc   = run_datetime + timedelta(hours=step_h)
        valid_local = valid_utc + timedelta(hours=config.UTC_OFFSET)

        u10,  v10  = a.get("10u"),  a.get("10v")
        u100, v100 = a.get("100u"), a.get("100v")
        fg10       = a.get("10fg")

        wind10_dir,  wind10_spd  = uv_to_dir_speed(u10,  v10)
        wind100_dir, wind100_spd = uv_to_dir_speed(u100, v100)

        rows.append({
            "valid_utc"      : valid_utc,
            "valid_local"    : valid_local,
            "step_h"         : step_h,
            # Vent 10m
            "wind10_dir_deg" : wind10_dir,
            "wind10_dir"     : degrees_to_cardinal(wind10_dir),
            "wind10_spd_kt"  : ms_to_knots(wind10_spd),
            "wind10_gust_kt" : ms_to_knots(fg10),
            # Vent 100m
            "wind100_dir_deg": wind100_dir,
            "wind100_dir"    : degrees_to_cardinal(wind100_dir),
            "wind100_spd_kt" : ms_to_knots(wind100_spd),
            # Autres paramètres
            "mslp_hpa"       : pa_to_hpa(a.get("msl")),
            "t2m_c"          : kelvin_to_celsius(a.get("2t")),
            "sst_c"          : kelvin_to_celsius(a.get("sst")),
            "swh_ecmwf_m"    : round(float(w["swh"]), 2) if "swh" in w else None,
        })
    return rows



# ---------------------------------------------------------------------------
# Extraction depuis GRIB2 locaux (téléchargés par Google Colab via Drive)
# ---------------------------------------------------------------------------

def _extract_from_local_grib(run_datetime: datetime, tmp_dir) -> pd.DataFrame:
    """
    Extrait les données ECMWF depuis des fichiers GRIB2 déjà présents localement
    (téléchargés par Google Colab et synchronisés via Google Drive).
    Utilise exactement la même logique que extract_ecmwf.
    """
    from pathlib import Path
    import cfgrib

    tmp_dir  = Path(tmp_dir)
    atm_file = tmp_dir / "ecmwf_atm.grib2"
    wav_file = tmp_dir / "ecmwf_wav.grib2"

    if not atm_file.exists() or not wav_file.exists():
        raise FileNotFoundError(f"Fichiers GRIB2 manquants dans {tmp_dir}")

    steps = list(range(0, 121, 3))  # 0 à 120h

    # ── Ouverture datasets cfgrib (même logique que extract_ecmwf) ─────────
    def open_ds(filepath):
        result = {}
        try:
            datasets = cfgrib.open_datasets(
                str(filepath),
                backend_kwargs={"indexpath": ""}
            )
            for ds in datasets:
                for var in ds.data_vars:
                    result[var] = ds
        except Exception as e:
            print(f"  ⚠️  Erreur ouverture {filepath.name} : {e}")
        return result

    print(f"  Lecture GRIB2 avec cfgrib...")
    ds_atm = open_ds(atm_file)
    ds_wav = open_ds(wav_file)
    ds_sst = {}

    if not ds_atm:
        print(f"  ⚠️  cfgrib échoué — tentative eccodes")
        rows = _read_grib_eccodes(atm_file, wav_file, run_datetime)
        df = pd.DataFrame(rows)
        print(f"  → {len(df)} pas de temps extraits (eccodes fallback).")
        return df

    print(f"  ✅ GRIB2 ouvert — variables ATM: {list(ds_atm.keys())}")

    def get_val(ds_dict, var, step_idx):
        ds = ds_dict.get(var)
        if ds is None:
            return None
        try:
            da = ds[var]
            if "step" in da.dims:
                da = da.isel(step=step_idx)
            elif "valid_time" in da.dims:
                da = da.isel(valid_time=step_idx)
            da = da.sel(latitude=config.POINT["lat"],
                        longitude=config.POINT["lon"],
                        method="nearest")
            val = float(da.values)
            return None if (val != val) else val
        except Exception:
            return None

    rows    = []
    tp_prev = None
    for i, step_h in enumerate(steps):
        valid_utc   = run_datetime + timedelta(hours=step_h)
        valid_local = valid_utc + timedelta(hours=config.UTC_OFFSET)

        u10  = get_val(ds_atm, "u10",  i)
        v10  = get_val(ds_atm, "v10",  i)
        fg10 = get_val(ds_atm, "fg10", i)
        u100 = get_val(ds_atm, "u100", i)
        v100 = get_val(ds_atm, "v100", i)
        msl  = get_val(ds_atm, "msl",  i)
        t2m  = get_val(ds_atm, "t2m",  i)
        d2m  = get_val(ds_atm, "d2m",  i)
        tcc  = get_val(ds_atm, "tcc",  i)
        tp   = get_val(ds_atm, "tp",   i)
        swh  = get_val(ds_wav, "swh",  i)

        wind10_dir,  wind10_spd  = uv_to_dir_speed(u10,  v10)
        wind100_dir, wind100_spd = uv_to_dir_speed(u100, v100)
        vis      = calc_visibility(t2m, d2m, tcc)
        rain_pct = calc_rain_chance(tp, tp_prev)
        tp_prev  = tp

        rows.append({
            "valid_utc"      : valid_utc,
            "valid_local"    : valid_local,
            "step_h"         : step_h,
            "wind10_dir_deg" : wind10_dir,
            "wind10_dir"     : degrees_to_cardinal(wind10_dir),
            "wind10_spd_kt"  : ms_to_knots(wind10_spd),
            "wind10_gust_kt" : ms_to_knots(fg10),
            "wind100_dir_deg": wind100_dir,
            "wind100_dir"    : degrees_to_cardinal(wind100_dir),
            "wind100_spd_kt" : ms_to_knots(wind100_spd),
            "mslp_hpa"       : pa_to_hpa(msl),
            "vis_km"         : vis,
            "t2m_c"          : kelvin_to_celsius(t2m),
            "rain_pct"       : rain_pct,
            "sst_c"          : None,
            "swh_ecmwf_m"    : round(swh, 2) if swh else None,
        })

    # Fermeture
    seen = []
    for ds_dict in [ds_atm, ds_wav, ds_sst]:
        for ds in ds_dict.values():
            if ds not in seen:
                seen.append(ds)
                try: ds.close()
                except: pass

    df = pd.DataFrame(rows)
    print(f"  → {len(df)} pas de temps extraits (GRIB2 local cfgrib).")
    return df

# ---------------------------------------------------------------------------
# Copernicus Marine — Swell1 + Swell2 + courants
# ---------------------------------------------------------------------------

def extract_copernicus(run_datetime: datetime) -> pd.DataFrame:
    """
    Extrait depuis Copernicus Marine (prévisions anfc) :
      Dataset vagues  : Swell1, Swell2, SWH
      Dataset physique: courants (uo, vo → dir + vit) + SST (thetao)

    Le dernier run disponible est automatiquement sélectionné par Copernicus.
    """
    # Étendre à 96h minimum pour garantir J+3 19h quelle que soit la run
    cop_hours  = max(config.FORECAST_HOURS, 120)
    date_start = run_datetime.strftime("%Y-%m-%dT%H:%M:%S")
    date_end   = (run_datetime + timedelta(hours=cop_hours)).strftime("%Y-%m-%dT%H:%M:%S")

    lat   = config.POINT["lat"]
    lon   = config.POINT["lon"]
    delta = 0.25

    # ── Dataset vagues ─────────────────────────────────────────────────────
    print("  🌊 Téléchargement Copernicus — vagues...")
    ds_wav = copernicusmarine.open_dataset(
        dataset_id        = config.COPERNICUS_DATASET,
        variables         = config.COPERNICUS_VARIABLES,
        minimum_latitude  = lat - delta,
        maximum_latitude  = lat + delta,
        minimum_longitude = lon - delta,
        maximum_longitude = lon + delta,
        start_datetime    = date_start,
        end_datetime      = date_end,
    )
    print("  ✅ Vagues chargées.")

    # ── Dataset physique (courants + SST) ──────────────────────────────────
    print("  🌊 Téléchargement Copernicus — courants + SST...")
    ds_phy = None
    try:
        ds_phy = copernicusmarine.open_dataset(
            dataset_id        = config.COPERNICUS_PHY_DATASET,
            variables         = config.COPERNICUS_PHY_VARIABLES,
            minimum_latitude  = lat - delta,
            maximum_latitude  = lat + delta,
            minimum_longitude = lon - delta,
            maximum_longitude = lon + delta,
            minimum_depth     = 0.4,   # profondeur réelle disponible = 0.494m
            maximum_depth     = 0.6,
            start_datetime    = date_start,
            end_datetime      = date_end,
        )
        print("  ✅ Courants + SST chargés.")
    except Exception as e:
        print(f"  ⚠️  Dataset physique non disponible : {e}")

    # ── Extraction vagues au point Sème ───────────────────────────────────
    pt_wav = ds_wav.sel(latitude=lat, longitude=lon, method="nearest")

    # ── Extraction physique au point Sème ─────────────────────────────────
    pt_phy = None
    if ds_phy is not None:
        pt_phy = ds_phy.sel(latitude=lat, longitude=lon, method="nearest")

    def val_wav(var, t):
        try:
            v = float(pt_wav[var].sel(time=t).values)
            return None if np.isnan(v) else v
        except Exception:
            return None

    def val_phy(var, t):
        if pt_phy is None:
            return None
        try:
            da = pt_phy[var].sel(time=t, method="nearest")
            # Si dimension depth, prendre surface
            if "depth" in da.dims:
                da = da.isel(depth=0)
            v = float(da.values.flat[0])
            return None if np.isnan(v) else v
        except Exception:
            return None

    # ── Construction du DataFrame ──────────────────────────────────────────
    rows = []
    for t in pt_wav.time.values:
        ts          = pd.Timestamp(t)
        valid_local = ts + pd.Timedelta(hours=config.UTC_OFFSET)

        sw1_dir = val_wav("VMDR_SW1", t)
        sw2_dir = val_wav("VMDR_SW2", t)
        swh_cop = val_wav("VHM0", t)

        # Courant : uo + vo → direction TO + vitesse en noeuds
        uo = val_phy("uo", t)
        vo = val_phy("vo", t)
        cur_dir_deg, cur_spd_ms = uv_to_current_dir_speed(uo, vo)

        # SST depuis dataset physique
        sst_raw = val_phy("thetao", t)

        rows.append({
            "valid_utc"   : ts,
            "valid_local" : valid_local,
            # SST (°C — déjà en °C dans Copernicus, pas besoin de conversion K)
            "sst_c"       : round(sst_raw, 1) if sst_raw else None,
            # Swell 1
            "sw1_dir_deg" : sw1_dir,
            "sw1_dir"     : degrees_to_cardinal(sw1_dir),
            "sw1_period_s": round(val_wav("VTM01_SW1", t), 0) if val_wav("VTM01_SW1", t) else None,
            "sw1_ht_m"    : round(val_wav("VHM0_SW1",  t), 1) if val_wav("VHM0_SW1",  t) else None,
            # Swell 2
            "sw2_dir_deg" : sw2_dir,
            "sw2_dir"     : degrees_to_cardinal(sw2_dir),
            "sw2_period_s": round(val_wav("VTM01_SW2", t), 0) if val_wav("VTM01_SW2", t) else None,
            "sw2_ht_m"    : round(val_wav("VHM0_SW2",  t), 1) if val_wav("VHM0_SW2",  t) else None,
            # Courant
            "cur_dir_deg" : cur_dir_deg,
            "cur_dir"     : degrees_to_cardinal(cur_dir_deg),
            "cur_spd_kt"  : ms_to_knots(cur_spd_ms),
            # SWH total Copernicus (option B)
            "swh_cop_m"   : round(swh_cop, 1) if swh_cop else None,
        })

    ds_wav.close()
    if ds_phy is not None:
        ds_phy.close()

    df = pd.DataFrame(rows)
    print(f"  → {len(df)} pas de temps Copernicus extraits.")
    return df


# ---------------------------------------------------------------------------
# Fusion des deux sources
# ---------------------------------------------------------------------------

def merge_sources(df_ecmwf: pd.DataFrame,
                  df_cop: pd.DataFrame) -> pd.DataFrame:
    """
    Fusionne ECMWF et Copernicus sur l'heure locale arrondie.
    La SST vient de Copernicus.
    Choisit le SWH selon config.SWH_SOURCE.
    """
    df_ecmwf = df_ecmwf.copy()
    df_cop   = df_cop.copy()

    # Arrondir à l'heure pour la jointure
    df_ecmwf["key"] = pd.to_datetime(df_ecmwf["valid_local"]).dt.floor("h")
    df_cop["key"]   = pd.to_datetime(df_cop["valid_local"]).dt.floor("h")

    df = pd.merge(df_ecmwf, df_cop, on="key", how="outer", suffixes=("_e", "_c"))

    df["valid_local"] = df["key"]

    # SST depuis Copernicus (priorité sur ECMWF qui n'a pas de SST)
    df["sst_c"] = df["sst_c_c"] if "sst_c_c" in df.columns else df.get("sst_c_e")

    # Récupérer colonnes suffixées après merge outer
    for col in ["vis_km","rain_pct","wind10_dir","wind10_spd_kt","wind10_gust_kt",
                "wind100_dir","wind100_spd_kt","mslp_hpa","t2m_c","swh_ecmwf_m","step_h"]:
        if col not in df.columns:
            if f"{col}_e" in df.columns: df[col] = df[f"{col}_e"]
            elif f"{col}_c" in df.columns: df[col] = df[f"{col}_c"]
    for col in ["sw1_dir","sw1_dir_deg","sw1_period_s","sw1_ht_m",
                "sw2_dir","sw2_dir_deg","sw2_period_s","sw2_ht_m",
                "cur_dir","cur_dir_deg","cur_spd_kt","swh_cop_m"]:
        if col not in df.columns:
            if f"{col}_c" in df.columns: df[col] = df[f"{col}_c"]
            elif f"{col}_e" in df.columns: df[col] = df[f"{col}_e"]

    # vis_km et rain_pct — colonnes ECMWF suffixées _e après merge
    for col in ["vis_km", "rain_pct", "wind10_dir", "wind10_spd_kt", "wind10_gust_kt",
                "wind100_dir", "wind100_spd_kt", "mslp_hpa", "t2m_c",
                "swh_ecmwf_m", "step_h"]:
        if col not in df.columns:
            if f"{col}_e" in df.columns:
                df[col] = df[f"{col}_e"]
            elif f"{col}_c" in df.columns:
                df[col] = df[f"{col}_c"]

    # sw1, sw2, cur — colonnes Copernicus suffixées _c après merge
    for col in ["sw1_dir","sw1_dir_deg","sw1_period_s","sw1_ht_m",
                "sw2_dir","sw2_dir_deg","sw2_period_s","sw2_ht_m",
                "cur_dir","cur_dir_deg","cur_spd_kt","swh_cop_m"]:
        if col not in df.columns:
            if f"{col}_c" in df.columns:
                df[col] = df[f"{col}_c"]
            elif f"{col}_e" in df.columns:
                df[col] = df[f"{col}_e"]

    # SWH final selon l'option choisie
    if config.SWH_SOURCE == "ecmwf":
        df["swh_m"]      = df["swh_ecmwf_m"]
        df["swh_source"] = "ECMWF"
    else:
        df["swh_m"]      = df["swh_cop_m"]
        df["swh_source"] = "Copernicus"

    # Colonnes finales — ordre exact du bulletin
    cols = [
        "valid_local",
        # Wind 10m
        "wind10_dir", "wind10_spd_kt", "wind10_gust_kt",
        # Wind 100m
        "wind100_dir", "wind100_spd_kt",
        # Weather params — ordre bulletin exact
        "mslp_hpa", "vis_km", "t2m_c", "rain_pct", "sst_c",
        # Swell 1
        "sw1_dir", "sw1_period_s", "sw1_ht_m",
        # Swell 2
        "sw2_dir", "sw2_period_s", "sw2_ht_m",
        # SWH
        "swh_m", "swh_source",
        # Currents
        "cur_dir", "cur_spd_kt",
    ]
    existing = [c for c in cols if c in df.columns]
    df_final = df[existing].sort_values("valid_local").reset_index(drop=True)

    # ── Filtrer : début J 19h → fin J+3 19h (inclus) ──────────────────────
    df_final["valid_local"] = pd.to_datetime(df_final["valid_local"])

    # Trouver le premier 19h disponible dans les données
    first_19h = None
    for ts in df_final["valid_local"]:
        if ts.hour == 19:
            first_19h = ts
            break

    if first_19h is None:
        # Pas de 19h exact — prendre la première heure >= 19h
        df_19h = df_final[df_final["valid_local"].dt.hour >= 19]
        first_19h = df_19h["valid_local"].iloc[0] if not df_19h.empty else df_final["valid_local"].iloc[0]

    # Fin : J+3 à 19h exactement
    end_19h = first_19h + pd.Timedelta(days=3)

    # Filtrer entre first_19h et end_19h inclus
    df_filtered = df_final[
        (df_final["valid_local"] >= first_19h) &
        (df_final["valid_local"] <= end_19h)
    ].reset_index(drop=True)

    if df_filtered.empty:
        print("  ⚠️  Pas de données dans la plage 19h → J+3 19h.")
        return df_final

    print(f"  → Bulletin : {df_filtered['valid_local'].iloc[0].strftime('%d/%m/%Y %H:%M')} "
          f"→ {df_filtered['valid_local'].iloc[-1].strftime('%d/%m/%Y %H:%M')} (heure locale)")
    return df_filtered