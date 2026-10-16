"""Inspect the closest incompatible candidate routes without design mutation."""
import shielded_symmetric_rf_plan_20261016 as m
import pickle
import json
import numpy as np
from itertools import combinations, product
from shapely.ops import nearest_points, substring
data=json.loads(m.base.SOURCE.read_text());groups=m.sym.build_groups(data);st=m.base.build_static(data)
pools=pickle.loads((m.OUT/'candidate_segments.pkl').read_bytes())
for pool in pools:
    for a in pool:
        if a['mode']=='qd':a['tail']=substring(a['line'],m.MAX_LAUNCH_EXCEPTION,a['line'].length)
bad=[]
for i,j in combinations(range(len(pools)),2):
    if {pools[i][0]['channel'],pools[j][0]['channel']}!={'SMP11','SMP12'}:continue
    if pools[i][0]['mode']!='qd' or pools[j][0]['mode']!='qd':continue
    if pools[i][0]['channel']==pools[j][0]['channel']:continue
    best=max(((min(a['tail'].distance(b['line']),b['tail'].distance(a['line'])),a,b) for a,b in product(pools[i],pools[j])),key=lambda q:q[0])
    if best[0]<m.RF_CENTRE_TARGET:
        gap,a,b=best
        print('BAD',a['channel'],a['mode'],b['channel'],b['mode'],gap,flush=True)
        bad.append(best)
for gap,a,b in bad:
    fig,ax=m.base.plt.subplots(figsize=(8,8),dpi=160)
    m.base.paint(ax,data,[],st,(41,56))
    for g in groups:
        for c in (g['capacitor'],g['resistor']):m.base.draw_component(ax,c,'#a98721')
    for c,col in ((a,'red'),(b,'blue')):
        xy=np.array(c['line'].coords);ax.plot(*xy.T,color=col,lw=2,label=c['channel'])
        ax.plot(*np.array(c['tail'].coords).T,color=col,lw=8,alpha=.2)
    aa,bb=nearest_points(a['tail'],b['line']);ax.plot([aa.x,bb.x],[aa.y,bb.y],'k--')
    print('nearest',list(aa.coords),list(bb.coords),'lengths',a['line'].length,b['line'].length,flush=True)
    ax.set_xlim(3,10);ax.set_ylim(32,45);ax.legend();ax.set_title(f'Best centre gap {gap:.4f} mm / target 1.29 mm')
    fig.savefig(m.OUT/f"diagnostic_{a['channel']}_{b['channel']}.png");m.base.plt.close(fig)
    break
