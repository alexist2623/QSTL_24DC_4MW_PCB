"""Include solder mask in the local verification-only native CAM export."""
from pathlib import Path
H=Path(__file__).resolve().parent
p=H/'paste_verification/Cap_Paste_Verification.OutJob'
s=p.read_text();old='Plot.Set=SerializeLayerHash.Version~2,ClassName~TPlotLayerStateArray,16973832~1,16973833~1|'
previous='Plot.Set=SerializeLayerHash.Version~2,ClassName~TPlotLayerStateArray,16973832~1,16973833~1,16973830~1,16973831~1|'
new='Plot.Set=SerializeLayerHash.Version~2,ClassName~TPlotLayerStateArray,16973832~1,16973833~1,16973834~1,16973835~1|'
assert old in s or previous in s or new in s
p.write_text(s.replace(old,new).replace(previous,new))
print('Verification job includes Top/Bottom paste and solder mask only')
