"""Render measured saved native signal copper without editing design inputs."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
from shapely.geometry import LineString

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
PCB=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'


def main():
    spec=importlib.util.spec_from_file_location('saved_render_reader',ROOT/'script/_support/zif_revision_v2/render_native_layout.py')
    r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
    r.SOURCE=PCB
    sch=json.loads((DEST/'schematic_validation.json').read_text())
    refs={uid:name for name,uid in sch['components'].items()}
    base_props=r.props
    def props(data):
        values=base_props(data)
        for value in values:
            if 'SOURCEUNIQUEID' in value:
                value['SOURCEDESIGNATOR']=refs.get(value['SOURCEUNIQUEID'].strip('\\'),value.get('SOURCEDESIGNATOR'))
        return values
    r.props=props
    native=r.read_native()
    assert len(native['components'])==50
    assert len(native['pads'])==243
    assert not native['arcs'], 'Handle saved native arcs before rendering this board'
    output=DEST/'review';output.mkdir(exist_ok=True)
    colors={1:'#dabf78',2:'#48b9f0',4:'#ef93ca',32:'#f3c878'}
    def draw(ax,layer,limits=None,labels=False):
        ax.set_facecolor('#112b28');ax.set_aspect('equal')
        ax.add_patch(Polygon(native['board_outline'],facecolor='#153b32',edgecolor='#bfd2c3',linewidth=.8))
        for t in native['tracks']:
            if t['layer']!=layer:continue
            shape=LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2,quad_segs=6)
            ax.add_patch(Polygon(list(shape.exterior.coords),facecolor=colors[layer],edgecolor='none'))
        for via in native['vias']:
            if via['net']=='GND' and layer not in (5,32):continue
            ax.add_patch(Circle((via['x'],via['y']),via['diameter']/2,facecolor='#438974' if via['net']=='GND' else colors[layer],edgecolor='none'))
            ax.add_patch(Circle((via['x'],via['y']),via['hole']/2,facecolor='#112221',edgecolor='none'))
        for p in native['pads']:
            if p['layer'] not in (layer,74):continue
            color='#9fae84' if p['net']=='GND' else colors[layer]
            if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:
                ax.add_patch(Circle((p['x'],p['y']),p['size_x']/2,facecolor=color,edgecolor='none'))
            else:
                ax.add_patch(Polygon(r.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation']),facecolor=color,edgecolor='none'))
            if p['hole']:
                ax.add_patch(Circle((p['x'],p['y']),p['hole']/2,facecolor='#102421',edgecolor='none'))
            if labels and p['component']=='Q1':
                q=next(c for c in native['components'] if c['designator']=='Q1')
                dx,dy=p['x']-q['x'],p['y']-q['y'];length=math.hypot(dx,dy)
                ax.text(p['x']-dx/length*.68,p['y']-dy/length*.68,p['number'],color='white',fontsize=8,ha='center',va='center')
        if layer in (1,32):
            for c in native['components']:
                if c['side']!=('TOP' if layer==1 else 'BOTTOM'):continue
                if c['designator']=='Q1':continue
                y=c['y']+(.95 if c['designator'][0] in 'RC' else 2.9)
                if c['designator']=='J1':y=8.3
                if limits is None or limits[2]<y<limits[3]:
                    ax.text(c['x'],y,c['designator'],color='#edf2ec',fontsize=6 if limits is None else 8,ha='center',va='bottom',bbox=dict(facecolor='#122b28',edgecolor='none',pad=.5))
        if limits is None:limits=(-.5,20.,-.5,68.4)
        ax.set_xlim(*limits[:2]);ax.set_ylim(*limits[2:])
        ax.tick_params(labelsize=7,color='#8a9d95');ax.set_xlabel('X (mm)',fontsize=8)
        ax.set_ylabel('Y (mm)',fontsize=8)
    fig,axes=plt.subplots(1,4,figsize=(13,12))
    titles={1:'Top: SMP / ZIF lands',32:'L6: RF + bias tees',2:'L2: DC routes',4:'L4: DC routes'}
    for ax,layer in zip(axes,[1,32,2,4]):
        draw(ax,layer);ax.set_title(titles[layer],fontsize=11)
    fig.suptitle('4QD + 2SET carrier | saved native PCB signal geometry',fontsize=15)
    fig.text(.5,.045,'All views use the same top-view coordinates. Bottom is not mirrored. GND pours and masks are omitted for signal visibility.',ha='center',fontsize=9)
    signal_vias=sum(v['net']!='GND' for v in native['vias']);ground_vias=sum(v['net']=='GND' for v in native['vias'])
    fig.text(.5,.026,f'19.5 × 67.9 mm | 38 DC / 16 RF | {len(native["components"])} components | {signal_vias} signal vias | {ground_vias} GND shield vias',ha='center',fontsize=9)
    fig.text(.5,.009,'Saved PCB SHA-256: '+native['source_sha256'],ha='center',fontsize=7)
    fig.tight_layout(rect=(0,.058,1,.975))
    overview=output/'Saved_native_signal_layout.png';fig.savefig(overview,dpi=180);plt.close(fig)
    q=next(c for c in native['components'] if c['designator']=='Q1')
    fig,ax=plt.subplots(figsize=(9,9))
    draw(ax,32,(q['x']-7.7,q['x']+7.7,q['y']-7.7,q['y']+7.7),labels=True)
    ax.set_title('Saved native L6: QD38 wire-bond lands and RF / DC bias tee routes\nTop-view coordinates; GND pours and masks omitted',fontsize=12)
    fig.tight_layout()
    detail=output/'Saved_native_QD_bias_tee_detail.png';fig.savefig(detail,dpi=180);plt.close(fig)
    assert hashlib.sha256(PCB.read_bytes()).hexdigest()==native['source_sha256']
    report=dict(native_file=str(PCB),native_sha256=native['source_sha256'],files=[str(overview),str(detail)],
                source='Saved native binary pads/tracks/vias, not the routing plan',ground_pours_shown=False,masks_shown=False,
                coordinate_projection='Top-view coordinates for every layer',native_unchanged=True)
    (H/'saved_signal_render_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
