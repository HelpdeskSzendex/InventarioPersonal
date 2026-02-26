@echo off
echo ====================================================
echo Iniciando Aplicacion de Gestion de Personal
echo ====================================================
echo.

:: Comprobar si las dependencias estan instaladas
python -c "import supabase; import streamlit; import pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Dependencias no detectadas. Instalando automaticamente...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [X] Error al instalar dependencias. Por favor, instala manualmente:
        echo     pip install -r requirements.txt
        pause
        exit /b
    )
    echo [OK] Dependencias instaladas con exito.
    echo.
)

echo [>] Iniciando Streamlit...
streamlit run Personal.py
pause
