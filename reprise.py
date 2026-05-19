"""
reprise.py — Régénère Excel + Word + CSV sans retélécharger les données
Usage : python reprise.py
        python reprise.py --date 2026-05-18 --hour 6
"""
import os
import glob
import argparse
import pandas as pd
import config
import exporter
import word_exporter
from run_pipeline import generate_warning
from datetime import datetime

# Table de conversion direction cardinale → degrés
CARDINAL_TO_DEG = {
    "N":0,"NNE":22.5,"NE":45,"ENE":67.5,
    "E":90,"ESE":112.5,"SE":135,"SSE":157.5,
    "S":180,"SSW":202.5,"SW":225,"WSW":247.5,
    "W":270,"WNW":292.5,"NW":315,"NNW":337.5,
    "SSO":202.5,"SO":225,"OSO":247.5,
    "O":270,"ONO":292.5,"NO":315,"NNO":337.5,
}

def parse_args():
    p = argparse.ArgumentParser(description="Reprise pipeline sans retéléchargement")
    p.add_argument("--date", type=str, default=None, help="Date du run (YYYY-MM-DD)")
    p.add_argument("--hour", type=int, default=None, help="Heure UTC du run (0,6,12,18)")
    return p.parse_args()

def find_latest_csv(folder):
    """Cherche le dernier CSV bulletin dans le dossier."""
    pattern = os.path.join(folder, "bulletin_marine_seme_*.csv")
    files = sorted(glob.glob(pattern))
    if files:
        return files[-1]
    # Fallback ancien nom
    old = os.path.join(folder, "latest_forecast.csv")
    if os.path.exists(old):
        return old
    return None

def main():
    args = parse_args()
    folder = os.path.dirname(os.path.abspath(config.OUTPUT_FILE))

    # 1. Trouver le CSV existant
    csv_in = find_latest_csv(folder)
    if csv_in is None:
        print("Aucun CSV trouve dans D:\\Pipeline\\")
        print("Lancez d'abord run_pipeline.py pour generer les donnees.")
        return

    print(f"CSV source : {csv_in}")
    df = pd.read_csv(csv_in)
    df["valid_local"] = pd.to_datetime(df["valid_local"])
    print(f"  -> {len(df)} lignes chargees")

    # 2. Résoudre la date/heure du run
    if args.date and args.hour is not None:
        run_dt = datetime.strptime(f"{args.date} {args.hour:02d}:00", "%Y-%m-%d %H:%M")
    elif args.date:
        run_dt = datetime.strptime(args.date, "%Y-%m-%d").replace(hour=6)
    else:
        # Déduire depuis le nom du fichier CSV
        basename = os.path.basename(csv_in)
        try:
            parts = basename.replace("bulletin_marine_seme_","").replace(".csv","").split("_")
            date_part = parts[0]  # DDMMYYYY
            hour_part = parts[1].replace("Z","")  # HH
            run_dt = datetime.strptime(f"{date_part} {hour_part}", "%d%m%Y %H")
            print(f"Run detecte : {run_dt.strftime('%d/%m/%Y %H:%M')} UTC")
        except Exception:
            run_dt = datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0)
            print(f"Date non detectee, utilisation : {run_dt.strftime('%d/%m/%Y %H:%M')} UTC")

    # 3. Warning
    print("\n[1/3] Warning...")
    warning_text = generate_warning(df, run_dt)
    print(f"  {warning_text[:100]}...")

    # 4. Excel
    print("\n[2/3] Export Excel...")
    exporter.export_excel(df, run_dt, config.OUTPUT_FILE, warning_text=warning_text)

    # 5. Word
    print("\n[3/3] Export Word...")
    word_path = config.OUTPUT_FILE.replace(".xlsx", ".docx")
    word_exporter.generate_word_bulletin(df, run_dt, warning_text, word_path)

    # 6. CSV bulletin avec directions en degrés
    date_str = run_dt.strftime("%d%m%Y")
    run_str  = f"{run_dt.hour:02d}Z"
    csv_out  = os.path.join(folder, f"bulletin_marine_seme_{date_str}_{run_str}.csv")

    df_csv = df.copy()
    for col in ["wind10_dir","wind100_dir","sw1_dir","sw2_dir","cur_dir"]:
        if col in df_csv.columns:
            df_csv[col] = df_csv[col].map(
                lambda x: CARDINAL_TO_DEG.get(str(x).strip(), None)
                if pd.notna(x) else None
            )
    df_csv.to_csv(csv_out, index=False, encoding="utf-8")

    print(f"\nExcel  OK")
    print(f"Word   OK")
    print(f"CSV    -> {csv_out}")
    print(f"\nPour publier sur GitHub :")
    print(f"  git add \"{csv_out}\"")
    print(f"  git commit -m \"reprise: {run_dt.strftime('%d/%m/%Y %HZ')}\"")
    print(f"  git push origin main")

if __name__ == "__main__":
    main()