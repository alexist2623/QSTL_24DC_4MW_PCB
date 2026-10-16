"""Report RF proximity regions without claiming measured impedance."""
from pathlib import Path
import argparse,json,itertools
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,nearest_points
from audit_rf_topology import pgeom,arc_points

H=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('candidate',type=Path)
ap.add_argument('--output',type=Path,default=H/'rf_parallel_regions.json')
args=ap.parse_args();p=json.loads(args.candidate.read_text())
lines={}
for t in p['tracks']:
    if t['layer']==32 and t['net'].startswith(('MW','S')):lines.setdefault(t['net'],[]).append(LineString([t['a'],t['b']]))
for a in p.get('arcs',[]):
    if a['layer']==32 and a['net'].startswith(('MW','S')):lines.setdefault(a['net'],[]).append(LineString(arc_points(a)))
lines={n:unary_union(v) for n,v in lines.items()};copper={n:g.buffer(.055,quad_segs=64) for n,g in lines.items()}
qdfield=unary_union([pgeom(d) for d in p['physical_pads'] if d['ref']=='Q1']).convex_hull
terminal=unary_union([pgeom(d) for d in p['physical_pads'] if d['net'] and d['net'].startswith(('MW','S'))]).buffer(.3)
pair=[]
for a,b in itertools.combinations(sorted(lines),2):
    ga,gb=copper[a],copper[b];gap=ga.distance(gb);na,nb=nearest_points(ga,gb)
    close_a=lines[a].intersection(gb.buffer(.4+.055,quad_segs=64))
    close_b=lines[b].intersection(ga.buffer(.4+.055,quad_segs=64))
    if gap<.8:
        pair.append(dict(a=a,b=b,min_copper_gap_mm=gap,nearest_points_mm=[list(na.coords)[0],list(nb.coords)[0]],
                         nearest_within_QD_field=qdfield.buffer(.001).covers(na) or qdfield.buffer(.001).covers(nb),
                         close_below_0p4mm_edge_gap_length_mm=[close_a.length,close_b.length],
                         close_length_outside_QD_field_mm=[close_a.difference(qdfield).length,close_b.difference(qdfield).length],
                         close_length_outside_terminal_0p3_margin_mm=[close_a.difference(terminal).length,close_b.difference(terminal).length]))
pair.sort(key=lambda r:r['min_copper_gap_mm'])
report=dict(candidate=str(args.candidate.resolve()),scope='Geometric proximity review. A .40 mm copper edge gap is the sum of two .20 mm coplanar clearances before allowing any intervening GND width; it is not an independently approved RF-pair rule or a measured impedance result.',QD_field_bounds_mm=list(qdfield.bounds),minimum_pair=pair[0],pairs=pair)
args.output.write_text(json.dumps(report,indent=2));print(json.dumps(dict(minimum_pair=pair[0],long_close_pairs=[r for r in pair if max(r['close_length_outside_terminal_0p3_margin_mm'])>2]),indent=2))
