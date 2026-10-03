"""Inspect native Altium saved metadata without editing the design."""
from pathlib import Path
import sys,json,struct
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,olefile,pads_stream,binary_records
for name in ('ZIF_to_2xZIF','ZIF_to_DSUB25'):
 p=R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002'/name/(name+'.PcbDoc')
 with olefile.OleFileIO(p) as o:
  print(name)
  print(json.dumps(properties(o.openstream('Components6/Data').read()),indent=2))
  pads=pads_stream(o.openstream('Pads6/Data').read())
  print('PAD_TAIL',pads[0]['blocks'][4][60:].hex())
  print('CONNECTIONS',len(o.openstream('Connections6/Data').read()))
  print('VIA_MASK_FIELDS',sorted({(v['body'][66],round(struct.unpack_from('<i',v['body'],54)[0]*2.54e-6,6),round(struct.unpack_from('<i',v['body'],242)[0]*2.54e-6,6)) for v in binary_records(o.openstream('Vias6/Data').read(),3)}))
  print('BOARD_STACK',{k:v for k,v in properties(o.openstream('Board6/Data').read())[0].items() if 'V9_SUBSTACK0' in k})
