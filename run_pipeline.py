# =============================================================================
# run_pipeline.py — Pipeline de prévision marine Sème (sans GEE)
#
# Sources : ECMWF Open Data + Copernicus Marine Service
#
# Usage :
#   python run_pipeline.py                               → run automatique
#   python run_pipeline.py --date 2026-05-09 --hour 12  → run spécifique
#   python run_pipeline.py --swh copernicus             → Option B
#   python run_pipeline.py --swh ecmwf                  → Option A (défaut)
# =============================================================================

import argparse
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import config
import extractor
import exporter
import word_exporter


def parse_args():
    p = argparse.ArgumentParser(description="Pipeline Marine — Sème")
    p.add_argument("--date",   type=str, default=None,
                   help="Date run ECMWF (YYYY-MM-DD). Défaut: aujourd'hui.")
    p.add_argument("--hour",   type=int, choices=[0, 6, 12, 18], default=None,
                   help="Heure UTC run (0, 6, 12 ou 18). Défaut: run la plus récente.")
    p.add_argument("--swh",    type=str, choices=["ecmwf","copernicus"], default=None,
                   help="Source SWH. Défaut: config.SWH_SOURCE.")
    p.add_argument("--output", type=str, default=None,
                   help="Fichier de sortie Excel.")
    return p.parse_args()


def get_latest_run():
    """
    Retourne la run ECMWF la plus récente disponible.
    ECMWF publie 4 runs par jour : 00Z, 06Z, 12Z, 18Z
    avec un délai d'environ 5-6h après l'heure de run.
    """
    now = datetime.utcnow()
    h   = now.hour
    if h >= 18:
        return now.replace(hour=12, minute=0, second=0, microsecond=0)
    elif h >= 12:
        return now.replace(hour=6,  minute=0, second=0, microsecond=0)
    elif h >= 6:
        return now.replace(hour=0,  minute=0, second=0, microsecond=0)
    else:
        return (now - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)


# =============================================================================
# MOD 6 — Génération automatique du texte Warning
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
    if 11 <= n <= 13:
        return f"{n}th"
    return {1:"st", 2:"nd", 3:"rd"}.get(n % 10, "th")

def generate_warning(df: pd.DataFrame, run_dt: datetime) -> str:
    df = df.copy()
    df["valid_local"] = pd.to_datetime(df["valid_local"])

    swh_col   = "swh_m"
    swh_vals  = df[swh_col].dropna()
    swh_max   = swh_vals.max()
    idx_max   = swh_vals.idxmax()
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
    if second_half > first_half + 0.2:
        trend = "gradually increasing"
    elif second_half < first_half - 0.2:
        trend = "gradually decreasing"
    else:
        trend = "relatively stable"

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


# =============================================================================
# EXPORT CSV POUR LE DASHBOARD
# =============================================================================

def export_csv_for_dashboard(df: pd.DataFrame, output_path: str):
    """
    Exporte le DataFrame au format CSV dans le même dossier que le Excel,
    sous le nom fixe 'latest_forecast.csv'.
    Ce fichier sera poussé sur GitHub et lu par le dashboard Streamlit.
    """
    folder   = os.path.dirname(os.path.abspath(output_path))
    csv_path = os.path.join(folder, "latest_forecast.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"  ✅ CSV dashboard → {csv_path}")
    return csv_path


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def run(run_dt, swh_source, output_path):

    print()
    print("=" * 65)
    print(f"  PIPELINE MARINE — {config.POINT['name']} "
          f"({config.POINT['lat']}°N, {config.POINT['lon']}°E)")
    print(f"  Run      : {run_dt.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  SWH src  : {swh_source.upper()}")
    print(f"  Sortie   : {output_path}")
    print("=" * 65)

    # 1. ECMWF Open Data
    print("\n[1/6] Extraction ECMWF Open Data...")
    df_ecmwf = extractor.extract_ecmwf(run_dt)

    # 2. Copernicus Marine
    print("\n[2/6] Extraction Copernicus Marine...")
    df_cop = extractor.extract_copernicus(run_dt)

    # 3. Fusion
    print("\n[3/6] Fusion des sources...")
    df = extractor.merge_sources(df_ecmwf, df_cop)
    print(f"  → {len(df)} lignes dans le tableau final.")

    # 4. Génération du Warning
    print("\n[4/6] Génération du texte Warning...")
    warning_text = generate_warning(df, run_dt)
    print(f"\n  {'─'*60}")
    print(f"  {warning_text}")
    print(f"  {'─'*60}")

    # 5. Export Excel
    print("\n[5/6] Export Excel...")
    exporter.export_excel(df, run_dt, output_path, warning_text=warning_text)

    # 6. Export Word
    print("\n[6/6] Export Word (bulletin complet)...")
    word_path = output_path.replace(".xlsx", ".docx") if output_path else None
    word_exporter.generate_word_bulletin(df, run_dt, warning_text, word_path)

    # 7. Export CSV pour le dashboard Streamlit
    print("\n[+] Export CSV pour dashboard Streamlit...")
    csv_path = export_csv_for_dashboard(df, output_path)

    # 8. Upload vers Google Drive (si configuré)
    folder_id = getattr(config, "GDRIVE_FOLDER_ID", None)
    if folder_id and folder_id != "VOTRE_FOLDER_ID_ICI":
        print("\n[+] Upload vers Google Drive...")
        try:
            import gdrive
            if output_path and os.path.exists(output_path):
                gdrive.upload_to_drive(output_path, folder_id)
            if word_path and os.path.exists(word_path):
                gdrive.upload_to_drive(word_path, folder_id)
        except Exception as e:
            print(f"  ⚠️  Upload Drive non disponible : {e}")

    print()
    print("=" * 65)
    print(f"  ✅ Pipeline terminé → {output_path}")
    print(f"  ✅ CSV dashboard    → {csv_path}")
    print("=" * 65)
    print()

    return csv_path   # retourné pour que le .bat puisse le vérifier


if __name__ == "__main__":
    args = parse_args()

    if args.date and args.hour is not None:
        run_dt = datetime.strptime(f"{args.date} {args.hour:02d}:00", "%Y-%m-%d %H:%M")
    elif args.date:
        run_dt = datetime.strptime(args.date, "%Y-%m-%d").replace(hour=12)
    else:
        run_dt = get_latest_run()

    if args.swh:
        config.SWH_SOURCE = args.swh

    output = args.output or config.OUTPUT_FILE

    try:
        run(run_dt, config.SWH_SOURCE, output)
    except KeyboardInterrupt:
        print("\n⚠️  Interrompu par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
