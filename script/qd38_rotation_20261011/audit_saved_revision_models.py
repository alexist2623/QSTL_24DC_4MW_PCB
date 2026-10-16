"""Read-only revision model transforms and original embedded STEP hash audit."""
from pathlib import Path
from collections import Counter
import json
import hashlib
import math
import sys

import olefile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'qd38_carrier_20261010'))
from audit_source_model_transforms import inspect

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'script/_support/qd_center_revision'))
from native_metadata_helpers import pads_stream,properties,UNIT


def step_hashes(body):
    return sorted({r['embedded_step_sha256'] for r in body['embedded_model_records'] if r['embedded_step_sha256']})


def main():
    source=ROOT/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc'
    target=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
    original=inspect(source);copied=inspect(target)
    sources={b['component']:b for b in original['bodies']}
    sch=json.loads((target.parent/'schematic_validation.json').read_text())
    assert sch['schematic_sha256']==hashlib.sha256((target.parent/'QSTL_QD4_2SET_38PAD.SchDoc').read_bytes()).hexdigest(),'Saved schematic differs from model-owner map'
    uid_to_ref={uid:name for name,uid in sch['components'].items()}
    with olefile.OleFileIO(target) as doc:
        components=properties(doc.openstream('Components6/Data').read())
        pads=pads_stream(doc.openstream('Pads6/Data').read())
    component_refs={i:uid_to_ref.get(c.get('SOURCEUNIQUEID','').strip('\\'),c.get('SOURCEDESIGNATOR')) for i,c in enumerate(components)}
    errors=[];items=[];counts=Counter()
    def check(ok,issue,ref,detail=None):
        if not ok:errors.append(dict(issue=issue,component=ref,detail=detail))
    for body in copied['bodies']:
        cf=body['component_fields'];ref=uid_to_ref.get(cf.get('SOURCEUNIQUEID','').strip('\\'),body['component'])
        check(ref is not None,'Unresolved body owner',str(ref))
        if not ref:continue
        body['component']=ref
        family='SMP' if ref.startswith('SMP') else ref[0]
        counts[family]+=1
        expected_source=sources['SMP1' if family=='SMP' else 'R1' if family=='R' else 'C1' if family=='C' else ref]
        hashes=step_hashes(body);expected_hashes=step_hashes(expected_source)
        check(hashes==expected_hashes,'Embedded STEP differs from original',ref,dict(actual=hashes,expected=expected_hashes))
        angle=float(cf['ROTATION'])
        if family=='SMP':
            expected_rotation=[90.,0.,angle]
            expected_dz=.5999988;expected_height=5.39999936;expected_standoff=-3.2100012;expected_projection=0
            expected_origin=body['component_origin_mm']
        elif family in ('R','C'):
            expected_rotation=[0.,0.,angle]
            expected_dz=0.;expected_standoff=0.;expected_projection=1
            expected_height=.45 if family=='R' else .553
            ownpads=[p for p in pads if component_refs.get(p['component'])==ref]
            check(len(ownpads)==2,'Passive pad count differs',ref,len(ownpads))
            expected_origin=[sum(p['coords'][axis] for p in ownpads)*UNIT/len(ownpads) for axis in (0,1)]
        else:
            expected_rotation=expected_source['rotation_xyz_deg']
            expected_dz=expected_source['dz_mm'];expected_height=expected_source['overall_height_mm']
            expected_standoff=expected_source['standoff_mm'];expected_projection=expected_source['body_projection']
            expected_origin=expected_source['model_origin_mm']
        errors_angle=[abs((actual-expected+180)%360-180) for actual,expected in zip(body['rotation_xyz_deg'],expected_rotation)]
        origin_delta=math.dist(body['model_origin_mm'],expected_origin)
        check(max(errors_angle)<.001,'Model rotation differs',ref,dict(actual=body['rotation_xyz_deg'],expected=expected_rotation))
        check(origin_delta<8*UNIT,'Model origin differs from intended pad/component centre',ref,origin_delta)
        for key,expected in [('dz_mm',expected_dz),('standoff_mm',expected_standoff),('overall_height_mm',expected_height)]:
            check(abs(body[key]-expected)<8*UNIT,'Model '+key+' differs',ref,dict(actual=body[key],expected=expected))
        check(body['body_projection']==expected_projection,'Model board side differs',ref,body['body_projection'])
        items.append(dict(component=ref,rotation_xyz_deg=body['rotation_xyz_deg'],component_rotation_deg=angle,
                          origin_mm=body['model_origin_mm'],origin_error_mm=origin_delta,
                          dz_mm=body['dz_mm'],standoff_mm=body['standoff_mm'],overall_height_mm=body['overall_height_mm'],
                          board_projection=body['body_projection'],embedded_step_sha256=hashes))
    check(dict(counts)=={'J':1,'R':16,'C':16,'SMP':16},'Saved model family counts differ','ALL',dict(counts))
    report=dict(passed=not errors,status='SAVED_NATIVE_EMBEDDED_MODELS_READ_ONLY_AUDIT',native_file=str(target),
                native_sha256=copied['source_sha256'],original_pcb_sha256=original['source_sha256'],
                model_counts=dict(counts),models=items,errors=errors,original_unchanged=original['source_unchanged'],
                native_unchanged=copied['source_unchanged'],scope='Native model transforms and source STEP hashes; not 3D body collision certification.')
    (HERE/'saved_revision_models.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='models'},indent=2))


if __name__=='__main__':main()
