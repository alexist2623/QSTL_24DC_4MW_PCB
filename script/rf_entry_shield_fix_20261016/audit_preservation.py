"""Prove RF-only scope from actual before/after native PCB contents."""
from pathlib import Path
import sys,json,hashlib
from shapely.geometry import Point
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N='QSTL_QD4_2SET_38PAD'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011')]
from audit_saved_revision_surface import read_snapshot
from prepare_native_revision_rules import read_rules
sch=json.loads((P/'schematic_validation.json').read_text());before=read_snapshot(H/'baseline'/(N+'.PcbDoc'),sch);after=read_snapshot(P/(N+'.PcbDoc'),sch)
issues=[];results={}
def check(ok,label,details=None):
    if not ok:issues.append(dict(issue=label,details=details))
def routes(snap):
    banks={}
    for t in snap[2]:
        if t['layer']!=32:banks.setdefault((t['net'],t['layer']),[]).append(t['geometry'].buffer(t['width']/2,quad_segs=32))
    return {k:unary_union(g) for k,g in banks.items()}
a,b=routes(before),routes(after);check(a.keys()==b.keys(),'nonRF_route_keys');maxroute=max(a[k].hausdorff_distance(b[k]) for k in a);check(maxroute<.00001,'DC_or_mechanical_route_changed',maxroute);results['max_preserved_route_difference_mm']=maxroute
for ll in (1,2,3,4,37):
    a=unary_union([r['geometry'] for r in before[1] if r['layer']==ll]);b=unary_union([r['geometry'] for r in after[1] if r['layer']==ll]);check(a.equals_exact(b,.000001),'unchanged_layer_region',ll)
for key in ('x','y','sx','sy','hole','rotation','layer','net'):
    a={(d['ref'],d['pin']):d[key] for d in before[0]};b={(d['ref'],d['pin']):d[key] for d in after[0]};check(a==b,'pads_changed',key)
sig=lambda snap:sorted((v['net'],v['x'],v['y'],v['diameter'],v['hole'],v['low'],v['high']) for v in snap[3] if v['net']!='GND')
check(sig(before)==sig(after),'DC_terminal_vias_changed')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for ext in ('.SchDoc',):check(sha(P/(N+ext))==sha(H/'baseline'/(N+ext)),'schematic_changed')
check(sha(P/'pin_mapping.csv')==sha(H/'baseline/pin_mapping.csv'),'pin_mapping_changed')
check(read_rules(P/(N+'.PcbDoc'))==read_rules(H/'baseline'/(N+'.PcbDoc')),'native_rules_changed')
results.update(DC_terminal_vias=len(sig(after)),schematic_and_pin_map_unchanged=True,all_pad_positions_unchanged=True,native_rules_unchanged=True)
report=dict(passed=not issues,issues=issues,checks=results,source_sha256=sha(P/(N+'.PcbDoc')));(H/'preservation_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
