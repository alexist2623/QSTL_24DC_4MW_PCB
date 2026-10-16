"""Preserve all 24 legacy even ZIF contacts and add 14 selected odd contacts."""
from pathlib import Path
import copy
import hashlib
import json
import sys

H=Path(__file__).resolve().parent


def main():
    source=Path(sys.argv[1]) if len(sys.argv)>1 else H/'placement_candidate.json'
    p=json.loads(source.read_text())
    selected=sorted(set(range(2,50,2)) | set(range(1,28,2)))
    assert len(selected)==38 and 50 not in selected
    contacts=sorted([a for a in p['physical_pads'] if a['ref']=='J1' and int(a['pin']) in selected],key=lambda a:(a['x'],a['y']))
    sources=sorted([v for v in p['vias'] if not v['label'].startswith('J1-')],key=lambda v:(v['x'],v['y']))
    assert len(sources)==len(contacts)==38
    p['vias']=sources
    mapping={};p['tracks']=[t for t in p['tracks'] if t['layer']!=1]
    for i,(v,a) in enumerate(zip(sources,contacts)):
        layer=2 if i<19 else 4
        pin=int(a['pin']);net=v['net'];q=int(net[2:])
        v.update(assigned_dc_layer=layer,routing_layer=layer)
        via=dict(x=a['x'],y=a['y']+(.55 if pin%2==0 else -.55),net=net,diameter=.4,hole=.2,
                 low=1,high=32,routing_layer=layer,assigned_dc_layer=layer,label=f'J1-{pin}')
        p['vias'].append(via);mapping[pin]=net
        p['tracks'].append(dict(net=net,layer=1,width=.15,a=[a['x'],a['y']],b=[via['x'],via['y']]))
        p['dc_endpoints'][str(q)].update(zif_pin=pin,layer=layer)
        row=next(row for row in p['pinmap'] if row['qd_pad']==q)
        row.update(zif_pin=pin,dc_layer=layer)
        job=next(j for j in p['route_jobs'] if j['kind']=='DC' and j['net']==net)
        job.update(a=[via['x'],via['y']],b=[v['x'],v['y']],layer=layer)
    for a in p['physical_pads']:
        if a['ref']=='J1':
            a['net']=mapping.get(int(a['pin']))
    p['nets']={}
    for a in p['physical_pads']:
        if a['ref'] and a['net']:
            p['nets'].setdefault(a['net'],[]).append(a['ref']+'-'+a['pin'])
    p['user_confirmed_contact_pool']=True
    p['contact_pool_policy']=dict(legacy_even_pins=list(range(2,50,2)),added_odd_pins=sorted(n for n in selected if n%2),
                                  pin50_unused=True,function_mapping_free_within_pool=True,
                                  source_placement_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    destination=Path(sys.argv[2]) if len(sys.argv)>2 else H/'pooled_placement_candidate.json'
    destination.write_text(json.dumps(p,indent=2))
    print(json.dumps(p['contact_pool_policy'],indent=2))


if __name__=='__main__':
    main()
