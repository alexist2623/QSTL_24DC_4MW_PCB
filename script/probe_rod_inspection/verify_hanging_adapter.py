"""Validate the current inward-facing mounting arrangement."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('verify_inward_mounting.py')),run_name='__main__')
