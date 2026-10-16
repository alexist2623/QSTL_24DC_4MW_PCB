"""Launch an explicit repository Altium script through its command-line process API."""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
stem = sys.argv[1] if len(sys.argv) > 1 else "NativeHeartbeat"
project = HERE / (stem + ".PrjScr")
assert project.is_file() and project.parent == HERE
assert not any(ch.isspace() for ch in str(project))
# Altium parses the raw Windows command line itself. Embedded quotes in a
# Popen argv list acquire backslashes and are not decoded as MSVCRT arguments.
command = f'-RScriptingSystem:RunScript(ProjectName={project}|ProcName={stem}.pas>{stem})'
process = subprocess.Popen([r"F:\Altium\AD26\X2.EXE", command])
print("DISPATCHED", stem, "PID", process.pid, flush=True)
