"""Dispatch an existing repository Altium script through the supported CLI."""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
stem = sys.argv[1]
project = HERE / (stem + '.PrjScr')
assert project.is_file() and project.parent == HERE
assert not any(ch.isspace() for ch in str(project))
command = f'-RScriptingSystem:RunScript(ProjectName={project}|ProcName={stem}.pas>{stem})'
process = subprocess.Popen([r'F:\Altium\AD26\X2.EXE', command])
print('DISPATCHED', stem, 'PID', process.pid, flush=True)
