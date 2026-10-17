"""Check fitted copper and every foreign pad/via before native application."""
from pathlib import Path
import sys,json
from itertools import combinations
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path[:0]=[str(ROOT/'script/native_16rf_apply_20261016')]
import build_candidate as bc
p=json.loads((H/'candidate.json').read_text());g={}
for t in p['tracks']:
    if t['layer']==32:g.setdefault(t['net'],[]).append(LineString([t['a'],t['b']]))
for a in p['arcs']:g.setdefault(a['net'],[]).append(LineString(bc.sample(dict(a,line=False))))
g={n:unary_union(v) for n,v in g.items()};errors=[];rows=[]
for n,line in g.items():
    foreign=unary_union([bc.pg(d) for d in p['physical_pads'] if d['net']!=n and d['layer'] in (32,74)])
    v=unary_union([Point(d['x'],d['y']).buffer(d['diameter']/2) for d in p['vias'] if d['net']!=n])
    a,b=line.distance(foreign)-.055,line.distance(v)-.055
    rows.append(dict(net=n,foreign_pad_gap_mm=a,foreign_via_gap_mm=b))
    if min(a,b)<.1999:errors.append(rows[-1])
pair=min((a.distance(b)-.11,na,nb) for (na,a),(nb,b) in combinations(g.items(),2))
if pair[0]<.1999:errors.append(dict(foreign_RF_pair=pair))
report=dict(passed=not errors,errors=errors,minimum_RF_pair=pair,rows=rows)
(H/'fitted_copper_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert not errors
