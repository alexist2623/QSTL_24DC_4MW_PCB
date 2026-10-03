"""Synchronize the native generic clearance matrix with the staggered geometry."""
from pathlib import Path
import sys,struct,shutil
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,olefile
from cfb_copy_update import update_copy
P=R/'QSTL_24DC_4MW_PCB/FPC_15015_0451/FPC_15015_0451.PcbDoc'
B=H/'before_clearance.PcbDoc';T=H/'clearance_updated.PcbDoc'
assert not B.exists() and not T.exists()
shutil.copy2(P,B)
with olefile.OleFileIO(B) as o:d=o.openstream('Rules6/Data').read()
p=0;out=[]
while p<len(d):
    n=struct.unpack_from('<I',d,p+2)[0];r=properties(d[p+2:p+6+n])[0]
    if r.get('RULEKIND')=='Clearance':
        r['GAP']=r['GENERICCLEARANCE']='2.783464567mil'
    v=('|'+'|'.join(k+'='+str(v) for k,v in r.items())+'\0').encode('cp1252')
    out.append(d[p:p+2]+struct.pack('<I',len(v))+v);p+=n+6
update_copy(B,T,{'Rules6/Data':b''.join(out)});shutil.copy2(T,P)
print('Clearance gap and generic matrix updated to 0.0707 mm.')
