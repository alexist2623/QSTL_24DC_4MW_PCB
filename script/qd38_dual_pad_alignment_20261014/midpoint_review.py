"""Review all QD pad short-edge midpoint alignments; never edit native sources."""
from copy import deepcopy
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as Patch, Rectangle
from shapely.geometry import Point, box
from analyze import ROOT, OUT, SRC, META, BASE, BOUND, pg, sha


def direction(p, side):
    axis, _, sign = BOUND[side]
    angle = math.radians(p['rotation'])
    u = [math.cos(angle), math.sin(angle)]
    if sign * u[axis] < 0:
        u = [-v for v in u]
    return u


def endpoints(p, side):
    u = direction(p, side)
    c = [p['x'], p['y']]
    return [[c[k] + sign * p['size_x'] / 2 * u[k] for k in (0, 1)]
            for sign in (-1, 1)]


def build(qd, meta, depth):
    sides = {}
    for p in qd:
        m = meta[p['number']]
        sides[p['number']] = m['side'] if m['side'] != 'CORNER' else (
            'TOP' if m['normal'][1] > 0 else 'BOTTOM')
    # Preserve the physical 0.20 mm cavity-to-copper distance, rather than
    # mistaking the midpoint datum for the nearest tilted corner.
    corner_offsets = []
    for p in qd:
        side = sides[p['number']]
        axis = BOUND[side][0]
        u = direction(p, side)
        v = [-u[1], u[0]]
        corner_offsets.append(p['size_y'] / 2 * abs(v[axis]))
    shift = math.ceil((max(corner_offsets) + 1e-5) / .005) * .005
    inner = {side: val + sign * shift for side, (_, val, sign) in BOUND.items()}
    rows = []
    for p in qd:
        side = sides[p['number']]
        axis, _, sign = BOUND[side]
        u = direction(p, side)
        length = depth / abs(u[axis])
        target = inner[side] + sign * depth / 2
        travel = (target - p[['x', 'y'][axis]]) / u[axis]
        after = deepcopy(p)
        after.update(x=p['x']+travel*u[0], y=p['y']+travel*u[1], size_x=length)
        rows.append(dict(number=p['number'], side=side, before=p, after=after,
                         before_midpoints=endpoints(p, side),
                         after_midpoints=endpoints(after, side)))
    return rows, inner, shift


def audit(rows, inner, depth, source):
    geos = {r['number']: pg(r['after']) for r in rows}
    pairs = [(a.distance(geos[nb]), na, nb) for na, a in geos.items()
             for nb in geos if int(na) < int(nb)]
    cavity = box(7.6, 39.85, 11.9, 45.15)
    foreign = []
    contain = []
    for via in source['vias']:
        if via['net'] == 'GND':
            continue
        for r in rows:
            p = r['before']
            point = Point(via['x'], via['y'])
            if via['net'] != p['net']:
                foreign.append((point.distance(geos[r['number']]) - via['diameter']/2,
                                r['number'], via['net']))
            elif point.distance(Point(p['x'], p['y'])) < 1:
                contain.append(dict(pad=r['number'], contained=geos[r['number']].buffer(1e-8).covers(
                    point.buffer(via['hole']/2, quad_segs=128))))
    grid_checks = []
    for r in rows:
        axis, _, sign = BOUND[r['side']]
        p = r['after']
        grid = 2.54e-6
        qp = dict(p, **{k: round(p[k]/grid)*grid for k in ('x', 'y', 'size_x', 'size_y')})
        mids = endpoints(qp, r['side'])
        grid_checks.append(dict(pad=r['number'],
            inner_error_mm=abs(mids[0][axis] - inner[r['side']]),
            outer_error_mm=abs(mids[1][axis] - inner[r['side']] - sign*depth)))
    return dict(min_pad_gap_mm=min(pairs),
                min_foreign_signal_via_gap_mm=min(foreign),
                min_cavity_gap_mm=min(g.distance(cavity) for g in geos.values()),
                existing_QD_drill_containment=contain,
                grid_midpoint_checks=grid_checks,
                max_grid_midpoint_error_mm=max(max(c['inner_error_mm'],c['outer_error_mm']) for c in grid_checks),
                length_range_mm=[min(r['after']['size_x'] for r in rows),
                                 max(r['after']['size_x'] for r in rows)])


def draw_field(ax, rows, state, inner, depth, title):
    ax.set_facecolor('#172c36')
    ax.add_patch(Rectangle((7.6,39.85),4.3,5.3,facecolor='#0c1922',edgecolor='#b4c1ca',lw=.8))
    for r in rows:
        p = r[state]
        g = pg(p)
        ax.add_patch(Patch(list(g.exterior.coords),fc='#ddb364',ec='#fff0c4',lw=.45))
        ax.text(p['x'],p['y'],p['number'],fontsize=6.4,ha='center',va='center',color='#102833')
    for side, (axis, _, sign) in BOUND.items():
        midvalues = [r[state+'_midpoints'][0][axis] for r in rows if r['side']==side]
        outervalues = [r[state+'_midpoints'][1][axis] for r in rows if r['side']==side]
        for v,color in ((inner[side],'#64e6dc'),(inner[side]+sign*depth,'#ff88ba')):
            if axis == 0:
                ax.plot([v,v],[38.15,46.85],ls='--',lw=.9,color=color,alpha=.65)
            else:
                ax.plot([5.85,13.65],[v,v],ls='--',lw=.9,color=color,alpha=.65)
    for r in rows:
        for point,color in zip(r[state+'_midpoints'],('#64e6dc','#ff88ba')):
            ax.scatter(*point,s=11,c=color,edgecolors='#102833',linewidths=.35,zorder=5)
    ax.text(9.75,42.85,'QD / CHIP',ha='center',color='white',fontsize=12)
    ax.text(9.75,42.1,'Existing cavity\n4.30 x 5.30 mm',ha='center',color='#b7c7cc',fontsize=10)
    ax.text(9.75,41.15,'Dots = centres of short end edges',ha='center',color='#b7c7cc',fontsize=8)
    ax.set(xlim=(5.85,13.65),ylim=(38.15,46.85),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)',title=title)
    ax.tick_params(labelsize=8)


def main():
    source=json.loads(SRC.read_text())
    protected=[Path(source['source']),ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.SchDoc',
               ROOT/'QSTL_QD4_2SET_38PAD/QD4_2SET_38.PcbLib']
    hashes={str(p):sha(p) for p in protected}
    assert source['source_sha256']==BASE and hashes[str(protected[0])]==BASE
    qd=[p for p in source['pads'] if p['component']=='Q1']
    assert len(qd)==38
    meta={str(p['number']):p for p in json.loads(META.read_text())['pads']}
    depth=.80
    rows,inner,shift=build(qd,meta,depth)
    result=audit(rows,inner,depth,source)
    assert result['max_grid_midpoint_error_mm']<4e-6
    assert result['min_cavity_gap_mm']>=.2-1e-8
    assert result['min_pad_gap_mm'][0]>=.15-1e-8
    for r in rows:
        assert r['before']['size_y']==r['after']['size_y']
        assert r['before']['rotation']==r['after']['rotation']
        assert r['before']['net']==r['after']['net']
        u=direction(r['after'],r['side'])
        delta=[r['after'][k]-r['before'][k] for k in ('x','y')]
        assert abs(delta[0]*u[1]-delta[1]*u[0])<1e-10
    fig=plt.figure(figsize=(16,8.8),dpi=170)
    gs=fig.add_gridspec(1,3,width_ratios=(1,1,.78),left=.045,right=.985,bottom=.16,top=.88,wspace=.20)
    left=fig.add_subplot(gs[0]);centre=fig.add_subplot(gs[1]);detail=fig.add_subplot(gs[2])
    draw_field(left,rows,'before',inner,depth,'Saved PCB: short-edge midpoints staggered')
    draw_field(centre,rows,'after',inner,depth,'Corrected plan: ALL 38 pad midpoints aligned')
    # Enlarge one side so the datum is visibly the middle of the edge.
    detail.set_facecolor('#172c36')
    top=[r for r in rows if r['side']=='TOP']
    top=sorted(top,key=lambda r:r['after']['x'])
    sample=top[:4]
    for r in sample:
        p=r['after'];g=pg(p)
        detail.add_patch(Patch(list(g.exterior.coords),fc='#ddb364',ec='#fff0c4',lw=1))
        u=direction(p,r['side']);v=[-u[1],u[0]]
        detail.text(p['x'],p['y'],p['number'],ha='center',va='center',fontsize=10,color='#102833')
        for point,color in zip(r['after_midpoints'],('#64e6dc','#ff88ba')):
            tips=[[point[k]+sign*p['size_y']/2*v[k] for k in (0,1)] for sign in (-1,1)]
            detail.plot([tips[0][0],tips[1][0]],[tips[0][1],tips[1][1]],color=color,lw=2)
            detail.scatter(*point,s=34,c=color,edgecolors='#102833',linewidths=.8,zorder=7)
    for offset,color,label in ((0,'#64e6dc','Inner-edge MIDPOINT line'),(depth,'#ff88ba','Outer-edge MIDPOINT line')):
        y=inner['TOP']+offset
        detail.axhline(y,color=color,ls='--',lw=1.2)
        detail.text(.04,.08 if offset==0 else .90,label,transform=detail.transAxes,color=color,fontsize=9)
    xmin=min(pg(r['after']).bounds[0] for r in sample)-.18
    xmax=max(pg(r['after']).bounds[2] for r in sample)+.18
    detail.set(xlim=(xmin,xmax),ylim=(inner['TOP']-.28,inner['TOP']+depth+.28),aspect='equal',
               title='Enlarged: the dot is the edge midpoint',xlabel='X (mm)',ylabel='Y (mm)')
    detail.tick_params(labelsize=8)
    fig.suptitle('Align the MIDPOINTS of both short end edges on each side',fontsize=17,y=.97)
    handles=[Line2D([0],[0],color='#29a89e',ls='--',marker='o',label='Inner-edge midpoint'),
             Line2D([0],[0],color='#da538c',ls='--',marker='o',label='Outer-edge midpoint')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.095),ncol=2,frameon=False,fontsize=11)
    fig.text(.5,.073,'Width 0.25 mm and existing pad angles retained | Midpoint-line separation 0.80 mm | Existing cavity retained',ha='center',fontsize=10)
    fig.text(.5,.045,'All 38 pads adjusted in this plan. Tilted corners may extend across the dashed lines; the midpoints lie ON them.',ha='center',fontsize=10)
    fig.text(.5,.018,'REVIEW ONLY: native PCB unchanged; routing, vias, GND and mask must be updated and verified before implementation.',ha='center',fontsize=9,color='#6b4a36')
    image=OUT/'Short_Edge_Midpoints_Aligned_Review.png'
    fig.savefig(image);plt.close(fig)
    assert hashes=={str(p):sha(p) for p in protected}
    report=dict(status='MIDPOINT_ALIGNMENT_REVIEW_ONLY_NOT_APPLIED',
                supersedes='Both_Pad_Ends_Aligned_Review.png extremal-corner interpretation',
                definition='The centre of each short end edge lies on its side-specific inner or outer common line.',
                pad_count=38,normal_depth_mm=depth,datum_outward_shift_from_old_corner_lines_mm=shift,
                inner_midpoint_lines_mm=inner,
                outer_midpoint_lines_mm={k:v+BOUND[k][2]*depth for k,v in inner.items()},
                source_hashes=hashes,native_sources_unchanged=True,image=str(image),
                checks=result,rows=rows,
                pending=['Reposition QD vias where their old locations violate updated pad clearances or containment',
                         'RF/DC reconnection, GND/shield/mask clearance and native save/reopen DRC'])
    (OUT/'midpoint_review_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    brief={k:v for k,v in report.items() if k not in ('rows','source_hashes','checks')}
    brief['checks']={k:v for k,v in result.items() if k not in ('existing_QD_drill_containment','grid_midpoint_checks')}
    brief['QD_drills_outside_pads']=[c['pad'] for c in result['existing_QD_drill_containment'] if not c['contained']]
    print(json.dumps(brief,indent=2))


if __name__=='__main__':
    main()
