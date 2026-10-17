"""Measure fixed-centre QD pad-width limits from saved native geometry."""
from pathlib import Path
import sys,json,hashlib,math
from shapely.geometry import Point,shape
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot,pad_shape
pcb=P/(P.name+'.PcbDoc');sch=json.loads((P/'schematic_validation.json').read_text())
pads,regions,tracks,vias,outline=read_snapshot(pcb,sch)
qd=sorted([p for p in pads if p['ref']=='Q1'],key=lambda p:int(p['pin']))
plan=json.loads((ROOT/'script/compact_masks_20261016/candidate.json').read_text())
cx,cy=plan['sample_center']
from shapely.geometry import box
cavity=box(cx-2.15+.5,cy-2.65+.5,cx+2.15-.5,cy+2.65-.5).buffer(.5,quad_segs=128)
obs={p['pin']:[] for p in qd}
for p in qd:
    for a in pads:
        if a['ref']!='Q1' and a['layer'] in (32,74) and a['net']!=p['net']:
            if a['geometry'].distance(p['geometry'])<1:obs[p['pin']].append((a['geometry'],.15,'pad '+str(a['ref'])+'.'+a['pin']))
    for i,v in enumerate(vias):
        if v['high']==32 and v['net']!=p['net']:
            g=Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=96)
            if g.distance(p['geometry'])<1:obs[p['pin']].append((g,.2 if v['net']=='GND' else .15,'via '+v['net']+' '+str(i)))
    for i,t in enumerate(tracks):
        if t['layer']==32 and t['net'] and t['net']!=p['net']:
            g=t['geometry'].buffer(t['width']/2,quad_segs=48)
            if g.distance(p['geometry'])<1:obs[p['pin']].append((g,.15,'route '+t['net']+' '+str(i)))
    obs[p['pin']].append((cavity,.2,'blind pocket'))
def evaluate(widths):
    pp=[dict(p,sy=widths.get(p['pin'],p['sy'])) for p in qd];geos=[pad_shape(p) for p in pp];checks=[]
    for i,(p,g) in enumerate(zip(pp,geos)):
        for j in range(i+1,len(pp)):
            if p['net']!=pp[j]['net']:checks.append(dict(pad=p['pin'],other='pad Q1.'+pp[j]['pin'],gap=g.distance(geos[j]),limit=.15))
        checks += [dict(pad=p['pin'],other=name,gap=g.distance(a),limit=lim) for a,lim,name in obs[p['pin']]]
    checks.sort(key=lambda r:r['gap']-r['limit']);return checks
actual=[dict(pin=p['pin'],width=p['sy'],length=p['sx'],rotation=p['rotation'],net=p['net']) for p in qd]
assert all(p['sx']>p['sy'] for p in qd)
trials={}
for w in (.25,.26,.27,.28,.3,.32,.35,.4):
    c=evaluate({p['pin']:w for p in qd});bad=[r for r in c if r['gap']<r['limit']-.000012]
    trials[str(w)]=dict(passed=not bad,worst=c[:5],violations=len(bad))
lo,hi=.25,.6
for _ in range(30):
    w=(lo+hi)/2;c=evaluate({p['pin']:w for p in qd})
    if c[0]['gap']-c[0]['limit']>=-.000001:lo=w
    else:hi=w
individual=[]
base_geos={p['pin']:p['geometry'] for p in qd}
for p in qd:
    a,b=.25,.6
    local=obs[p['pin']]+[(base_geos[q['pin']],.15,'pad Q1.'+q['pin']) for q in qd if q['net']!=p['net'] and base_geos[q['pin']].distance(p['geometry'])<1]
    for _ in range(20):
        m=(a+b)/2;g=pad_shape(dict(p,sy=m));margin=min(g.distance(o)-limit for o,limit,name in local)
        if margin>=-.000001:a=m
        else:b=m
    individual.append(dict(pin=p['pin'],width_limit=a))
report=dict(source_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),pads=actual,trials=trials,uniform_limit_mm=lo,limiting=evaluate({p['pin']:lo for p in qd})[:8],individual_limits_with_other_pads_unchanged=individual)
(H/'width_analysis.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('pads','individual_limits_with_other_pads_unchanged')},indent=2))
