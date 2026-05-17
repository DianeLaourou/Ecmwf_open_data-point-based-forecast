# =============================================================================
# check_variables.py — Diagnostic des noms de variables dans les fichiers GRIB2
# =============================================================================

from ecmwf.opendata import Client
from datetime import datetime, timedelta
from pathlib import Path
import cfgrib
import sys

yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
RUN_DATE  = yesterday
RUN_HOUR  = 0
SOURCE    = "aws"

print("=" * 60)
print(f"  DIAGNOSTIC VARIABLES ECMWF GRIB2")
print(f"  Date : {RUN_DATE}  Heure : {RUN_HOUR:02d}Z")
print("=" * 60)

client  = Client(source=SOURCE)
tmp_dir = Path("tmp_diag")
tmp_dir.mkdir(exist_ok=True)

# ── Fichier atmosphérique principal ───────────────────────────────────────────
print("\n📡 Téléchargement atmosphérique...")
atm_file = tmp_dir / "diag_atm.grib2"
client.retrieve(
    date=RUN_DATE, time=RUN_HOUR, step=[3],
    stream="oper", type="fc",
    param=["10u", "10v", "10fg", "100u", "100v", "msl", "2t"],
    target=str(atm_file),
)
print("  ✅ OK")

# ── SST — stream oper, type an (analyse) ─────────────────────────────────────
print("\n📡 Recherche SST (stream oper, type=an)...")
sst_file1 = tmp_dir / "diag_sst1.grib2"
try:
    client.retrieve(
        date=RUN_DATE, time=RUN_HOUR, step=[0],
        stream="oper", type="an",
        param=["sst"],
        target=str(sst_file1),
    )
    print("  ✅ SST (an) téléchargé.")
except Exception as e:
    print(f"  ❌ SST (an) : {e}")
    sst_file1 = None

# ── SST — stream oper, type fc ────────────────────────────────────────────────
print("\n📡 Recherche SST (stream oper, type=fc)...")
sst_file2 = tmp_dir / "diag_sst2.grib2"
try:
    client.retrieve(
        date=RUN_DATE, time=RUN_HOUR, step=[3],
        stream="oper", type="fc",
        param=["sst"],
        target=str(sst_file2),
    )
    print("  ✅ SST (fc) téléchargé.")
except Exception as e:
    print(f"  ❌ SST (fc) : {e}")
    sst_file2 = None

# ── Fichier wave ──────────────────────────────────────────────────────────────
print("\n📡 Téléchargement wave...")
wav_file = tmp_dir / "diag_wav.grib2"
client.retrieve(
    date=RUN_DATE, time=RUN_HOUR, step=[3],
    stream="wave", type="fc",
    param=["swh"],
    target=str(wav_file),
)
print("  ✅ OK")

# ── Inspection ────────────────────────────────────────────────────────────────
def inspect_grib(filepath, label):
    if filepath is None or not Path(filepath).exists():
        return
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    try:
        datasets = cfgrib.open_datasets(str(filepath))
        for i, ds in enumerate(datasets):
            print(f"\n  --- Dataset {i+1} ---")
            for var in ds.data_vars:
                attrs = ds[var].attrs
                print(f"  Variable cfgrib  : '{var}'")
                print(f"    GRIB_shortName : {attrs.get('GRIB_shortName','N/A')}")
                print(f"    long_name      : {attrs.get('long_name','N/A')}")
                print(f"    units          : {attrs.get('units','N/A')}")
                try:
                    import numpy as np
                    vals = ds[var].values.flatten()
                    vals = vals[~np.isnan(vals)]
                    if len(vals) > 0:
                        print(f"    Valeur exemple : {vals[0]:.4f}")
                    else:
                        print(f"    Valeur exemple : NaN (pas de donnée)")
                except Exception:
                    pass
                print()
    except Exception as e:
        print(f"  ❌ Erreur : {e}")

inspect_grib(atm_file,  "Fichier atmosphérique (oper fc)")
inspect_grib(sst_file1, "SST (oper, type=an)")
inspect_grib(sst_file2, "SST (oper, type=fc)")
inspect_grib(wav_file,  "Fichier wave")

# ── Nettoyage ─────────────────────────────────────────────────────────────────
for f in tmp_dir.glob("*"):
    f.unlink()
tmp_dir.rmdir()

print("\n✅ Diagnostic terminé.")
print("=" * 60)
