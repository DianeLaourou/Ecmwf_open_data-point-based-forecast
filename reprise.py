import pandas as pd
import config
import exporter
import word_exporter
from run_pipeline import generate_warning
from datetime import datetime

df = pd.read_csv("D:/pipeline/latest_forecast.csv")
df["valid_local"] = pd.to_datetime(df["valid_local"])

run_dt = datetime(2026, 5, 18, 6, 0)
warning_text = generate_warning(df, run_dt)

print(f"Warning: {warning_text[:80]}...")

exporter.export_excel(df, run_dt, config.OUTPUT_FILE, warning_text=warning_text)

word_path = config.OUTPUT_FILE.replace(".xlsx", ".docx")
word_exporter.generate_word_bulletin(df, run_dt, warning_text, word_path)

# Export CSV avec directions en degrés
import os
csv_path = os.path.join(os.path.dirname(os.path.abspath(config.OUTPUT_FILE)), "latest_forecast.csv")
df_csv = df.copy()
if "wind10_dir_deg" in df_csv.columns:
    df_csv["wind10_dir"] = df_csv["wind10_dir_deg"]
if "wind100_dir_deg" in df_csv.columns:
    df_csv["wind100_dir"] = df_csv["wind100_dir_deg"]
if "cur_dir_deg" in df_csv.columns:
    df_csv["cur_dir"] = df_csv["cur_dir_deg"]
if "sw1_dir_deg" in df_csv.columns:
    df_csv["sw1_dir"] = df_csv["sw1_dir_deg"]
if "sw2_dir_deg" in df_csv.columns:
    df_csv["sw2_dir"] = df_csv["sw2_dir_deg"]
df_csv.to_csv(csv_path, index=False, encoding="utf-8")

print(f"✅ Excel + Word + CSV générés !")
print(f"   CSV : {csv_path}")
