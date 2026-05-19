@echo off
:: =============================================================================
:: run_marine_pipeline.bat — Pipeline de prévision marine Sème
:: =============================================================================

:: Débloquer les DLL (évite l'erreur Windows à chaque run)
powershell -Command "Get-ChildItem -Path 'D:\marine_env' -Recurse -Include '*.pyd','*.dll' | Unblock-File" 2>nul

:: Activer l'environnement conda dans D:\
call conda activate D:\marine_env

:: Se placer dans le dossier pipeline
cd /d D:\Pipeline

:: Créer le dossier logs si inexistant
if not exist "D:\Pipeline\logs" mkdir D:\Pipeline\logs

:: Lancer le pipeline
echo [%date% %time%] Démarrage du pipeline... >> D:\Pipeline\logs\pipeline.log
python run_pipeline.py --swh ecmwf >> D:\Pipeline\logs\pipeline.log 2>&1

if errorlevel 1 (
    echo [%date% %time%] ERREUR pipeline. >> D:\Pipeline\logs\pipeline.log
    echo  ERREUR pipeline - consultez D:\Pipeline\logs\pipeline.log
    pause
    exit /b 1
)

echo [%date% %time%] Pipeline terminé. >> D:\Pipeline\logs\pipeline.log
echo  Pipeline terminé avec succès.

:: Pousser le CSV bulletin sur GitHub
echo  Publication sur GitHub...
git add D:\Pipeline\bulletin_marine_seme_*.csv >> D:\Pipeline\logs\pipeline.log 2>&1
git commit -m "auto: prevision marine %date%" >> D:\Pipeline\logs\pipeline.log 2>&1
git push origin main >> D:\Pipeline\logs\pipeline.log 2>&1

if errorlevel 1 (
    echo  Push GitHub echoue - verifiez la connexion
    echo [%date% %time%] Push GitHub ECHOUE. >> D:\Pipeline\logs\pipeline.log
) else (
    echo  CSV publie sur GitHub - dashboard mis a jour !
    echo [%date% %time%] Push GitHub OK. >> D:\Pipeline\logs\pipeline.log
)

pause