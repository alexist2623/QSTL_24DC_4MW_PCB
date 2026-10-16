"""Compare dual QD pad-boundary constructions without changing native designs."""
from pathlib import Path
import hashlib
import json
import math
from copy import deepcopy
from shapely.geometry import Polygon, Point, box, mapping
from shapely.affinity import rotate, translate

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SRC = ROOT / 'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json'
META = ROOT / 'QSTL_QD4_2SET_38PAD/full_copper_candidate.json'
BASE = '9607d5bfbdd962c49c9a6d4ecce671a4de9f5552322f134225bcbadf5796e351'
BOUND = {'LEFT': (0, 7.4, -1), 'RIGHT': (0, 12.1, 1),
         'BOTTOM': (1, 39.65, -1), 'TOP': (1, 45.35, 1)}


def pg(p):
    return translate(rotate(box(-p['size_x']/2, -p['size_y']/2,
                                p['size_x']/2, p['size_y']/2),
                            p['rotation'], origin=(0, 0)), p['x'], p['y'])


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    s = json.loads(SRC.read_text())
    meta = {str(p['number']): p for p in json.loads(META.read_text())['pads']}
    assert s['source_sha256'] == BASE and sha(Path(s['source'])) == BASE
    qd = [p for p in s['pads'] if p['component'] == 'Q1']
    cavity = box(7.6, 39.85, 11.9, 45.15)
    trials = []
    for depth in (.75, .78, .8, .82, .84, .85):
        for mode in ('rectangle_extrema', 'flat_end_faces'):
            rows = []
            for p in qd:
                m = meta[p['number']]
                side = m['side']
                if side == 'CORNER':
                    side = 'TOP' if m['normal'][1] > 0 else 'BOTTOM'
                axis, inner, sign = BOUND[side]
                angle = math.radians(p['rotation'])
                u = [math.cos(angle), math.sin(angle)]
                if u[axis]*sign < 0:
                    u = [-x for x in u]
                v = [-u[1], u[0]]
                c = [p['x'], p['y']]
                width = p['size_y']
                length = (depth-width*abs(v[axis]))/abs(u[axis])
                mid = inner+sign*depth/2
                t = (mid-c[axis])/u[axis]
                after = deepcopy(p)
                after.update(x=c[0]+t*u[0], y=c[1]+t*u[1], size_x=length)
                if mode == 'rectangle_extrema':
                    geom = pg(after)
                else:
                    pts = []
                    for bound, off in ((inner, -width/2),
                                       (inner+sign*depth, -width/2),
                                       (inner+sign*depth, width/2),
                                       (inner, width/2)):
                        t = (bound-c[axis]-off*v[axis])/u[axis]
                        pts.append([c[k]+t*u[k]+off*v[k] for k in (0, 1)])
                    geom = Polygon(pts)
                rows.append(dict(number=p['number'], net=p['net'], side=side,
                                 before=p, after=after, polygon=mapping(geom),
                                 removed_mm2=pg(p).difference(geom).area,
                                 added_mm2=geom.difference(pg(p)).area))
            geos = {r['number']: Polygon(r['polygon']['coordinates'][0]) for r in rows}
            pairs = [(a.distance(geos[nb]), na, nb) for na, a in geos.items()
                     for nb in geos if int(na) < int(nb)]
            vgap = []
            vcontain = []
            for via in s['vias']:
                if via['net'] == 'GND':
                    continue
                for p in qd:
                    if via['net'] != p['net']:
                        vgap.append((Point(via['x'], via['y']).distance(geos[p['number']])-via['diameter']/2,
                                     p['number'], via['net']))
                    elif abs(via['x']-p['x'])<1 and abs(via['y']-p['y'])<1:
                        vcontain.append(dict(pad=p['number'], contained=geos[p['number']].buffer(1e-7).covers(
                            Point(via['x'], via['y']).buffer(via['hole']/2, quad_segs=128))))
            trials.append(dict(mode=mode, depth_mm=depth, pad_pair_min=min(pairs),
                               foreign_via_min=min(vgap), cavity_gap=min(g.distance(cavity) for g in geos.values()),
                               via_drills_contained=all(v['contained'] for v in vcontain),
                               length_range=[min(r['after']['size_x'] for r in rows),max(r['after']['size_x'] for r in rows)],
                               rows=rows))
    result=dict(source_sha256=BASE, source_snapshot_sha256=sha(SRC), trials=trials)
    (OUT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in t.items() if k!='rows'} for t in trials],indent=2))


if __name__ == '__main__':
    main()
