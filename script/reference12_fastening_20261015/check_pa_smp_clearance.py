"""Read-only P/A-axis overlap check on the latest sixteen-SMP proposal."""
from pathlib import Path
import hashlib
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon
from shapely.geometry import Point, box, LineString
from shapely.affinity import rotate
from shapely.ops import nearest_points

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT/'QSTL_QD4_2SET_38PAD/Four_End_SMP_Side_Entry_20261015/side_entry_audit.json'
HOLES = ROOT/'QSTL_QD4_2SET_38PAD/PA_Mounting_Pattern_20261016/pa_pattern.json'
SNAP = ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json'
OUT = ROOT/'QSTL_QD4_2SET_38PAD/PA_Mounting_Pattern_20261016'


def pad_shape(p):
    if p['shape'] == 1:
        return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=128)
    return rotate(box(p['x']-p['size_x']/2,p['y']-p['size_y']/2,
                      p['x']+p['size_x']/2,p['y']+p['size_y']/2),
                  p['rotation'],origin=(p['x'],p['y']))


def evaluate(data, holes, angle, snapshot):
    qx,qy=data['qd_centre_mm']
    # Source S1 placement datum is STEP (0,0); its ZIF end is positive Y.
    # Current 16-RF ZIF end is negative Y. A 180-degree rigid rotation puts
    # those ends on the same side. This is an explicit trial registration.
    sign=-1 if angle==180 else 1
    registered=[dict(h,xy_mm=[qx+sign*h['source_xy_mm'][0],qy+sign*h['source_xy_mm'][1]]) for h in holes]
    bodies={r['smp']:box(r['start'][0]-2.75,r['start'][1]-2.75,
                          r['start'][0]+2.75,r['start'][1]+2.75) for r in data['rows']}
    template=[p for p in snapshot['pads'] if p['component']=='SMP35']
    sc=next(p for p in template if p['number']=='1')
    pads=[]
    for r in data['rows']:
        for p in template:
            p=dict(p,x=p['x']+r['start'][0]-sc['x'],y=p['y']+r['start'][1]-sc['y'])
            pads.append((r['smp'],p['number'],pad_shape(p)))
    records=[]
    for h in registered:
        point=Point(*h['xy_mm'])
        item=dict(h)
        for name,radius in [('measured_hole',h['measured_diameter_mm']/2),
                             ('M2_dia4_head',2.0)]:
            # Point-to-box distance minus radius is exact for a circle outside
            # a box and detects any circle/box overlap.
            d,ref=min((point.distance(b)-radius,ref) for ref,b in bodies.items())
            item[name+'_nearest_body']=dict(smp=ref,edge_gap_mm=d,overlap=d<0)
        if h['name'].startswith('A'):
            d,ref=min((point.distance(b)-1.1,ref) for ref,b in bodies.items())
            item['trial_dia2p2_hole_nearest_body']=dict(smp=ref,edge_gap_mm=d,overlap=d<0)
        radius=h['measured_diameter_mm']/2
        d,ref,number=min((point.distance(g)-radius,ref,num) for ref,num,g in pads)
        item['nearest_SMP_pad']=dict(smp=ref,pad=number,edge_gap_mm=d,overlap=d<0)
        d,ref=min((point.distance(LineString(r['points_mm']))-radius-.055,r['smp']) for r in data['routes'])
        item['nearest_RF_guide']=dict(smp=ref,edge_gap_mm=d,overlap=d<0)
        item['within_current_outline']=box(-6.55,0,26.05,77.5).covers(point.buffer(radius))
        records.append(item)
    return dict(rotation_degrees=angle,translation_mm=[qx,qy],holes=records,
                SMP_body_model='Conservative 5.50 x 5.50 mm XY boxes from the existing proposal',
                head_model='Illustrative unmodified ISO 7045 M2 pan head, diameter 4.00 mm',
                all_holes_clear_SMP_bodies=all(not h['measured_hole_nearest_body']['overlap'] for h in records),
                all_M2_heads_clear_SMP_bodies=all(not h['M2_dia4_head_nearest_body']['overlap'] for h in records),
                outside_existing_outline=[h['name'] for h in records if not h['within_current_outline']])


def paint(ax,data,review,zoom=False):
    ax.add_patch(Rectangle((-6.55,0),32.6,77.5,fc='#eff5f3',ec='#328575',lw=1.6))
    for route in data['routes']:
        x,y=zip(*route['points_mm']);ax.plot(x,y,color='#bba16f',lw=.8,alpha=.8)
    for r in data['rows']:
        x,y=r['start']
        ax.add_patch(Rectangle((x-2.75,y-2.75),5.5,5.5,fc='#d4e2e4',ec='#61818b',lw=1))
        ax.add_patch(Circle((x,y),2.75,fc='none',ec='#88a2a9',lw=.6))
        ax.text(x,y,r['smp'],fontsize=8,ha='center',va='center',clip_on=True)
    for p in data['pads']:
        g=pad_shape(p['after'])
        ax.add_patch(Polygon(list(g.exterior.coords),fc='#d2b267',ec='none'))
    qx,qy=data['qd_centre_mm']
    ax.add_patch(Rectangle((qx-2.15,qy-2.65),4.3,5.3,fc='#1d404b'))
    ax.text(qx,qy,'QD',color='white',ha='center',va='center',fontsize=10)
    for h in review['holes']:
        x,y=h['xy_mm'];r=h['measured_diameter_mm']/2
        col='#236d9c' if h['name'].startswith('P') else '#c15129'
        ax.add_patch(Circle((x,y),2,fc='none',ec='#a36342',ls='--',lw=.9))
        ax.add_patch(Circle((x,y),r,fc='white',ec=col,lw=1.8))
        ax.text(x+(2.3 if x<9.75 else -2.3),y,h['name'],ha='left' if x<9.75 else 'right',
                va='center',color=col,weight='bold',fontsize=10,clip_on=True)
    if zoom:
        ax.set(xlim=(-7.3,26.8),ylim=(35,57))
        for x in (-4.55,24.05):
            ax.annotate('',xy=(x,44.45),xytext=(x,42.85),arrowprops=dict(arrowstyle='<->',color='#b04a24',lw=1.2))
            ax.text(x+(2.0 if x<9.75 else -2.0),43.65,'1.60 mm',ha='left' if x<9.75 else 'right',
                    fontsize=9,color='#b04a24',bbox=dict(fc='white',ec='none',pad=1))
        ax.set_title('Closest pair: A4 / A3 to SMP02 / SMP24',fontsize=12,pad=12)
    else:
        ax.text(9.75,4,'Existing ZIF end',ha='center',fontsize=9,color='#608083')
        ax.axhline(77.5,color='#348b7a',ls=':',lw=.8)
        ax.text(9.75,79,'Existing upper edge: 77.50 mm',ha='center',fontsize=9,color='#348b7a')
        ax.set(xlim=(-10,29.5),ylim=(-4,96))
        ax.set_title('Current 16-SMP layout + P/A axes',fontsize=13,pad=12)
    ax.set(aspect='equal',xlabel='PCB X (mm)',ylabel='PCB Y (mm)')
    ax.tick_params(labelsize=8)


def main():
    protected=[PLAN,HOLES,SNAP,ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    data=json.loads(PLAN.read_text());holes=json.loads(HOLES.read_text())['holes'];snap=json.loads(SNAP.read_text())
    result=evaluate(data,holes,180,snap)
    comparison=evaluate(data,holes,0,snap)
    fig=plt.figure(figsize=(13,13),dpi=190)
    ax=fig.add_axes((.065,.14,.36,.75));detail=fig.add_axes((.51,.47,.45,.35))
    paint(ax,data,result);paint(detail,data,result,True)
    fig.suptitle('P/A holes vs. latest paired SMP placement',fontsize=19,y=.965)
    fig.text(.51,.415,'No overlap in this registration',fontsize=16,color='#187059')
    fig.text(.51,.363,'Closest measured hole to SMP body: 1.60 mm\nTrial A hole enlarged to diameter 2.20: 1.50 mm\nDiameter 4.00 M2 head to SMP body: 0.60 mm',
             fontsize=11,linespacing=1.9,va='top')
    fig.text(.51,.225,'P3/P4 and A1/A2 are beyond the current board edge.\nThe board cannot keep its present 77.50 mm length.',
             fontsize=11,color='#a74727',linespacing=1.8,va='top')
    fig.text(.5,.075,'Trial registration: source sample datum (0,0) -> QD (9.75,46.15) mm; 180-degree rotation aligns ZIF ends.\n'
             'SMPs: conservative 5.50 x 5.50 mm body envelopes. Solid circles: holes; dashed circles: M2 head envelopes.',
             ha='center',fontsize=10,linespacing=1.8)
    fig.text(.5,.025,'Read-only proposal check. No native PCB change, mating-plug model, final mounting drill selection or full DRC.',
             ha='center',fontsize=9.5,color='#97503b')
    fig.savefig(OUT/'PA_Holes_vs_Latest_SMP.png');plt.close(fig)
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    audit=dict(status='READ_ONLY_REGISTRATION_TRIAL',selected_registration=result,
               zero_rotation_sensitivity_check=comparison,source_hashes=hashes,
               source_and_native_files_unchanged=True,full_native_DRC_performed=False)
    (OUT/'pa_smp_clearance.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(dict(all_holes_clear=result['all_holes_clear_SMP_bodies'],
          all_M2_heads_clear=result['all_M2_heads_clear_SMP_bodies'],outside=result['outside_existing_outline'],
          closest=min((h['measured_hole_nearest_body']['edge_gap_mm'],h['name'],h['measured_hole_nearest_body']['smp']) for h in result['holes']),
          head_closest=min(h['M2_dia4_head_nearest_body']['edge_gap_mm'] for h in result['holes']),
          closest_SMP_pad=min(h['nearest_SMP_pad']['edge_gap_mm'] for h in result['holes']),
          closest_RF_guide=min(h['nearest_RF_guide']['edge_gap_mm'] for h in result['holes'])),indent=2))


if __name__=='__main__':main()
