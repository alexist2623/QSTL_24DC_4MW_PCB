"""Apply the final user-selected 1.6 mm thickness to the current helpers."""
from pathlib import Path
H=Path(__file__).resolve().parent
R=H.parents[1]
for p in H.glob('*.ps1'):
    s=p.read_text(encoding='utf-8-sig').replace('support_flange_1mm_20260924','support_flange_1p6mm_20260924')
    if p.name=='apply_supports.ps1':
        s=s.replace("Expression='1 mm'","Expression='1.6 mm'")
        s=s.replace('Outer_End_1mm_45deg','Outer_End_1p6mm_45deg')
        s=s.replace('rod_free_plane_local_z_mm=11.5','rod_free_plane_local_z_mm=10.9')
        s=s.replace('$m.Cell(3,4)+=.1','$m.Cell(3,4)+=.04')
        s=s.replace('head_bearing_z_mm=-1','head_bearing_z_mm=-1.6').replace('tip_z_mm=7;tip_projection_mm=1','tip_z_mm=6.4;tip_projection_mm=.4')
        s=s.replace('1 mm flange','1.6 mm flange')
    if p.name=='render_native.ps1':
        s=s.replace('Cylinder_top_1mm','Cylinder_top_1p6mm').replace('Support_end_1mm','Support_end_1p6mm').replace('1 mm support','1.6 mm support')
    p.write_text(s,encoding='utf-8-sig')
s=(H/'prepare_checks.py').read_text(encoding='utf-8')
s=s.replace("'before[2,3] += 3.0'","'before[2,3] += 2.4'")
s=s.replace("'6,80,3).Shape()'","'6,80,2.4).Shape()'")
s=s.replace("'xx=(0,1,0) if side==\\'Left\\' else (51,50,51)'","'xx=(0,1.6,0) if side==\\'Left\\' else (51,49.4,51)'")
s=s.replace("'zip(xx,(11.5,11.5,12.5))'","'zip(xx,(10.9,10.9,12.5))'")
s=s.replace('"bevels[0][\'bounds\'][2]-1)"','"bevels[0][\'bounds\'][2]-1.6)"')
s=s.replace("'flange_thickness_mm=1,chamfer_leg_mm=1'","'flange_thickness_mm=1.6,chamfer_leg_mm=1.6'")
s=s.replace("'plane_faces(screw,-1)'","'plane_faces(screw,-1.6)'").replace("'plane_faces(solid,-1)'","'plane_faces(solid,-1.6)'").replace("'underhead_plane_z_mm=-1'","'underhead_plane_z_mm=-1.6'")
s=s.replace('support_flange_1mm_validation','support_flange_1p6mm_validation').replace("'C1 bevel'","'C1.6 bevel'")
s=s.replace("'Value-.1'","'Value-.16'").replace("'flange_mm=1;chamfer_mm=1'","'flange_mm=1.6;chamfer_mm=1.6'").replace("'1 mm flanges, native C1'","'1.6 mm flanges, native C1.6'")
s=s.replace('support_flange_1mm_20260924','support_flange_1p6mm_20260924')
s=s.replace("'$bx=if($isLeft){1.0}else{50.0}'","'$bx=if($isLeft){1.6}else{49.4}'").replace("'@($bx,0,11.5)'","'@($bx,0,10.9)'").replace("'V 55 249 1'","'V 55 249 1.6'").replace("'C1 X 45'","'C1.6 X 45'").replace("'THROUGH 1.00 FLANGE'","'THROUGH 1.60 FLANGE'")
(H/'prepare_checks.py').write_text(s,encoding='utf-8')
p=R/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md'
s=p.read_text(encoding='utf-8').replace('Latest 1 mm flange correction','Latest 1.6 mm flange correction').replace('flanges from 2 mm to 1 mm','flanges from 2 mm to 1.6 mm').replace('(now C1)','(now C1.6)')
p.write_text(s,encoding='utf-8')
print('Final thickness: 1.6 mm. C1.6 x45; clearance holes retained; screw tip projection 0.4 mm.')
