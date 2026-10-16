"""Draw only four central R0603/C1206 pairs; preserve native designs."""
import csv
import hashlib
import json
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as Patch, Circle
from shapely.geometry import box, Point

from latest_connection_plan import ROOT, SOURCES, pg
from outline_mount_concept import draw

OUT = ROOT / 'QSTL_QD4_2SET_38PAD/Central_Four_RC_Plan_20261015'
OUT.mkdir(exist_ok=True)
PLAN = ROOT / 'QSTL_QD4_2SET_38PAD/Outline_Mount_Concept_20261014/qd28_left_entry_audit.json'
CHOICES = {'SMP05': (6.9, 53.7, 50.7, 1),
           'SMP21': (12.6, 53.7, 50.7, -1),
           'SMP02': (6.9, 38.6, 41.6, 1),
           'SMP24': (12.6, 38.6, 41.6, -1)}
COLORS = {'SMP05':'#255eac', 'SMP21':'#ad5838',
          'SMP02':'#7a429a', 'SMP24':'#178375'}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def component(ref, x, y, pads, body_size, kind):
    return dict(ref=ref, centre_mm=[x,y], kind=kind, pads=pads,
                body_bounds_mm=[x-body_size[0]/2, y-body_size[1]/2,
                                x+body_size[0]/2, y+body_size[1]/2])


def pad(pin, x, y, w, h):
    return dict(pin=str(pin), x=x, y=y, width=w, height=h)


def pad_shape(p):
    return box(p['x']-p['width']/2,p['y']-p['height']/2,
               p['x']+p['width']/2,p['y']+p['height']/2)


def occupied(c):
    g=box(*c['body_bounds_mm'])
    for p in c['pads']:g=g.union(pad_shape(p))
    return g


def build(data):
    result=[]
    for r in data['rows']:
        if r['smp'] not in CHOICES:continue
        cx,cy,ry,dc_direction=CHOICES[r['smp']]
        upper=cy>data['qd_centre_mm'][1]
        toward_qd=-1 if upper else 1
        cap=component(r['capacitor'],cx,cy,
            [pad(1,cx,cy-1.5*toward_qd,1.8,1.0),
             pad(2,cx,cy+1.5*toward_qd,1.8,1.0)],(1.8,3.5),'C1206')
        resistor=component(r['resistor'],cx+.85*dc_direction,ry,
            [pad(1,cx,ry,1.1,1.0),pad(2,cx+1.7*dc_direction,ry,1.1,1.0)],
            (1.6,.8),'R0603')
        result.append(dict(**r, capacitor_component=cap,resistor_component=resistor))
    return result


def audit(data, groups):
    components=[c for r in groups for c in (r['resistor_component'],r['capacitor_component'])]
    smp=[(r['smp'],box(r['start'][0]-2.75,r['start'][1]-2.75,
                       r['start'][0]+2.75,r['start'][1]+2.75)) for r in data['rows']]
    qdpads=[(p['number'],pg(p['after'])) for p in data['pads']]
    pairgaps=sorted((occupied(a).distance(occupied(b)),a['ref'],b['ref'])
                   for a,b in combinations(components,2))
    smpgaps=sorted((occupied(c).distance(g),c['ref'],name) for c in components for name,g in smp)
    qdgaps=sorted((occupied(c).distance(g),c['ref'],'QD'+name) for c in components for name,g in qdpads)
    mountgaps=sorted((occupied(c).distance(pg(m)),c['ref'],m['concept_group']) for c in components for m in data['mounts'])
    cavity=box(9.75-2.15,46.15-2.65,9.75+2.15,46.15+2.65)
    failures=[]
    for label,gaps in [('R/C',pairgaps),('SMP',smpgaps),('QD',qdgaps),('mount',mountgaps)]:
        if gaps[0][0]<.15-1e-7:failures.append(dict(kind=label,gap=gaps[0]))
    if any(occupied(c).intersects(cavity) for c in components):failures.append('cavity overlap')
    assert not failures, failures
    return dict(placement_only_passed=True,component_count=8,pair_count=4,
        minimum_component_envelope_gap_mm=pairgaps[0],
        minimum_RC_to_SMP_body_box_gap_mm=smpgaps[0],
        minimum_RC_to_QD_pad_gap_mm=qdgaps[0],
        minimum_RC_to_mount_land_gap_mm=mountgaps[0],
        minimum_RC_to_cavity_gap_mm=min(occupied(c).distance(cavity) for c in components),
        envelope_definition='Union of copper pad rectangles and component body projection; C max 3.5 x 1.8 mm, R nominal 1.6 x 0.8 mm.',
        no_RF_routes_or_other_12_RC_pairs_validated=True)


def paint_component(ax,c,col):
    for p in c['pads']:
        g=pad_shape(p)
        ax.add_patch(Patch(list(g.exterior.coords),fc='#dab162',ec='#856521',lw=.5,zorder=8))
        ax.text(p['x'],p['y'],p['pin'],ha='center',va='center',fontsize=6.8,color='#332a14',zorder=12)
    x0,y0,x1,y1=c['body_bounds_mm']
    ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#37474f' if c['kind']=='R0603' else '#eee2bb',
                          ec=col,lw=.9,alpha=.8,zorder=9))
    x,y=c['centre_mm']
    ax.text(x,y,c['ref'],ha='center',va='center',fontsize=8,
            color='white' if c['kind']=='R0603' else '#25404b',weight='bold',zorder=11,
            rotation=0)


def paint(ax,data,groups,snapshot):
    draw(ax,data['rows'],data['pads'],data['mounts'],snapshot,
         proposed=False,height=77.5,ylim=(33.5,60.6),qd_center=tuple(data['qd_centre_mm']))
    ax.set_xlim(-.45,19.95)
    ax.plot([5.5,5.5],[33.5,60.6],color='#9cb4ae',ls=':',lw=.7)
    ax.plot([14,14],[33.5,60.6],color='#9cb4ae',ls=':',lw=.7)
    bynum={int(p['number']):p for p in data['pads']}
    for r in groups:
        col=COLORS[r['smp']]
        c=r['capacitor_component'];res=r['resistor_component']
        paint_component(ax,c,col);paint_component(ax,res,col)
        cp=c['pads'][1];rp=res['pads'][0]
        ax.plot([cp['x'],rp['x']],[cp['y'],rp['y']],color=col,lw=1.6,zorder=10)
        x,y=r['start']
        ax.add_patch(Circle((x,y),2.75,fc='none',ec=col,lw=1.25,zorder=5))
        pr=bynum[r['qd_pad']]['after'];g=pg(pr)
        ax.add_patch(Patch(list(g.exterior.coords),fc=col,ec='#162b35',lw=.4,zorder=10))
        side=-1 if x<9.75 else 1
        ax.text(pr['x']+side*.55,pr['y'],str(r['qd_pad']),ha='right' if side<0 else 'left',
                va='center',fontsize=7,color=col,weight='bold',zorder=12)
    # Static placement uses mirror symmetry; mapping is the existing circuit table.
    ax.text(9.75,57.0,'R0603 horizontal + C1206 vertical',ha='center',fontsize=8.5,color='#344f59',
            bbox=dict(fc='white',ec='none',alpha=.88),zorder=15)


def render(data,groups,snapshot,checks):
    fig=plt.figure(figsize=(13,10.4),dpi=210)
    gs=fig.add_gridspec(2,2,width_ratios=(1.1,1),height_ratios=(1,.85),left=.055,right=.97,
                      top=.88,bottom=.12,wspace=.22,hspace=.18)
    board=fig.add_subplot(gs[:,0]);unit=fig.add_subplot(gs[0,1]);tableax=fig.add_subplot(gs[1,1])
    paint(board,data,groups,snapshot)
    board.set_title('Central four circuits on the current SMP / QD plan',fontsize=11,pad=12)
    # One enlarged L pair, on local coordinates.
    r=next(r for r in groups if r['smp']=='SMP05')
    col=COLORS['SMP05'];c=r['capacitor_component'];res=r['resistor_component']
    paint_component(unit,c,col);paint_component(unit,res,col)
    unit.plot([6.9,6.9],[50.7,52.2],color=col,lw=2,zorder=10)
    unit.text(8.6,50.7,'2',ha='center',va='center',fontsize=9,zorder=15,color='white')
    unit.annotate('C05 pad 1 -> SMP05',xy=(6.9,55.2),xytext=(8.5,55.6),fontsize=9,
                  arrowprops=dict(arrowstyle='->',color=col),color=col)
    unit.annotate('R05 pad 1 -> QD11',xy=(6.9,50.7),xytext=(5.7,49.1),fontsize=9,
                  arrowprops=dict(arrowstyle='->',color=col),color=col)
    unit.annotate('R05 pad 2 -> DC11',xy=(8.6,50.7),xytext=(9.4,51.9),fontsize=9,
                  arrowprops=dict(arrowstyle='->',color='#567169'),color='#567169')
    unit.annotate('',xy=(5.6,51.7),xytext=(5.6,55.7),arrowprops=dict(arrowstyle='<->',color='#54666b'))
    unit.text(5.4,53.7,'4.00 mm copper length',rotation=90,ha='right',va='center',fontsize=9)
    unit.annotate('',xy=(6.35,49.9),xytext=(9.15,49.9),arrowprops=dict(arrowstyle='<->',color='#54666b'))
    unit.text(7.75,49.7,'2.80 mm R copper width',ha='center',va='top',fontsize=8.5)
    unit.set(xlim=(4.8,12.3),ylim=(48.5,56.4),aspect='equal');unit.axis('off')
    unit.set_title('L-shaped bias-tee pair | example SMP05',fontsize=12)
    tableax.axis('off')
    cells=[]
    for r in groups:
        cx,cy=r['capacitor_component']['centre_mm'];rx,ry=r['resistor_component']['centre_mm']
        cells.append([r['smp'],str(r['qd_pad']),f"{r['capacitor']}\n({cx:.2f}, {cy:.2f})",
                      f"{r['resistor']}\n({rx:.2f}, {ry:.2f})"])
    tab=tableax.table(cellText=cells,colLabels=['Channel','QD pad','C centre (mm)','R centre (mm)'],
                     colWidths=[.20,.15,.325,.325],cellLoc='center',bbox=[0,.26,1,.71])
    tab.auto_set_font_size(False);tab.set_fontsize(9)
    for (rr,cc),cell in tab.get_celld().items():
        cell.set_edgecolor('#cedbdc');cell.set_facecolor('#234b54' if rr==0 else '#f0f5f4' if rr%2 else 'white')
        cell.get_text().set_color('white' if rr==0 else '#263d43')
    tableax.text(.0,.17,'Placement checks (pads + body projections):',weight='bold',fontsize=9)
    tableax.text(.0,.10,
        f"R/C to R/C: {checks['minimum_component_envelope_gap_mm'][0]:.3f} mm   |   R/C to SMP: {checks['minimum_RC_to_SMP_body_box_gap_mm'][0]:.3f} mm\n"
        f"R/C to QD pads: {checks['minimum_RC_to_QD_pad_gap_mm'][0]:.3f} mm   |   No component overlap",
        va='top',fontsize=9,linespacing=1.7)
    fig.suptitle('Central channels 02 / 05 / 21 / 24: R/C placement proposal',fontsize=18,y=.975)
    fig.text(.5,.932,'Four pairs only | R: 0603 imperial | C: Yageo CC1206JKNPO9BN104, 1206',ha='center',fontsize=11)
    fig.text(.5,.078,'C maximum body: 3.50 x 1.80 mm. C lands: 1.00 x 1.80 mm at 3.00 mm pitch. Existing R lands: 1.10 x 1.00 mm.',ha='center',fontsize=9)
    fig.text(.5,.052,'Only local C2-to-R1 junctions are drawn. Full RF/DC routes, the other 12 pairs, shields and masks are not validated.',ha='center',fontsize=9)
    fig.text(.5,.026,'PLAN ONLY: native PCB/CAD unchanged. The known M2.5 mounting conflicts remain unresolved.',ha='center',fontsize=9,color='#a34a37')
    fig.savefig(OUT/'Central_02_05_21_24_RC_Placement.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,12),dpi=210)
    paint(ax,data,groups,snapshot)
    ax.set_title('Four central R/C pairs: SMP02, SMP05, SMP21, SMP24',fontsize=14,pad=18)
    fig.text(.5,.04,'R0603 / C1206 | Placement only, no full RF routes or native changes',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.065,1,.98));fig.savefig(OUT/'Central_RC_Enlarged.png');plt.close(fig)


def main():
    native=ROOT/'QSTL_QD4_2SET_38PAD'
    protected=[native/p for p in ('QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc',
                                  'QD4_2SET_38.PcbLib','pin_mapping.csv')]
    protected += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/p for p in ('Bottom_reference.step','Top_ForFridge_reference.step')]
    hashes={str(p.relative_to(ROOT)):digest(p) for p in protected}
    data=json.loads(PLAN.read_text());groups=build(data);checks=audit(data,groups)
    snapshot=json.loads(SOURCES['snapshot'].read_text())
    render(data,groups,snapshot,checks)
    assert hashes=={str(p.relative_to(ROOT)):digest(p) for p in protected}
    result=dict(status='CENTRAL_FOUR_RC_PLACEMENT_ONLY_NOT_APPLIED',source_plan_sha256=digest(PLAN),
        group_count=4,groups=groups,checks=checks,source_hashes=hashes,native_unchanged=True,
        omitted='Other 12 R/C pairs and all full-length RF/DC paths; this is not a completed routing or assembly fit.',
        copper_fit='Known upper M2.5 blockage and lower mounting-axis mismatch remain unresolved.')
    (OUT/'central_rc_placement_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    with (OUT/'placement.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['channel','qd_pad','ref','kind','x_mm','y_mm'])
        for r in groups:
            for key in ('resistor_component','capacitor_component'):
                c=r[key];w.writerow([r['smp'],r['qd_pad'],c['ref'],c['kind'],*c['centre_mm']])
    print(json.dumps(checks,indent=2))


if __name__=='__main__':main()
