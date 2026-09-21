"""Create an offline routed PCB WORKCOPY; never modifies an opened project.

Full mode requires the canonical approved100-pin37-net mapping and its approved
JSON provenance. Dry-run may inspect an unapproved planning netlist but writes
no PcbDoc. Known-external mode can change only SMP1..4.1 / C1..4.1 to S1..4.
All dimensions are millimeters; copper layers are native Altium1,2,4.
"""
from pathlib import Path
import sys,json,struct,hashlib,uuid,math,re,argparse,collections

P=Path(__file__).resolve().parent
FINAL=P.parent
WORK=FINAL.parent
ROOT=WORK.parent
sys.path.insert(0,str(WORK/'qd_center_revision'))
from native_metadata_helpers import properties,pads_stream,binary_records,primitive_guid_records,GUID_TAGS,UNIT,sha,olefile
from cfb_copy_update import update_copy

BASE=ROOT/'outputs'/'QSTL_QD_centered_project'/'QSTL_24DC_4MW_PCB.PcbDoc'
BASE_HASH='406e8213d5fc75d9c71ac91908929e01525054cb675725dd391dec3d466afe71'
TEMPLATE=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc')
VIA_PROBE=FINAL/'native_probe'/'RoutingNativeProbe.PcbDoc'
NAMESPACE=uuid.UUID('e8dc1e3a-d80b-5aa0-bad8-87a2b31aa1e7')
U16NULL=65535
SOURCE_PARSER='https://raw.githubusercontent.com/KiCad/kicad-source-mirror/master/pcbnew/pcb_io/altium/altium_parser_pcb.cpp'

def require(ok,message):
    if not ok:raise ValueError(message)

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def snapshot(path):
    with olefile.OleFileIO(path) as o:return {'/'.join(k):o.openstream(k).read() for k in o.listdir()}

def coord(value):
    value=float(value);require(math.isfinite(value),'Nonfinite coordinate')
    out=round(value/UNIT);require(-2147483648<=out<=2147483647,'Coordinate outside native int32')
    return out

def chunks(data):
    out=[];i=0
    while i<len(data):
        n=struct.unpack_from('<I',data,i)[0]&0xffffff;out.append(data[i+4:i+4+n]);i+=4+n
    require(i==len(data),'Property chunk boundary mismatch');return out

def packchunks(rows):return b''.join(struct.pack('<I',len(r))+r for r in rows)
def packobjects(rows,kind):return b''.join(bytes([kind])+struct.pack('<I',len(r))+r for r in rows)
def field_bytes(row):return ('|'+'|'.join(k+'='+str(v) for k,v in row.items())+'\0').encode('cp1252')

def replace_fields(raw,changes):
    value=raw.rstrip(b'\0').decode('cp1252')
    for key,new in changes.items():
        value,count=re.subn(r'(?<=\|)'+re.escape(key)+r'=[^|]*',lambda _:key+'='+str(new),value)
        require(count==1,'Expected exactly one property '+key)
    return value.encode('cp1252')+b'\0'

def read_inputs(basepath,netpath,routepath):
    digest=sha(basepath);require(digest==BASE_HASH,'Base is not the verified centered406e8213 PCB')
    d=snapshot(basepath);original=snapshot(TEMPLATE)
    netlist=load(netpath) if netpath else None;route=load(routepath)
    require(route.get('units')=='mm','Route schema must declare units:mm')
    require(route.get('source_pcb_sha256')==digest,'Route plan not anchored to this centered PCB')
    for name in ['tracks','arcs','vias']:require(isinstance(route.get(name),list),'Route schema requires '+name+' list')
    comps=properties(d['Components6/Data']);pads=pads_stream(d['Pads6/Data']);nets=properties(d['Nets6/Data'])
    require(len(comps)==18 and len(pads)==100,'Expected18 components100 pads')
    ids={comps[p['component']]['SOURCEDESIGNATOR']+'-'+p['number']:p for p in pads}
    require(len(ids)==100,'Duplicate actual component-pad identifiers')
    require(len(binary_records(d['Tracks6/Data'],4))==30 and not d['Vias6/Data'],'Base already contains routing')
    require(len(binary_records(d['Arcs6/Data'],1))==6,'Expected six fixed connector arcs')
    for storage,kind in [('Tracks6',4),('Arcs6',1),('Fills6',6),('Regions6',11),('ShapeBasedRegions6',11),('ComponentBodies6',12),('ShapeBasedComponentBodies6',12)]:
        require(all(struct.unpack_from('<H',r['body'],3)[0]==U16NULL for r in binary_records(d[storage+'/Data'],kind)),'Unexpected assigned net on retained '+storage)
    for storage in ['Connections6','DifferentialPairs6','FromTos6','SmartUnions']:
        require(not d[storage+'/Data'],'Unexpected derived connectivity needing remap: '+storage)
    return d,original,netlist,route,comps,pads,nets,ids

def native_templates(original,current):
    tracks={layer:next(r['body'] for r in binary_records(original['Tracks6/Data'],4) if r['body'][0]==layer) for layer in (1,2,4)}
    for layer,b in tracks.items():
        require(len(b)==49 and struct.unpack_from('<I',b,41)[0]==0x01000000+layer,'Unexpected track layer encoding')
        require(b[5:13]==b'\xff'*8,'Track template has polygon/component ownership')
    arc=binary_records(current['Arcs6/Data'],1)[0]['body']
    require(len(arc)==60,'Arc template not60 bytes')
    native_probe=snapshot(VIA_PROBE)
    vias=[r['body'] for r in binary_records(native_probe['Vias6/Data'],3)]
    require(len(vias)==1,'Native via probe must contain exactly one native-created via')
    via=vias[0]
    require(len(via)==321 and via[29:31]==b'\x01\x20','Expected321-byte through-via')
    require(via[74]==0,'Only native simple pad-stack via template supported')
    diameter=struct.unpack_from('<i',via,21)[0]
    require(all(struct.unpack_from('<i',via,75+4*i)[0]==diameter for i in range(32)),'Unexpected via per-layer diameter encoding')
    # These two fields are cache template/library IDs, not object IDs. Native
    # saving auto-created a matching template even for the factory-default via.
    cache=native_probe['PadViaLibraryCache/Data'].decode('cp1252',errors='replace').upper()
    tid=str(uuid.UUID(bytes_le=via[259:275])).upper();lid=str(uuid.UUID(bytes_le=via[275:291])).upper()
    require('TEMPLATE.TEMPLATEID={'+tid+'}' in cache,'Via tail template GUID not proven')
    require('PADVIALIBRARY.LIBRARYID={'+lid+'}' in cache,'Via tail library GUID not proven')
    require(all(v[259:291]==via[259:291] for v in vias),'Via tail IDs differ across saved template examples')
    return tracks,arc,via,{'track_body_length':49,'track_layer_v7_offset':41,'arc_body_length':60,'arc_layer_v7_offset':52,
        'via_body_length':321,'via_diameter_offset':21,'via_hole_offset':25,'via_32_layer_diameter_start':75,
        'via_cached_template_guid_offset':259,'via_cached_library_guid_offset':275,'old_via_template_guid':tid,'old_via_cache_library_guid':lid,
        'authentic_via_template_source':str(VIA_PROBE),'authentic_via_template_source_sha256':sha(VIA_PROBE),
        'cache_detachment':'New via cache GUID fields zeroed; no PadViaCacheLibraryLinks entries created. Native reopen/save must validate detachment.',
        'format_crosscheck_primary_source':SOURCE_PARSER}

def uid8(token,used):
    number=int(hashlib.sha256(token.encode()).hexdigest(),16);letters=''
    for _ in range(8):letters+=chr(65+number%26);number//=26
    require(letters not in used,'Deterministic UID collision');used.add(letters);return letters

def approved_map(netlist,route,ids,dry):
    require(netlist is not None,'Full mode requires canonical netlist')
    mapping=netlist.get('pin_net_map',{});expected=netlist.get('nets',{})
    require(len(mapping)==100 and set(mapping)==set(ids),'Netlist does not cover exactly100 actual pads')
    require(len(expected)==37 and set(mapping.values())==set(expected),'Netlist must retain37 names')
    require({p:n for n,pp in expected.items() for p in pp}==mapping and sum(map(len,expected.values()))==100,'Netlist membership fields disagree')
    if not dry:
        require(netlist.get('approved') is True,'No full write: mapping has not been approved')
        path=Path(netlist['mapping_file']);require(sha(path)==netlist['mapping_sha256'],'Approved mapping provenance changed')
        approved=load(path);require(approved.get('approved') is True and bool(approved.get('decision_source')),'Approved mapping decision missing')
        require(route.get('mapping_sha256')==netlist['mapping_sha256'],'Route plan does not declare canonical approved mapping SHA256')
    return mapping,sorted(expected)

def prepare_updates(d,original,netlist,route,comps,pads,oldnets,ids,mode,dry,seed):
    changes={};audit={};tracks,arctemplate,viatemplate,template_audit=native_templates(original,d)
    useduids={r.get('UNIQUEID') for r in oldnets if r.get('UNIQUEID')}
    oldname=[r['NAME'] for r in oldnets]
    if mode=='full':
        pin_net,names=approved_map(netlist,route,ids,dry)
        newnets=[]
        for name in names:
            row=dict(oldnets[0]);row.update(NAME=name,UNIQUEID=uid8(seed+'|net|'+name,useduids));newnets.append(row)
        audit['mapping_approved']=netlist.get('approved') is True
    else:
        require(mode=='known_external','Unknown mode')
        names=oldname+['S'+str(i) for i in range(1,5)]
        require(len(set(names))==30,'Partial net names already exist')
        newnets=list(oldnets)
        for name in names[len(oldnets):]:
            row=dict(oldnets[0]);row.update(NAME=name,UNIQUEID=uid8(seed+'|partial|'+name,useduids));newnets.append(row)
        pin_net={key:(oldname[p['net']] if p['net']!=U16NULL else None) for key,p in ids.items()}
        for i in range(1,5):
            for key in [f'SMP{i}-1',f'C{i}-1']:pin_net[key]='S'+str(i)
        require(all(r['net'] in {'S1','S2','S3','S4'} for kind in ['tracks','arcs'] for r in route[kind]),'Partial mode supports only proven S1..4 connector-capacitor tracks/arcs')
        for r in route['vias']:
            ordinary=r['net'] in {'S1','S2','S3','S4'}
            validation_probe=route.get('scratch_native_validation') is True and r['net']=='GND' and r.get('x')==9.75 and r.get('y')==63 and r.get('diameter')==.3 and r.get('hole')==.2
            require(ordinary or validation_probe,'Partial GND via requires exact authorized scratch validation fixture')
        audit['mapping_approved']=False;audit['partial_scope']='Only eight SMP1..4 center/C1..4 pin1 endpoints assigned; old QD/DC placeholder nets preserved.'
    index={name:i for i,name in enumerate(names)}
    changes['Nets6/Data']=packchunks([field_bytes(r) for r in newnets]);changes['Nets6/Header']=struct.pack('<I',len(newnets))
    padbytes=bytearray(d['Pads6/Data']);changedpads=[]
    for key,p in ids.items():
        value=index[pin_net[key]] if pin_net[key] is not None else U16NULL
        struct.pack_into('<H',padbytes,p['block_offsets'][4]+3,value)
        if value!=p['net']:changedpads.append(key)
    changes['Pads6/Data']=bytes(padbytes)
    # Preserve all four polygon geometries and settings; only remap their net.
    polyraw=chunks(d['Polygons6/Data']);polys=properties(d['Polygons6/Data'])
    require(len(polys)==4 and all(oldname[int(p['NET'])]=='GND' for p in polys),'Expected four GND polygons')
    changes['Polygons6/Data']=packchunks([replace_fields(b,{'NET':index['GND']}) for b in polyraw])
    classes=properties(d['Classes6/Data']);classraw=chunks(d['Classes6/Data']);classchanges=[]
    for i,c in enumerate(classes):
        if c.get('KIND')!='0':continue
        members=[k for k in c if re.fullmatch('M[0-9]+',k)]
        if not members:continue
        require(c['NAME']=='All Nets' and c.get('SUPERCLASS')=='TRUE','Explicit named net class needs human remap: '+c['NAME'])
        new={k:v for k,v in c.items() if k not in members}
        new.update({'M'+str(j):name for j,name in enumerate(names)});classraw[i]=field_bytes(new);classchanges.append(c['NAME'])
    if classchanges:changes['Classes6/Data']=packchunks(classraw)
    guidrows=primitive_guid_records(d['PrimitiveGuids/Data'])
    if mode=='full':retained=[r['raw'] for r in guidrows if r['type_tag']!=GUID_TAGS['Nets6']];newnetstart=0
    else:retained=[r['raw'] for r in guidrows];newnetstart=len(oldnets)
    def addguid(kind,i):
        retained.append(struct.pack('<II',GUID_TAGS[kind],i)+uuid.uuid5(NAMESPACE,seed+'|'+kind+'|'+str(i)).bytes_le)
    for i in range(newnetstart,len(newnets)):addguid('Nets6',i)
    rows_tracks=[r['body'] for r in binary_records(d['Tracks6/Data'],4)]
    rows_arcs=[r['body'] for r in binary_records(d['Arcs6/Data'],1)]
    rows_vias=[];quantized={'tracks':[],'arcs':[],'vias':[]};skipped=[]
    def netid(r):
        require(isinstance(r.get('net'),str) and r['net'] in index,'Unknown route net '+str(r.get('net')))
        return index[r['net']]
    def copper_layer(r):
        layer=r.get('layer');require(layer in (1,2,4),'Only native copper layers1,2,4 allowed');return layer
    for i,r in enumerate(route['tracks']):
        layer=copper_layer(r);b=bytearray(tracks[layer]);ni=netid(r)
        values=[coord(r[k]) for k in ('x1','y1','x2','y2','width')]
        require(values[4]>0,'Track width must be positive')
        if values[:2]==values[2:4]:skipped.append({'kind':'track','input_index':i,'reason':'zero length on native coordinate grid'});continue
        struct.pack_into('<H',b,3,ni);struct.pack_into('<5i',b,13,*values)
        struct.pack_into('<I',b,36,0)
        addguid('Tracks6',len(rows_tracks));rows_tracks.append(bytes(b))
        quantized['tracks'].append(dict(net=r['net'],layer=layer,**dict(zip(('x1','y1','x2','y2','width'),[v*UNIT for v in values]))))
    for i,r in enumerate(route['arcs']):
        layer=copper_layer(r);b=bytearray(arctemplate);ni=netid(r)
        x=r['cx'] if 'cx' in r else r['x'];y=r['cy'] if 'cy' in r else r['y']
        values=[coord(v) for v in (x,y,r['radius'],r['width'])]
        require(values[2]>0 and values[3]>0,'Arc radius and width must be positive')
        start=float(r['start_angle']);end=float(r['end_angle']);require(math.isfinite(start) and math.isfinite(end),'Nonfinite arc angle')
        require(r.get('direction','ccw').lower()=='ccw','Arcs must use native CCW start/end convention')
        sweep=(end-start)%360;require(0<sweep<360,'New routing arc must be a nonzero partial circle')
        start%=360;end%=360;b[0]=layer;b[1]=tracks[layer][1];b[2]=0
        struct.pack_into('<3H',b,3,ni,U16NULL,U16NULL);b[9:13]=b'\xff'*4
        struct.pack_into('<3i',b,13,*values[:3]);struct.pack_into('<2d',b,25,start,end);struct.pack_into('<i',b,41,values[3])
        struct.pack_into('<I',b,48,0);struct.pack_into('<I',b,52,0x01000000+layer);b[56]=0
        addguid('Arcs6',len(rows_arcs));rows_arcs.append(bytes(b))
        quantized['arcs'].append(dict(net=r['net'],layer=layer,x=values[0]*UNIT,y=values[1]*UNIT,radius=values[2]*UNIT,width=values[3]*UNIT,start_angle=start,end_angle=end,direction='ccw'))
    for i,r in enumerate(route['vias']):
        ni=netid(r);b=bytearray(viatemplate)
        require(r.get('start_layer',1)==1 and r.get('end_layer',32)==32,'Only verified Top-Bottom through-vias supported')
        values=[coord(r[k]) for k in ('x','y','diameter','hole')]
        require(0<values[3]<values[2],'Via hole must be positive and smaller than copper diameter')
        struct.pack_into('<H',b,3,ni);struct.pack_into('<4i',b,13,*values)
        for j in range(32):struct.pack_into('<i',b,75+4*j,values[2])
        b[259:291]=b'\0'*32
        addguid('Vias6',len(rows_vias));rows_vias.append(bytes(b))
        quantized['vias'].append(dict(net=r['net'],x=values[0]*UNIT,y=values[1]*UNIT,diameter=values[2]*UNIT,hole=values[3]*UNIT,start_layer=1,end_layer=32))
    for storage,kind,rows in [('Tracks6',4,rows_tracks),('Arcs6',1,rows_arcs),('Vias6',3,rows_vias)]:
        changes[storage+'/Data']=packobjects(rows,kind);changes[storage+'/Header']=struct.pack('<I',len(rows))
    changes['PrimitiveGuids/Data']=b''.join(retained);changes['PrimitiveGuids/Header']=struct.pack('<I',len(retained))
    # Existing75 pad-cache links remain valid. No newly cloned via inherits a
    # link to the old0.5/0.25mm template, even when its index equals an old via.
    cache=d['PadViaCacheLibraryLinksSection/Data'];require(len(cache)==750,'Expected75 retained pad-cache links')
    require(all(struct.unpack_from('<BIBI',cache,i)[2]==2 for i in range(0,len(cache),10)),'Base still has via cache links')
    audit.update(template_audit=template_audit,net_index=index,pin_net_map=pin_net,changed_pad_net_fields=changedpads,
        component_and_pad_geometry_preserved=True,pad_uniqueids_preserved=True,retained_tracks=30,retained_arcs=6,
        polygons_net_remapped_to=index['GND'],classes_updated=classchanges,net_count=len(newnets),
        added_primitive_counts={k:len(v) for k,v in quantized.items()},skipped_quantized_zero_length_tracks=skipped,
        primitive_guid_count=len(retained),cache_links_preserved=75,new_via_cache_links=0,
        requires_native_repour_and_DRC=True,quantized_routes=quantized)
    verify_updates(d,changes,audit)
    return changes,audit

def verify_updates(before,changes,audit):
    after=before|changes;guids=primitive_guid_records(after['PrimitiveGuids/Data'])
    require(len({(g['type_tag'],g['index']) for g in guids})==len(guids),'Duplicate primitive type/index GUID records')
    # Native shape-based and rendered regions/bodies intentionally share GUIDs.
    # Preserve those existing pairs while forbidding any new duplication.
    old_counts=collections.Counter(g['guid'] for g in primitive_guid_records(before['PrimitiveGuids/Data']))
    new_counts=collections.Counter(g['guid'] for g in guids)
    require(all(count<=max(1,old_counts[key]) for key,count in new_counts.items()),'New duplicate primitive GUID')
    for name in ('Nets6','Tracks6','Arcs6','Vias6'):
        count=struct.unpack('<I',after[name+'/Header'])[0]
        indices={g['index'] for g in guids if g['type_tag']==GUID_TAGS[name]}
        require(indices==set(range(count)),'Incomplete primitive GUID index set '+name)
    a=pads_stream(before['Pads6/Data']);b=pads_stream(after['Pads6/Data'])
    allowed=set()
    for x,y in zip(a,b):
        require(x['coords']==y['coords'] and x['number']==y['number'] and x['component']==y['component'] and x['rotation']==y['rotation'],'Pad identity or geometry altered')
        allowed.update(range(x['block_offsets'][4]+3,x['block_offsets'][4]+5))
    require(len(before['Pads6/Data'])==len(after['Pads6/Data']),'Pad stream resized')
    require(all(i in allowed for i,(x,y) in enumerate(zip(before['Pads6/Data'],after['Pads6/Data'])) if x!=y),'Pad non-net bytes modified')
    for name,kind,keep in [('Tracks6',4,30),('Arcs6',1,6)]:
        old=[r['body'] for r in binary_records(before[name+'/Data'],kind)]
        new=[r['body'] for r in binary_records(after[name+'/Data'],kind)]
        require(old==new[:keep],'Retained connector/passive primitive altered')
    for row,expected in zip(binary_records(after['Vias6/Data'],3),audit['quantized_routes']['vias']):
        b=row['body'];dim=coord(expected['diameter'])
        require(b[259:291]==b'\0'*32 and all(struct.unpack_from('<i',b,75+4*i)[0]==dim for i in range(32)),'Via size/cache detachment mismatch')
    require(before['UniqueIDPrimitiveInformation/Data']==after['UniqueIDPrimitiveInformation/Data'],'Pad UID data changed')
    audit['independent_payload_structural_checks_passed']=True

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=BASE);ap.add_argument('--netlist',type=Path,default=P/'rf_expected_netlist.json')
    ap.add_argument('--routes',required=True,type=Path);ap.add_argument('--destination',required=True,type=Path);ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--mode',choices=['full','known_external'],default='full');args=ap.parse_args()
    source=args.source.resolve();dest=args.destination.resolve();require(dest.is_relative_to(FINAL.resolve()),'Destination must be a new work/final_routing file')
    require(dest.suffix.lower()=='.pcbdoc' and not dest.exists() and dest!=source,'Destination must be a new PcbDoc workcopy')
    out=dest.with_suffix('.dry_run.json' if args.dry_run else '.build.json')
    require(not out.exists(),'Audit output already exists; choose fresh destination')
    reference=load(WORK/'rf_revision'/'reference_netlist.json')
    protected=[source,TEMPLATE,VIA_PROBE,Path(reference['reference_schematic']),Path(reference['reference_pcb'])]
    hashes={str(x):sha(x) for x in protected}
    netpath=args.netlist.resolve() if args.mode=='full' else None
    d,old,netlist,route,comps,pads,nets,ids=read_inputs(source,netpath,args.routes)
    seed=hashes[str(source)]+'|'+sha(args.routes)+'|'+(sha(netpath) if netpath else 'known_external')
    changes,audit=prepare_updates(d,old,netlist,route,comps,pads,nets,ids,args.mode,args.dry_run,seed)
    audit.update(mode=args.mode,dry_run=args.dry_run,source=str(source),destination=str(dest),protected_input_hashes=hashes,
        route_file=str(args.routes.resolve()),route_sha256=sha(args.routes),netlist_file=str(netpath) if netpath else None,
        updated_streams={k:{'old_size':len(d[k]),'new_size':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in changes.items()})
    if not args.dry_run:audit['copy_write']=update_copy(source,dest,changes)
    require(hashes=={str(x):sha(x) for x in protected},'Protected input changed during operation')
    audit['all_protected_inputs_unchanged']=True
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'dry_run':args.dry_run,'mode':args.mode,'report':str(out),'net_count':audit['net_count'],
                      'added_primitive_counts':audit['added_primitive_counts'],'source_unchanged':True,'written_pcb':None if args.dry_run else str(dest)},indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,AssertionError) as exc:print('GUARD STOP: '+str(exc));raise SystemExit(2)
