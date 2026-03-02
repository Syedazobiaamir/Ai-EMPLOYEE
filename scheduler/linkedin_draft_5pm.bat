@echo off
cd /d "C:\Users\GibTek\Desktop\hackathone ai employee fte"
python -X utf8 watchers\linkedin_watcher.py --vault AI_Employee_Vault --generate-post >> AI_Employee_Vault\Logs\scheduler.log 2>&1
