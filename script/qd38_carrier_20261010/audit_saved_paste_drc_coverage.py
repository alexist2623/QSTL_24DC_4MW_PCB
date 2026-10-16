"""Read-only saved native paste-object inventory and DRC coverage inventory."""
from pathlib import Path
from collections import Counter
import hashlib
import html
import json
import re
import struct
import sys

import olefile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,binary_records,pads_stream,UNIT


def main():
    path=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    with olefile.OleFileIO(path) as doc:
        blobs={'/'.join(k):doc.openstream(k).read() for k in doc.listdir()}
    board=properties(blobs['Board6/Data'])[0]
    rules=[];offset=0;data=blobs['Rules6/Data']
    while offset<len(data):
        kind,count=struct.unpack_from('<HI',data,offset);offset+=6
        fields=dict(t.split('=',1) for t in data[offset:offset+count].rstrip(b'\0').decode('cp1252').split('|') if '=' in t)
        offset+=count
        rules.append(dict(kind=kind,fields=fields))
    paste_objects={};all_layers={}
    for stream,kind in [('Tracks6/Data',4),('Arcs6/Data',1),('Fills6/Data',6),('Regions6/Data',11),('ShapeBasedRegions6/Data',11)]:
        records=binary_records(blobs.get(stream,b''),kind)
        paste_objects[stream]=[i for i,record in enumerate(records) if record['body'][0] in (35,36)]
        all_layers[stream]=dict(Counter(record['body'][0] for record in records))
    pads=pads_stream(blobs['Pads6/Data'])
    paste_objects['Pads6/Data']=[p['index'] for p in pads if p['layer'] in (35,36)]
    vias=binary_records(blobs['Vias6/Data'],3)
    integers={name:round(value/UNIT) for name,value in [('negative2mm',-2),('negative1mm',-1)]}
    matches={}
    for name,value in integers.items():
        needle=struct.pack('<i',value)
        histogram=Counter()
        for record in vias:
            b=record['body']
            offsets=[i for i in range(len(b)-3) if b[i:i+4]==needle]
            histogram[str(offsets)]+=1
        matches[name]=dict(histogram)
    text=(HERE/'Native_DRC.html').read_text(errors='replace')
    summary=re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>',text,re.S)
    summary=[dict(rule=html.unescape(re.sub('<[^>]+>','',name)),violations=int(count)) for name,count in summary]
    interesting={k:v for k,v in board.items() if re.search(r'DRC|CHECK|VIOLATION',k,re.I)}
    paste_like=[]
    for stream,data in blobs.items():
        if not stream.endswith('/Data') or stream.split('/')[0] in ('Board6','Rules6'):
            continue
        value=data.decode('cp1252',errors='replace')
        found=sorted(set(re.findall(r'\|([^|\x00]{0,40}PASTE[^|\x00]{0,80})',value,re.I)))
        if found:paste_like.append(dict(stream=stream,fields=found[:40]))
    report=dict(status='SAVED_NATIVE_READ_ONLY_INVENTORY_NOT_CAM_EXPORT',native_file=str(path),native_sha256=before,
                explicit_paste_object_count=sum(len(v) for v in paste_objects.values()),explicit_paste_objects=paste_objects,
                layer_counts=all_layers,via_count=len(vias),via_record_lengths=dict(Counter(len(v['body']) for v in vias)),
                via_negative_expansion_binary_matches=matches,
                saved_board_drc_fields=interesting,saved_rules=rules,reported_rules=summary,
                drc_stopped_at_limit='DRC was stopped' in text,
                component_clearance_in_report=any('Component Clearance' in x['rule'] for x in summary),
                routing_via_style_in_report=any('Via' in x['rule'] and ('Style' in x['rule'] or 'Routing' in x['rule']) for x in summary),
                paste_property_fields=paste_like,
                source_unchanged=hashlib.sha256(path.read_bytes()).hexdigest()==before)
    (HERE/'saved_paste_drc_coverage.json').write_text(json.dumps(report,indent=2))
    small={k:v for k,v in report.items() if k not in ('saved_rules','reported_rules','layer_counts','paste_property_fields')}
    print(json.dumps(small,indent=2))
    print('RULES')
    for rule in rules:
        f=rule['fields']; print(rule['kind'],{k:v for k,v in f.items() if re.search(r'NAME|KIND|ENABLED|DRC|BATCH',k,re.I)})
    print('REPORTED_RULE_TYPES',[r['rule'].split('(')[0] for r in summary])
    print('PASTE_EXTRA_FIELDS',paste_like)


if __name__=='__main__':main()
