"""Adapt the established native geometry and drawing checks for revision D."""
from pathlib import Path
H=Path(__file__).resolve().parent
old=H.parent/'support_flange_2mm_20260924'
s=(old/'verify_assembly.py').read_text(encoding='utf-8').replace('before[2,3] += 2.0','before[2,3] += 2.4')
(H/'verify_assembly.py').write_text(s,encoding='utf-8')
s=(old/'verify_flange.py').read_text(encoding='utf-8')
s=s.replace("old=solid(read(H/'before'/", "old=solid(read(H.parent/'support_flange_2mm_20260924/before'/")
s=s.replace('6,80,2).Shape()','6,80,2.4).Shape()').replace('xx=(0,2,0) if side==\'Left\' else (51,49,51)','xx=(0,1.6,0) if side==\'Left\' else (51,49.4,51)')
s=s.replace('zip(xx,(10.5,10.5,12.5))','zip(xx,(10.9,10.9,12.5))').replace("bevels[0]['bounds'][2]-2)","bevels[0]['bounds'][2]-1.6)")
s=s.replace('flange_thickness_mm=2,chamfer_leg_mm=2','flange_thickness_mm=1.6,chamfer_leg_mm=1.6').replace('plane_faces(screw,-2)','plane_faces(screw,-1.6)').replace('plane_faces(solid,-2)','plane_faces(solid,-1.6)').replace('underhead_plane_z_mm=-2','underhead_plane_z_mm=-1.6')
s=s.replace('support_flange_2mm_validation.json','support_flange_1p6mm_validation.json').replace('C2 bevel','C1.6 bevel')
(H/'verify_flange.py').write_text(s,encoding='utf-8')
s=(old/'verify_native_saved.ps1').read_text(encoding='utf-8-sig').replace('support_flange_2mm_20260924','support_flange_1p6mm_20260924').replace('Value-.2','Value-.16').replace('flange_mm=2;chamfer_mm=2','flange_mm=1.6;chamfer_mm=1.6').replace('2 mm flanges, native C2','1.6 mm flanges, native C1.6')
s=s.replace("$threads=@($cd.Features.ThreadFeatures", "if(@($cd.Features.ThreadFeatures|Where-Object Name -like 'Rod_*').Count -ne 0) {throw 'Cancelled flange threading remains'}\n  if([math]::Abs($cd.Parameters.UserParameters.Item('RodClearanceDiameter').Value-.34) -gt 1e-8) {throw 'Wrong clearance diameter'}\n  $threads=@($cd.Features.ThreadFeatures")
(H/'verify_native_saved.ps1').write_text(s,encoding='utf-8-sig')
s=(H.parent/'probe_rod_inspection/read_pocket_placement.ps1').read_text(encoding='utf-8-sig').replace("Mechanical_Assembly\\Rod_Holder_Adapter'", "Mechanical_Assembly\\Rod_Holder_Adapter_Drop8p5'").replace('Rod_Holder_Assembly.iam','Rod_Holder_Assembly_Drop8p5.iam')
(H/'read_pocket_placement.ps1').write_text(s,encoding='utf-8-sig')
s=(old/'build_dwg.ps1').read_text(encoding='utf-8-sig').replace('support_flange_2mm_20260924','support_flange_1p6mm_20260924').replace('RevC','RevD').replace('REV C','REV D')
s=s.replace('$bx=if($isLeft){2.0}else{49.0}','$bx=if($isLeft){1.6}else{49.4}').replace('@($bx,0,10.5)','@($bx,0,10.9)').replace('V 55 249 2','V 55 249 1.6').replace('C2 X 45','C1.6 X 45').replace('THROUGH 2.00 FLANGE','THROUGH 1.60 FLANGE')
(H/'build_dwg.ps1').write_text(s,encoding='utf-8-sig')
s=(old/'verify_dwg.ps1').read_text(encoding='utf-8-sig').replace('RevC','RevD')
(H/'verify_dwg.ps1').write_text(s,encoding='utf-8-sig')
print('Prepared revision D saved geometry, native support, transform and DWG checks.')
