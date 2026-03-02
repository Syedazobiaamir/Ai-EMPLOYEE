#!/usr/bin/env python3
"""Create Windows Task Scheduler task: generate LinkedIn draft at 5 PM daily."""
import subprocess
import sys

BAT_FILE = r"C:\Users\GibTek\Desktop\hackathone ai employee fte\scheduler\linkedin_draft_5pm.bat"

result = subprocess.run([
    'schtasks', '/create',
    '/tn', 'AIEmployee_LinkedInDraft_5PM',
    '/tr', BAT_FILE,
    '/sc', 'DAILY',
    '/st', '17:00',
    '/f'
], capture_output=True, text=True)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)

if result.returncode == 0:
    print("\nTask created: AIEmployee_LinkedInDraft_5PM")
    print("  Runs: Every day at 5:00 PM")
    print("  Action: Generates LinkedIn post draft -> saves to /Needs_Action/")
else:
    print("\nFailed to create task")
