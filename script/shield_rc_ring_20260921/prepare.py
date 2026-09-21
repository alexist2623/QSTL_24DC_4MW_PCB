"""Plan component-perimeter shielding, equal-angle SMP rings and bare solid mounts."""
from pathlib import Path
import json,math,collections
H=Path(__file__).resolve().parent;OLD=H.parent/'shield_spacing_20260921'
# Reuse the read-only baseline parser and clearance predicates. The mutation
# section of the previous revision is deliberately not executed.
prefix=(OLD/'prepare.py').read_text(encoding='utf-8').split('# Ring increments use')[0]
prefix=prefix.replace("OLD=H.parent/'rf50_hdi_milling_20260920'","OLD=H.parent/'shield_spacing_20260921'")
exec(compile(prefix,str(OLD/'prepare.py'),'exec'))
from shapely.geometry import mapping
from shapely.geometry.polygon import orient
rc_envelopes={name:unary_union([padshape(p) for p in n['pads'] if p['component']==name]).convex_hull for name in [f'{k}{i}' for k in ('R','C') for i in range(1,7)]}
rc_forbidden=unary_union(list(rc_envelopes.values()))
original_valid=valid
def valid(x,y,near=True):
    if Point(x,y).buffer(LAND/2,quad_segs=32).intersects(rc_forbidden):return False
    return original_valid(x,y,near)
ring_reports=[]
for ch in range(1,7):
    p=next(p for p in n['pads'] if p['component']==f'SMP{ch}' and p['number']=='1');radius=p['size_x']/2+.33+LAND/2
    track=next(t for t in n['tracks'] if t['net']==f'S{ch}' and min(math.dist((p['x'],p['y']),(t['x1'],t['y1'])),math.dist((p['x'],p['y']),(t['x2'],t['y2'])))<.00005)
    endpoint=max([(track['x1'],track['y1']),(track['x2'],track['y2'])],key=lambda q:math.dist((p['x'],p['y']),q))
    exit_angle=math.atan2(endpoint[1]-p['y'],endpoint[0]-p['x']);count=math.floor(math.pi/math.asin(PITCH/(2*radius)));step=2*math.pi/count
    placed=[];omitted=[]
    for j in range(count):
        angle=exit_angle+step*(j+.5);x=p['x']+radius*math.cos(angle);y=p['y']+radius*math.sin(angle)
        ok=add(x,y,'SMP_RING',component=f'SMP{ch}',angle=math.degrees(angle)%360,radius_mm=radius,angular_grid_index=j)
        (placed if ok else omitted).append(j)
    # Exactly the symmetric two positions at the RF exit are excluded.
    assert omitted==[0,count-1],(ch,count,omitted)
    ring_reports.append(dict(component=f'SMP{ch}',grid_count=count,placed_count=len(placed),step_degrees=360/count,centre_chord_mm=2*radius*math.sin(math.pi/count),radius_mm=radius,exit_angle_degrees=math.degrees(exit_angle),omitted_indices=omitted))
def sample(line,kind,**extra):
    chosen=[];d=0.0
    while d<=line.length:
        pt=line.interpolate(d);x,y=snap(pt.x),snap(pt.y)
        if add(x,y,kind,path_distance_mm=d,**extra):
            chosen.append(d);lo=d;hi=min(d+PITCH,line.length)
            def distance(s):
                q=line.interpolate(s);return math.dist((x,y),(q.x,q.y))
            while hi<line.length and distance(hi)<PITCH:hi=min(hi+.025,line.length)
            if distance(hi)<PITCH:break
            for _ in range(24):
                mid=(lo+hi)/2
                if distance(mid)<PITCH:lo=mid
                else:hi=mid
            d=hi
        else:d+=.002
    return chosen
# Each paired R/C envelope includes the bridges between each component's two
# pads. A perimeter fence never cuts across the inter-pad/body area.
component_perimeters=[]
for ch in range(1,7):
    g=unary_union([rc_envelopes[f'R{ch}'],rc_envelopes[f'C{ch}']]).buffer(.33+LAND/2,quad_segs=64)
    for idx,poly in enumerate(g.geoms if hasattr(g,'geoms') else [g]):
        contour=LineString(poly.exterior.coords);chosen=sample(contour,'RC_PERIMETER',channel=ch,component_group=f'R{ch}/C{ch}')
        component_perimeters.append(dict(channel=ch,part=idx,geometry=mapping(contour),via_distances_mm=chosen))
for net,path in sorted(paths.items()):
    for side in (-1,1):
        g=path.offset_curve(side*OFFSET,quad_segs=64,join_style='round')
        for idx,line in enumerate(g.geoms if hasattr(g,'geoms') else [g]):
            chosen=sample(line,'RF_FENCE',net_along=net,side=side)
            fences.append(dict(net=net,side=side,part=idx,path_length_mm=line.length,via_distances_mm=chosen))
minpair=min(math.dist((a['x'],a['y']),(b['x'],b['y']))-LAND for i,a in enumerate(vias) for b in vias[:i]);assert minpair>=GAP-2*UNIT
local_counts={name:sum(Point(v['x'],v['y']).distance(g)<.65 for v in vias) for name,g in rc_envelopes.items()};assert min(local_counts.values())>=4,local_counts
mounts=[p for p in n['pads'] if p['component'] is None];assert len(mounts)==6
mount_opening=unary_union([padshape(p).buffer(.35,quad_segs=48) for p in mounts])
openings={}
for layer in (37,38):
    prev=unary_union([r['geometry'] for r in regions if r['layer']==layer and r['name'].startswith('SURFACE_MASK_OPEN_')])
    openings[layer]=prev.union(mount_opening)
plan.update(source_sha256=sha(source),shield_vias=vias,fences=fences,SMP_rings=ring_reports,RC_keepouts={k:mapping(v) for k,v in rc_envelopes.items()},RC_perimeters=component_perimeters,Top_mask_opening=mapping(openings[37]),Bottom_mask_opening=mapping(openings[38]),mount_mask_removed=True,mount_polygon_connect='Direct')
(H/'plan.json').write_text(json.dumps(plan,indent=2))
report=dict(source_sha256=sha(source),shield_vias=len(vias),counts=dict(collections.Counter(v['kind'] for v in vias)),min_land_edge_gap_mm=minpair,min_trace_edge_gap_mm=min(v['rf_copper_edge_gap_mm'] for v in vias),SMP_rings=ring_reports,RC_nearby_via_counts=local_counts,RC_interpad_via_intrusions=0,mounting_holes=6)
(H/'preflight.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
req=P/'docs/DESIGN_REQUIREMENTS.md';s=req.read_text(encoding='utf-8')
addition='''- Extend shield fences around R1-R6 and C1-C6. Treat each two-pad convex hull (including the inter-pad bridge/body area) as a forbidden region for shield-via lands; surround the outside instead of cutting between the pads.
- Active SMP rings must use equal angular increments and symmetric RF exits. Use a 14-position angular grid (25.7142857 degrees) at the retained nominal 0.955 mm radius; omit only the two positions symmetrically straddling the RF exit. The remaining 12 vias per ring have approximately 0.425 mm chord spacing, close to 0.40 mm straight-fence spacing.
- Latest mechanical-hole instruction supersedes the earlier protected mounting mask: expose all six mounting lands and their surrounding ring on both solder-mask layers. Connect these GND mounting pads directly to every GND polygon with no thermal spokes/voids. SMP solder-control masks and normal SMD paste remain unchanged; mounting paste remains disabled.
'''
if 'Extend shield fences around R1-R6' not in s:s=s.replace('## Vias and validation\n','## Vias and validation\n\n'+addition)
s=s.replace('SMP signal/ground pins and mounting lands','SMP signal/ground pins').replace('removing their solder mask. Retain solder-control masks at these sites.','removing their solder mask. Retain SMP solder-control masks; the later explicit mounting-hole request now removes mounting masks.')
req.write_text(s,encoding='utf-8')
ag=R/'AGENTS.md';s=ag.read_text(encoding='utf-8')
if 'Surround R/C footprints' not in s:s+='\nSurround R/C footprints with shield vias without crossing the two-pad/inter-pad body envelopes. SMP rings use an equal-angle grid with symmetric RF escape gaps. Remove solder mask around all six mounting holes on both faces and use direct GND connections without thermal relief; this supersedes the earlier mounting-mask preservation instruction. Preserve SMP masks and keep mounting paste disabled.\n'
ag.write_text(s,encoding='utf-8')
# Copy validated audit infrastructure, changing only count/report expectations.
for name in ('audit_connectivity.py','verify_final.py','AuditPaste.pas','ReopenAudit.pas','read_drc.py','fabrication_notes.py','publish_outputs.py','verify_fabrication.py'):
    s=(OLD/name).read_text(encoding='utf-8').replace('shield_spacing_20260921','shield_rc_ring_20260921').replace('Shield_spacing_DRC.html','Shield_RC_Ring_DRC.html').replace('shield_spacing_reopen_check.txt','shield_rc_ring_reopen_check.txt').replace('Shield_spacing_validation.json','Shield_RC_Ring_validation.json')
    if name=='verify_final.py':
        s=s.replace('(22,147,37,347)',f'(22,147,37,{60+len(vias)})').replace('len(shield)==287',f'len(shield)=={len(vias)}')
        s=s.replace('solid[\'SCOPE1EXPRESSION\']=="IsVia And InNet(\'GND\')"','solid[\'SCOPE1EXPRESSION\']=="(IsVia Or (IsPad And Not InComponent(\'*\'))) And InNet(\'GND\')"')
    if name in ('publish_outputs.py','verify_fabrication.py'):s=s.replace('len(shield)==287',f'len(shield)=={len(vias)}').replace('len(holes)==287',f'len(holes)=={len(vias)}').replace('287 GND shields',f'{len(vias)} GND shields')
    if name=='fabrication_notes.py':
        s=s.replace('287 saved L5-L6 vias',f'{len(vias)} saved L5-L6 vias').replace('Circular blind-via fences surround each active SMP signal centre, with local gaps at RF exits and through holes','Equal-angle 14-position grids surround each active SMP centre; only two symmetric RF-exit positions are omitted, leaving 12 vias and approximately 0.425 mm centre chords').replace('No via, SMP or mounting-pad paste apertures.','No via, SMP or mounting-pad paste apertures. R/C perimeter fences avoid each two-pad bridge/body envelope. All six mounting lands and their surrounding rings are unmasked on both faces and directly joined to GND without thermal relief.')
    (H/name).write_text(s,encoding='utf-8')
# Replace only shield vias, mounting mask openings, and the mounting connection
# scope; signal copper, component placement and all other masks stay unchanged.
pas=(OLD/'ApplyShieldSpacing.pas').read_text(encoding='utf-8')
pas=pas.replace('shield_spacing_20260921','shield_rc_ring_20260921').replace('N<>78','N<>287')
start=pas.index('AddShield(B,GN,');end=pas.index("  Mark('NEW_SHIELDS",start)
pas=pas[:start]+'\n'.join(f"AddShield(B,GN,{round(v['x']/UNIT)},{round(v['y']/UNIT)});" for v in vias)+'\n'+pas[end:]
pas=pas.replace('NEW_SHIELDS=287',f'NEW_SHIELDS={len(vias)}')
pas=pas.replace('N,J,NP:Integer;','N,J,NP,NM,NR:Integer;Reg:IPCB_Region;Regions:Array[0..15] Of IPCB_Region;Rule:IPCB_Rule;Solid:IPCB_PolygonConnectStyleRule;Pad:IPCB_Pad;Comp:IPCB_Component;C:IPCB_Contour;G:IPCB_GeometricPolygon;')
before_pre='''
 Solid:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));Rule:=I.FirstPCBObject;
 While Rule<>Nil Do Begin If Rule.Name='ZIF24V2_GND_VIA_SOLID' Then Solid:=Rule;Rule:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 If Solid=Nil Then Begin Mark('NO_SOLID_RULE');Exit;End;
 Solid.Scope1Expression:='(IsVia Or (IsPad And Not InComponent(''*''))) And InNet(''GND'')';Solid.Comment:='Solid GND shield vias and free mounting pads; component pads retain their rules.';Solid.ConnectStyle:=eDirectConnectToPlane;
 B.InvalidateScopeTester;B.ValidateScopeTester;
 NM:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));Pad:=I.FirstPCBObject;
 While Pad<>Nil Do Begin Comp:=Pad.Component;Rule:=B.FindDominantRuleForObject(Pad,eRule_PolygonConnectStyle);If Comp=Nil Then Begin Inc(NM);If Rule=Nil Then Begin Mark('MOUNT_RULE_MISSING');Exit;End;If Rule.Name<>Solid.Name Then Begin Mark('MOUNT_RULE_NOT_DOMINANT');Exit;End;End Else If Rule<>Nil Then If Rule.Name=Solid.Name Then Begin Mark('COMPONENT_PAD_MATCHED_MOUNT_RULE');Exit;End;Pad:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Mark('MOUNT_SOLID_RULE_MATCHES='+IntToStr(NM));If NM<>6 Then Exit;
 NR:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));Reg:=I.FirstPCBObject;
 While Reg<>Nil Do Begin If Pos('SURFACE_MASK_OPEN_',Reg.Name)=1 Then Begin Regions[NR]:=Reg;Inc(NR);End;Reg:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
'''
pas=pas.replace(' PCBServer.PreProcess;',before_pre+' PCBServer.PreProcess;')
masklines=['For J:=0 To NR-1 Do B.RemovePCBObject(Regions[J]);']
for layer,geom in openings.items():
    for idx,poly in enumerate(geom.geoms if hasattr(geom,'geoms') else [geom]):
        poly=orient(poly,sign=1);masklines+=['G:=PCBServer.PCBGeometricPolygonFactory;']
        for hole,ring in [(False,poly.exterior)]+[(True,r) for r in poly.interiors]:
            masklines+=['C:=PCBServer.PCBContourFactory;']+[f'C.AddPoint({round(x/UNIT)},{round(y/UNIT)});' for x,y in list(ring.coords)[:-1]]+[f'G.AddContourIsHole(C,{hole});']
        masklines += [f"Reg:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);Reg.Kind:=eRegionKind_Copper;Reg.Layer:={'eTopSolder' if layer==37 else 'eBottomSolder'};Reg.Name:='SURFACE_MASK_OPEN_{layer}_{idx}';Reg.SetGeometricPolygon(G);B.AddPCBObject(Reg);"]
pas=pas.replace('  For J:=0 To N-1 Do B.RemovePCBObject(Dead[J]);','  For J:=0 To N-1 Do B.RemovePCBObject(Dead[J]);\n'+'\n'.join(masklines))
(H/'ApplyShieldSpacing.pas').write_text(pas,encoding='utf-8')
