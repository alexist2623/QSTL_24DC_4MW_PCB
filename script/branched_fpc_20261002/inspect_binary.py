"""Read native template field layouts for the new adapter generator."""
from pathlib import Path
import sys,struct,json
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,pads_stream,binary_records,olefile
for label,p in [('fpc',R/'QSTL_24DC_4MW_PCB/FPC_15015_0451/FPC_15015_0451.PcbDoc'),('carrier',R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc')]:
 with olefile.OleFileIO(p) as o:d={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
 if label=='fpc':
  print('STREAMS',[(k,len(v)) for k,v in d.items() if len(v)])
  for kind,stream in [(11,'Regions6'),(4,'Tracks6')]:
   b=binary_records(d[stream+'/Data'],kind)[0]['body'];print(stream,len(b),b[:100].hex(),repr(b[:200]))
  print('TEXTS',d['Texts6/Data'][:270].hex(),repr(d['Texts6/Data'][:270]))
  print('BoardRegions',d.get('BoardRegions/Data',b'')[:450])
  print('OTHER',[(k,v[:500]) for k,v in d.items() if ('Unique' in k or 'Extended' in k) and v])
 else:
  p=next(p for p in pads_stream(d['Pads6/Data']) if p['coords'][8]>0)
  print('PTH',p['layer'],p['number'],p['coords'],p['blocks'][4].hex())
  print('VIASPANS',list(set((len(v['body']),v['body'][29],v['body'][30]) for v in binary_records(d['Vias6/Data'],3))))
