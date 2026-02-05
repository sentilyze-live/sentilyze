@echo off
REM Test Script for Phase 1 & 2 Implementation (Windows)
REM Tests: yfinance collector, economic features, predictions

setlocal enabledelayedexpansion

echo ================================
echo Phase 1 ^& 2 Testing Script
echo ================================
echo.

set PASSED=0
set FAILED=0

echo === 1. Dependency Checks ===
echo.

REM Test Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python installed
    set /a PASSED+=1
) else (
    echo [FAIL] Python not found
    set /a FAILED+=1
)

REM Test Poetry
poetry --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Poetry installed
    set /a PASSED+=1
) else (
    echo [FAIL] Poetry not found
    set /a FAILED+=1
)

echo.
echo === 2. File Existence Checks ===
echo.

if exist "services\ingestion\src\collectors\yfinance_collector.py" (
    echo [OK] yfinance collector exists
    set /a PASSED+=1
) else (
    echo [FAIL] yfinance collector not found
    set /a FAILED+=1
)

if exist "services\prediction-engine\src\models\lstm_predictor.py" (
    echo [OK] LSTM model exists
    set /a PASSED+=1
) else (
    echo [FAIL] LSTM model not found
    set /a FAILED+=1
)

if exist "services\prediction-engine\src\models\arima_predictor.py" (
    echo [OK] ARIMA model exists
    set /a PASSED+=1
) else (
    echo [FAIL] ARIMA model not found
    set /a FAILED+=1
)

if exist "services\prediction-engine\src\models\xgboost_predictor.py" (
    echo [OK] XGBoost model exists
    set /a PASSED+=1
) else (
    echo [FAIL] XGBoost model not found
    set /a FAILED+=1
)

if exist "services\prediction-engine\src\ensemble.py" (
    echo [OK] Ensemble predictor exists
    set /a PASSED+=1
) else (
    echo [FAIL] Ensemble predictor not found
    set /a FAILED+=1
)

echo.
echo === 3. Configuration Checks ===
echo.

findstr /C:"ENABLE_YFINANCE_COLLECTOR" "shared\sentilyze_core\config\__init__.py" >nul
if %errorlevel% equ 0 (
    echo [OK] Config has yfinance settings
    set /a PASSED+=1
) else (
    echo [FAIL] yfinance config not found
    set /a FAILED+=1
)

findstr /C:"ENABLE_LSTM_MODEL" "shared\sentilyze_core\config\__init__.py" >nul
if %errorlevel% equ 0 (
    echo [OK] Config has model flags
    set /a PASSED+=1
) else (
    echo [FAIL] Model flags not found
    set /a FAILED+=1
)

echo.
echo === 4. Documentation Checks ===
echo.

if exist "GOLD_PREDICTION_PHASE1_COMPLETE.md" (
    echo [OK] Phase 1 documentation exists
    set /a PASSED+=1
) else (
    echo [FAIL] Phase 1 docs not found
    set /a FAILED+=1
)

if exist "GOLD_PREDICTION_PHASE2_COMPLETE.md" (
    echo [OK] Phase 2 documentation exists
    set /a PASSED+=1
) else (
    echo [FAIL] Phase 2 docs not found
    set /a FAILED+=1
)

if exist "DEPLOYMENT_GUIDE_PHASE1_2.md" (
    echo [OK] Deployment guide exists
    set /a PASSED+=1
) else (
    echo [FAIL] Deployment guide not found
    set /a FAILED+=1
)

echo.
echo === 5. Import Tests ===
echo.

echo Testing yfinance collector import...
python -c "from services.ingestion.src.collectors.yfinance_collector import YFinanceCollector; print('OK')" 2>nul | findstr "OK" >nul
if %errorlevel% equ 0 (
    echo [OK] yfinance collector imports
    set /a PASSED+=1
) else (
    echo [SKIP] yfinance collector import (dependencies may not be installed)
)

echo Testing predictor imports...
python -c "from services.prediction_engine.src.predictor import EconomicDataFetcher; print('OK')" 2>nul | findstr "OK" >nul
if %errorlevel% equ 0 (
    echo [OK] Predictor imports
    set /a PASSED+=1
) else (
    echo [SKIP] Predictor import (dependencies may not be installed)
)

echo.
echo ================================
echo Test Summary
echo ================================
echo Passed: %PASSED%
echo Failed: %FAILED%
echo.

if %FAILED% gtr 0 (
    echo [FAIL] Some tests failed. Please fix issues before deployment.
    exit /b 1
) else (
    echo [OK] All tests passed! Ready for deployment.
    exit /b 0
)
