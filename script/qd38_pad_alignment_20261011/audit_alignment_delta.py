"""Saved physical alignment, immutable-source and declared-rule delta audit."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,math,re,sys
import olefile
from shapely.geometry import Point,Polygon,shape,box
from shapely.ops import unary_union

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
OLD=ROOT/'script/qd38_rotation_20261011'
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(OLD))
from audit_saved_revision_surface import read_snapshot
from prepare_native_revision_rules import read_rules
from alignment_invariants import declaration,via_groups,assert_plan_contacts
sys.path.insert(0,str(ROOT/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,pads_stream,UNIT
from diagnose_pad_cache_identity import keyed as keyed_native_pads

BASE_SHA='1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
BASE_CANDIDATE_SHA='835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BOUNDARIES={'LEFT':(0,7.4,1),'RIGHT':(0,12.1,-1),'BOTTOM':(1,39.65,1),'TOP':(1,45.35,-1)}

def mm(value):
    match=re.fullmatch(r'([-+0-9.eE]+)(mil|mm)',value)
    assert match,value
    return float(match[1])*(.0254 if match[2]=='mil' else 1)

def inspect_rules(plan,native_path):
    manifest=declaration(plan)
    before=read_rules(H/'before_alignment/QSTL_QD4_2SET_38PAD.PcbDoc')
    saved=read_rules(native_path)
    declared={(x['name'],x['field']):x for x in manifest['allowed_rule_changes']}
    assert len(declared)==len(manifest['allowed_rule_changes'])
    failures=[];changed=[];used=set()
    if before.keys()!=saved.keys():failures.append(dict(issue='rule_names_changed'))
    for name,old in before.items():
        new=saved.get(name,{})
        for field in old.keys()|new.keys():
            if old.get(field)==new.get(field):continue
            entry=declared.get((name,field))
            if entry is None:failures.append(dict(issue='undeclared_rule_change',name=name,field=field,before=old.get(field),after=new.get(field)));continue
            used.add((name,field))
            assert entry['before']==old.get(field), 'Declared rule baseline is stale'
            ok=abs(mm(new[field])-entry['after_mm'])<1e-5 if 'after_mm' in entry else new.get(field)==entry['after']
            if not ok:failures.append(dict(issue='declared_rule_value_mismatch',name=name,field=field))
            changed.append(dict(name=name,field=field,before=old[field],after=new.get(field)))
    if used!=set(declared):failures.append(dict(issue='declared_rule_change_not_observed',unused=sorted(set(declared)-used)))
    # A geometry-only alignment normally changes no rule. A smaller QD land
    # requires three explicit width changes, never a looser general rule.
    land=manifest['qd_endpoint_via']['land_mm']
    if land!=.4:
        required={('QD38_QD_VIA_0P4_0P2',f) for f in ('WIDTH','MINWIDTH','MAXWIDTH')}
        if not required<=set(declared):failures.append(dict(issue='QD_land_rule_change_not_declared'))
    for name,field in declared:
        if name!='QD38_QD_VIA_0P4_0P2' or field not in ('WIDTH','MINWIDTH','MAXWIDTH','SCOPE1EXPRESSION'):
            failures.append(dict(issue='rule_delta_outside_QD_via_scope',name=name,field=field))
    row=saved['QD38_QD_VIA_0P4_0P2']
    for field,wanted in (('WIDTH',land),('MINWIDTH',land),('MAXWIDTH',land),('HOLEWIDTH',.2),('MINHOLEWIDTH',.2),('MAXHOLEWIDTH',.2)):
        if abs(mm(row[field])-wanted)>1e-5:failures.append(dict(issue='QD_rule_dimension_mismatch',field=field))
    match=re.search(r'InRegionAbsolute\(([^)]+)\)',row['SCOPE1EXPRESSION'])
    assert match,'No explicit QD via spatial rule scope'
    bounds=[float(x)*.0254 for x in match[1].split(',')]
    for v in plan['vias']:
        if v['label'].startswith('Q1-') and not(bounds[0]<=v['x']<=bounds[2] and bounds[1]<=v['y']<=bounds[3] and f"InNet('{v['net']}')" in row['SCOPE1EXPRESSION']):
            failures.append(dict(issue='QD_via_outside_saved_rule_scope',via=v['label']))
    return dict(passed=not failures,native_sha256=sha(native_path),candidate_sha256=manifest['candidate_sha256'],baseline_sha256=BASE_SHA,
                saved_rule_count=len(saved),declared_changes=changed,all_unrelated_rules_unchanged=not failures,failures=failures)

def main(candidate):
    plan=json.loads(candidate.read_text());manifest=declaration(plan)
    native_path=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc';baseline=H/'before_alignment/QSTL_QD4_2SET_38PAD.PcbDoc'
    native_hash=sha(native_path);candidate_hash=sha(candidate)
    assert sha(baseline)==BASE_SHA and native_hash!=BASE_SHA,'Alignment not saved or baseline changed'
    oldpath=H/'before_alignment/full_copper_candidate.json';assert sha(oldpath)==BASE_CANDIDATE_SHA
    old=json.loads(oldpath.read_text());assert_plan_contacts(plan);groups=via_groups(plan)
    failures=[]
    def check(ok,issue,detail=None):
        if not ok:failures.append(dict(issue=issue,detail=detail))
    for field in ('nets','pinmap','components','sample_center','cavity_mm','cavity_depth_mm','board_outline','pad_solder_mask_overrides'):
        check(plan[field]==old[field],'unexpected_candidate_delta',field)
    unrelated_pads=lambda p:[x for x in p['physical_pads'] if x['ref']!='Q1']
    unrelated_vias=lambda p:[x for x in p['vias'] if not x['label'].startswith('Q1-')]
    check(unrelated_pads(plan)==unrelated_pads(old),'non_QD_candidate_pads_changed')
    check(unrelated_vias(plan)==unrelated_vias(old),'non_QD_endpoint_vias_changed')
    freeze=json.loads((H/'before_alignment/manifest.json').read_text());sources={}
    immutable={'QSTL_QD4_2SET_38PAD.SchDoc','QSTL_QD4_2SET_38PAD.SchLib','QSTL_QD4_2SET_38PAD.PrjPcb','pin_mapping.csv'}
    for entry in freeze['files']:
        check(sha(Path(entry['backup']))==entry['sha256'],'baseline_backup_changed',entry['backup'])
        if Path(entry['source']).name in immutable:
            sources[Path(entry['source']).name]=sha(Path(entry['source']))==entry['sha256']
    check(all(sources.values()),'schematic_project_or_pinmap_changed',sources)
    sch=json.loads((DEST/'schematic_validation.json').read_text())
    pads,regions,tracks,vias,board=read_snapshot(native_path,sch)
    bp,br,bt,bv,bb=read_snapshot(baseline,sch)
    qd={p['pin']:p for p in pads if p['ref']=='Q1'}
    oldmeta={str(p['number']):p for p in old['pads']}
    oldphysical={p['pin']:p for p in old['physical_pads'] if p['ref']=='Q1'}
    cavity=box(7.6,39.85,11.9,45.15)
    alignment=[]
    for pin,p in qd.items():
        meta=oldmeta[pin];side=meta['side']
        if side=='CORNER':side='TOP' if meta['normal'][1]>0 else 'BOTTOM'
        axis,line,sign=BOUNDARIES[side]
        coords=list(p['geometry'].exterior.coords)[:-1]
        actual=max(z[axis] for z in coords) if sign>0 else min(z[axis] for z in coords)
        base=oldphysical[pin];ux,uy=meta['normal'];dx=p['x']-meta['absolute_chip'][0];dy=p['y']-meta['absolute_chip'][1]
        item=dict(pin=pin,side=side,target_mm=line,actual_mm=actual,error_mm=abs(actual-line),
                  cavity_gap_mm=p['geometry'].distance(cavity),bond_ray_cross_error_mm=abs(dx*uy-dy*ux))
        check(abs(actual-line)<1e-5,'QD_common_inner_extent_failed',item)
        check(item['cavity_gap_mm']>=.2-1e-5,'QD_cavity_clearance_failed',item)
        check(item['bond_ray_cross_error_mm']<1e-5,'QD_bond_ray_changed',item)
        check(abs(p['sx']-.8)<1e-5 and abs(p['sy']-.25)<1e-5 and p['shape']==2,'QD_size_or_shape_changed',pin)
        check(abs((p['rotation']-base['rotation']+180)%360-180)<1e-7,'QD_angle_changed',pin)
        check(p['net']==base['net'] and p['layer']==32,'QD_net_or_layer_changed',pin)
        alignment.append(item)
    check(len(alignment)==38,'QD_pad_count')
    for v in groups['direct_qd']:
        pin=v['label'].split('-')[1];p=qd[pin]
        actual=[a for a in vias if a['net']==v['net'] and a['y']>8]
        check(len(actual)==1,'QD_endpoint_via_count',pin)
        if len(actual)!=1:continue
        a=actual[0];drill=Point(a['x'],a['y']).buffer(a['hole']/2,quad_segs=128)
        check(p['geometry'].buffer(1e-5).covers(drill),'QD_drill_outside_pad',pin)
        check(abs(a['diameter']-manifest['qd_endpoint_via']['land_mm'])<1e-5 and abs(a['hole']-.2)<1e-5 and (a['low'],a['high'])==(1,32),'QD_endpoint_geometry',pin)
    # Inspect opaque pad records too: changing XY may not change masks, paste,
    # identity, ownership, size, shape or any other stored pad attribute.
    # Native net rebuild may reorder the serialization, so compare by stable
    # SourceUniqueID and terminal number; free mounts additionally use XY.
    raw=[keyed_native_pads(path) for path in (baseline,native_path)]
    check(len(raw[0])==len(raw[1])==243 and raw[0].keys()==raw[1].keys(),'raw_pad_membership')
    mask_changed=[];unexpected_pad_bytes=[];pad_xy_changes=[]
    for key,a in raw[0].items():
        if key not in raw[1]:continue
        b=raw[1][key]
        is_qd=key[0].strip('\\')==sch['components']['Q1']
        changed=[]
        for index,(x,y) in enumerate(zip(a['blocks'],b['blocks'])):
            check(len(x)==len(y),'raw_pad_block_length_changed',dict(pad=key,block=index))
            changed.extend((index,i) for i,(u,v) in enumerate(zip(x,y)) if u!=v)
        unexpected=[offset for offset in changed if not(is_qd and offset[0]==4 and 13<=offset[1]<21)]
        if unexpected:unexpected_pad_bytes.append(dict(pad=key,offsets=unexpected))
        if changed:pad_xy_changes.append(dict(pad=key,changed_bytes=len(changed)))
        if a['blocks'][4][60:]!=b['blocks'][4][60:] or a['blocks'][5]!=b['blocks'][5]:
            mask_changed.append(list(key))
    check(not unexpected_pad_bytes,'non_XY_saved_pad_bytes_changed',unexpected_pad_bytes)
    check(not mask_changed,'pad_cache_or_tail_changed',mask_changed)
    oldmodels=json.loads((OLD/'saved_revision_models.json').read_text());newmodels=json.loads((H/'saved_revision_models.json').read_text())
    check(oldmodels['native_sha256']==BASE_SHA,'model_baseline_hash')
    byref=lambda data:{r['component']:{k:v for k,v in r.items() if k!='origin_error_mm'} for r in data['models']}
    check(byref(oldmodels)==byref(newmodels),'models_or_transforms_changed')
    # All local routing/surface edits must be declared, not inferred after
    # looking at differences. Arc tessellation in this reader has a0.1um
    # chord-error bound; allow twice that plus native coordinate rounding.
    edit=shape(manifest['edit_region']);assert edit.is_valid and not edit.is_empty
    assert manifest['inner_alignment']=='nearest_corner_per_side'
    assert manifest['outer_alignment']=='not_requested'
    def copper(pads,tracks):
        result=defaultdict(list)
        for p in pads:
            if p['net'] and p['net']!='GND':
                for layer in ((1,2,3,4,5,32) if p['layer']==74 else (p['layer'],)):
                    result[p['net'],layer].append(p['geometry'])
        for t in tracks:
            if t['net'] and t['net']!='GND':result[t['net'],t['layer']].append(t['geometry'].buffer(t['width']/2,quad_segs=96))
        return {k:unary_union(v).difference(edit) for k,v in result.items()}
    oldc,newc=copper(bp,bt),copper(pads,tracks);local=[]
    for key in oldc.keys()|newc.keys():
        a=oldc.get(key,Polygon());b=newc.get(key,Polygon())
        added=b.difference(a.buffer(.00021)).area;removed=a.difference(b.buffer(.00021)).area
        if added>1e-8 or removed>1e-8:local.append(dict(net=key[0],layer=key[1],added_mm2=added,removed_mm2=removed))
    check(not local,'signal_edit_outside_declared_region',local)
    surfaces=[]
    for layer in (1,2,3,4,5,32,37,38):
        select=lambda rows:unary_union([r['geometry'] for r in rows if r['layer']==layer and (layer in (37,38) or r['net']=='GND')]).difference(edit)
        a,b=select(br),select(regions)
        added=b.difference(a.buffer(.003)).area;removed=a.difference(b.buffer(.003)).area
        if added>1e-8 or removed>1e-8:surfaces.append(dict(layer=layer,added_mm2=added,removed_mm2=removed))
    check(not surfaces,'surface_edit_outside_declared_region',surfaces)
    shield_key=lambda v:(v['net'],round(v['x']/UNIT),round(v['y']/UNIT),round(v['diameter']/UNIT),round(v['hole']/UNIT),v['low'],v['high'])
    outside_shields=lambda rows:{shield_key(v) for v in rows if v['net']=='GND' and Point(v['x'],v['y']).distance(edit)>v['diameter']/2+1e-5}
    check(outside_shields(bv)==outside_shields(vias),'shield_edit_outside_declared_region')
    check(sha(native_path)==native_hash and sha(candidate)==candidate_hash,'input_changed_during_audit')
    report=dict(passed=not failures,native_sha256=native_hash,candidate_sha256=candidate_hash,baseline_sha256=BASE_SHA,
                declaration_sha256=sha(H/'alignment_delta_manifest.json'),unchanged_sources=sources,alignment=alignment,
                maximum_inner_boundary_error_mm=max(r['error_mm'] for r in alignment),
                minimum_cavity_clearance_mm=min(r['cavity_gap_mm'] for r in alignment),
                declared_QD_endpoint=manifest['qd_endpoint_via'],signal_edits_confined=not local,
                surface_edits_confined=not surfaces,
                all_pad_mask_paste_caches_unchanged=not mask_changed,
                all_other_pad_bytes_unchanged=not unexpected_pad_bytes,
                native_pad_record_order_changed=list(raw[0])!=list(raw[1]),
                pad_XY_byte_changes=pad_xy_changes,failures=failures,completion=False)
    (H/'saved_alignment_delta.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='alignment'},indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':main(Path(sys.argv[1]).resolve())
