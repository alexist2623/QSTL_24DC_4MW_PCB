"""Read saved copper and publish final reports; never modifies Altium documents."""
from pathlib import Path
import sys,json,math,csv,shutil,collections,hashlib,importlib.util
from shapely.geometry import LineString,Point
H=Path(__file__).resolve().parent;W=H.parent/'_support';R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';D=P/'docs';B='QSTL_24DC_4MW_PCB'
n=json.loads((H/'native_render_snapshot.json').read_text());board_hash=hashlib.sha256((P/(B+'.PcbDoc')).read_bytes()).hexdigest()
assert n['source_sha256']==board_hash
reports={key:json.loads((D/file).read_text()) for key,file in [('native','validation.json'),('connection','connection_validation.json'),('angle','RF_position_and_angles.json'),('model','model_validation.json')]}
assert all(r['passed'] and r['pcb_sha256']==board_hash for r in reports.values())
dc=json.loads((H/'dc_routes.json').read_text());rf=json.loads((H/'rf_routes.json').read_text())
g=json.loads((H/'geometry.json').read_text());e=json.loads((H/'expected.json').read_text())
def save(name,data):
    (D/name).write_text(json.dumps(dict(pcb_sha256=board_hash,**data),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def line(t):return LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])])
def length(t):return math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])
dt=[t for t in n['tracks'] if t['net'].startswith('ZIF') and t['layer'] in (2,4)]
layers={net:sorted({t['layer'] for t in dt if t['net']==net}) for net in sorted({t['net'] for t in dt})}
assert len(layers)==24 and all(len(v)==1 for v in layers.values())
via_classes=collections.Counter();extra=[]
for v in n['vias']:
    found=[p for p in n['pads'] if p['net']==v['net'] and math.dist((p['x'],p['y']),(v['x'],v['y']))<.00002]
    if found:
        assert len(found)==1 and found[0]['component'].startswith(('Q','R','C'))
        via_classes['QD' if found[0]['component']=='Q1' else 'R_C']+=1
    else:
        found=[t for t in n['tracks'] if t['net']==v['net'] and t['layer']==1 and min(math.dist((t['x1'],t['y1']),(v['x'],v['y'])),math.dist((t['x2'],t['y2']),(v['x'],v['y'])))<.00002]
        if found:via_classes['ZIF_fanout']+=1
        else:extra.append(v)
assert not extra and dict(via_classes)=={'R_C':24,'QD':24,'ZIF_fanout':24}
trace_min=min(line(a).distance(line(b))-(a['width']+b['width'])/2 for i,a in enumerate(dt) for b in dt[:i] if a['net']!=b['net'] and a['layer']==b['layer'])
obstacles=[(Point(v['x'],v['y']),v['diameter']/2,v['net']) for v in n['vias']]
obstacles += [(Point(p['x'],p['y']),p['size_x']/2,p['net']) for p in n['pads'] if p['layer']==74 and abs(p['size_x']-p['size_y'])<.00001]
obstacle_min=min(line(t).distance(pt)-radius-t['width']/2 for t in dt for pt,radius,net in obstacles if t['net']!=net)
holes=[]
for p in n['pads']:
    if p['component'] is None and p['hole']>3.9:
        gap=min(line(t).distance(Point(p['x'],p['y']))-p['size_x']/2-t['width']/2 for t in dt)
        holes.append(dict(center_mm=[p['x'],p['y']],minimum_DC_copper_clearance_mm=gap))
assert len(holes)==2 and min(x['minimum_DC_copper_clearance_mm'] for x in holes)>.36
oldspec=importlib.util.spec_from_file_location('old_native',W/'zif_revision_v2/render_native_layout.py');old=importlib.util.module_from_spec(oldspec);oldspec.loader.exec_module(old)
old.SOURCE=H/'before_models.PcbDoc';prior=old.read_native();old_dc=[t for t in prior['tracks'] if t['net'].startswith('ZIF') and t['layer'] in (2,4)]
dc_report=dict(passed=True,nets=24,internal_layers_by_net=layers,extra_DC_transition_vias=extra,via_classification=dict(via_classes),
               internal_track_segments=len(dt),previous_internal_track_segments=len(old_dc),removed_segments=len(old_dc)-len(dt),
               total_planar_DC_length_mm=sum(map(length,dt)),previous_total_planar_DC_length_mm=sum(map(length,old_dc)),
               central_bus=dc['central_bus'],same_layer_trace_edge_clearance_min_mm=trace_min,trace_to_through_pad_or_via_min_mm=obstacle_min,
               large_GND_holes=holes,zif_to_target=dc['zif_to_target'],tracks_by_layer=dict(collections.Counter(t['layer'] for t in dt)),
               width_mm=.125,Top_ZIF_escape_width_mm=.15,schematic_swap='ZIF23 -> R3.2, ZIF25 -> R2.2',
               note='Every DC net has one internal routing layer. Through vias remain only at QD/R/C pads and ZIF fanouts.')
save('DC_simplified.json',dc_report)
save('DC_direct.json',dc_report)
channels={}
for k,plan in rf['channels'].items():
    nn={f'S{k}',f'MW{k}'};ts=[t for t in n['tracks'] if t['net'] in nn];ars=[a for a in n['arcs'] if a['net'] in nn]
    measured=sum(map(length,ts))+sum(a['radius']*math.radians((a['end_angle']-a['start_angle'])%360) for a in ars)
    pad=next(p for p in n['pads'] if p['component']==f'R{k}' and p['number']=='1');pt=Point(pad['x'],pad['y'])
    interior=[t for t in ts if t['net']==f'MW{k}' and line(t).distance(pt)<.00002 and .001<line(t).project(pt)<line(t).length-.001]
    assert len(interior)==1 and abs(measured-plan['main_length_mm'])<.0001
    channels[k]=dict(QD_pin=plan['QD_pin'],input=plan['input'],capacitor=plan['capacitor'],bias=plan['bias'],
                     native_planar_copper_length_mm=measured,resistor_RF_pad_on_main_line=True,resistor_branch_stub_mm=0)
save('RF_stubless.json',dict(passed=True,channels=channels,RF_layer=32,RF_arcs=18,RF_tracks=30,shield_vias=0))
save('RF_delay.json',dict(channels=channels,delay_matching_deferred_by_user=True,
                        note='Planar track/arc lengths only, excluding component internals and via barrels. No 1 ps or 50 ohm verification is claimed.'))
save('RF_surface_stack.json',dict(from_QD_side=['L6 RF','L5 GND','L4 DC','L3 GND','L2 DC','L1 GND'],
                                physical_stack=n['copper_layers'],dielectric_dimensions_unchanged=True,ground_polygons=[1,3,5],
                                RF_width_mm=next(t['width'] for t in n['tracks'] if t['net']=='S1'),DC_width_mm=.125))
target_to_zif={v:int(k) for k,v in dc['zif_to_target'].items()};qd_to_ch={int(v):int(k) for k,v in g['rf_qd_map'].items()}
with (D/'PIN_MAPPING.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f);w.writerow(['QD_pad','Role','ZIF_pin','Reference_carrier_bond_pad','SMP','Bias_resistor','Series_capacitor','QD_net'])
    for qd in range(1,25):
        ch=qd_to_ch.get(qd);z=target_to_zif[f'R{ch}-2' if ch else f'Q1-{qd}']
        w.writerow([qd,'RF+DC_bias' if ch else 'DC',z,z if z<=12 else z-2,f'SMP{ch}' if ch else '',f'R{ch}' if ch else '',f'C{ch}' if ch else '',e['pin_net_map'][f'Q1-{qd}']])
shutil.copy2(P/'work/rf6_schematic_compile.txt',D/'native_schematic_compile.txt')
shutil.copy2(P/'work/rf6_reopen_check.txt',D/'native_reopen_check.txt')
print(json.dumps(dict(extra_transition_vias=len(extra),internal_DC_segments=len(dt),removed_segments=len(old_dc)-len(dt),DC_trace_min_mm=trace_min,ground_holes=holes),indent=2))
