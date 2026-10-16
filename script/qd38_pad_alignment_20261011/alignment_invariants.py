"""Strict endpoint invariants for an explicitly declared alignment delta."""
from collections import Counter
from pathlib import Path
import hashlib,json,sys

H=Path(__file__).resolve().parent
OLD=H.parent/'qd38_rotation_20261011'
sys.path.insert(0,str(OLD))
from revision_invariants import contact_pool,assert_plan_contacts

def declaration(plan):
    manifest=json.loads((H/'alignment_delta_manifest.json').read_text())
    path=Path(manifest['candidate_file'])
    assert path.resolve().parent==H, 'Candidate must be in the alignment namespace'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['candidate_sha256']
    assert json.loads(path.read_text())==plan, 'Manifest candidate differs from audited plan'
    q=manifest['qd_endpoint_via']
    assert q['count']==22 and q['baseline_land_mm']==.4
    assert .35<=q['land_mm']<=.4 and q['drill_mm']==.2
    assert (q['low'],q['high'])==(1,32)
    return manifest

def via_groups(plan):
    m=declaration(plan)
    groups={'zif':[],'direct_qd':[],'resistor':[],'shield':list(plan['shield_vias'])}
    for via in plan['vias']:
        label=via['label']
        key='zif' if label.startswith('J1-') else 'direct_qd' if label.startswith('Q1-') else 'resistor' if label.startswith('R') and label.endswith('-2') else None
        assert key is not None, f'Unexpected signal endpoint {label}'
        groups[key].append(via)
    expected={'zif':(38,.4,.2,1,32),'direct_qd':(22,m['qd_endpoint_via']['land_mm'],.2,1,32),
              'resistor':(16,.5,.25,1,32),'shield':(len(groups['shield']),.25,.1,5,32)}
    for key,(count,land,hole,low,high) in expected.items():
        assert len(groups[key])==count and count>0
        assert all(abs(v['diameter']-land)<1e-8 and abs(v['hole']-hole)<1e-8 and (v['low'],v['high'])==(low,high) for v in groups[key]),key
    assert len({v['net'] for v in groups['direct_qd']})==22
    assert len({v['net'] for v in groups['resistor']})==16
    assert not ({v['net'] for v in groups['direct_qd']} & {v['net'] for v in groups['resistor']})
    assert all(v['net']=='GND' for v in groups['shield'])
    assert not any(v['net'].startswith(('S','MW')) for v in plan['vias'])
    assert all(t['layer']==32 for field in ('tracks','arcs') for t in plan.get(field,[]) if t['net'].startswith(('S','MW')))
    assert Counter(v['net'] for v in plan['vias'])==Counter({n:2 for n in plan['nets'] if n.startswith('DC')})
    pads={(p['ref'],p['pin']):p for p in plan['physical_pads']}
    for key in ('direct_qd','resistor'):
        for v in groups[key]:
            ref,pin=v['label'].split('-')
            assert pads[ref,pin]['net']==v['net']
    return groups
