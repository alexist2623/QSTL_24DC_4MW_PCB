"""Read-only comparison of full QD component/cavity rotation with fixed seven SMP rows."""
import copy
import json
from shapely.affinity import rotate
from shapely.ops import unary_union
import through_dc_smp_side_feasibility as base

preserved_files=[base.H/'seven_rows_3222223_feasibility.json',base.H/'through_dc_smp_side_feasibility.json']
preserved_hashes={str(p):base.sha(p) for p in preserved_files if p.exists()}
original_pads=copy.deepcopy(base.QD)
original_cavity=base.cavity
results={}
for angle in (0,90):
    pads=[]
    for original in original_pads:
        pad=dict(original)
        if angle:
            pad['x']=9.75-(original['y']-42.5)
            pad['y']=42.5+(original['x']-9.75)
            pad['rotation']=(original['rotation']+90)%360
        pads.append(pad)
    base.QD=pads
    base.cavity=rotate(original_cavity,angle,origin=(9.75,42.5))
    result=base.evaluate()
    field=unary_union([base.geom(p) for p in pads])
    cavity_bounds=base.cavity.bounds
    result.update(rotation_deg_CCW=angle,cavity_bounds_mm=list(cavity_bounds),
                  cavity_width_height_mm=[cavity_bounds[2]-cavity_bounds[0],cavity_bounds[3]-cavity_bounds[1]],
                  QD_pad_union_bounds_mm=list(field.bounds),
                  minimum_QD_pad_to_cavity_mm=min(base.geom(p).distance(base.cavity) for p in pads),
                  QD_pad_field_to_left_right_board_edge_mm=[field.bounds[0],base.board.bounds[2]-field.bounds[2]],
                  cavity_to_left_right_board_edge_mm=[cavity_bounds[0],base.board.bounds[2]-cavity_bounds[2]],
                  minimum_QD_pad_board_edge_mm=field.distance(base.board.boundary),
                  rotated_pads=[{key:p[key] for key in ('number','net','x','y','rotation','size_x','size_y')} for p in pads])
    results[str(angle)]=result
base.QD=original_pads
base.cavity=original_cavity
report=dict(native_sha256=base.before,board_bounds_mm=list(base.board.bounds),rotation_origin_mm=[9.75,42.5],
            row_counts=[3,2,2,2,2,2,3],comparisons=results,
            interpretation='Full QD component pads, their orientations and milling cavity are rotated together. Every pin number and net moves with its pad. Existing DC vias/routes, RF/bias components, ground exclusions, masks and shields are not rotated in this read-only study and would require redesign. Opposite-face body projections are not physical collision evidence; all SMP multilayer drills/lands are checked against QD copper.',
            source_unchanged=base.sha(base.PCB)==base.before,
            earlier_studies_unchanged={name:base.sha(base.Path(name))==value for name,value in preserved_hashes.items()})
(base.H/'qd90_feasibility.json').write_text(json.dumps(report,indent=2))
for angle,result in results.items():
    print(json.dumps({key:result[key] for key in ['rotation_deg_CCW','minimum_SMP_land_to_QD_pad','minimum_SMP_hole_to_cavity','minimum_body_projection_to_cavity_mm','minimum_body_projection_to_QD_pad_mm','body_projection_QD_pad_overlap_mm2','minimum_QD_pad_to_cavity_mm','QD_pad_union_bounds_mm','QD_pad_field_to_left_right_board_edge_mm','cavity_width_height_mm']},indent=2))
print('SAVED',str(base.H/'qd90_feasibility.json'))
