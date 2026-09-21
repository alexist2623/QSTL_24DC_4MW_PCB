"""Prepare the matching QD footprint without changing its central 4.3 mm drawing."""
from pathlib import Path
import json,struct,sys,shutil
H=Path(__file__).resolve().parent;W=H.parent/'_support';P=H.parents[1]/'QSTL_24DC_4MW_PCB';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/'qd_center_revision'),str(W/'final_routing/schematic')]
from native_metadata_helpers import pad_record,UNIT,sha
from build_routed_copy import snapshot
from cfb_copy_update import update_copy
source=P/(B+'.PcbLib');backup=H/'before.PcbLib'
if not backup.exists():shutil.copy2(source,backup)
s=snapshot(backup);raw=s['QD4/Data'];out=bytearray(raw);pos=4+(struct.unpack_from('<I',raw,0)[0]&0xffffff)
plan=json.loads((H/'plan.json').read_text());moves={m['number']:m for m in plan['pad_moves']}
cx,cy=json.loads((H.parent/'rf_six_inward_20260920/geometry.json').read_text())['qd_component_center'];audit=[]
while pos<len(raw):
    if raw[pos]!=2:pos+=5+(struct.unpack_from('<I',raw,pos+1)[0]&0xffffff);continue
    p=pad_record(raw,pos);pos=p['end'];m=moves[p['number']]
    assert abs(cx-p['coords'][0]*UNIT-m['old'][0])<4*UNIT and abs(cy+p['coords'][1]*UNIT-m['old'][1])<4*UNIT
    x,y=round((cx-m['new'][0])/UNIT),round((m['new'][1]-cy)/UNIT)
    struct.pack_into('<ii',out,p['block_offsets'][4]+13,x,y)
    audit.append(dict(pin=p['number'],local_xy_mm=[x*UNIT,y*UNIT],board_xy_mm=[cx-x*UNIT,cy+y*UNIT]))
assert len(audit)==24
update_copy(backup,H/'QD_updated.PcbLib',{'QD4/Data':bytes(out)})
(H/'library_plan.json').write_text(json.dumps(dict(source_sha256=sha(source),prepared_sha256=sha(H/'QD_updated.PcbLib'),pads=audit,central_drawing_preserved=True),indent=2))
print('Prepared 24-pad matching library; original library is unchanged until the board is saved.')
