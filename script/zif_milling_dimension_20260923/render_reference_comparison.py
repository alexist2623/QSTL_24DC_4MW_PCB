"""Compare the reference mechanical pocket and current cavity using native datums."""
from pathlib import Path
import hashlib
import json
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from gerbonara import GerberFile

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'QSTL_24DC_4MW_PCB'
OUT = PROJECT / 'Mechanical_Assembly' / 'Dimensions'
ref, adapter = json.loads((Path(__file__).parent / 'reference_geometry.json').read_text())
cur = json.loads((ROOT / 'script' / 'mechanical_assembly_20260921' / 'pcb_geometry.json').read_text())
measure = json.loads((OUT / 'ZIF_to_milling_distance.json').read_text())
digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert digest(ref['source']) == ref['sha256']
assert digest(adapter['source']) == adapter['sha256']
assert digest(PROJECT / 'QSTL_24DC_4MW_PCB.PcbDoc') == cur['pcb_sha256'] == measure['pcb_sha256']
offset = [min(p[0] for p in ref['board_outline_mm']), min(p[1] for p in ref['board_outline_mm'])]
relative = lambda p: [p[i]-offset[i] for i in range(2)]
datum = relative(next(c['xy_mm'] for c in ref['components'] if c['name']=='Dsub'))
sample = relative(next(c['xy_mm'] for c in ref['components'] if c['name']=='Sample'))
fills = [f for f in ref['fills'] if f['layer']==58 and f['component_index']==65535]
assert len(fills)==1
f = fills[0]['xyxy_mm']
bbox = [f[0]-offset[0], f[1]-offset[1], f[2]-offset[0], f[3]-offset[1]]
centre = [(bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2]
delta = [centre[i]-datum[i] for i in range(2)]
distance = math.dist(datum, centre)
ref_cam = Path(ref['source']).parent / 'Project Outputs for narrow_v4' / 'narrow_v2.GM2'
g = GerberFile.open(ref_cam)
(gx0, gy0), (gx1, gy1) = g.bounding_box()
gerber_centre = [(gx0+gx1)/2, (gy0+gy1)/2]
assert math.dist(gerber_centre, centre) < .008
assert abs((gx1-gx0)-4.5) < 1e-5 and abs((gy1-gy0)-5) < 1e-5
current_datum = measure['zif_J1_placement_origin_xy_mm']
current_centre = measure['milling_centre_xy_mm']
report = {
    'reference_pcb': ref['source'], 'reference_sha256': ref['sha256'],
    'reference_connector': 'Dsub, 581-M25-113L461; no ZIF connector on this PCB',
    'coordinate_system': 'mm relative to board lower-left; XY planar distance',
    'Dsub_placement_origin_mm': datum, 'Sample_placement_origin_mm': sample,
    'Mechanical_2_fill_bbox_mm': bbox, 'Mechanical_2_fill_centre_mm': centre,
    'Dsub_to_Mechanical_2_centre_dx_dy_mm': delta,
    'Dsub_to_Mechanical_2_centre_distance_mm': distance,
    'Dsub_to_Sample_placement_origin_distance_mm': math.dist(datum, sample),
    'exported_GM2': str(ref_cam), 'exported_GM2_centre_mm': gerber_centre,
    'exported_GM2_resolution_mm': .01,
    'reference_note_conflict': 'Changes.txt requests a 3.5 x 4.0 mm cavity; saved PCB Mechanical 2 and exported GM2 both contain a 4.5 x 5.0 mm rectangle.',
    'current_ZIF_origin_to_cavity_distance_mm': measure['placement_origin_to_milling_centre_mm'],
    'current_cavity_shift_from_reference_mm': [current_centre[i]-centre[i] for i in range(2)],
    'separate_ZIF_adapter': {'source': adapter['source'], 'sha256': adapter['sha256'], 'observation': 'ZIF-to-ZIF adapter with no sample component or Mechanical 2 pocket fill.'},
    'all_source_files_unchanged': True,
}
(OUT / 'Reference_to_milling_comparison.json').write_text(json.dumps(report, indent=2)+'\n')

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none'})
blue, orange, ink = '#176bb5', '#d36b13', '#20313f'
fig = plt.figure(figsize=(12.6, 10.4), facecolor='white')
fig.text(.045, .956, 'REFERENCE / CURRENT PCB', color=ink, fontsize=22, weight='bold')
fig.text(.045, .925, 'Connector placement origin to pocket centre  |  XY planar distance in mm', color='#64727f', fontsize=11)

def panel(rect, title, sub, pads, comps, origin, pocket, shift, is_reference):
    ax = fig.add_axes(rect)
    ax.set_aspect('equal');ax.set_xlim(-7, 28);ax.set_ylim(-2, 71);ax.axis('off')
    ax.set_title(title, loc='center', fontsize=15, color=ink, weight='bold', pad=19)
    ax.text(9.75, 70.15, sub, ha='center', fontsize=8.8, color='#677780')
    ax.add_patch(Rectangle((0,0), 19.5,67.9,fc='#e5eee9',ec='#466558',lw=1.3))
    ax.plot([9.75,9.75],[0,67.9],color='#a1b0a7',lw=.65,ls='-.')
    for p in pads:
        vals=p['coords_mm'];px,py=vals[0]-shift[0],vals[1]-shift[1];sx,sy=vals[2:4];hole=vals[8]
        if hole>0:
            ax.add_patch(Circle((px,py),max(sx,sy)/2,fc='#c8cfbc',ec='#889174',lw=.45))
            ax.add_patch(Circle((px,py),hole/2,fc='white',ec='#65736b',lw=.5))
        elif p['component'] in ['Sample','Q1','J1']:
            ax.add_patch(Rectangle((px-sx/2,py-sy/2),sx,sy,angle=p['rotation'],rotation_point='center',fc='#c8ab68',ec='none'))
    for name, xy in comps:
        if name.startswith('SMP'):
            ax.add_patch(Circle((xy[0]-shift[0],xy[1]-shift[1]),2.75,fc='none',ec='#90a095',lw=.65))
    if is_reference:
        ax.add_patch(Rectangle((bbox[0],bbox[1]),bbox[2]-bbox[0],bbox[3]-bbox[1],fc='#fff0dc',ec=orange,lw=1.4))
        ax.plot(*sample,marker='x',color='#697480',ms=6,mew=1)
        ax.annotate('Sample\norigin',xy=sample,xytext=(21,46.4),color='#697480',fontsize=8.6,arrowprops={'arrowstyle':'-','color':'#697480','lw':.7})
        ax.annotate('Pocket\ncentre',xy=pocket,xytext=(21,39.0),color=orange,fontsize=8.6,arrowprops={'arrowstyle':'-','color':orange,'lw':.9})
        ax.plot([origin[0],pocket[0]],[origin[1],pocket[1]],color=orange,lw=1,ls='--')
        ax.text(9.75,7.4,'D-sub datum',ha='center',color=blue,fontsize=9,weight='bold')
    else:
        bb=measure['zif_J1_model_envelope_xy_mm']
        ax.add_patch(Rectangle((bb[0],bb[1]),bb[2]-bb[0],bb[3]-bb[1],fc='none',ec='#4e5d69',lw=1.1))
        ax.add_patch(FancyBboxPatch((7.6,40.35),4.3,4.3,boxstyle='round,pad=0,rounding_size=0.5',fc='#fff0dc',ec=orange,lw=1.4,ls='--'))
        ax.annotate('Milling\ncentre',xy=pocket,xytext=(21,46.4),color=orange,fontsize=8.6,arrowprops={'arrowstyle':'-','color':orange,'lw':.9})
        ax.text(9.75,1.4,'ZIF J1 datum',ha='center',color=blue,fontsize=9,weight='bold')
    for p in [origin,pocket]:
        ax.plot([-4.5,p[0]],[p[1],p[1]],color=blue,lw=.75)
    ax.plot(*origin,marker='+',ms=11,mew=1.6,color=blue)
    ax.plot(*pocket,marker='+',ms=11,mew=1.6,color=orange)
    ax.annotate('',xy=(-3.7,pocket[1]),xytext=(-3.7,origin[1]),arrowprops={'arrowstyle':'<->','color':blue,'lw':1.3,'shrinkA':0,'shrinkB':0})
    ax.text(-4.9,(origin[1]+pocket[1])/2,f'Y = {pocket[1]-origin[1]:.3f} mm',rotation=90,ha='center',va='center',color=blue,fontsize=13,weight='bold',bbox={'fc':'white','ec':'none','pad':4})
    return ax

panel([.035,.20,.43,.65],'ORIGINAL REFERENCE','Narrow_v4 (May2024) / narrow_v2.PcbDoc',ref['pads'],[(c['name'],c['xy_mm']) for c in ref['components']],datum,centre,offset,True)
mm=lambda v:float(v.removesuffix('mil'))*.0254
panel([.54,.20,.43,.65],'CURRENT PCB','QSTL_24DC_4MW_PCB',cur['pads'],[(c['SOURCEDESIGNATOR'],[mm(c['X']),mm(c['Y'])]) for c in cur['components']],current_datum,current_centre,[0,0],False)
fig.text(.074,.17,f'Straight-line distance: {distance:.3f} mm',color=orange,fontsize=15,weight='bold')
fig.text(.074,.14,f'X offset: {delta[0]:.3f} mm    |    Y offset: {delta[1]:.3f} mm',color=ink,fontsize=10)
fig.text(.074,.117,'Pocket centre: X 8.475, Y 41.025\nD-sub origin: X 9.750, Y 4.850',va='top',color='#64727f',fontsize=10,linespacing=1.5)
fig.text(.574,.17,'Straight-line distance: 37.650 mm',color=blue,fontsize=15,weight='bold')
fig.text(.574,.14,'X offset: 0.000 mm    |    Y offset: 37.650 mm',color=ink,fontsize=10)
fig.text(.574,.117,'Milling centre: X 9.750, Y 42.500\nZIF origin: X 9.750, Y 4.850',va='top',color='#64727f',fontsize=10,linespacing=1.5)
fig.text(.045,.054,'Reference Sample origin is not the Mechanical 2 pocket centre. The reference connector is D-sub, not ZIF.',color=ink,fontsize=10)
fig.text(.045,.030,'Native PCB + GM2 geometry verified. Reference pocket: 4.5 x 5.0 mm; Changes.txt states 3.5 x 4.0 mm. Source files unchanged.',color='#64727f',fontsize=9)
fig.savefig(OUT/'Reference_to_milling_comparison.png',dpi=180,facecolor='white')
fig.savefig(OUT/'Reference_to_milling_comparison.svg',facecolor='white')
assert digest(ref['source']) == ref['sha256']
print(json.dumps({k:v for k,v in report.items() if k not in ['separate_ZIF_adapter']},indent=2))
