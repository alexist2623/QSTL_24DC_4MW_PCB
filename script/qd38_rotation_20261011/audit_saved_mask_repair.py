"""Audit reopened native pad caches and the exact saved mask-only delta."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
import olefile

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
sys.path.insert(0,str(ROOT/'script/_support/qd_center_revision'))
from native_metadata_helpers import pads_stream, properties
UNIT=2.54e-6
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def dump(path, stage, candidate_hash):
    lines=path.read_text().splitlines()
    assert 'COMPLETE' in lines and f'STAGE={stage}' in lines
    assert f'CANDIDATE_SHA256={candidate_hash}' in lines
    values={}
    for line in lines:
        if not line.startswith('PAD='): continue
        r,p,x,y,top,bottom,paste,enabled=line[4:].split('|')
        key=(r,p,int(x),int(y))
        assert key not in values
        values[key]=tuple(map(int,(top,bottom,paste,enabled)))
    assert len(values)==243 and 'PAD_COUNT=243' in lines
    return values

def native_pads(path):
    with olefile.OleFileIO(path) as ole:
        comp=properties(ole.openstream('Components6/Data').read())
        raw=pads_stream(ole.openstream('Pads6/Data').read())
    sch=json.loads((ROOT/'QSTL_QD4_2SET_38PAD/schematic_validation.json').read_text())
    by_uid={value:ref for ref,value in sch['components'].items()}
    names={i:by_uid.get(c.get('SOURCEUNIQUEID','').strip('\\'),c.get('SOURCEDESIGNATOR')) for i,c in enumerate(comp)}
    assert all(names.values()), 'Native component identity cannot be resolved'
    rows={}
    for p in raw:
        r='MOUNT' if p['component']==65535 else names[p['component']]
        key=(r,p['number'],p['coords'][0],p['coords'][1])
        assert key not in rows
        rows[key]=p
    assert len(rows)==243
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate',type=Path,default=H/'full_copper_mask_repair_candidate.json')
    ap.add_argument('--output',type=Path,default=H/'saved_mask_repair_audit.json')
    args=ap.parse_args()
    native=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
    baseline=H/'pre_mask_repair/QSTL_QD4_2SET_38PAD.PcbDoc'
    candidate_hash=sha(args.candidate);native_hash=sha(native)
    plan=json.loads(args.candidate.read_text())
    source=json.loads((H/'pre_mask_repair/full_copper_candidate.json').read_text())
    expected={(r['ref'],r['pin']) for r in plan['pad_solder_mask_overrides']}
    errors=[]
    def check(ok,issue,detail=None):
        if not ok: errors.append(dict(issue=issue,detail=detail))
    check(len(expected)==18,'wrong_override_count')
    check(all(r['expansion_mm']==.025 for r in plan['pad_solder_mask_overrides']),'unexpected_mask_override_value')
    without={k:v for k,v in plan.items() if k not in ('pad_solder_mask_overrides','mask_sliver_repair')}
    check(without==source,'candidate_non_mask_delta')
    check(sha(baseline)==plan['mask_sliver_repair']['native_before_sha256'],'baseline_hash_mismatch')
    before_path=H/'native_mask_before.txt';after_path=H/'native_mask_after_reopen.txt'
    before=dump(before_path,'BEFORE_REPAIR',candidate_hash)
    after=dump(after_path,'AFTER_REOPEN',candidate_hash)
    check(before.keys()==after.keys(),'native_pad_membership_or_positions_changed')
    changes=[]
    for key,old in before.items():
        new=after.get(key)
        selected=key[:2] in expected
        if selected:
            check(new is not None and all(abs(v*UNIT-.025)<3e-6 for v in new[:2]),'reopened_override_wrong',key)
            check(all(abs(v*UNIT-.05)<3e-6 for v in old[:2]),'baseline_override_not_005',key)
            check(new is not None and new[2:]==old[2:],'selected_pad_paste_changed',key)
            changes.append(dict(ref=key[0],pin=key[1],before_coord=list(old),after_coord=list(new)))
        else: check(new==old,'unselected_pad_mask_or_paste_changed',key)
    oldpads=native_pads(baseline);newpads=native_pads(native)
    check(oldpads.keys()==newpads.keys(),'saved_native_pad_membership_changed')
    byte_changes=[]
    for key,old in oldpads.items():
        new=newpads.get(key)
        if new is None:continue
        for field in ('number','component','net','coords','rotation','shape','layer'):
            check(old[field]==new[field],'native_pad_copper_or_net_changed',dict(pad=key,field=field))
        check(old['blocks'][:4]==new['blocks'][:4],'native_pad_identity_changed',key)
        changed=[]
        for bi,(a,b) in enumerate(zip(old['blocks'],new['blocks'])):
            check(len(a)==len(b),'native_pad_block_length_changed',dict(pad=key,block=bi))
            changed.extend((bi,i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y)
        if key[:2] not in expected:
            check(not changed,'unselected_saved_pad_bytes_changed',dict(pad=key,changes=changed))
        else:
            # Read actual before/after values and allow only stored +.05 to
            # +.025 expansion fields. Do not guess their binary offsets.
            allowed=set();fields=[]
            for bi,(a,b) in enumerate(zip(old['blocks'],new['blocks'])):
                for i in range(0,min(len(a),len(b))-3):
                    av=struct.unpack_from('<i',a,i)[0];bv=struct.unpack_from('<i',b,i)[0]
                    if abs(av*UNIT-.05)<3e-6 and abs(bv*UNIT-.025)<3e-6:
                        fields.append([bi,i]);allowed.update((bi,j) for j in range(i,i+4))
            check(bool(fields),'saved_override_not_found',key)
            check(all((bi,i) in allowed for bi,i,_,_ in changed),'unexpected_saved_pad_byte_delta',dict(pad=key,changes=changed,allowed_fields=fields))
            byte_changes.append(dict(ref=key[0],pin=key[1],mask_fields=fields,changed_bytes=len(changed)))
    check(len(changes)==18 and len(byte_changes)==18,'saved_change_count_wrong')
    check(sha(native)==native_hash and sha(args.candidate)==candidate_hash,'files_changed_during_audit')
    report=dict(passed=not errors,candidate_sha256=candidate_hash,native_sha256=native_hash,
                baseline_native_sha256=sha(baseline),before_log_sha256=sha(before_path),after_log_sha256=sha(after_path),
                pad_count=243,changed_pad_count=len(changes),positive_expansion_mm=.025,
                untouched_pad_mask_and_all_pad_paste_preserved=not errors,changes=changes,saved_byte_changes=byte_changes,errors=errors,
                native_drc_verified_separately=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],changed_pad_count=len(changes),errors=errors),indent=2))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
