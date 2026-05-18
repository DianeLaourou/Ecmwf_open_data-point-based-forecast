@echo off
:: =============================================================================
:: run_marine_pipeline.bat — Pipeline de prévision marine Sème
::
:: Processus complet :
::   1. Lance le pipeline Python (~50 min)
::   2. Génère Excel + Word + latest_forecast.csv
::   3. Pousse latest_forecast.csv sur GitHub
::   4. Le dashboard Streamlit lit automatiquement le nouveau CSV
::
:: Planifier via : Planificateur de tâches Windows
:: Heure recommandée : 15h00 heure locale (= 14h00 UTC)
:: =============================================================================

setlocal enabledelayedexpansion

:: ── Paramètres ────────────────────────────────────────────────────────────────
set PIPELINE_DIR=D:\pipeline
set LOG_FILE=%PIPELINE_DIR%\logs\pipeline.log
set CSV_FILE=%PIPELINE_DIR%\latest_forecast.csv

:: ── Activation environnement conda ───────────────────────────────────────────
call C:\Users\Narcisse\.conda\envs\marine_pipeline\Scripts\activate.bat 2>nul
if errorlevel 1 (
    call C:\ProgramData\anaconda3\Scripts\activate.bat marine_pipeline 2>nul
)

:: ── Dossier de travail ────────────────────────────────────────────────────────
cd /d %PIPELINE_DIR%

:: ── Créer le dossier logs si inexistant ──────────────────────────────────────
if not exist "%PIPELINE_DIR%\logs" mkdir "%PIPELINE_DIR%\logs"

:: ═══════════════════════════════════════════════════════════════════════════════
:: ÉTAPE 1 — LANCER LE PIPELINE (~50 minutes)
:: ═══════════════════════════════════════════════════════════════════════════════
echo.
echo [%date% %time%] ============================================= >> %LOG_FILE%
echo [%date% %time%] DEMARRAGE PIPELINE MARINE — SEME             >> %LOG_FILE%
echo [%date% %time%] ============================================= >> %LOG_FILE%
echo.
echo  ⏳  Pipeline en cours... (environ 50 minutes)
echo      Logs : %LOG_FILE%
echo.

python run_pipeline.py --swh ecmwf >> %LOG_FILE% 2>&1

if errorlevel 1 (
    echo.
    echo  ❌  ERREUR pipeline — consultez %LOG_FILE%
    echo [%date% %time%] ERREUR pipeline >> %LOG_FILE%
    goto :end
)

echo [%date% %time%] Pipeline Python termine avec succes. >> %LOG_FILE%
echo  ✅  Pipeline terminé — Excel + Word + CSV générés.

:: ═══════════════════════════════════════════════════════════════════════════════
:: ÉTAPE 2 — VÉRIFIER QUE LE CSV EXISTE
:: ═══════════════════════════════════════════════════════════════════════════════
if not exist "%CSV_FILE%" (
    echo.
    echo  ⚠️   latest_forecast.csv introuvable — push annulé.
    echo [%date% %time%] CSV introuvable, push annule. >> %LOG_FILE%
    goto :end
)
echo  ✅  latest_forecast.csv trouvé.

:: ═══════════════════════════════════════════════════════════════════════════════
:: ÉTAPE 3 — POUSSER LE CSV SUR GITHUB
:: ═══════════════════════════════════════════════════════════════════════════════
echo.
echo  📤  Publication sur GitHub...
echo [%date% %time%] Publication GitHub en cours... >> %LOG_FILE%

:: Horodatage pour le message de commit
set COMMIT_MSG=auto: prevision marine %date% %time:~0,5%

git add latest_forecast.csv >> %LOG_FILE% 2>&1
git commit -m "%COMMIT_MSG%" >> %LOG_FILE% 2>&1
git push origin main >> %LOG_FILE% 2>&1

if errorlevel 1 (
    echo.
    echo  ⚠️   Push GitHub échoué — vérifiez la connexion internet.
    echo       Le CSV est disponible localement : %CSV_FILE%
    echo [%date% %time%] Push GitHub ECHOUE >> %LOG_FILE%
) else (
    echo  ✅  CSV publié sur GitHub — dashboard mis à jour !
    echo [%date% %time%] Push GitHub OK. >> %LOG_FILE%
)

:: ═══════════════════════════════════════════════════════════════════════════════
:: RÉSUMÉ FINAL
:: ═══════════════════════════════════════════════════════════════════════════════
echo.
echo  ════════════════════════════════════════════════════════
echo   ✅  PIPELINE COMPLET — %date% %time:~0,5%
echo   📊  Excel + Word générés dans D:\pipeline\
echo   🌐  Dashboard Streamlit mis à jour sur GitHub
echo   📝  Ouvrez le Word, corrigez si besoin, uploadez sur le dashboard
echo  ════════════════════════════════════════════════════════
echo.
echo [%date% %time%] ============= FIN PIPELINE ============= >> %LOG_FILE%

:end
pause
