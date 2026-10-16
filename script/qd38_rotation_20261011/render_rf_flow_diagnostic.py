"""Render offline RF flow paths and terminal conflicts for routing review."""
from pathlib import Path
import argparse
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
from shapely.geometry import LineString
from shapely.ops import nearest_points
from route_rf_corridor_bounded import pgeom

H=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--flow',type=Path,required=True)
parser.add_argument('--placement',type=Path,default=H/'placement_lower_over_smp_candidate.json')
parser.add_argument('--output',type=Path,default=H/'rf_flow_diagnostic.png')
args=parser.parse_args()
flow=json.loads(args.flow.read_text());plan=json.loads(args.placement.read_text())
fig,ax=plt.subplots(figsize=(11,17))
for pad in plan['physical_pads']:
    if pad['layer'] not in (32,74):continue
    geom=pgeom(pad)
    ax.add_patch(Patch(list(geom.exterior.coords),facecolor='#c0b387',edgecolor='#6b644e',alpha=.55,lw=.4))
    if pad['ref']=='Q1' and str(pad['net']).startswith('MW'):
        ax.text(pad['x'],pad['y'],pad['pin'],fontsize=7,zorder=10)
for component in plan['components']:
    if str(component['ref']).startswith('R'):
        ax.text(component['x'],component['y']+.35,component['ref'],fontsize=7,color='#323232')
routes=flow['routes'];colors=plt.get_cmap('tab20')
for i,route in enumerate(routes):
    xy=route['points'];x,y=zip(*xy)
    ax.plot(x,y,lw=1.4,color=colors(i),label=f"R{route['group']:02} -> QD{route['target']}")
    ax.scatter([x[0],x[-1]],[y[0],y[-1]],s=15,color=[colors(i)])
for i,a in enumerate(routes):
    for b in routes[i+1:]:
        aa,bb=LineString(a['points']),LineString(b['points'])
        gap=aa.distance(bb)-.11
        if gap<.15-1e-7:
            ap,bp=nearest_points(aa,bb);x=(ap.x+bp.x)/2;y=(ap.y+bp.y)/2
            ax.plot(x,y,'rx',ms=10)
            ax.annotate(f"{a['group']}/{b['group']} {gap:.3f}",(x,y),xytext=(7,7),textcoords='offset points',fontsize=7,color='red')
ax.set(xlim=(0,19.5),ylim=(22,62),aspect='equal',xlabel='X / mm',ylabel='Y / mm')
ax.grid(alpha=.15);ax.legend(loc='upper right',fontsize=7,ncol=2)
ax.set_title('Offline RF flow diagnostic - not a finished PCB')
fig.savefig(args.output,dpi=140,bbox_inches='tight');plt.close(fig)
print(args.output)
