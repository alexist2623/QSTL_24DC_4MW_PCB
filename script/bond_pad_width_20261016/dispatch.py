"""Dispatch a repository-local DelphiScript through Altium's scripting API."""
from pathlib import Path
import sys,subprocess
HERE=Path(__file__).resolve().parent
stem=sys.argv[1];project=HERE/(stem+'.PrjScr')
assert project.is_file() and (HERE/(stem+'.pas')).is_file()
exe=Path(r'F:\Altium\AD26\X2.EXE');assert exe.is_file()
p=subprocess.Popen([str(exe),f'-RScriptingSystem:RunScript(ProjectName={project}|ProcName={stem}.pas>{stem})'])
print('Dispatched',stem,'launcher PID',p.pid)
