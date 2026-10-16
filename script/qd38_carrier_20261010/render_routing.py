"""Render route geometry for inspection, explicitly marking unfinished results."""
from pathlib import Path
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as P,Circle
from design_geometry import DEST,polygon
p=json.loads((DEST/'negotiated_plan.json').read_text())
fig,axes=plt.subplots(1,3,figsize=(13,15))
colors=plt.get_cmap('tab20')
for ax,layer in zip(axes,[32,2,4]):
 ax.set_aspect('equal');ax.set_facecolor('#151d23')
 for d in p['physical_pads']:
  if d['layer'] not in (layer,74):continue
  g=Circle((d['x'],d['y']),d['sx']/2) if d['shape']=='round' else P(list(polygon((d['x'],d['y']),[d['sx'],d['sy']],d['rotation']).exterior.coords))
  g.set_facecolor('#928d6f');ax.add_patch(g)
 for v in p['vias']:
  if v['low']<=layer<=v['high']:ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,color='#827663'))
 for t in p['tracks']:
  if t['layer']!=layer:continue
  n=int(''.join(c for c in t['net'] if c.isdigit()) or '0')
  ax.plot([t['a'][0],t['b'][0]],[t['a'][1],t['b'][1]],c=colors(n%20),lw=.85)
 for j in p['unrouted_jobs']:
  q=j['job']
  if q['layer']==layer:ax.plot([q['a'][0],q['b'][0]],[q['a'][1],q['b'][1]],'r--',lw=.8)
 if layer==32:
  for d in p['physical_pads']:
   if d['ref']=='Q1':ax.text(d['x'],d['y'],d['pin'],fontsize=5,color='white')
 ax.set_xlim(0,19.5);ax.set_ylim(0,67.9);ax.set_title({32:'Bottom: RF / bias tee',2:'L2: DC',4:'L4: DC'}[layer]);ax.grid(alpha=.1)
fig.suptitle('QD38 signal routing candidate — 38 DC + 16 RF bias tees\nGround, shields, masks and native validation pending',fontsize=13)
fig.tight_layout();fig.savefig(DEST/'review/Routing_development.png',dpi=160)
