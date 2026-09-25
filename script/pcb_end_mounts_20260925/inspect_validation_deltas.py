"""Inspect native serialization differences and mounting contact coverage."""
exec((__import__('pathlib').Path(__file__).with_name('verify_saved.py')).read_text().split('errors=[]')[0])
from shapely.ops import unary_union
from shapely.geometry import Point
r0={r['NAME']:r for r in read_rules(before['Rules6/Data'])}; r1={r['NAME']:r for r in read_rules(after['Rules6/Data'])}
print('RULE SETS',r0.keys()==r1.keys())
for name in r0:
    changes={k:(r0[name].get(k),r1[name].get(k)) for k in r0[name].keys()|r1[name].keys() if r0[name].get(k)!=r1[name].get(k)}
    if changes:print(name,changes)
a,b=before['Texts6/Data'],after['Texts6/Data']
print('TEXT LENGTHS',len(a),len(b),'FIRST DIFFS',[(i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y][:40])
polys=properties(after['Polygons6/Data']);rs=read_regions(after['Regions6/Data'])
print('POLYGONS',[(i,p['LAYER'],{k:v for k,v in p.items() if k.startswith(('VX','VY'))}) for i,p in enumerate(polys)])
for layer in (1,2,3,4,5,32):
    gg=unary_union([r['geometry'] for r in rs if r['layer']==layer and r['polygon_index']!=65535])
    print('CONTACT',layer,gg.bounds,[(deg,round(gg.distance(Point(1.6+1.1*math.cos(math.radians(deg)),1.2+1.1*math.sin(math.radians(deg)))),6)) for deg in range(0,360,15)])
print('VIA LOG PREVIOUS', (H.parent/'dwg_gerber_refresh_20260924/native_paste_audit.txt').read_text().splitlines()[-5:])
