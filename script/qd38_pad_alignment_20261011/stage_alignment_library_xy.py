"""Patch only canonical library pad XY bytes into a new staged copy."""
from pathlib import Path
import hashlib,json,math,shutil,struct,sys
import olefile

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
sys.path.insert(0,str(ROOT/'script/_support/qd_center_revision'))
from native_metadata_helpers import pad_record,UNIT

SOURCE=H/'before_alignment/QD4_2SET_38.PcbLib'
SOURCE_SHA='21948bf605c8762cbc141ac7bd40f55f10d5df138c5afeb757d2092a5f776e0b'
PROPOSAL=H/'aligned_qd_vias_land_0p35_candidate.json'
PROPOSAL_SHA='89829a12e11b6dc548c045df0735d62824996275f4f32d5fe4379d4804b3273c'
STAGE=H/'library_staging/QD4_2SET_38.PcbLib'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def streams(path):
    with olefile.OleFileIO(path) as o:return {'/'.join(k):o.openstream(k).read() for k in o.listdir()}

def records(data):
    pos=4+(struct.unpack_from('<I',data)[0]&0xffffff);rows=[]
    while pos<len(data):
        assert data[pos]==2, 'Unexpected library primitive; stop without editing'
        r=pad_record(data,pos);rows.append(r);pos=r['end']
    assert pos==len(data) and len(rows)==38
    return rows

def main():
    assert sha(SOURCE)==SOURCE_SHA and sha(PROPOSAL)==PROPOSAL_SHA
    proposal=json.loads(PROPOSAL.read_text());pads={p['pin']:p for p in proposal['qd_pads']}
    assert len(pads)==38 and all(p['ref']=='Q1' and p['shape']=='rect' and p['layer']==32 and p['sx']==.8 and p['sy']==.25 for p in pads.values())
    snapshot=ROOT/'script/qd38_rotation_20261011/saved_revision_snapshot.json'
    native=json.loads(snapshot.read_text());assert native['source_sha256']=='1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
    q1=next(c for c in native['components'] if c['designator']=='Q1')
    assert q1['rotation']==90 and q1['side']=='BOTTOM'
    origin=[round(q1[k]/UNIT) for k in ('x','y')]
    before=streams(SOURCE);name='QD4_2SET_38/Data';data=before[name];updated=bytearray(data)
    allowed=set();changes=[]
    for r in records(data):
        pin=r['number'];p=pads[pin];base=r['block_offsets'][4]
        assert r['layer']==1 and r['shape']==2 and r['coords'][-1]==0
        assert abs(r['coords'][2]*UNIT-.8)<3e-6 and abs(r['coords'][3]*UNIT-.25)<3e-6
        angle=(90-r['rotation'])%360
        assert min(abs((angle-p['rotation']+180)%360-180),abs((angle-p['rotation'])%180))<1e-7
        absolute=[round(p[k]/UNIT) for k in ('x','y')]
        # Exact integer-grid inverse of canonical Top -> Bottom/+90:
        # placed.x = Q1.x - library.y; placed.y = Q1.y - library.x.
        xy=[origin[1]-absolute[1],origin[0]-absolute[0]]
        for axis,value in enumerate(xy):
            offset=base+13+4*axis;struct.pack_into('<i',updated,offset,value)
            allowed.update(range(offset,offset+4))
        changes.append(dict(pin=pin,before_xy_coord=r['coords'][:2],after_xy_coord=xy,
                            planned_absolute_mm=[p['x'],p['y']],quantized_absolute_coord=absolute,
                            changed=r['coords'][:2]!=xy,rotation_preserved_deg=r['rotation']))
    actual_changes={i for i,(a,b) in enumerate(zip(data,updated)) if a!=b}
    assert len(data)==len(updated) and actual_changes<=allowed
    STAGE.parent.mkdir(exist_ok=True)
    shutil.copy2(SOURCE,STAGE)
    with olefile.OleFileIO(STAGE,write_mode=True) as o:o.write_stream(name,bytes(updated))
    after=streams(STAGE);assert before.keys()==after.keys()
    assert all(before[k]==after[k] for k in before if k!=name)
    assert after[name]==bytes(updated)
    newrecords=records(after[name]);oldrecords=records(data)
    checks=[]
    for a,b in zip(oldrecords,newrecords):
        assert a['number']==b['number'] and a['rotation']==b['rotation']
        assert a['blocks'][:4]==b['blocks'][:4] and a['blocks'][5]==b['blocks'][5]
        assert a['blocks'][4][:13]==b['blocks'][4][:13] and a['blocks'][4][21:]==b['blocks'][4][21:]
        target=pads[b['number']];absolute=[round(target[k]/UNIT) for k in ('x','y')]
        placed=[origin[0]-b['coords'][1],origin[1]-b['coords'][0]]
        assert placed==absolute
        checks.append(dict(pin=b['number'],placed_mm=[v*UNIT for v in placed],exact_quantized_position_match=True,
                           continuous_target_error_mm=math.dist([v*UNIT for v in placed],[target['x'],target['y']])))
    assert sha(SOURCE)==SOURCE_SHA and sha(PROPOSAL)==PROPOSAL_SHA
    report=dict(passed=True,source_library=str(SOURCE),source_library_sha256=SOURCE_SHA,
                proposal=str(PROPOSAL),proposal_sha256=PROPOSAL_SHA,staged_library=str(STAGE),staged_library_sha256=sha(STAGE),
                native_baseline_sha256=native['source_sha256'],native_Q1_origin_coord=origin,native_grid_mm=UNIT,
                changed_pad_count=sum(p['changed'] for p in changes),changed_data_bytes=len(actual_changes),
                only_pad_XY_fields_changed=True,all_other_records_and_streams_byte_identical=True,
                source_unchanged=True,project_library_not_promoted=True,
                preserved_stream_sha256={k:hashlib.sha256(v).hexdigest() for k,v in before.items() if k!=name},
                changes=changes,inverse_transform_checks=checks,
                limitation='Staged library only. Final routed candidate, promotion, actual placed pads and native DRC remain pending.')
    (H/'library_staging/library_xy_patch_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('changes','inverse_transform_checks','preserved_stream_sha256')},indent=2))

if __name__=='__main__':main()
