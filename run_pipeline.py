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
    """Retourne le suffixe ordinal : 1st, 2nd, 3rd, 4th..."""
    if 11 <= n <= 13:
        return f"{n}th"
    return {1:"st", 2:"nd", 3:"rd"}.get(n % 10, "th")

def generate_warning(df: pd.DataFrame, run_dt: datetime) -> str:
    """
    Génère automatiquement le texte du Warning à partir des données.

    Analyse :
      - SWH maximum et moment d'occurrence
      - Vent maximum et moment d'occurrence
      - Tendance générale (hausse, baisse, stable)

    Retourne le texte du Warning en anglais.
    """
    df = df.copy()
    df["valid_local"] = pd.to_datetime(df["valid_local"])

    # ── SWH ──────────────────────────────────────────────────────────────
    swh_col = "swh_m"
    swh_vals = df[swh_col].dropna()
    swh_max  = swh_vals.max()
    swh_min  = swh_vals.min()
    swh_mean = swh_vals.mean()
    idx_max  = swh_vals.idxmax()
    swh_peak_time = df.loc[idx_max, "valid_local"]

    # ── Vent ──────────────────────────────────────────────────────────────
    wind_vals = df["wind10_spd_kt"].dropna()
    wind_max  = wind_vals.max()
    idx_wind  = wind_vals.idxmax()
    wind_peak_time = df.loc[idx_wind, "valid_local"]
    wind_dir_peak  = df.loc[idx_wind, "wind10_dir"] if "wind10_dir" in df.columns else "—"

    gust_vals = df["wind10_gust_kt"].dropna()
    gust_max  = gust_vals.max() if not gust_vals.empty else None

    # ── Tendance SWH ──────────────────────────────────────────────────────
    n = len(swh_vals)
    first_half = swh_vals.iloc[:n//2].mean()
    second_half = swh_vals.iloc[n//2:].mean()
    if second_half > first_half + 0.2:
        trend = "gradually increasing"
    elif second_half < first_half - 0.2:
        trend = "gradually decreasing"
    else:
        trend = "relatively stable"

    # ── Formatage de la date/heure du pic ────────────────────────────────
    def fmt_time(dt):
        day  = ENG_DAYS_FULL[dt.weekday()]
        date = f"{dt.day}{ordinal(dt.day)}"
        mon  = ENG_MONTHS_FULL[dt.month]
        hour = dt.strftime("%I:%M %p").lstrip("0")
        return f"{day}, {date} {mon} at {hour}"

    # ── Construction du texte ─────────────────────────────────────────────

    # Cas 1 : Aucune alerte (SWH < 2.0m ET vent < seuil)
    if swh_max < config.ALERT_SWH_DANGER and wind_max < config.ALERT_WIND_WARNING:
        text = (f"Warning: None. Significant wave heights are expected to remain "
                f"below {config.ALERT_SWH_DANGER:.1f} m throughout the forecast period, "
                f"peaking at {swh_max:.1f} m. "
                f"Wind speeds will remain below {config.ALERT_WIND_WARNING} knots.")

    # Cas 2 : SWH entre 1.6 et 2.0m — avertissement mais PAS de Warning texte
    elif swh_max >= config.ALERT_SWH_WARNING and swh_max < config.ALERT_SWH_DANGER:
        text = (f"Warning: None. Significant wave heights are expected to be {trend}, "
                f"peaking at {swh_max:.1f} m around "
                f"{fmt_time(swh_peak_time)} (local time). "
                f"Mariners are advised to exercise caution.")

    # Cas 3 : Alerte SWH ≥ 2.0m (danger)
    elif swh_max >= config.ALERT_SWH_DANGER:
        text = (f"Warning: Significant wave heights are expected to increase "
                f"{trend}, reaching a peak of {swh_max:.1f} meters around "
                f"{fmt_time(swh_peak_time)} (local time).")

    # Cas 4 : Alerte vent
    else:
        text = (f"Warning: Wind speeds are expected to reach {wind_max:.0f} knots "
                f"from {wind_dir_peak} around {fmt_time(wind_peak_time)} (local time).")

    # Ajouter info vent fort seulement si SWH ≥ 2.0m (vrai Warning)
    if (swh_max >= config.ALERT_SWH_DANGER and
            wind_max >= config.ALERT_WIND_WARNING):
        gust_txt = f" with gusts up to {gust_max:.0f} knots" if gust_max else ""
        text += (f" Wind speeds are also expected to reach {wind_max:.0f} knots{gust_txt} "
                 f"from {wind_dir_peak}.")

    return text


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
    print("\n[1/5] Extraction ECMWF Open Data...")
    df_ecmwf = extractor.extract_ecmwf(run_dt)

    # 2. Copernicus Marine
    print("\n[2/5] Extraction Copernicus Marine...")
    df_cop = extractor.extract_copernicus(run_dt)

    # 3. Fusion
    print("\n[3/5] Fusion des sources...")
    df = extractor.merge_sources(df_ecmwf, df_cop)
    print(f"  → {len(df)} lignes dans le tableau final.")

    # 4. Génération du Warning (Mod 6)
    print("\n[4/5] Génération du texte Warning...")
    warning_text = generate_warning(df, run_dt)
    print(f"\n  {'─'*60}")
    print(f"  {warning_text}")
    print(f"  {'─'*60}")

    # 5. Export Excel
    print("\n[5/6] Export Excel...")
    exporter.export_excel(df, run_dt, output_path, warning_text=warning_text)

    # 6. Export Word (Mod 7)
    print("\n[6/6] Export Word (bulletin complet)...")
    word_path = output_path.replace(".xlsx", ".docx") if output_path else None
    word_exporter.generate_word_bulletin(df, run_dt, warning_text, word_path)

    # 7. Export CSV pour le dashboard Streamlit
    import os

    CARDINAL_TO_DEG = {
        "N":0,"NNE":22.5,"NE":45,"ENE":67.5,
        "E":90,"ESE":112.5,"SE":135,"SSE":157.5,
        "S":180,"SSW":202.5,"SW":225,"WSW":247.5,
        "W":270,"WNW":292.5,"NW":315,"NNW":337.5,
        "SSO":202.5,"SO":225,"OSO":247.5,
        "O":270,"ONO":292.5,"NO":315,"NNO":337.5,
    }

    folder   = os.path.dirname(os.path.abspath(output_path))
    date_str = run_dt.strftime("%d%m%Y")
    run_str  = f"{run_dt.hour:02d}Z"
    csv_name = f"bulletin_marine_seme_{date_str}_{run_str}.csv"
    csv_path = os.path.join(folder, csv_name)

    df_csv = df.copy()
    for col in ["wind10_dir","wind100_dir","sw1_dir","sw2_dir","cur_dir"]:
        if col in df_csv.columns:
            df_csv[col] = df_csv[col].map(
                lambda x: CARDINAL_TO_DEG.get(str(x).strip(), None) if pd.notna(x) else None
            )
    df_csv.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"\n  ✅ CSV bulletin → {csv_path}")

    print()
    print("=" * 65)
    print(f"  ✅ Pipeline terminé → {output_path}")
    print("=" * 65)
    print()


if __name__ == "__main__":
    args = parse_args()

    # Résoudre la date/heure
    if args.date and args.hour is not None:
        run_dt = datetime.strptime(f"{args.date} {args.hour:02d}:00", "%Y-%m-%d %H:%M")
    elif args.date:
        run_dt = datetime.strptime(args.date, "%Y-%m-%d").replace(hour=12)
    else:
        run_dt = get_latest_run()

    # Résoudre la source SWH
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
