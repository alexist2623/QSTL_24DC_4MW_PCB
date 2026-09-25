"""Prepare M1-specific review and acceptance scripts; retain previous reviews."""
from pathlib import Path
import json, shutil

H = Path(__file__).resolve().parent
P = H.parents[1] / 'QSTL_24DC_4MW_PCB'
out = P / 'Mechanical_Assembly/ZIF_M1_Review'
old = P / 'Mechanical_Assembly/ZIF_M1p6_Review'
(out / 'Standard_Fasteners').mkdir(parents=True, exist_ok=True)
member = json.loads((old / 'm1_round_member.json').read_text(encoding='utf-8-sig'))
dest = out / 'Standard_Fasteners/KS_B1021_M1x4.ipt'
shutil.copy2(member['file'], dest)
member['file'] = str(dest)
(out / 'm1_round_member.json').write_text(json.dumps(member, indent=2), encoding='utf-8')

s = (H / 'prepare_review.py').read_text(encoding='utf-8').replace('ZIF_M1p6_Review','ZIF_M1_Review')
(H / 'prepare_m1_review.py').write_text(s, encoding='utf-8')
s = (H / 'build_review.ps1').read_text(encoding='utf-8-sig')
s = s.replace('ZIF_M1p6', 'ZIF_M1').replace('m1p6_member.json','m1_round_member.json')
s = s.replace('ISO_4762_M1p6x4','KS_B1021_M1x4').replace('ISO4762_M1p6x4','KSB1021_M1x4')
s = s.replace('ZIF_M1_Top','ZIF_M1_Round_Top').replace('ZIF_M1_Oblique','ZIF_M1_Round_Oblique')
start = s.index(" $c=@($occs|Where-Object")
end = s.index(' $report|ConvertTo-Json', start)
transparent = (H / 'update_round_review.ps1').read_text(encoding='utf-8-sig')
start2 = transparent.index(" $screws=@($occs|Where-Object", transparent.index("Screenshot $doc 'ZIF_M1p6_Round_Oblique'"))
end2 = transparent.index(' $report|ConvertTo-Json',start2)
tail = transparent[start2:end2].replace('ZIF_M1p6','ZIF_M1').replace('ISO_7045_H_M1p6x4','KS_B1021_M1x4')
s = s[:start] + tail + s[end:]
(H / 'build_m1_review.ps1').write_text(s, encoding='utf-8-sig')

s = (H / 'verify_saved.py').read_text(encoding='utf-8')
s = s.replace('M1.6','M1').replace('ZIF_M1p6_mount','ZIF_M1_mount')
s = s.replace("[1.6 if p['number']=='MH7' else 17.9,1.2]+[2.2]*6+[1.8]", "[1.05 if p['number']=='MH7' else 18.45,1.2]+[1.6]*6+[1.2]")
s = s.replace('buffer(1.15,','buffer(.85,').replace('buffer(1.08,','buffer(.78,')
s = s.replace('hole_pitch_mm=16.3','hole_pitch_mm=17.4').replace('nearest_drill_to_edge_mm=.3','nearest_drill_to_edge_mm=.45')
(H / 'verify_m1_saved.py').write_text(s, encoding='utf-8')

s = (H / 'package_cam.py').read_text(encoding='utf-8')
s = s.replace('M1.6','M1').replace('2 x 1.8 mm','2 x 1.2 mm').replace('1.8 mm plated drill, 2.2 mm land','1.2 mm plated drill, 1.6 mm land')
s = s.replace('X1.60 / X17.90','X1.05 / X18.45').replace('16.30 mm pitch','17.40 mm pitch')
(H / 'package_m1_cam.py').write_text(s, encoding='utf-8')
archive = H / 'superseded_m1p6_cam'
archive.mkdir(exist_ok=True)
for f in (P/'fabrication/JLCPCB_HDI_20260925').glob('*.zip'):
    if not (archive/f.name).exists(): shutil.copy2(f, archive/f.name)

s = (H / 'render_cable_hole_clearance.py').read_text(encoding='utf-8')
for a,b in [('ZIF_M1p6','ZIF_M1'),('diameter 1.80','diameter 1.20'),('16.30 mm hole','17.40 mm hole'),('0.55 mm overlap','0.30 mm clearance'),('14.50 mm','16.20 mm'),('-0.55 mm on each side (overlap)','+0.30 mm on each side (clearance)'),('Hole positions unchanged; no fit clearance has been added.','Hole geometry from the saved M1 PCB; board width preserved.')]:
    s=s.replace(a,b)
s=s.replace("xy=(mounts[0]['x']-.6,mounts[0]['y']+.65)","xy=(mounts[0]['x']-.35,mounts[0]['y']+.45)")
s=s.replace("[m['y']]*2,color='#b52225',lw=5", "[m['y']]*2,color='#168354',lw=5")
s=s.replace("'0.30 mm clearance',ha='center',color='#b52225'","'0.30 mm clearance',ha='center',color='#168354'")
s=s.replace("(clearance)',fontsize=12,color='#b52225'","(clearance)',fontsize=12,color='#168354'")
(H / 'render_m1_clearance.py').write_text(s, encoding='utf-8')
print('M1 scripts and unmodified standard member prepared.')
