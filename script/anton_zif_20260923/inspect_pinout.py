"""Inspect Anton's KiCad source pin assignments without changing its files."""
from pathlib import Path
import collections
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
REF = HERE / 'reference' / 'DSUBtoZIF_20250306'
ROOT = HERE.parents[1]
OUT = ROOT / 'QSTL_24DC_4MW_PCB' / 'docs' / 'Anton_ZIF_20260923'
OUT.mkdir(exist_ok=True)

def parse(path):
    stack = [[]]
    for match in re.finditer(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', Path(path).read_text(encoding='utf-8')):
        token = match.group()
        if token == '(':
            node=[];stack[-1].append(node);stack.append(node)
        elif token == ')':
            assert len(stack)>1
            stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    assert len(stack)==1 and len(stack[0])==1
    return stack[0][0]

def rows(node, key):
    return [v for v in node if isinstance(v,list) and v and v[0]==key]

def row(node, key, default=None):
    found=rows(node,key)
    return found[0] if found else default

def val(node, key, default=None):
    r=row(node,key)
    return r[1] if r and len(r)>1 else default

def main():
    pcb_path=REF/'DSUBtoZIF_20250106.kicad_pcb'
    net_path=REF/'DSUBtoZIF_20250106.net'
    board=parse(pcb_path);netlist=parse(net_path)
    footprints=[];pads=[]
    for fp in rows(board,'footprint'):
        props={r[1]:r[2] for r in rows(fp,'property')}
        ref=props['Reference']
        footprints.append({'reference':ref,'value':props.get('Value'),'footprint':fp[1], 'at':row(fp,'at')[1:], 'layer':val(fp,'layer')})
        for p in rows(fp,'pad'):
            n=row(p,'net',['net','0',''])
            pads.append({'reference':ref,'pin':p[1],'net_code':int(n[1]),'net':n[2], 'type':p[2], 'shape':p[3],
                         'at':row(p,'at')[1:], 'size':row(p,'size')[1:], 'layers':row(p,'layers')[1:]})
    nodes={}
    for net in rows(row(netlist,'nets'),'net'):
        for node in rows(net,'node'):
            nodes[(val(node,'ref'),val(node,'pin'))]=val(net,'name')
    zif=next(f['reference'] for f in footprints if '502598' in f['value'])
    dsub=next(f['reference'] for f in footprints if '381-025' in f['value'])
    mapping=[];mismatches=[]
    for p in sorted([p for p in pads if p['reference']==zif],key=lambda p:int(p['pin']) if p['pin'].isdigit() else 1000):
        connected=[{'reference':q['reference'],'pin':q['pin']} for q in pads if q['net_code']==p['net_code'] and p['net_code'] and q['reference']!=zif]
        peers=[q['pin'] for q in pads if q['reference']==zif and q['net_code']==p['net_code'] and q['pin']!=p['pin'] and p['net_code']]
        schematic_net=nodes.get((zif,p['pin']))
        item=p|{'connected_pads':connected,'other_ZIF_pins_on_net':peers,'exported_netlist_net':schematic_net}
        mapping.append(item)
        if schematic_net is not None and schematic_net!=p['net']:
            mismatches.append({'ZIF_pin':p['pin'],'pcb_net':p['net'],'exported_netlist_net':schematic_net})
    result={'source_message':'https://qstlab.slack.com/archives/D095YL5JJAC/p1790190544437059',
            'source_note':'Anton states this is equivalent but not exactly the same as the blue PCB; he offered to confirm pin numbering.',
            'archive_sha256':hashlib.sha256((HERE/'DSUBtoZIF_20250306.zip').read_bytes()).hexdigest(),
            'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in REF.iterdir() if p.is_file()},
            'footprints':footprints,'ZIF_reference':zif,'Dsub_reference':dsub,'ZIF_pad_mapping':mapping,
            'PCB_vs_exported_netlist_name_differences':mismatches,
            'segment_count':len(rows(board,'segment')),'via_count':len(rows(board,'via'))}
    (OUT/'pinout_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'footprints':footprints,'segments':result['segment_count'],'vias':result['via_count'],'netlist_differences':mismatches},indent=2))
    for item in mapping:
        print(item['pin'],item['net'],item['connected_pads'])

if __name__=='__main__':
    main()
