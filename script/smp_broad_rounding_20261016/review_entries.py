"""Review every SMP approach before deciding which entries may be changed."""
from pathlib import Path
import sys,json,math
import numpy as np
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path[:0]=[str(ROOT/'script/native_16rf_apply_20261016')]
import build_candidate as bc
p=json.loads((H/'baseline/candidate.json').read_text());gs=json.loads((H/'entry_routes.json').read_text())['groups'];vv=json.loads((H/'trial_shield_records.json').read_text())['vias']
fig,axes=plt.subplots(4,4,figsize=(16,16));rows=[]
for ax,g in zip(axes.flat,gs):
    n=g['row']['smp'];cx,cy=g['row']['start'];line=LineString(g['smp_to_c1']);ax.set_facecolor('#10252e')
    for d in p['physical_pads']:
        z=bc.pg(d)
        if Point(cx,cy).distance(z)<5:
            ax.add_patch(Polygon(z.exterior.coords,fc='#c1a964' if d['net']!='GND' else '#53737c'))
            if d['hole']:ax.add_patch(Circle((d['x'],d['y']),d['hole']/2,fc='#10252e'))
    ax.plot(*line.xy,c='#ffb45c',lw=2)
    for v in vv:
        if math.hypot(v['x_mm']-cx,v['y_mm']-cy)<5:
            ax.add_patch(Circle((v['x_mm'],v['y_mm']),.125,fc='#58a18a'));ax.add_patch(Circle((v['x_mm'],v['y_mm']),.05,fc='#10252e'))
    for side in (-1,1):
        ring=np.array([[v['x_mm'],v['y_mm']] for v in vv if v['channel']==n and v['kind']=='SMP ring'])
        row=np.array([[v['x_mm'],v['y_mm']] for v in vv if v['channel']==n and v['kind']==f'C-SMP side {side}'])
        dist=np.linalg.norm(row-np.array([cx,cy]),axis=1);close=row[dist<3.6];close=close[np.argsort(np.linalg.norm(close-[cx,cy],axis=1))]
        step=[min(np.linalg.norm(ring-close[0],axis=1))]+[np.linalg.norm(b-a) for a,b in zip(close[:-1],close[1:])]
        rows.append(dict(channel=n,side=side,count=len(close),max_step_mm=max(step),clear=bool(len(close)>=6 and max(step)<.56)))
    ax.set(xlim=(cx-3.6,cx+3.6),ylim=(cy-3.6,cy+3.6));ax.set_aspect('equal');ax.set_title(n);ax.grid(alpha=.1)
fig.suptitle('Offline SMP-entry review | no native changes yet',fontsize=16);fig.tight_layout();fig.savefig(H/'SMP_entry_review.png',dpi=145)
(H/'entry_review.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
