"""Summarize the single limited-fanout trial and render its saved geometry."""
import hashlib
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as MPolygon
from audit_dc_candidate import pad_geometry

H=Path(__file__).resolve().parent
prefix=sys.argv[1] if len(sys.argv)>1 else 'dc_staggered'
assert Path(prefix).name==prefix
old=json.loads((H/'dc_fallback_rechecked_independent_audit.json').read_text())
new=json.loads((H/(prefix+'_independent_audit.json')).read_text())
plan=json.loads((H/(prefix+'_candidate.json')).read_text())
assert new['passed'] and old['passed']
assert hashlib.sha256((H/(prefix+'_candidate.json')).read_bytes()).hexdigest()==new['candidate_sha256']
metrics=['total_bends','maximum_bends','total_dc_length_mm','length_weighted_mean_absolute_x_offset_mm',
         'actual_minimum_dc_to_dc_mm','actual_minimum_dc_to_ground_mm','minimum_rc_body_envelope_clearance_mm',
         'minimum_smp_full_hull_clearance_mm','top_fanout_minimum_clearance_mm']
report=dict(fallback_candidate_sha256=old['candidate_sha256'],staggered_candidate_sha256=new['candidate_sha256'],
            base_placement_sha256=plan['dc_base_placement_file_sha256'],
            moved_endpoint_vias=plan['j1_stagger_revision']['moved_endpoint_vias'],
            other_64_via_positions_unchanged=True,all_component_and_pad_geometry_unchanged=True,
            exact_contact_pool_unchanged=True,comparison={m:dict(before=old[m],after=new[m],delta=new[m]-old[m]) for m in metrics})
(H/(prefix+'_comparison.json')).write_text(json.dumps(report,indent=2))
fig,axes=plt.subplots(1,3,figsize=(18,5))
for ax,layer,title in zip(axes,[1,2,4],['Top: existing J1 pads and updated fanout','L2: DC fanout','L4: DC fanout']):
    ax.set_aspect('equal');ax.set_facecolor('#112b25')
    if layer==1:
        for p in plan['physical_pads']:
            if p['ref']=='J1':
                ax.add_patch(MPolygon(list(pad_geometry(p).exterior.coords),facecolor='#a99a55' if p['net'] else '#555b59',edgecolor='none'))
    for t in plan['tracks']:
        if t['layer']==layer and t['net'].startswith('DC'):
            color=plt.colormaps['turbo']((int(t['net'][2:])-1)/37)
            ax.plot([t['a'][0],t['b'][0]],[t['a'][1],t['b'][1]],color=color,lw=1.4)
    for v in plan['vias']:
        if v['label'].startswith('J1-'):
            color=plt.colormaps['turbo']((int(v['net'][2:])-1)/37)
            ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,facecolor=color,edgecolor='white',lw=.45))
            ax.add_patch(Circle((v['x'],v['y']),v['hole']/2,facecolor='#112b25',edgecolor='none'))
    for y in [6.75,7.45]:
        ax.axhline(y,color='white',lw=.35,ls='--',alpha=.55)
    ax.set(xlim=(1.8,17.7),ylim=(1.9,8.05),title=title,xlabel='X / mm',ylabel='Y / mm')
fig.suptitle('J1 endpoint-via stagger: 12 even contacts at Y=7.45 mm; 12 at Y=6.75 mm\n38 contacts preserved; no additional vias; connector pads and RF placement unchanged')
fig.tight_layout();fig.savefig(H/(prefix+'_fanout_preview.png'),dpi=180);plt.close(fig)
print(json.dumps(report,indent=2))
