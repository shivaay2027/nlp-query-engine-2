@echo off
echo Activating virtual environment (if present)...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo No virtual env found. It's recommended to create one: python -m venv venv
)
echo Installing requirements (skip if already done)...
pip install -r requirements.txt
echo Starting server...
uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause
