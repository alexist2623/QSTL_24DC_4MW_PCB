"""Document the rod-only hardware revision without regenerating plate DWGs."""
from pathlib import Path
import json, zipfile, shutil, hashlib
H=Path(__file__).resolve().parent;R=H.parents[1]
M=R/'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf-8')
report=load(M/'rod_button_head_verification.json')
for p in (M/'README.md', M/'Manufacturing_DWG/README.md'):
    s=p.read_text(encoding='utf-8-sig')
    s=s.replace('The full assembly also uses ten supplied ISO 4762 M3x8 screws at the rod/device interfaces.', 'The full assembly uses eight supplied ISO 7380-1 M3x8 button-head screws at the rod interfaces and two supplied ISO 4762 M3x8 screws at the device interfaces.')
    s=s.replace('The existing eight Content Center ISO 4762 M3x8 screws retain their insertion direction through the support into the rod, with heads reseated at global Z=-1.6 mm. The rods and supplied hardware are unchanged.', 'The eight rod screws are now unmodified Content Center ISO 7380-1 M3x8 button-head members. They retain their insertion direction through the support into the rod and bearing planes at global Z=-1.6 mm. The original rods remain unchanged.')
    s=s.replace('The C1.6 bevel leaves 67.11% of the actual flat under-head bearing area supported (10.546 of 15.716 mm2 per rod screw).', 'With the ISO 7380-1 button heads, the C1.6 bevel leaves 70.70% of the actual flat under-head bearing area supported (10.845 of 15.339 mm2 per rod screw). The previous 67.11% result applies to the superseded ISO 4762 rod heads.')
    s=s.replace('Current revision helpers are in `script/support_flange_1p6mm_20260924/`; `verify_assembly.py` checks the full assembly including the rod screw seating change.', 'Current rod-hardware helpers are in `script/rod_button_head_20260924/`. The flange-generation and drawing helpers remain in `script/support_flange_1p6mm_20260924/`; their saved pre-button-head verification is historical for rod screws.')
    if '## Button-head rod hardware' not in s:
        s+='''

## Button-head rod hardware - 2026-09-24

Eight rod screws are actual Inventor 2027 Content Center ISO 7380-1 M3x8 members: head diameter 5.7 mm, head height 1.65 mm, 2 mm hex drive, M3x0.5-6g external thread. The two device screws and eight DIN 7991 plate screws remain unchanged. The copied library member retains its original SHA-256 and Content Center identity. No washers are present.

The native assembly was saved and reopened. Only the eight rod occurrence file references changed; every occurrence transform and all three fabricated IPT/STEP pairs are unchanged. STEP solid validity and assembly/component volume agreement were checked using adaptive integration for the curved heads. See rod_button_head_native_audit.json and rod_button_head_verification.json in the model directory.

Per rod screw, the sleeve overlap falls from approximately 3.398 to 0.576 mm3, but is not eliminated. The supplied R0.3 under-head fillet also intersects the unchamfered 3.4 mm flange-hole mouth by approximately 0.00492 mm3. This is an unresolved geometric seating issue, not cosmetic thread overlap. Hole geometry and supplied screws were not modified to conceal it. Original rod-corner/support/sleeve clashes and device fillet intersections remain.

Cylinder_top_round_heads.png shows the native axial view; Rod_button_head_assembly.png shows the mounting screws with the sleeve hidden for inspection. Fabricated geometry, the plate-only IAM/IPN and all six Rev D DWGs are byte-for-byte unchanged by this hardware-only update. Rod installation is outside the plate drawing scope; source_cad_hashes.json remains the historical drawing-generation record, including its then-current full-installation IAM hash. The rod change does not invalidate the associated plate views.
'''
    p.write_text(s,encoding='utf-8')
req=R/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md'
s=req.read_text(encoding='utf-8-sig').replace('eight DIN 7991 M3x10 deck screws and ten ISO 4762 M3x8 rod/device screws', 'eight DIN 7991 M3x10 deck screws, eight ISO 7380-1 M3x8 button-head rod screws and two ISO 4762 M3x8 device screws')
req.write_text(s,encoding='utf-8')
plan=load(M/'variant_plan.json');plan['rod_fasteners']='8 unmodified Inventor Content Center ISO 7380-1 M3x8 button-head screws, original insertion direction'
plan['rod_head_diameter_mm']=5.7;plan['rod_head_height_mm']=1.65;plan['rod_hardware_verification']='rod_button_head_verification.json';save(M/'variant_plan.json',plan)
# Keep the plate-only delivery archive consistent without changing its drawings.
archive=M/'QSTL_Plate_DWG_Package_RevD.zip'
backup=H/'before/QSTL_Plate_DWG_Package_RevD.zip'
if not backup.exists():shutil.copy2(archive,backup)
with zipfile.ZipFile(backup) as z:
    entries=[(info,z.read(info.filename)) for info in z.infolist()]
updates=[]
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for info,data in entries:
        name=info.filename.replace('\\','/')
        if name=='README.md':data=(M/'Manufacturing_DWG/README.md').read_bytes();updates.append(name)
        elif name=='Manufacturing_DWG/README.md':data=(M/'Manufacturing_DWG/README.md').read_bytes();updates.append(name)
        z.writestr(info,data)
    z.writestr('rod_button_head_verification.json',(M/'rod_button_head_verification.json').read_bytes())
with zipfile.ZipFile(archive) as z:
    for info,data in entries:
        if info.filename.replace('\\','/') not in updates:assert z.read(info.filename)==data
    assert z.testzip() is None
save(M/'rod_button_head_package_audit.json',dict(plate_drawings_unchanged=True,archive=archive.name,updated_readmes=updates,added_report='rod_button_head_verification.json',comment='The archive remains a plate-only package, without rod hardware or full-installation drawings.'))
print(json.dumps(dict(documentation_updated=True,package_readmes=updates,plate_dwg_bytes_unchanged=True)))
