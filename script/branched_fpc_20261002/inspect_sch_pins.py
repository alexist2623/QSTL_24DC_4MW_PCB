"""Read original schematic pin placement and nearby wires for format evidence."""
from pathlib import Path
import sys
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,olefile
with olefile.OleFileIO(R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.SchDoc') as o:r=properties(o.openstream('FileHeader').read())
comp=next((i,p) for i,p in enumerate(r) if p.get('RECORD')=='1')
print('COMP',comp)
owner=str(comp[0]-1)
pins=[p for p in r if p.get('RECORD')=='2' and p.get('OwnerIndex')==owner]
for p in pins:
 print('PIN',p)
 x=float(p.get('Location.X',0));y=float(p.get('Location.Y',0))
 for w in r:
  if w.get('RECORD')=='27' and any(abs(float(w.get('X'+str(j),99999))-x)<80 and abs(float(w.get('Y'+str(j),99999))-y)<80 for j in range(1,4)):
   print('WIRE',w)
