"""Freeze the saved baseline and measure the user's circled RF approaches."""
from pathlib import Path
import sys,json,shutil,hashlib
import numpy as np
from itertools import combinations
from shapely.geometry import Point,box
from shapely.ops import nearest_points
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';B=H/'baseline';B.mkdir(exist_ok=True)
sys.path[:0]=[str(ROOT/'script/rf_redline_review_20261011'),str(ROOT/'script/native_16rf_apply_20261016')]
import finalize_shielded_rf_20261016 as f
import build_candidate as bc
for src in [P/'QSTL_QD4_2SET_38PAD.PcbDoc',P/'QSTL_QD4_2SET_38PAD.SchDoc',P/'pin_mapping.csv',ROOT/'script/native_16rf_apply_20261016/candidate.json',P/'Shielded_Symmetric_RF_Plan_20261016/routing_working.json']:
    dst=B/src.name
    if not dst.exists():shutil.copy2(src,dst)
data,groups,st=f.load_routes();p=json.loads((B/'candidate.json').read_text())
for xy in ((6.2,41.2),(14.3,44.4)):
    window=Point(xy).buffer(1.2)
    near=[g for g in groups if g['qline'].distance(Point(xy))<2]
    print('CIRCLE',xy,[(g['row']['smp'],g['row']['rf_net'],g['row']['qd_pad'],g['qline'].distance(Point(xy))) for g in near])
    for a,b in combinations(near,2):
        la=a['qline'].intersection(window);lb=b['qline'].intersection(window)
        if la.is_empty or lb.is_empty:continue
        print('GAP',a['row']['smp'],b['row']['smp'],la.distance(lb)-.11,[list(z.coords) for z in nearest_points(la,lb)])
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Circle
fig,axes=plt.subplots(1,2,figsize=(15,8))
for ax,lim in zip(axes,[(3.5,8,38.5,44.5),(12,16.5,42,48)]):
    ax.set_facecolor('#10252e')
    for d in p['physical_pads']:
        if d['layer']==32:
            z=bc.pg(d);ax.add_patch(Polygon(z.exterior.coords,fc='#cdaa5e'))
            if d['ref'] in ('Q1','R11','R24','R28','R02'):ax.text(d['x'],d['y'],d['ref']+'-'+d['pin'],fontsize=7,color='white')
    for g in groups:
        for k in ('qline','sline'):
            ax.plot(*g[k].xy,lw=1.6,label=g['row']['smp'] if k=='qline' else None)
        z=g['qline'].intersection(box(lim[0],lim[2],lim[1],lim[3]))
        if not z.is_empty:
            pt=z.interpolate(.65,normalized=True);ax.text(pt.x,pt.y,g['row']['rf_net'],color='white',fontsize=10)
    for v in p['shield_vias']:ax.add_patch(Circle((v['x'],v['y']),.125,fc='#526d76'))
    ax.set(xlim=lim[:2],ylim=lim[2:]);ax.set_aspect('equal');ax.grid(alpha=.1)
fig.savefig(H/'baseline_closeups.png',dpi=180);plt.close(fig)
print('Source',hashlib.sha256((B/'QSTL_QD4_2SET_38PAD.PcbDoc').read_bytes()).hexdigest())
