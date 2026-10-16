"""Reuse the established mask/ground construction with rotated geometry and arcs."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'qd38_carrier_20261010'
sys.path.insert(0,str(OLD))
from route_rf_rotated import arc_line

source=(OLD/'prepare_surface_plan.py').read_text()
source=source.replace("DEST/'negotiated_plan.json'", "DEST/'merged_candidate.json'")
source=source.replace("DEST/'routed_candidate_audit.json'", "DEST/'routing_audit.json'")
source=source.replace('exclusion=box(6.9,40.15,12.6,44.85)',
    "cx,cy=p['sample_center']; cw,ch=p['cavity_mm']; exclusion=box(cx-cw/2-.2,cy-ch/2-.2,cx+cw/2+.2,cy+ch/2+.2)")
source=source.replace('    rf=unary_union(rf_lines)',
    "    rf_lines += [arc_line(a) for a in p.get('arcs',[]) if a['layer']==32]\n    rf=unary_union(rf_lines)")
source=source.replace('    forbidden=unary_union(signal_bottom)',
    "    signal_bottom += [arc_line(a).buffer(a['width']/2+.00001,quad_segs=32) for a in p.get('arcs',[]) if a['layer']==32]\n    forbidden=unary_union(signal_bottom)")
source=source.replace("        direction=90 if s['y']<42.5 else 270", "        direction=s.get('escape_angle_deg',90 if s['y']<42.5 else 270)")
source=source.replace("        for v in p['vias']:\n            if v['low']<=layer<=v['high']:\n                obstacles.append",
    "        for a in p.get('arcs',[]):\n            if a['layer']==layer:\n                obstacles.append(arc_line(a).buffer(a['width']/2+ground_gap+.00001,quad_segs=32))\n        for v in p['vias']:\n            if v['low']<=layer<=v['high']:\n                obstacles.append")
source=source.replace("        exported_ground_gaps[str(layer)]=min(gaps)",
    "        for a in p.get('arcs',[]):\n            if a['layer']==layer:\n                gaps.append(exported.distance(arc_line(a))-a['width']/2-.00001)\n        exported_ground_gaps[str(layer)]=min(gaps)")
source=source.replace("qd_inner_ground_exclusion_mm=[5.7,4.7]", "qd_inner_ground_exclusion_mm=[cw+.4,ch+.4]")
# Shield lands are grounded copper on Bottom and must retain the same 0.20 mm
# signal clearance as the surrounding pour. Measure from an exact land radius;
# keep the established 3 um allowance for native/polygon approximation.
old_shield_check="        if land.distance(forbidden)<.15-1e-7:return 'signal_clearance'"
assert source.count(old_shield_check)==1
source=source.replace(old_shield_check,
    "        if Point(x,y).distance(forbidden)-.125<GROUND_GAP_MM+GROUND_GEOMETRY_GUARD_MM:return 'signal_clearance'")
old_surface_update="    p.update(shield_vias=shields,ground_regions="
assert source.count(old_surface_update)==1
source=source.replace(old_surface_update,
    "    assert len(ring_counts)==16 and all(n>0 for n in ring_counts.values()),ring_counts\n"
    "    minimum_shield_signal_gap=min(Point(v['x'],v['y']).distance(forbidden)-v['diameter']/2 for v in shields)\n"
    "    assert minimum_shield_signal_gap>=GROUND_GAP_MM+GROUND_GEOMETRY_GUARD_MM-1e-9\n"+old_surface_update)
source=source.replace("                 ground_nominal_clearance_mm=GROUND_GAP_MM,ground_geometry_guard_mm=GROUND_GEOMETRY_GUARD_MM,",
    "                 ground_nominal_clearance_mm=GROUND_GAP_MM,ground_geometry_guard_mm=GROUND_GEOMETRY_GUARD_MM,\n"
    "                 shield_nominal_signal_clearance_mm=GROUND_GAP_MM,shield_signal_geometry_guard_mm=GROUND_GEOMETRY_GUARD_MM,\n"
    "                 minimum_shield_signal_gap_mm=minimum_shield_signal_gap,")
namespace={'__name__':'rotation_surfaces_impl','__file__':str(OLD/'prepare_surface_plan.py'),'arc_line':arc_line}
exec(compile(source,str(OLD/'prepare_surface_plan.py'),'exec'),namespace)
namespace['DEST']=HERE
if __name__=='__main__':
    namespace['main']()
