"""Draw a topology plan on the exact latest relocation; no native PCB writes."""
from pathlib import Path
from itertools import combinations
import csv
import hashlib
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon as Patch
from shapely.geometry import LineString, Point, box
from shapely.affinity import translate, rotate

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'QSTL_QD4_2SET_38PAD/Relocation_RF_Plan_20261014'
OUT.mkdir(exist_ok=True)
SOURCES={
 'placement': HERE/'corrected_endpair_measurements.json',
 'pads': ROOT/'script/qd38_dual_pad_alignment_20261014/midpoint_review_manifest.json',
 'mapping': ROOT/'QSTL_QD4_2SET_38PAD/pin_mapping.csv',
 'snapshot': ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json',
}
ASSIGN={'P1L':2,'P1R':35,'P2L':5,'P2R':34,'P3L':9,'P3R':32,
        'P4L':11,'P4R':31,'P5L':12,'P5R':30,'P6L':13,'P6R':28,
        'P7L':15,'P7R':24,'P8L':16,'P8R':21}
PALETTE=['#55c7ff','#afe4ff','#ffb544','#ffd39d','#69da79','#b6f5ad',
         '#ff756e','#ffb3a9','#bc9dff','#e6ceff','#d3a284','#f4ceaf',
         '#f77bb8','#ffc1df','#b7cacf','#f6f7da']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    placement=json.loads(SOURCES['placement'].read_text())['candidate']['centres']
    padrows=json.loads(SOURCES['pads'].read_text())['rows']
    pads={int(r['number']):r for r in padrows}
    with SOURCES['mapping'].open(newline='') as f:
        existing={int(r['qd_pad']):r for r in csv.DictReader(f)}
    assert set(ASSIGN.values())=={n for n,r in existing.items() if r['rf']=='True'}
    assert len(placement)==len(ASSIGN)==16
    rows=[]
    for s in placement:
        n=ASSIGN[s['name']];p=pads[n];m=existing[n]
        e=np.array(p['after_midpoints'][1]);c=np.array([p['after']['x'],p['after']['y']])
        u=(e-c)/np.linalg.norm(e-c)
        rows.append(dict(position=s['name'],smp=m['smp'],qd_pad=n,
            resistor=m['resistor'],capacitor=m['capacitor'],chip_net=m['chip_net'],
            rf_net=m['rf_net'],dc_net=m['dc_net'],zif_pin=int(m['zif_pin']),
            start=[s['x'],s['y']],end=list(e),outward=list(u),kind=s['kind']))
    return rows,padrows


def rounded(points,trim=.4):
    pp=[np.array(p,dtype=float) for p in points]
    output=[pp[0]]
    for i,b in enumerate(pp[1:-1],1):
        a=pp[i-1];c=pp[i+1]
        ab=np.linalg.norm(a-b);cb=np.linalg.norm(c-b)
        if min(ab,cb)<1e-8:continue
        d=min(trim,ab*.35,cb*.35)
        p=b+(a-b)*d/ab;q=b+(c-b)*d/cb
        output.append(p)
        for t in np.linspace(0,1,51)[1:]:
            output.append((1-t)**2*p+2*t*(1-t)*b+t*t*q)
    output.append(pp[-1])
    return LineString(output)


def planned_lines(rows):
    buses={'P1L':8.05,'P1R':11.30,'P2L':6.75,'P2R':12.95,
           'P3L':5.85,'P3R':13.75,'P4L':4.95,'P4R':14.65,
           'P5L':4.95,'P5R':14.65,'P6L':5.80,'P6R':13.75,
           'P7L':6.65,'P7R':12.85,'P8L':8.20,'P8R':10.90}
    paths=[]
    for r in rows:
        s=np.array(r['start']);e=np.array(r['end']);u=np.array(r['outward'])
        upper='upper' in r['kind'];sgn=1 if upper else -1
        b=buses[r['position']]
        e1=e+u*.65
        # This is a smooth connection sketch, not final 50-ohm copper.
        if 'end' in r['kind']:
            sy=s[1]-sgn*2.3
            pts=[s,[s[0],sy],[b,sy],[b,e1[1]+sgn*2.1],e1,e]
        else:
            pts=[s,[b,s[1]],[b,e1[1]+sgn*.45],e1,e]
        paths.append(rounded(pts))
    return paths


def pg(p):
    if p['shape']==1:return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=64)
    return translate(rotate(box(-p['size_x']/2,-p['size_y']/2,p['size_x']/2,p['size_y']/2),
        p['rotation'],origin=(0,0)),p['x'],p['y'])


def check(rows,paths,padrows):
    crosses=[(rows[i]['position'],rows[j]['position']) for i,j in combinations(range(16),2)
             if paths[i].intersects(paths[j])]
    gap=min((paths[i].distance(paths[j]),rows[i]['position'],rows[j]['position'])
             for i,j in combinations(range(16),2))
    snapshot=json.loads(SOURCES['snapshot'].read_text())
    template=[p for p in snapshot['pads'] if p['component']=='SMP35']
    centre=next(p for p in template if p['number']=='1')
    smppads=[]
    for r in rows:
        for p in template:
            t=dict(p,component=r['smp'],x=p['x']+r['start'][0]-centre['x'],
                   y=p['y']+r['start'][1]-centre['y'])
            smppads.append(t)
    collisions=[]
    min_foreign=[]
    for r,l in zip(rows,paths):
        for p in smppads:
            if p['component']==r['smp'] and p['number']=='1':continue
            dist=l.distance(pg(p))
            min_foreign.append([dist-.055,r['position'],p['component']+'.'+p['number']])
            if dist<.055:
                collisions.append([r['position'],p['component']+'.'+p['number'],dist])
        for pr in padrows:
            if int(pr['number'])==r['qd_pad']:continue
            dist=l.distance(pg(pr['after']))
            min_foreign.append([dist-.055,r['position'],'QD'+pr['number']])
            if dist<.055:collisions.append([r['position'],'QD'+pr['number'],dist])
    return dict(centerline_crossings=crosses,min_centerline_gap_mm=gap,
                min_projected_0p11mm_trace_to_SMP_or_foreign_QD_gap_mm=min(min_foreign),
                projected_0p11mm_trace_to_SMP_or_foreign_QD_pad_overlaps=collisions),smppads


def patch(ax,g,fc,ec='none',lw=.5,alpha=1):
    ax.add_patch(Patch(list(g.exterior.coords),facecolor=fc,edgecolor=ec,lw=lw,alpha=alpha))


def draw(ax,rows,paths,padrows,smppads,zoom=False):
    colors=lambda i: PALETTE[i]
    ax.set_facecolor('#142a33')
    ax.add_patch(Rectangle((0,0),19.5,67.9,facecolor='#17343b',edgecolor='#96a6ae',lw=.8))
    snapshot=json.loads(SOURCES['snapshot'].read_text())
    if not zoom:
        for r in rows:
            x,y=r['start']
            ax.add_patch(Circle((x,y),2.75,fc='#a3b0b7',ec='#718e96',lw=.75,alpha=.12))
        for p in snapshot['pads']:
            if not p['component']:
                patch(ax,pg(p),'#6b8c8e')
                ax.add_patch(Circle((p['x'],p['y']),p['hole']/2,fc='#10252c',ec='none'))
        for p in smppads:
            patch(ax,pg(p),'#dfbc6d' if p['number']=='1' else '#607a80')
            ax.add_patch(Circle((p['x'],p['y']),p['hole']/2,fc='#18333b',ec='none'))
    bypad={r['qd_pad']:i for i,r in enumerate(rows)}
    for pr in padrows:
        n=int(pr['number']);p=pr['after']
        color=colors(bypad[n]) if n in bypad else '#738d95'
        patch(ax,pg(p),color,'#d6e4e3',.3)
        ax.text(p['x'],p['y'],n,ha='center',va='center',fontsize=7.5 if zoom else 5,
                color='#08232c',fontweight='bold' if n in bypad else 'normal',zorder=8)
    for i,(r,l) in enumerate(zip(rows,paths)):
        xx,yy=l.xy
        ax.plot(xx,yy,color=colors(i),lw=1.6 if zoom else 1.15,zorder=5)
        ax.scatter(*r['end'],s=12 if zoom else 5,c=[colors(i)],zorder=7)
        if not zoom:
            x,y=r['start'];c=colors(i)
            ax.text(x,y+2.06,r['smp'],color='#f6f8ed',ha='center',va='center',fontsize=8,
                    bbox=dict(facecolor='#17343b',edgecolor='none',alpha=.86,pad=.1),zorder=10)
            ax.text(x,y-2.06,f"QD {r['qd_pad']}",color=c,ha='center',va='center',fontsize=8,
                    bbox=dict(facecolor='#17343b',edgecolor='none',alpha=.86,pad=.1),zorder=10)
    ax.add_patch(Rectangle((7.6,39.85),4.3,5.3,facecolor='#091b23',edgecolor='#a9babc',lw=.8,ls='--'))
    ax.text(9.75,42.9,'QD',ha='center',va='center',fontsize=15 if zoom else 11,color='white')
    ax.text(9.75,42.05,'4.3 x 5.3 mm\nexisting cavity',ha='center',va='center',fontsize=9 if zoom else 6.5,color='#a9babc')
    ax.set(xlim=(5.8,13.7) if zoom else (-.35,19.85),
           ylim=(38.1,46.9) if zoom else (18.8,66.7),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)')
    ax.tick_params(labelsize=8)
    ax.set_title('QD detail: corrected end-edge midpoints' if zoom else 'Latest relocation: same 16 SMP coordinates',fontsize=12)


def render(rows,paths,pads,smppads):
    fig=plt.figure(figsize=(15,14),dpi=190)
    gs=fig.add_gridspec(2,2,width_ratios=(1.05,1.2),height_ratios=(.72,1),
                       left=.055,right=.975,top=.92,bottom=.13,wspace=.22,hspace=.18)
    overview=fig.add_subplot(gs[:,0]);detail=fig.add_subplot(gs[1,1]);tableax=fig.add_subplot(gs[0,1])
    draw(overview,rows,paths,pads,smppads)
    draw(detail,rows,paths,pads,smppads,zoom=True)
    tableax.axis('off')
    cells=[]
    for i in range(8):
        a,b=rows[2*i:2*i+2]
        label='Top end pair' if i==0 else 'Bottom end pair' if i==7 else f'Side row {i}'
        cells.append([f"{label}\nY = {a['start'][1]:.2f}",
                      f"{a['smp']}  >  QD {a['qd_pad']}",f"{b['smp']}  >  QD {b['qd_pad']}"])
    tbl=tableax.table(cellText=cells,colLabels=['Physical row (mm)','LEFT connector > pad','RIGHT connector > pad'],
                      cellLoc='center',colWidths=[.32,.34,.34],bbox=[0,.18,1,.78])
    tbl.auto_set_font_size(False);tbl.set_fontsize(9.5)
    for (rr,cc),cell in tbl.get_celld().items():
        cell.set_edgecolor('#d1dfe0');cell.set_linewidth(.6)
        cell.set_facecolor('#21444e' if rr==0 else '#f1f6f6' if rr%2 else '#ffffff')
        cell.get_text().set_color('white' if rr==0 else '#17343b')
        if rr==0:cell.get_text().set_fontweight('bold')
    tableax.text(.5,1.03,'Proposed physical assignment | existing circuit IDs retained',ha='center',fontsize=11,
                 transform=tableax.transAxes)
    tableax.text(.5,.10,'For example: SMP34 / C34 / R34 remains connected to QD pad 2.\n'
                  'All 16 RF targets and all 38 independent DC channels are retained.',
                 ha='center',va='center',fontsize=9.5,linespacing=1.5,transform=tableax.transAxes)
    fig.suptitle('Latest relocation: SMP-to-QD RF connection plan',fontsize=19,y=.975)
    fig.text(.5,.947,'Board XY view consistent with the supplied RF drawing | Line colours identify the proposed connections',ha='center',fontsize=11)
    fig.text(.5,.093,'Each path: SMP signal -> C (1206) -> R RF-pad-1 junction -> QD pad',ha='center',fontsize=11)
    fig.text(.5,.069,'DC bias: ZIF -> R (0603), pad 2 -> resistor -> the same RF-pad-1 junction',ha='center',fontsize=10.5)
    fig.text(.5,.044,'C: Yageo CC1206JKNPO9BN104. R/C locations are not placed in this mapping drawing.',ha='center',fontsize=10,color='#36515c')
    fig.text(.5,.021,'PLANNING ONLY: smooth connection guides, not final copper. Component fit, shields, masks and native DRC remain to be checked.',ha='center',fontsize=9.5,color='#80513d')
    fig.savefig(OUT/'Latest_Relocation_RF_Connection_Plan.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,16),dpi=200)
    draw(ax,rows,paths,pads,smppads)
    fig.suptitle('Latest SMP placement + proposed RF connections',fontsize=15,y=.985)
    fig.text(.5,.043,'Existing SMP IDs retained; destinations are QD pad numbers.\n'
             'Conceptual connections only. R0603 / C1206 placement and full routing remain pending.',
             ha='center',fontsize=9,linespacing=1.5)
    fig.tight_layout(rect=(0,.07,1,.96));fig.savefig(OUT/'Latest_Relocation_RF_Overview.png');plt.close(fig)


def main():
    native=ROOT/'QSTL_QD4_2SET_38PAD'
    protected=[native/'QSTL_QD4_2SET_38PAD.PcbDoc',native/'QSTL_QD4_2SET_38PAD.SchDoc',
               native/'QD4_2SET_38.PcbLib',SOURCES['mapping'],SOURCES['placement'],
               native/'full_copper_candidate.json']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in protected}
    rows,pads=load()
    lines=planned_lines(rows)
    result,smppads=check(rows,lines,pads)
    assert not result['centerline_crossings']
    assert not result['projected_0p11mm_trace_to_SMP_or_foreign_QD_pad_overlaps']
    snapshot=json.loads(SOURCES['snapshot'].read_text())
    lookup={(p['component'],p['number']):p for p in snapshot['pads']}
    for r in rows:
        assert lookup[('Q1',str(r['qd_pad']))]['net']==r['rf_net']
        assert lookup[(r['resistor'],'1')]['net']==r['rf_net']
        assert lookup[(r['resistor'],'2')]['net']==r['dc_net']
        assert lookup[(r['capacitor'],'2')]['net']==r['rf_net']
        assert lookup[(r['capacitor'],'1')]['net']==lookup[(r['smp'],'1')]['net']
    render(rows,lines,pads,smppads)
    columns=['position','smp','qd_pad','capacitor','resistor','rf_net','dc_net','zif_pin','chip_net','smp_x_mm','smp_y_mm']
    with (OUT/'SMP_to_QD_plan.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for r in rows:
            writer.writerow({**{k:r[k] for k in columns if k in r},'smp_x_mm':r['start'][0],'smp_y_mm':r['start'][1]})
    assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in protected}
    report=dict(status='CONNECTION_TOPOLOGY_PLAN_ONLY_NOT_APPLIED',source_hashes=hashes,
        other_source_hashes={k:sha(p) for k,p in SOURCES.items()},native_and_input_files_unchanged=True,
        SMP_coordinates_exactly_match_latest_candidate=True,RF_target_count=16,
        existing_circuit_membership_preserved=True,DC_mapping_unchanged=True,checks=result,
        paths=[dict(**r,points_mm=list(l.coords)) for r,l in zip(rows,lines)],
        limitations=['No individual R0603/C1206 placement is represented or certified.',
                     'The guides collapse capacitor and bias-tee junction into each conceptual SMP-to-QD link.',
                     'Smooth guide curves do not constitute Altium copper or a 50-ohm impedance solution.',
                     'DC/via/GND/mask/paste/shield clearances and component fit are pending a full routing review.',
                     'No native DRC, Gerber generation, purchase or Git push is performed.'])
    (OUT/'connection_plan_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    md=['# Latest relocation RF connection plan','',
        'This plan uses the exact horizontal-end-pair SMP positions from the latest mechanical review and the corrected short-edge-midpoint QD pad geometry. Native files are unchanged.','',
        'All 16 selected QD RF targets and all 38 DC connections are retained. Existing SMP/C/R circuit identities are retained rather than silently renumbered: move the indicated circuit to its proposed physical position. QD pad numbers therefore need not equal connector designators.','',
        '| Position | SMP | X / Y (mm) | QD pad | C / R | RF net | ZIF DC pin |',
        '| --- | --- | --- | ---: | --- | --- | ---: |']
    for r in rows:
        md.append(f"| {r['position']} | {r['smp']} | {r['start'][0]:.3f} / {r['start'][1]:.2f} | {r['qd_pad']} | {r['capacitor']} / {r['resistor']} | {r['rf_net']} | {r['zif_pin']} |")
    md+=['','## Scope and checks','',
         '- The coloured lines are conceptual smooth connection guides. They are not final PCB traces and do not establish electrical length, impedance or manufacturing clearances.',
         '- The conceptual centre lines have zero intersections. Their sampled minimum centre separation is '+f"{result['min_centerline_gap_mm'][0]:.6f} mm. The limited 0.11 mm swept-line check finds no overlap with SMP or foreign QD pads. This does not include DC, existing vias, GND, shields or R/C placement.",
         '- Verify existing native net membership independently: SMP signal to C pad 1; C pad 2, R pad 1 and QD share the RF net; R pad 2 retains its DC net. All 16 checks pass.',
         '- Component basis remains R0603 and exact Yageo CC1206JKNPO9BN104 C1206. Individual R/C positions and their 1206 occupancy are not yet solved or displayed. The drawing states the intended bias-tee topology only.',
         '- Preserve Bottom-only RF without signal vias, 0.11 mm target width, the specified GND gap, tangent turns and body-envelope restrictions in the later native implementation.',
         '- PCB/schematic/library/current pin mapping/canonical plan and latest placement file hashes are preserved. No native layout, Gerber or DRC result is generated by this plan.','',
         '[Connection plan and table](Latest_Relocation_RF_Connection_Plan.png) | [Large overview](Latest_Relocation_RF_Overview.png) | [CSV](SMP_to_QD_plan.csv) | [Source-bound audit](connection_plan_audit.json)','']
    (OUT/'README.md').write_text('\n'.join(md))
    print(json.dumps(dict(output=str(OUT),checks=result,native_unchanged=True,circuit_membership_checks=16),indent=2))


if __name__=='__main__':main()
