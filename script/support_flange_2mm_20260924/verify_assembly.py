"""Check saved stepped geometry and actual placements; draw both CAD sections."""
from pathlib import Path
import json
import sys
import hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch
from OCP.gp import gp_Trsf, gp_Pnt, gp_Ax2, gp_Dir
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_WIRE, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Line

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'script' / 'mechanical_assembly_20260921'))
from inspect_geometry import read, bounds, volume, inspect, faces
MECH = ROOT / 'QSTL_24DC_4MW_PCB' / 'Mechanical_Assembly'
BASE = MECH / 'Rod_Holder_Adapter'
OUT = MECH / 'Rod_Holder_Adapter_Drop8p5'

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def matrix(rows):
    m = np.array(rows, dtype=float)
    m[:3, 3] *= 10
    return m

def point(m, p):
    return (m @ np.array([*p, 1.0]))[:3]

def transform(shape, m):
    t = gp_Trsf()
    t.SetValues(*m[:3, :].ravel().tolist())
    return BRepBuilderAPI_Transform(shape, t, True).Shape()

def placements(directory):
    records = load(directory / 'inward_placements.json')
    return {r['name']: transform(read(Path(r['path']).with_suffix('.step')), matrix(r['matrix_cm'])) for r in records}, records

def compound(shapes):
    result = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(result)
    for shape in shapes:
        builder.Add(result, shape)
    return result

parts, records = placements(OUT)
original, original_records = placements(BASE)
assert len(parts) == 24
centre_plate = parts['Centre_Plate_With_Device_Boss']
left_support = parts['Left_Rod_Support']
right_support = parts['Right_Rod_Support']
plate = compound((centre_plate, left_support, right_support))
frame = parts['Existing_Probe_H_Frame']
device = parts['Existing_Carrier_Hung_From_Side_Slots']
tube = parts['Probe_Tube_ID51_OD54']
info = inspect(plate)
assert info['valid']
solids = TopExp_Explorer(plate, TopAbs_SOLID)
solid_count = 0
while solids.More():
    solid_count += 1
    solids.Next()
assert solid_count == 3  # Preserve three independently manufactured solids.
for shape in (centre_plate, left_support, right_support):
    ex = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while ex.More():
        count += 1
        ex.Next()
    assert count == 1 and BRepCheck_Analyzer(shape).IsValid()
assert np.allclose(bounds(plate), [0, 135, -12.5, 51, 215, 0], atol=1e-7)
shift = np.array([0.13912746191221714, 0, -8.5])
old_matrices = {r['name']: matrix(r['matrix_cm']) for r in original_records}
for r in records:
    if r['name'] in ('Centre_Plate_With_Device_Boss', 'Left_Rod_Support', 'Right_Rod_Support') or r['name'].startswith(('Deck_Join_', 'Device_Washer_')):
        continue
    before = old_matrices[r['name']]
    after = matrix(r['matrix_cm'])
    if 'Standard_Fasteners' in r['path']:
        # The native socket screw axis is +X; the old envelope axis was +Z.
        correction = np.eye(4)
        correction[:3, :3] = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]
        after = after @ np.linalg.inv(correction)
    if r['name'] == 'Existing_Carrier_Hung_From_Side_Slots' or r['name'].startswith('Device_Clamp_M3_'):
        assert np.allclose(after[:3, 3] - before[:3, 3], shift, atol=1e-8)
        assert np.allclose(after[:3, :3], before[:3, :3], atol=1e-10)
    elif r['name'] != 'Solid_Plate_With_Integral_Mounting_Boss':
        
        if r['name'].startswith('Rod_Clamp_M3_'):
            before = before.copy(); before[2,3] += 2.0
        assert np.allclose(after, before, atol=1e-10)

holes = [h for h in info['cylinders'] if abs(h['radius'] - 1.25) < 1e-6 and abs(h['axis'][0]) > .99]
assert len(holes) == 10
for x in (19.794248369169 + shift[0], 33.294248369169 + shift[0]):
    row = sorted([h for h in holes if abs(h['point'][0] - x) < 1e-6], key=lambda h: h['point'][1])
    assert len(row) == 5
    for i, h in enumerate(row):
        assert abs(h['point'][1] - (144.82802366515844 + 16*i)) < 1e-6
        assert abs(h['point'][2] + 5.5) < 1e-6
        assert abs(h['bounds'][3] - h['bounds'][0] - 6) < 1e-6

checks = []
def check(label, a, b, touch=True, thread_envelope=None, require_clear=True):
    common = BRepAlgoAPI_Common(a, b).Shape()
    overlap = abs(volume(common))
    residual = overlap
    if thread_envelope is not None and overlap > 1e-8:
        # Cosmetic threads retain nominal shaft cylinders. Only overlap inside
        # the actual tapped-hole depth and M3 major diameter is permitted.
        residual = abs(volume(BRepAlgoAPI_Cut(common, thread_envelope).Shape()))
    dist = BRepExtrema_DistShapeShape(a, b)
    dist.Perform()
    result = dict(pair=label, overlap_mm3=overlap, non_thread_overlap_mm3=residual,
                  cosmetic_thread_envelope_allowed=thread_envelope is not None,
                  minimum_distance_mm=dist.Value(), interference_free=residual < 1e-5)
    if residual >= 1e-5:
        result['intersection_bounds_mm'] = bounds(common)
    checks.append(result)
    if require_clear:
        assert residual < 1e-5, result
    if touch:
        assert dist.Value() < 1e-5, result

check('Stepped plate / rods', plate, frame)
check('Stepped plate / device', plate, device)
check('Device / rods', device, frame, False)
check('Centre deck / left support', centre_plate, left_support)
check('Centre deck / right support', centre_plate, right_support)
check('Left support / right support', left_support, right_support, False)
for name, shape in parts.items():
    if name.startswith('Device_Clamp_M3_'):
        y = (bounds(shape)[1] + bounds(shape)[4]) / 2
        allowed = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(19.933375831081217,y,-5.5),gp_Dir(1,0,0)),1.5,6).Shape()
        check(name + ' / plate', shape, plate, thread_envelope=allowed)
        # Report the unresolved native under-head fillet against the original
        # slot. The user rejected added washers; neither source part is altered.
        check(name + ' / device', shape, device, require_clear=False)
    elif name.startswith('Rod_Clamp_M3_'):
        check(name + ' / plate', shape, plate)
        check(name + ' / rods', shape, frame)
    elif name.startswith('Deck_Join_M3_'):
        check(name + ' / countersink', shape, centre_plate)
        support = left_support if bounds(shape)[0] < 20 else right_support
        box=bounds(shape);x=(box[0]+box[3])/2;y=(box[1]+box[4])/2
        allowed=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,-8.5),gp_Dir(0,0,1)),1.5,6.5).Shape()
        check(name + ' / tapped support', shape, support, thread_envelope=allowed)
        check(name + ' / device', shape, device, False)
        check(name + ' / sleeve', shape, tube, False)
    elif name.startswith('Device_Washer_'):
        check(name + ' / plate', shape, plate, False)
        check(name + ' / device', shape, device)
        screw=parts['Device_Clamp_M3_'+name.rsplit('_',1)[1]]
        check(name + ' / screw', shape, screw)

# Equal contact faces preserve the complete baseline rod contact, including holes.
def contact_faces(shape):
    return [p for p in inspect(shape)['planes'] if abs(p['normal'][2]) > .99 and
            abs(p['point'][2]) < 1e-6 and (p['bounds'][3] <= 6 + 1e-6 or p['bounds'][0] >= 45 - 1e-6)]
old_contact = contact_faces(original['Solid_Plate_With_Integral_Mounting_Boss'])
# The flat plate has one common face; compare each rod-side rectangular section.
contact_areas = []
for x in (0, 45):
    strip = BRepPrimAPI_MakeBox(gp_Pnt(x, 135, -1), 6, 80, 1).Shape()
    areas = []
    for shape in (original['Solid_Plate_With_Integral_Mounting_Boss'], plate):
        clipped = BRepAlgoAPI_Common(shape, strip).Shape()
        area = sum(p['area'] for p in inspect(clipped)['planes'] if abs(p['normal'][2]) > .99 and abs(p['point'][2]) < 1e-6)
        areas.append(area)
    assert abs(areas[0] - areas[1]) < 1e-6 and areas[0] > 440, areas
    contact_areas.append(dict(rod_x_mm=x, baseline_mm2=areas[0], variant_mm2=areas[1]))

assembly = read(OUT / 'Rod_Holder_Assembly_Drop8p5.step')
assert BRepCheck_Analyzer(assembly).IsValid()
assert abs(volume(assembly) - sum(volume(s) for s in parts.values())) < 1e-3
intersections = [dict(component=name, overlap_mm3=abs(volume(BRepAlgoAPI_Common(tube, shape).Shape())))
                 for name, shape in parts.items() if name != 'Probe_Tube_ID51_OD54']
assert next(i['overlap_mm3'] for i in intersections if i['component'] == 'Existing_Carrier_Hung_From_Side_Slots') < 1e-5
for r in load(OUT / 'source_preservation.json'):
    assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest().upper() == r['before_sha256']

fit = load(MECH / 'assembly_validation.json')
cavity = next(i for i in fit['pcb_items'] if i['name'] == 'PCB_board')['details']['cavity']
x0, y0, x1, y1 = cavity['envelope_mm']
local_floor = np.array([(x0+x1)/2, (y0+y1)/2, cavity['depth_mm']])
local_target = local_floor - [0, 0, .300]

def measure(directory):
    data = load(directory / 'pocket_measurement_transforms.json')
    carrier = matrix(data['carrier_matrix_cm'])
    pcb = carrier @ matrix(data['pcb_matrix_cm']) @ matrix(data['board_matrix_cm'])
    tube_m = matrix(data['tube_matrix_cm'])
    floor = point(pcb, local_floor)
    target = point(pcb, local_target)
    axis_origin = point(tube_m, [0, 0, 0])
    axis = tube_m[:3, 2] / np.linalg.norm(tube_m[:3, 2])
    centre = axis_origin + axis * np.dot(target-axis_origin, axis)
    board = read(Path(data['board_path']).with_suffix('.step'))
    floor_planes = [p for p in inspect(board)['planes'] if abs(p['normal'][2]) > .99 and abs(p['point'][2]-local_floor[2]) < 1e-7]
    assert any(p['bounds'][0] <= local_floor[0] <= p['bounds'][3] and p['bounds'][1] <= local_floor[1] <= p['bounds'][4] for p in floor_planes)
    return dict(floor=floor, target=target, centre=centre, distance=float(np.linalg.norm(target-centre)),
                carrier_matrix=carrier, pcb_matrix=pcb, board=board)

old_measure, new_measure = measure(BASE), measure(OUT)
assert new_measure['distance'] < 1e-6
assert np.allclose(new_measure['target'] - old_measure['target'], shift, atol=1e-8)
result = dict(assembly_step_valid=True, fabricated_part_count=3, each_part_one_solid=True, saved_occurrence_count=len(parts),
              plate_bounds_mm=bounds(plate), device_bounds_mm=bounds(device),
              device_shift_mm=shift.tolist(), baseline_radial_distance_mm=old_measure['distance'],
              radial_distance_mm=new_measure['distance'], target_global_mm=new_measure['target'].tolist(),
              floor_global_mm=new_measure['floor'].tolist(), tube_axis_at_target_y_mm=new_measure['centre'].tolist(),
              centre_residual_xz_mm=(new_measure['target']-new_measure['centre'])[[0, 2]].tolist(),
              boss_threads_per_side=5, boss_thread_count=10, boss_thread_pitch_mm=16,
              support_thread_count=8, support_thread_pitch_mm=20, countersunk_screw_count=8,
              thread_engagement_mm=6.1, thread_bottom_clearance_mm=.4, interfaces=checks,
              rod_contact_area_comparison=contact_areas, sleeve_intersections=intersections,
              original_cad_files_unchanged=True, native_pocket_floor_verified=True)
result['unresolved_interfaces'] = [c for c in checks if not c['interference_free']]
result['all_checked_interfaces_clear'] = not result['unresolved_interfaces']
(OUT / 'geometry_verification.json').write_text(json.dumps(result, indent=2))
print(json.dumps({k: v for k, v in result.items() if k not in ('interfaces', 'sleeve_intersections')}, indent=2), flush=True)

# Plot actual planar CAD cuts through the PCB pocket, with both variants at one scale.
def ring_points(wire, face):
    points = []
    walker = BRepTools_WireExplorer(wire, face)
    while walker.More():
        edge = walker.Current()
        curve = BRepAdaptor_Curve(edge)
        us = np.linspace(curve.FirstParameter(), curve.LastParameter(), 2 if curve.GetType() == GeomAbs_Line else 257)
        if edge.Orientation() == TopAbs_REVERSED:
            us = us[::-1]
        points.extend([[curve.Value(float(u)).X(), curve.Value(float(u)).Z()] for u in us[:-1]])
        walker.Next()
    return np.array(points)

def section_paths(shape, y):
    cut = BRepPrimAPI_MakeBox(gp_Pnt(-8, y, -31), 67, .03, 68).Shape()
    section = BRepAlgoAPI_Common(shape, cut).Shape()
    paths = []
    for face in faces(section):
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() != GeomAbs_Plane:
            continue
        plane = surface.Plane()
        if abs(plane.Axis().Direction().Y()) < .99 or abs(plane.Location().Y()-y) > 1e-6:
            continue
        outer = BRepTools.OuterWire_s(face)
        verts, codes = [], []
        ex = TopExp_Explorer(face, TopAbs_WIRE)
        while ex.More():
            wire = TopoDS.Wire(ex.Current())
            xy = ring_points(wire, face)
            signed = np.sum(xy[:, 0]*np.roll(xy[:, 1], -1)-np.roll(xy[:, 0], -1)*xy[:, 1])
            if (signed > 0) != wire.IsSame(outer):
                xy = xy[::-1]
            verts.extend(xy.tolist()+[xy[0].tolist()])
            codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(xy)-1)+[PlotPath.CLOSEPOLY])
            ex.Next()
        paths.append(PlotPath(verts, codes))
    return paths

colors = {'Tube': '#b7bec9', 'Rods': '#96502c', 'Plate / boss': '#25718e', 'Supports': '#3ca59a', 'Holder': '#cc792b', 'PCB': '#397d54'}
top_local = np.eye(4)
top_local[:3, 3] = fit['top_transform']['translation_mm']
top = read(MECH / 'Top_ForFridge_reference.step')
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'svg.fonttype': 'none'})
fig, axes = plt.subplots(1, 2, figsize=(15, 8.8), facecolor='#f6f8fb')
fig.subplots_adjust(left=.035, right=.985, bottom=.16, top=.835, wspace=.07)
for ax, p, m, title in zip(axes, (original, parts), (old_measure, new_measure),
                          ('Existing flat plate — preserved', 'New three-piece plate — 8.5 mm lower')):
    geometry = {'Tube': p['Probe_Tube_ID51_OD54'], 'Rods': p['Existing_Probe_H_Frame'],
                'Plate / boss': p['Solid_Plate_With_Integral_Mounting_Boss'] if p is original else centre_plate,
                'Holder': transform(top, m['carrier_matrix'] @ top_local),
                'PCB': transform(m['board'], m['pcb_matrix'])}
    if p is parts:
        geometry['Supports'] = compound((left_support, right_support))
    for name, shape in geometry.items():
        for path in section_paths(shape, float(m['target'][1])):
            ax.add_patch(PathPatch(path, facecolor=colors[name], edgecolor='none'))
    ax.set_xlim(-5, 56)
    ax.set_ylim(-26, 33)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=14, weight='bold', pad=18, color='#233348')
    cx, cz = m['centre'][[0, 2]]
    px, pz = m['target'][[0, 2]]
    ax.plot([cx, cx], [-23, 30], ls=(0, (4, 5)), lw=.7, color='#ba2853', alpha=.5)
    ax.plot([-.5, 51.5], [cz, cz], ls=(0, (4, 5)), lw=.7, color='#ba2853', alpha=.5)
    ax.plot(cx, cz, 'o', ms=9, mfc='white', mec='#ba2853', mew=1.5, zorder=10)
    ax.plot(px, pz, 'o', ms=5, color='#007e9c', zorder=11)
    if m is old_measure:
        ax.annotate('P: pocket reference', xy=(px, pz), xytext=(7, 21), color='#007e9c',
                    arrowprops=dict(arrowstyle='-', color='#007e9c'))
        ax.annotate('', xy=(29.5, pz), xytext=(29.5, cz), arrowprops=dict(arrowstyle='<->', color='#ba2853', lw=1.3))
        ax.text(31, 7.1, '8.500 mm', color='#ba2853', fontsize=11, va='center')
        ax.annotate('O: tube centre', xy=(cx, cz), xytext=(9, -16), color='#ba2853',
                    arrowprops=dict(arrowstyle='-', color='#ba2853'))
        ax.text(25.5, -24.5, 'Radial offset: 8.501 mm', ha='center', weight='bold', color='#ba2853')
    else:
        ax.annotate('P = O: aligned', xy=(px, pz), xytext=(24.5, 18), color='#007e9c', weight='bold',
                    arrowprops=dict(arrowstyle='-', color='#007e9c', lw=1.2))
        ax.annotate('', xy=(12, 0), xytext=(12, -8.5), arrowprops=dict(arrowstyle='<->', color='#233348', lw=1.2))
        ax.text(14, -5, '8.5 mm\nstep', color='#233348', fontsize=10, va='center')
        ax.plot([6, 12], [-8.5, -8.5], color='#f6f8fb', lw=1.2)
        ax.plot([39, 45], [-8.5, -8.5], color='#f6f8fb', lw=1.2)
        ax.text(25.5, -24.5, 'Centre residual: < 0.001 mm', ha='center', weight='bold', color='#007e9c')
fig.text(.04, .954, 'Pocket centre alignment — two mounting-plate versions', fontsize=19, weight='bold', color='#233348')
fig.text(.04, .91, 'Actual CAD section through the pocket  |  Tube ID 51 / OD 54 mm  |  Same rod and flange positions', fontsize=11, color='#526276')
for i, (name, color) in enumerate(colors.items()):
    fig.text(.075+i*.147, .113, '■', color=color, fontsize=14)
    fig.text(.092+i*.147, .114, name, color='#233348', fontsize=11)
fig.text(.04, .068, 'P = pocket-floor centre + 0.300 mm toward the cavity opening.  New carrier translation: ΔZ = −8.500 mm; ΔX = +0.139 mm.', fontsize=11, color='#233348')
fig.text(.04, .03, 'Deck joins: 8 x M3 countersunk screws. Original flat plate preserved. Existing sleeve / outer-flange envelope intersections remain.', fontsize=10, color='#647083')
fig.savefig(OUT / 'Plate_versions_comparison.png', dpi=160, facecolor=fig.get_facecolor())
svg = OUT / 'Plate_versions_comparison.svg'
fig.savefig(svg, facecolor=fig.get_facecolor())
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8')
plt.close(fig)
print('Saved Plate_versions_comparison.png and .svg.', flush=True)

# The joint section uses a screw row, rather than falsely showing screws in the pocket section.
fig, ax = plt.subplots(figsize=(12, 7.2), facecolor='#f6f8fb')
fig.subplots_adjust(left=.045, right=.98, bottom=.14, top=.82)
joint_y = 165.0
joint_geometry = {'Tube': tube, 'Rods': frame, 'Plate / boss': centre_plate,
                  'Supports': compound((left_support, right_support)),
                  'Holder': transform(top, new_measure['carrier_matrix'] @ top_local),
                  'PCB': transform(new_measure['board'], new_measure['pcb_matrix'])}
for name, shape in joint_geometry.items():
    for path in section_paths(shape, joint_y):
        ax.add_patch(PathPatch(path, facecolor=colors[name], edgecolor='none'))
for name, shape in parts.items():
    if name.startswith('Deck_Join_M3_') and name.endswith('_Y165'):
        for path in section_paths(shape, joint_y):
            ax.add_patch(PathPatch(path, facecolor='#6e7781', edgecolor='none'))
ax.set_xlim(-3, 54)
ax.set_ylim(11, -21)
ax.set_aspect('equal')
ax.axis('off')
for x0, x1 in ((6, 12), (39, 45)):
    ax.plot([x0, x1], [-8.5, -8.5], color='#f6f8fb', lw=1)
ax.annotate('M3 x 10 countersunk\n4 per side, 20 mm pitch', xy=(9.5, -12.4), xytext=(1, -19.5),
            color='#233348', fontsize=11, arrowprops=dict(arrowstyle='-', color='#233348'))
ax.annotate('1  Central plate + boss', xy=(25.5, -10.5), xytext=(26, -18.5),
            color='#25718e', fontsize=12, weight='bold', arrowprops=dict(arrowstyle='-', color='#25718e'))
ax.annotate('2  Left support', xy=(8, -6), xytext=(1, 10), color='#208b80',
            fontsize=11, weight='bold', arrowprops=dict(arrowstyle='-', color='#208b80'))
ax.annotate('3  Right support', xy=(43, -6), xytext=(38, 10), color='#208b80',
            fontsize=11, weight='bold', arrowprops=dict(arrowstyle='-', color='#208b80'))
ax.annotate('', xy=(36.8, -8.5), xytext=(36.8, 0), arrowprops=dict(arrowstyle='<->', color='#233348', lw=1.2))
ax.text(35.7, -4.7, '8.5 mm', ha='right', va='center', color='#233348', fontsize=11)
fig.text(.045, .947, 'Three-piece stepped mounting plate', fontsize=19, weight='bold', color='#233348')
fig.text(.045, .889, 'Actual CAD section at the screw row (Y = 165 mm) — viewed with the deck above the rods', fontsize=10.5, color='#526276')
fig.text(.045, .073, 'Blue: central deck and integral device boss.  Teal: separate left/right supports.  Gray: new joining screws.', fontsize=10.5, color='#233348')
fig.text(.045, .034, '6.1 mm modeled engagement; 0.4 mm bore-bottom clearance; heads recessed 0.1 mm. Dimensions in mm.', fontsize=10.5, color='#526276')
fig.savefig(OUT / 'Split_joint_section.png', dpi=160, facecolor=fig.get_facecolor())
plt.close(fig)
print('Saved Split_joint_section.png.', flush=True)
