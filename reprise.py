"""
reprise.py — Régénère Excel + Word + CSV sans retélécharger les données
Usage de routine : python reprise.py
Usage rattrapage : python reprise.py --date 2026-05-20 --hour 6
"""
import os
import glob
import json
import shutil
import argparse
import pandas as pd
import config
import word_exporter
from datetime import datetime

# =============================================================================
# Génération automatique du texte Warning
# =============================================================================

ENG_MONTHS_FULL = {
    1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
    7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"
}
ENG_DAYS_FULL = {
    0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",
    4:"Friday",5:"Saturday",6:"Sunday"
}

def ordinal(n):
    if 11 <= n <= 13: return f"{n}th"
    return {1:"st",2:"nd",3:"rd"}.get(n % 10,"th")

def generate_warning(df: pd.DataFrame, run_dt: datetime) -> str:
    df = df.copy()
    df["valid_local"] = pd.to_datetime(df["valid_local"])
    swh_vals = df["swh_m"].dropna()
    swh_max  = swh_vals.max()
    idx_max  = swh_vals.idxmax()
    swh_peak_time = df.loc[idx_max, "valid_local"]
    wind_vals = df["wind10_spd_kt"].dropna()
    wind_max  = wind_vals.max()
    idx_wind  = wind_vals.idxmax()
    wind_peak_time = df.loc[idx_wind, "valid_local"]
    wind_dir_peak  = df.loc[idx_wind, "wind10_dir"] if "wind10_dir" in df.columns else "—"
    gust_vals = df["wind10_gust_kt"].dropna()
    gust_max  = gust_vals.max() if not gust_vals.empty else None
    n = len(swh_vals)
    first_half  = swh_vals.iloc[:n//2].mean()
    second_half = swh_vals.iloc[n//2:].mean()
    if second_half > first_half + 0.2:   trend = "gradually increasing"
    elif second_half < first_half - 0.2: trend = "gradually decreasing"
    else:                                trend = "relatively stable"

    def fmt_time(dt):
        day  = ENG_DAYS_FULL[dt.weekday()]
        date = f"{dt.day}{ordinal(dt.day)}"
        mon  = ENG_MONTHS_FULL[dt.month]
        hour = dt.strftime("%I:%M %p").lstrip("0")
        return f"{day}, {date} {mon} at {hour}"

    if swh_max < config.ALERT_SWH_DANGER and wind_max < config.ALERT_WIND_WARNING:
        text = (f"Warning: None. Significant wave heights are expected to remain "
                f"below {config.ALERT_SWH_DANGER:.1f} m throughout the forecast period, "
                f"peaking at {swh_max:.1f} m. "
                f"Wind speeds will remain below {config.ALERT_WIND_WARNING} knots.")
    elif swh_max >= config.ALERT_SWH_WARNING and swh_max < config.ALERT_SWH_DANGER:
        text = (f"Warning: None. Significant wave heights are expected to be {trend}, "
                f"peaking at {swh_max:.1f} m around "
                f"{fmt_time(swh_peak_time)} (local time). "
                f"Mariners are advised to exercise caution.")
    elif swh_max >= config.ALERT_SWH_DANGER:
        text = (f"Warning: Significant wave heights are expected to increase "
                f"{trend}, reaching a peak of {swh_max:.1f} meters around "
                f"{fmt_time(swh_peak_time)} (local time).")
    else:
        text = (f"Warning: Wind speeds are expected to reach {wind_max:.0f} knots "
                f"from {wind_dir_peak} around {fmt_time(wind_peak_time)} (local time).")

    if swh_max >= config.ALERT_SWH_DANGER and wind_max >= config.ALERT_WIND_WARNING:
        gust_txt = f" with gusts up to {gust_max:.0f} knots" if gust_max else ""
        text += (f" Wind speeds are also expected to reach {wind_max:.0f} knots{gust_txt} "
                 f"from {wind_dir_peak}.")
    return text


# Table de conversion direction cardinale → degrés
CARDINAL_TO_DEG = {
    "N":0,"NNE":22.5,"NE":45,"ENE":67.5,
    "E":90,"ESE":112.5,"SE":135,"SSE":157.5,
    "S":180,"SSW":202.5,"SW":225,"WSW":247.5,
    "W":270,"WNW":292.5,"NW":315,"NNW":337.5,
    "SSO":202.5,"SO":225,"OSO":247.5,
    "O":270,"ONO":292.5,"NO":315,"NNO":337.5,
}

# 🎯 Chemins de synchronisation locale pour votre dossier Google Drive spécifique
GDRIVE_PATHS = [
    "G:/Mon Drive/Automatisation_taches_spam_2026",
    "G:/My Drive/Automatisation_taches_spam_2026",
    "H:/Mon Drive/Automatisation_taches_spam_2026",
    "H:/My Drive/Automatisation_taches_spam_2026",
    "G:/Shared drives/Automatisation_taches_spam_2026",
    "G:/Lecteurs partagés/Automatisation_taches_spam_2026",
]

def find_gdrive_folder():
    """Trouve automatiquement l'emplacement physique du dossier Google Drive sur le PC."""
    for p in GDRIVE_PATHS:
        if os.path.exists(p):
            return p
    return None

def parse_args():
    p = argparse.ArgumentParser(description="Reprise pipeline — GRIB2 Drive ou CSV")
    p.add_argument("--date",     type=str, default=None, help="Date du run (YYYY-MM-DD)")
    p.add_argument("--hour",     type=int, default=None, help="Heure UTC du run (0,6,12,18)")
    p.add_argument("--from-csv", action="store_true",   help="Forcer lecture depuis CSV local")
    p.add_argument("--gdrive",   type=str, default=None, help="Chemin personnalisé optionnel")
    return p.parse_args()

def find_latest_csv(folder):
    """Cherche le dernier CSV bulletin dans D:\\Pipeline\\ en secours."""
    pattern = os.path.join(folder, "bulletin_marine_seme_*.csv")
    files = sorted(glob.glob(pattern))
    if files:
        return files[-1]
    old = os.path.join(folder, "latest_forecast.csv")
    if os.path.exists(old):
        return old
    return None

def resolve_run_dt(args, name=None):
    """Résout la date/heure du run depuis les args ou le nom de fichier."""
    if args.date and args.hour is not None:
        return datetime.strptime(f"{args.date} {args.hour:02d}:00", "%Y-%m-%d %H:%M")
    elif args.date:
        return datetime.strptime(args.date, "%Y-%m-%d").replace(hour=6)
    elif name:
        try:
            parts = os.path.basename(name).replace("bulletin_marine_seme_","").replace(".csv","").replace(".json","").split("_")
            return datetime.strptime(f"{parts[0]} {parts[1].replace('Z','')}", "%d%m%Y %H")
        except Exception:
            pass
    return None


def export_all(df, run_dt, folder):
    """Génère Warning + Word + CSV bulletin."""
    print("\n[1/3] Warning...")
    warning_text = generate_warning(df, run_dt)
    print(f"  {warning_text[:100]}...")

    print("\n[2/3] Export Word...")
    date_str = run_dt.strftime("%d%m%Y")
    run_str  = f"{run_dt.hour:02d}Z"
    word_path = os.path.join(folder, f"Marine_forecast_{date_str}_{run_str}.docx")
    word_exporter.generate_word_bulletin(df, run_dt, warning_text, word_path)

    print("\n[3/3] Export CSV...")
    date_str = run_dt.strftime("%d%m%Y")
    run_str  = f"{run_dt.hour:02d}Z"
    csv_out  = os.path.join(folder, f"bulletin_marine_seme_{date_str}_{run_str}.csv")
    df_csv = df.copy()
    for col in ["wind10_dir","wind100_dir","sw1_dir","sw2_dir","cur_dir"]:
        if col in df_csv.columns:
            df_csv[col] = df_csv[col].map(
                lambda x: CARDINAL_TO_DEG.get(str(x).strip(), None) if pd.notna(x) else None
            )
    df_csv.to_csv(csv_out, index=False, encoding="utf-8")

    print(f"\n✅ Fichiers de production régénérés avec succès !")
    print(f"   Dossier local de travail : {folder}")
    print(f"   Fichier CSV mis à jour   : {os.path.basename(csv_out)}")


def main():
    args = parse_args()
    folder = os.path.dirname(os.path.abspath(config.OUTPUT_FILE)) # D:\Pipeline

    # Recherche du dossier Google Drive ciblé
    gdrive = args.gdrive or find_gdrive_folder()
    grib_ok = False
    run_dt = None

    # ── Mode 1 : GRIB2 depuis le dossier connecté Google Drive ────────────
    if not args.from_csv and gdrive:
        meta_f = os.path.join(gdrive, "ecmwf_meta.json")
        run_dt = resolve_run_dt(args)
        
        # Lecture de ecmwf_meta.json uniquement s'il existe dans le dossier identifié
        if run_dt is None and os.path.exists(meta_f):
            try:
                with open(meta_f) as f:
                    meta = json.load(f)
                run_dt = datetime.strptime(f"{meta['run_date']} {meta['run_hour']:02d}:00", "%Y-%m-%d %H:%M")
                print(f"📂 Suivi Google Drive actif : Dossier trouvé ({os.path.basename(gdrive)})")
                print(f"📅 Run ciblé par Colab      : {run_dt.strftime('%d/%m/%Y %H:%M')} UTC")
            except Exception as e:
                print(f"⚠️ Impossible de lire ecmwf_meta.json : {e}")

        if run_dt:
            date_str = run_dt.strftime("%Y%m%d")
            run_str  = f"{run_dt.hour:02d}Z"
            atm = os.path.join(gdrive, f"ecmwf_atm_{date_str}_{run_str}.grib2")
            wav = os.path.join(gdrive, f"ecmwf_wav_{date_str}_{run_str}.grib2")
        else:
            # Fallback sur les fichiers GRIB2 étiquetés les plus récents du dossier
            atm_files = sorted(glob.glob(os.path.join(gdrive, "ecmwf_atm_*_*.grib2")))
            if atm_files:
                atm = atm_files[-1]
                base = os.path.basename(atm)
                parts = base.replace("ecmwf_atm_", "").replace(".grib2", "").split("_")
                run_dt = datetime.strptime(f"{parts[0]} {parts[1].replace('Z','')}", "%Y%m%d %H")
                wav = os.path.join(gdrive, f"ecmwf_wav_{parts[0]}_{parts[1]}.grib2")
            else:
                atm = os.path.join(gdrive, "ecmwf_atm.grib2")
                wav = os.path.join(gdrive, "ecmwf_wav.grib2")

        # Vérification stricte de la synchronisation locale des fichiers sur votre PC
        if os.path.exists(atm) and os.path.exists(wav):
            print(f"\n=== Traitement des fichiers GRIB2 synchronisés ===")
            print(f"   ATM : {os.path.basename(atm)} ({os.path.getsize(atm)/1024/1024:.1f} MB)")
            print(f"   WAV : {os.path.basename(wav)} ({os.path.getsize(wav)/1024/1024:.1f} MB)")

            # Extraction temporaire locale (D:\Pipeline\tmp_ecmwf)
            tmp_dir = os.path.join(folder, "tmp_ecmwf")
            os.makedirs(tmp_dir, exist_ok=True)
            shutil.copy2(atm, os.path.join(tmp_dir, "ecmwf_atm.grib2"))
            shutil.copy2(wav, os.path.join(tmp_dir, "ecmwf_wav.grib2"))

            try:
                import extractor as _ext
                from pathlib import Path
                print("\n[ECMWF] Extraction depuis GRIB2...")
                df_ecmwf = _ext._extract_from_local_grib(run_dt, Path(tmp_dir))
                print("\n[Copernicus] Extraction Swell 2 + SST + Courants...")
                df_cop = _ext.extract_copernicus(run_dt)
                print("\n[Fusion]...")
                df = _ext.merge_sources(df_ecmwf, df_cop)
                print(f"  → {len(df)} lignes fusionnées.")
                grib_ok = True
            except Exception as e:
                print(f"❌ Erreur lors de l'extraction GRIB2 : {e}")
                import traceback; traceback.print_exc()
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            if run_dt:
                print(f"\n⚠️ Synchro en cours... Le fichier suivant n'est pas encore télécharge localement :\n   → {os.path.basename(atm)}")
                print("   (Veuillez attendre la fin du téléchargement par l'application Google Drive).")
            else:
                print("\n⚠️ Aucun fichier GRIB2 trouvé dans votre dossier distant.")
    else:
        print("\n⚠️ Mode connecté Google Drive indisponible (Dossier introuvable localement).")

    # ── Mode 2 : CSV local (Sécurité / Fallback) ──────────────────────────
    if not grib_ok:
        print("\n=== Mode CSV local (Secours) ===")
        csv_in = find_latest_csv(folder)
        if csv_in is None:
            print("❌ Aucun CSV historique trouvé dans D:\\Pipeline\\")
            return

        print(f"CSV historique utilisé : {csv_in}")
        df = pd.read_csv(csv_in)
        df["valid_local"] = pd.to_datetime(df["valid_local"])
        
        if run_dt is None:
            run_dt = resolve_run_dt(args, csv_in) or datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0)
        print(f"📅 Date associée au Bulletin : {run_dt.strftime('%d/%m/%Y %H:%M')} UTC")

    export_all(df, run_dt, folder)

if __name__ == "__main__":
    main()