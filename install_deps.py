# =============================================================================
# install_deps.py — Vérifie et installe les dépendances supplémentaires
# À lancer une seule fois après pip install ecmwf-opendata copernicusmarine
# =============================================================================

import subprocess
import sys

PACKAGES = [
    ("cfgrib",   "cfgrib"),    # lecture fichiers GRIB2
    ("eccodes",  "eccodes"),   # bibliothèque GRIB de base
    ("numpy",    "numpy"),
    ("xarray",   "xarray"),
]

print("Vérification des dépendances...\n")

missing = []
for import_name, pip_name in PACKAGES:
    try:
        __import__(import_name)
        print(f"  ✅ {import_name}")
    except ImportError:
        print(f"  ❌ {import_name} — à installer")
        missing.append(pip_name)

if missing:
    print(f"\nInstallation des packages manquants : {', '.join(missing)}")
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
    print("\n✅ Installation terminée.")
else:
    print("\n✅ Toutes les dépendances sont présentes.")

# Test final
print("\nTest d'import complet...")
try:
    import cfgrib, eccodes, numpy, xarray, pandas, openpyxl
    import ecmwf.opendata
    import copernicusmarine
    print("✅ Tout est OK — vous pouvez lancer run_pipeline.py")
except Exception as e:
    print(f"❌ Erreur : {e}")
