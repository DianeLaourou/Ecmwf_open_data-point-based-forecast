# =============================================================================
# tides.py — Prédiction automatique des marées via WorldTides API
# Point : Sème / Cotonou (6.22°N, 2.63°E)
#
# Inscription gratuite : https://www.worldtides.info
# Clé API à renseigner dans config.py : WORLDTIDES_API_KEY = "votre_cle"
# =============================================================================

import requests
from datetime import datetime, timedelta
import config

def get_tides(start_date: datetime, days: int = 4) -> list:
    """
    Récupère les marées hautes et basses pour la période donnée.

    Retourne une liste de dicts :
    [
      {
        "date"  : "Sat. 09 May",
        "type"  : "High" ou "Low",
        "time"  : "10:25 am",
        "height": "1.2 m"
      },
      ...
    ]
    """
    api_key = getattr(config, "WORLDTIDES_API_KEY", None)
    if not api_key:
        print("  ⚠️  WORLDTIDES_API_KEY non définie dans config.py — marées non disponibles.")
        return []

    lat = config.POINT["lat"]
    lon = config.POINT["lon"]

    # Timestamp de début et fin
    start_ts = int(start_date.timestamp())
    end_ts   = int((start_date + timedelta(days=days)).timestamp())

    url = "https://www.worldtides.info/api/v3"
    params = {
        "extremes": "",
        "lat"     : lat,
        "lon"     : lon,
        "start"   : start_ts,
        "length"  : days * 86400,
        "datum"   : "LAT",
        "key"     : api_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ⚠️  Erreur WorldTides API : {e}")
        return []

    if "extremes" not in data:
        print(f"  ⚠️  Pas de données de marées : {data.get('error','unknown error')}")
        return []

    ENG_DAYS = {0:"Mon.",1:"Tue.",2:"Wed.",3:"Thu.",4:"Fri.",5:"Sat.",6:"Sun."}
    ENG_MONTHS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                  7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

    results = []
    for extreme in data["extremes"]:
        dt_utc   = datetime.utcfromtimestamp(extreme["dt"])
        dt_local = dt_utc + timedelta(hours=config.UTC_OFFSET)
        height   = extreme["height"]
        t_type   = "High" if extreme["type"] == "High" else "Low"

        results.append({
            "date"      : f"{ENG_DAYS[dt_local.weekday()]} {dt_local.day:02d} {ENG_MONTHS[dt_local.month]}",
            "date_obj"  : dt_local.date(),
            "type"      : t_type,
            "time"      : dt_local.strftime("%I:%M %p").lstrip("0"),
            "height_m"  : round(height, 1),
            "height_str": f"{height:.1f} m",
        })

    print(f"  ✅ {len(results)} événements de marées récupérés (WorldTides API).")
    return results


def format_tide_table(tides: list, start_date: datetime, days: int = 4) -> list:
    """
    Formate les marées en tableau :
    Une ligne par jour avec HIGH TIDES (2 colonnes) et LOW TIDES (2 colonnes).

    Retourne une liste de dicts par jour :
    [
      {
        "date"    : "Sat. 09 May",
        "high1"   : {"time": "10:25 am", "height": "1.2 m"},
        "high2"   : {"time": "09:45 pm", "height": "1.2 m"},
        "low1"    : {"time": "03:30 am", "height": "0.5 m"},
        "low2"    : {"time": "04:07 pm", "height": "0.8 m"},
      },
      ...
    ]
    """
    from datetime import date, timedelta as td

    ENG_DAYS = {0:"Mon.",1:"Tue.",2:"Wed.",3:"Thu.",4:"Fri.",5:"Sat.",6:"Sun."}
    ENG_MONTHS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                  7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

    rows = []
    for d in range(days):
        day = (start_date + timedelta(days=d)).date()
        day_tides = [t for t in tides if t["date_obj"] == day]

        highs = [t for t in day_tides if t["type"] == "High"]
        lows  = [t for t in day_tides if t["type"] == "Low"]

        dt_obj = start_date + timedelta(days=d)
        day_label = f"{ENG_DAYS[dt_obj.weekday()]} {dt_obj.day:02d} {ENG_MONTHS[dt_obj.month]}"

        def get(lst, idx):
            if idx < len(lst):
                return {"time": lst[idx]["time"], "height": lst[idx]["height_str"]}
            return {"time": "—", "height": "—"}

        rows.append({
            "date" : day_label,
            "high1": get(highs, 0),
            "high2": get(highs, 1),
            "low1" : get(lows,  0),
            "low2" : get(lows,  1),
        })

    return rows
