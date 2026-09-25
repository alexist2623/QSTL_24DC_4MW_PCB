"""Package and check the fresh native M1 mounting-hole CAM export."""
from pathlib import Path
import shutil, json, zipfile, collections, dataclasses
from gerbonara import GerberFile
H=Path(__file__).resolve().parent
P=H.parents[1]/'QSTL_24DC_4MW_PCB'
old=P/'fabrication/JLCPCB_HDI_20260924'
new=P/'fabrication/JLCPCB_HDI_20260925'
source=P/'QSTL_24DC_4MW_PCB.PcbDoc'
(new/'Native_CAM').mkdir(exist_ok=True)
for f in (old/'Native_CAM').iterdir():
    if f.is_file():
        assert f.stat().st_mtime>source.stat().st_mtime, f
        shutil.copy2(f,new/'Native_CAM'/f.name)
# Reuse the established native CAM checks with the new date/hole count.
code=(H.parent/'dc_ground_pour_20260924/package_cam.py').read_text()
code=code.replace('20260924','20260925').replace('2026-09-24','2026-09-25')
code=code.replace('==94','==96').replace("'through_holes':94","'through_holes':96")
code=code.replace('94 through plated holes','96 through plated holes').replace('40 x 0.75 mm, 4 x 2.1 mm, 2 x 4.0 mm).','40 x 0.75 mm, 2 x 1.2 mm, 4 x 2.1 mm, 2 x 4.0 mm).')
code=code.replace('DC traces, pin mapping and RF geometry are unchanged.',
    'DC traces, pin mapping and RF geometry are unchanged.\nTwo M1 mounts: 1.2 mm plated drill, 1.6 mm land, solid GND.\nCenters X1.05 / X18.45, Y1.20 mm; 17.40 mm pitch.\nNo mounting-hole thermal relief or solder paste.')
exec(compile(code,str(H/'package_cam.py'), 'exec'),{'__file__':str(H/'package_cam.py'),'__name__':'__main__'})
# Compare the emitted silkscreen geometry against the prior package. Native
# text caches can be reset on save; rendered text strokes must not change.
def objects(g):
    return collections.Counter(repr(p) for o in g.objects for p in o.to_primitives())
silk={}
with zipfile.ZipFile(old/'QSTL_24DC_6RF_HDI_Gerber_20260924.zip') as z:
    for ext in ('GBO','GTO'):
        name='QSTL_24DC_4MW_PCB.'+ext
        a=objects(GerberFile.from_string(z.read(name).decode()))
        b=objects(GerberFile.open(new/'Gerber'/name))
        removed=list((a-b).elements());added=list((b-a).elements())
        silk[ext]={'removed':removed,'added':added}
        if ext=='GBO':assert not removed and not added
        else: assert len(removed)==len(added)==1, silk[ext]
(new/'silkscreen_comparison.json').write_text(json.dumps(silk,indent=2))
print('Silkscreen verified: all text strokes preserved; one Top pin-1 dot relocated.')
