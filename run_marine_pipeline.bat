@echo off
:: =============================================================================
:: run_marine_pipeline.bat — Pipeline de prévision marine Sème
:: Planifier via : Planificateur de tâches Windows
:: Heure recommandée : 15h00 heure locale (= 14h00 UTC)
:: =============================================================================

:: Activer l'environnement conda marine_pipeline
call C:\Users\Narcisse\.conda\envs\marine_pipeline\Scripts\activate.bat 2>nul
if errorlevel 1 (
    call C:\ProgramData\anaconda3\Scripts\activate.bat marine_pipeline 2>nul
)

:: Se placer dans le dossier pipeline
cd /d D:\pipeline

:: Créer le dossier logs si inexistant
if not exist "D:\pipeline\logs" mkdir D:\pipeline\logs

:: Lancer le pipeline
echo [%date% %time%] Démarrage du pipeline... >> D:\pipeline\logs\pipeline.log
python run_pipeline.py --swh ecmwf >> D:\pipeline\logs\pipeline.log 2>&1
echo [%date% %time%] Pipeline terminé. >> D:\pipeline\logs\pipeline.log
