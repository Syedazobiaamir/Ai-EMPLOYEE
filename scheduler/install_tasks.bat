@echo off
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\GibTek\Desktop\hackathone ai employee fte"
python scheduler\setup_task_scheduler.py --vault "C:\Users\GibTek\Desktop\hackathone ai employee fte\AI_Employee_Vault" --install > "%TEMP%\sched_install.log" 2>&1
echo Done. Log saved to %TEMP%\sched_install.log
type "%TEMP%\sched_install.log"
pause
