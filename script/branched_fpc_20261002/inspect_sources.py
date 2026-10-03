"""Extract read-only connector geometry and native record templates."""
from pathlib import Path
import sys,json,hashlib,struct
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/anton_zif_20260923'))
from inspect_pinout import parse,rows,row,val
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,pads_stream,binary_records,olefile
ref=R/'script/anton_zif_20260923/reference/DSUBtoZIF_20250306'
p=parse(ref/'DSUBtoZIF_20250106.kicad_pcb');n=parse(ref/'DSUBtoZIF_20250106.net')
fp=next(f for f in rows(p,'footprint') if dict((r[1],r[2]) for r in rows(f,'property')).get('Reference')=='J1')
out={'dsub_part':'381-025-112L565','pads':[],'mapping':{},'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in ref.iterdir() if f.is_file()}}
for pad in rows(fp,'pad'):
    out['pads'].append({'pin':pad[1],'at_mm':list(map(float,row(pad,'at')[1:3])),'size_mm':list(map(float,row(pad,'size')[1:])),'drill_mm':float(val(pad,'drill'))})
for net in rows(row(n,'nets'),'net'):
    nodes={val(x,'ref'):val(x,'pin') for x in rows(net,'node')}
    if 'J1' in nodes and 'J2' in nodes:out['mapping'][nodes['J1']]=int(nodes['J2'])
assert len(out['pads'])==25 and len(out['mapping'])==25
(H/'reference/anton_connector.json').write_text(json.dumps(out,indent=2)+'\n')
for name,path in [('cable',R/'QSTL_24DC_4MW_PCB/FPC_15015_0451/FPC_15015_0451.PcbDoc'),('two_layer',R/'script/fpc_15015_0451_20261002/before_stack.PcbDoc'),('carrier',R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc')]:
    with olefile.OleFileIO(path) as o:d={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
    if name!='carrier':
        result={'components':properties(d['Components6/Data']),'nets':properties(d['Nets6/Data'])[:1],'classes':properties(d['Classes6/Data']),'board_regions_hex':d.get('BoardRegions/Data',b'').hex(),'stream_counts':{k:len(v) for k,v in d.items()},'board':properties(d['Board6/Data'])[0]}
        (H/f'{name}_templates.json').write_text(json.dumps(result,indent=2))
    print(name,{'pad_blocks':[len(v) for v in pads_stream(d['Pads6/Data'])[0]['blocks']], 'pad_count':len(pads_stream(d['Pads6/Data'])),'via_count':len(binary_records(d['Vias6/Data'],3))})
print(json.dumps({'dsub_pin_mapping':out['mapping'],'pad_bounds':[min(x['at_mm'][0] for x in out['pads']),max(x['at_mm'][0] for x in out['pads'])]},indent=2))
