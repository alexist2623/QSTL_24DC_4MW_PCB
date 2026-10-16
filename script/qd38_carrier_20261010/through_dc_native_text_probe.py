from pathlib import Path
import json,importlib.util,struct
h=Path(__file__).resolve().parent;root=h.parents[1];dest=root/'QSTL_QD4_2SET_38PAD'
spec=importlib.util.spec_from_file_location('nr',root/'script/_support/zif_revision_v2/render_native_layout.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
with r.olefile.OleFileIO(dest/'QSTL_QD4_2SET_38PAD.PcbDoc') as o:d=o.openstream('Texts6/Data').read()
pos=0
for i in range(3):
 print('offset',pos,'type',d[pos]);n=struct.unpack_from('<I',d,pos+1)[0]&0xffffff;b=d[pos+5:pos+5+n];print('body',len(b),b[:100],b[-100:]);pos+=5+n;n=struct.unpack_from('<I',d,pos)[0]&0xffffff;print('stringblock',n,d[pos+4:pos+4+n]);pos+=4+n
