"""Render actual candidate geometry for engineering review, never a mock-up."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPolygon, Circle, Rectangle
from route_rf_rotated import pgeom, arc_line

H = Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--plan', type=Path, default=H/'placement_candidate.json')
    ap.add_argument('--progress', action='store_true')
    ap.add_argument('--progress-file', type=Path)
    ap.add_argument('--output', type=Path, default=H/'routing_review.png')
    args=ap.parse_args()
    p=json.loads(args.plan.read_text())
    tracks=list(p.get('tracks', []));arcs=list(p.get('arcs', []))
    if args.progress or args.progress_file:
        rf=json.loads((args.progress_file or H/'rf_progress.json').read_text())
        tracks += [t for r in rf['routes'] if r for t in r['tracks']]
        arcs += [a for r in rf['routes'] if r for a in r['arcs']]
    fig,ax=plt.subplots(figsize=(12,15),dpi=140)
    ax.set_facecolor('#151b22')
    for pad in p['physical_pads']:
        if pad['layer'] not in (32,74):continue
        g=pgeom(pad)
        ax.add_patch(MPolygon(list(g.exterior.coords),facecolor='#8f8f8f' if pad['net']=='GND' else '#cca751',edgecolor='none',alpha=.65))
        if pad['ref']=='Q1':
            ax.text(pad['x'],pad['y'],pad['pin'],color='white',fontsize=6,ha='center',va='center')
    palette=plt.get_cmap('tab20')
    def color(net):
        digits=''.join(c for c in net if c.isdigit())
        return palette(int(digits or 0)%20)
    for t in tracks:
        if t['layer']!=32:continue
        ax.plot([t['a'][0],t['b'][0]],[t['a'][1],t['b'][1]],color=color(t['net']),lw=1.3)
    for a in arcs:
        g=arc_line(a);xx,yy=g.xy
        ax.plot(xx,yy,color=color(a['net']),lw=1.3)
    for via in p['vias']:
        ax.add_patch(Circle((via['x'],via['y']),via['diameter']/2,color='#bb5555',alpha=.7))
    for c in p['components']:
        if c['ref']=='J1' or c['ref']=='Q1':continue
        ax.text(c['x'],c['y']+.25,c['ref'],fontsize=6,color='white',ha='center')
    cx,cy=p['sample_center'];w,h=p['cavity_mm']
    ax.add_patch(Rectangle((cx-w/2,cy-h/2),w,h,facecolor='#303030',edgecolor='white',ls='--'))
    ax.set(xlim=(0,19.5),ylim=(22,64),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)',title='Bottom copper: provisional routed geometry')
    fig.tight_layout();fig.savefig(args.output);plt.close(fig)

if __name__=='__main__':main()
