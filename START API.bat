@echo off
cd /d C:\Users\Administrator\Desktop\MBPI-Projects\DEPLOYMENT-WAREHOUSE-PROGRAM-BACKEND
echo Starting Warehouse Program FastAPI server...
C:\Users\Administrator\Desktop\MBPI-Projects\DEPLOYMENT-WAREHOUSE-PROGRAM-BACKEND\venv\Scripts\python.exe -m uvicorn backend._app.main:app --host 0.0.0.0 --port 8000
pause
