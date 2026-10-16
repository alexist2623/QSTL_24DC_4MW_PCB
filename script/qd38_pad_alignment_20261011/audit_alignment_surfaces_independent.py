"""Independent offline check of the local cutback and inherited mask/shields."""
from collections import Counter
from pathlib import Path
from copy import deepcopy
import hashlib,json,math,sys
import shapely
from shapely.geometry import Point,LineString,shape,box
from shapely.ops import unary_union

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
OLD=H.parent/'qd38_rotation_20261011'
sys.path.insert(0,str(OLD))
from audit_saved_revision_surface import read_snapshot
from audit_aligned_via_placement import pg,quantized
from alignment_surface_contract import retained_mask_field

UNIT=2.54e-6
LAYERS=(1,2,3,4,5,32)
LOCAL=box(5.5,36,14,49)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    cp=H/'alignment_full_candidate.json';bp=H/'before_alignment/full_copper_candidate.json'
    native=H/'before_alignment/QSTL_QD4_2SET_38PAD.PcbDoc'
    p=json.loads(cp.read_text());old=json.loads(bp.read_text());initial=sha(cp)
    assert sha(native)=='1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
    assert sha(bp)=='835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495'
    sch=json.loads((ROOT/'QSTL_QD4_2SET_38PAD/schematic_validation.json').read_text())
    _,regions,_,_,_=read_snapshot(native,sch)
    errors=[]
    def check(ok,issue,detail=None):
        if not ok:errors.append(dict(issue=issue,detail=detail))
    preserved=('shield_vias','solder_openings','qd_mask_field','qd_ground_exclusion','rc_mask_rectangles',
               'zif_bottom_mask_rectangle','pad_solder_mask_overrides','arcs','components','nets','pinmap')
    for key in preserved:check(p[key]==old[key],'unrelated_candidate_field_changed',key)
    rf=lambda plan:[t for t in plan['tracks'] if t['net'].startswith(('S','MW'))]
    check(rf(p)==rf(old),'RF_tracks_changed')
    tracks=deepcopy(p['tracks'])
    for t in tracks:
        t['a']=[round(v/UNIT)*UNIT for v in t['a']]
        t['b']=[round(v/UNIT)*UNIT for v in t['b']]
        t['width']=round(t['width']/UNIT)*UNIT
    pads=quantized(p['physical_pads'],('x','y','sx','sy','hole'))
    vias=quantized(p['vias'],('x','y','diameter','hole'))
    qd=[x for x in pads if x['ref']=='Q1']
    qv=[x for x in vias if x['label'].startswith('Q1-')]
    rows=[]
    ground={int(k):shape(v) for k,v in p['ground_regions'].items()}
    for layer in LAYERS:
        before=shapely.set_precision(unary_union([r['geometry'] for r in regions if r['layer']==layer and r['net']=='GND']),UNIT)
        actual=shapely.set_precision(ground[layer],UNIT)
        outside=before.symmetric_difference(actual).difference(LOCAL).area
        added=actual.difference(before).area
        check(outside<1e-10,'ground_change_outside_local',dict(layer=layer,area=outside))
        check(added<1e-10,'ground_added',dict(layer=layer,area=added))
        objects=[(f"VIA:{v['label']}",Point(v['x'],v['y']),v['diameter']/2) for v in qv]
        if layer==32:objects.extend((f"PAD:Q1-{x['pin']}",pg(x),0) for x in qd)
        objects.extend((f"TRACK:{i}:{t['net']}",LineString([t['a'],t['b']]),t['width']/2)
                       for i,t in enumerate(tracks) if layer in (2,4) and t['layer']==layer and t['net'].startswith('DC'))
        gap,label=min((actual.distance(g)-r,key) for key,g,r in objects)
        check(gap>=.2-1e-6,'new_signal_ground_clearance',dict(layer=layer,gap=gap,nearest=label))
        rows.append(dict(layer=layer,outside_difference_mm2=outside,added_GND_mm2=added,
                         minimum_new_signal_GND_mm=gap,nearest=label))
    shield_min=(float('inf'),None)
    for sv in quantized(p['shield_vias'],('x','y','diameter','hole')):
        center=Point(sv['x'],sv['y'])
        for v in qv:
            gap=math.dist([sv['x'],sv['y']],[v['x'],v['y']])-(sv['diameter']+v['diameter'])/2
            if gap<shield_min[0]:shield_min=(gap,[sv['label'],v['label']])
        for pad in qd:
            gap=center.distance(pg(pad))-sv['diameter']/2
            if gap<shield_min[0]:shield_min=(gap,[sv['label'],'Q1-'+pad['pin']])
    check(shield_min[0]>=.2,'inherited_shield_new_signal_gap',shield_min)
    saved_style_pads=[dict(x,geometry=pg(x)) for x in pads]
    _,mask=retained_mask_field(p,saved_style_pads,regions,native)
    check(mask['passed'],'retained_mask_contract',mask['errors'])
    check(len(qd)==38 and len(qv)==22 and len(p['shield_vias'])==668,'expected_counts')
    check(sha(cp)==initial,'candidate_changed_during_audit')
    result=dict(passed=not errors,candidate_sha256=initial,baseline_native_sha256=sha(native),
                layers=rows,new_QD_signal_to_shield_minimum=shield_min,mask=mask,errors=errors,
                inherited_RF_and_shields_unchanged=True,
                scope='Independent local native-grid GND subset and new-signal clearance proof; retained baseline RF geometry and mask families. Full saved connectivity, via geometry, DRC and paste remain separate.')
    (H/'independent_alignment_surfaces.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
