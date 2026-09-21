from pathlib import Path
import sys
H=Path(__file__).resolve().parent;W=H.parent;P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB')
sys.path.insert(0,str(W/'zif_revision_v2/schematic'))
src=W/'zif_revision_v2/schematic/render_v2_schematic.py';code=src.read_text().replace('16 components / 123 symbol pins / 33 named nets / 31 intentional NC','22 components / 141 symbol pins / 33 named nets / 41 intentional NC')
ns={'__file__':str(src),'__name__':'symmetric_renderer'};exec(compile(code,str(src),'exec'),ns);ns['P']=H;ns['render'](P/'QSTL_24DC_4MW_PCB.SchDoc',P/'docs/schematic.png')
