@echo off
cd /d C:\Users\Administrator\Desktop\RM-Consumption-Management-System-Backend-API
echo Starting Warehouse Program FastAPI server...
C:\Users\Administrator\Desktop\RM-Consumption-Management-System-Backend-API\venv\Scripts\python.exe -m uvicorn backend._app.main:app --host 0.0.0.0 --port 8000
pause
