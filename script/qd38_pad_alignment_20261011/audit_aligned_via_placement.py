"""Independent native-grid audit of an offline aligned pad/via proposal only."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,math,sys
from shapely.affinity import rotate,translate
from shapely.geometry import Point,box

H=Path(__file__).resolve().parent
UNIT=2.54e-6
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def pg(p):
    if p['shape']=='rect':return translate(rotate(box(-p['sx']/2,-p['sy']/2,p['sx']/2,p['sy']/2),p['rotation'],origin=(0,0)),p['x'],p['y'])
    assert abs(p['sx']-p['sy'])<1e-8
    return Point(p['x'],p['y']).buffer(p['sx']/2,quad_segs=256)

def quantized(rows,fields):
    result=deepcopy(rows)
    for p in result:
        for field in fields:p[field]=round(p[field]/UNIT)*UNIT
    return result

def main():
    source=H/'before_alignment/full_copper_candidate.json'
    candidate=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else H/'aligned_qd_vias_land_0p35_candidate.json'
    old=json.loads(source.read_text());p=json.loads(candidate.read_text());candidate_hash=sha(candidate)
    assert sha(source)==p['source_candidate_sha256']
    q=quantized(p['qd_pads'],('x','y','sx','sy','hole'))
    v=quantized(p['qd_vias'],('x','y','diameter','hole'))
    others=quantized([x for x in old['physical_pads'] if x['ref']!='Q1'],('x','y','sx','sy','hole'))
    otherv=quantized([x for x in old['vias'] if not x['label'].startswith('Q1-')],('x','y','diameter','hole'))
    padgeo=[(x,pg(x)) for x in q+others];qp={x['pin']:pg(x) for x in q}
    minpad=(float('inf'),None);minvia=(float('inf'),None);minhole=(float('inf'),None);bad=[]
    for a in v:
        pin=a['label'].split('-')[1];xy=Point(a['x'],a['y']);drill=xy.buffer(a['hole']/2,quad_segs=256)
        if not qp[pin].buffer(1e-7).covers(drill):bad.append(dict(issue='drill_not_contained',pin=pin,missing_mm2=drill.difference(qp[pin]).area))
        for b,g in padgeo:
            if a['net']==b['net']:continue
            gap=xy.distance(g)-a['diameter']/2
            if gap<minpad[0]:minpad=(gap,[a['label'],b['ref'],b['pin']])
        for b in v+otherv:
            if a['label']==b['label']:continue
            d=math.dist([a['x'],a['y']],[b['x'],b['y']])
            gap=d-(a['diameter']+b['diameter'])/2
            hg=d-(a['hole']+b['hole'])/2
            if gap<minvia[0]:minvia=(gap,[a['label'],b['label']])
            if hg<minhole[0]:minhole=(hg,[a['label'],b['label']])
    if minpad[0]<.15:bad.append(dict(issue='pad_clearance',detail=minpad))
    if minvia[0]<.15:bad.append(dict(issue='land_clearance',detail=minvia))
    if minhole[0]<.254:bad.append(dict(issue='drill_clearance',detail=minhole))
    assert len(q)==38 and len(v)==22
    report=dict(passed=not bad,candidate_sha256=candidate_hash,source_candidate_sha256=sha(source),
                native_grid_mm=UNIT,pad_count=38,QD_endpoint_count=22,nominal_QD_land_mm=p['via_land_mm'],nominal_QD_drill_mm=p['via_drill_mm'],
                minimum_foreign_pad_clearance=minpad,minimum_foreign_via_land_clearance=minvia,minimum_drill_clearance=minhole,
                drill_containment_passed=not any(x['issue']=='drill_not_contained' for x in bad),failures=bad,
                scope='Offline aligned38pads/22endpointvias after native-grid quantization. Existing routes, GND/shields, masks, canonical library and actual native DRC are not certified by this report.')
    assert sha(candidate)==candidate_hash
    (H/'independent_aligned_via_placement.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if bad:raise SystemExit(1)

if __name__=='__main__':main()
