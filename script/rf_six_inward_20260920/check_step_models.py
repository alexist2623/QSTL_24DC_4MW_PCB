from pathlib import Path
import json,hashlib
from OCP.STEPControl import STEPControl_Reader
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
H=Path(__file__).resolve().parent;report={}
for f in [H/'embedded_0.step',H/'R_0603_1608Metric.step']:
 r=STEPControl_Reader();assert int(r.ReadFile(str(f)))==1;r.TransferRoots();s=r.OneShape();b=Bnd_Box();BRepBndLib.Add_s(s,b);lo=b.CornerMin();hi=b.CornerMax();bounds=[lo.X(),lo.Y(),lo.Z(),hi.X(),hi.Y(),hi.Z()];dims=[bounds[i+3]-bounds[i] for i in range(3)]
 report[f.name]=dict(bounds_mm=bounds,dimensions_mm=dims,valid=BRepCheck_Analyzer(s).IsValid(),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
(H/'STEP_dimensions.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
