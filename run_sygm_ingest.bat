@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ======================================================= >> "logs\sygm_cron.log"
echo [%date% %time%] SYGM Medya Raporu Zamanlanmis Gorev Basladi >> "logs\sygm_cron.log"
"C:\Users\murat.erman\AppData\Local\Microsoft\WindowsApps\python.exe" "app\sygm_auto_ingest.py" >> "logs\sygm_cron.log" 2>&1
echo [%date% %time%] SYGM Medya Raporu Tamamlandi >> "logs\sygm_cron.log"
