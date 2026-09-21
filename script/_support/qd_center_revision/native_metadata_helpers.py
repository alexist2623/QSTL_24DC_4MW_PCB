"""Read-only/native-stream preparation helpers. These functions never write a PCB.

The caller receives stream update bytes to apply to a separate workcopy using a
proper compound-document writer. In-place olefile.write_stream cannot resize.
"""
from pathlib import Path
import struct,sys,math,uuid,collections,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pcb_python'))
import olefile
UNIT=2.54e-6
GUID_TAGS={'Board6':83,'Classes6':278,'Nets6':520,'Components6':777,'Polygons6':1034,
           'Arcs6':3329,'Pads6':3586,'Vias6':3843,'Tracks6':4100,'Texts6':4357,'Fills6':4614,
           'Regions6':4953,'ShapeBasedRegions6':5209,'ComponentBodies6':5466,'ShapeBasedComponentBodies6':5722,
           'BoardRegions':7522,'SignalClasses':8214,'TComponentClearanceViolation':12114,'TSilkToSilkClearanceViolation':19026}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def properties(data):
    i=0;out=[]
    while i<len(data):
        n=struct.unpack_from('<I',data,i)[0]&0xffffff;i+=4
        out.append(dict(p.split('=',1) for p in data[i:i+n].rstrip(b'\0').decode('cp1252').split('|') if '=' in p));i+=n
    assert i==len(data)
    return out
def binary_records(data,kind):
    i=0;out=[]
    while i<len(data):
        assert data[i]==kind,(i,data[i],kind)
        n=struct.unpack_from('<I',data,i+1)[0]&0xffffff
        out.append({'index':len(out),'start':i,'end':i+5+n,'body_offset':i+5,'body':data[i+5:i+5+n]});i+=5+n
    assert i==len(data)
    return out
def pad_record(data,position):
    start=position;assert data[position]==2;position+=1;blocks=[];offsets=[]
    for j in range(6):
        n=struct.unpack_from('<I',data,position)[0]&0xffffff
        offsets.append(position+4);blocks.append(data[position+4:position+4+n]);position+=4+n
    b=blocks[4];assert len(b)>=60
    return {'start':start,'end':position,'blocks':blocks,'block_offsets':offsets,'number':blocks[0][1:].decode(),
            'component':struct.unpack_from('<H',b,7)[0],'net':struct.unpack_from('<H',b,3)[0],
            'coords':list(struct.unpack_from('<9i',b,13)),'rotation':struct.unpack_from('<d',b,52)[0],'shape':b[49],'layer':b[0]}
def pads_stream(data):
    out=[];i=0
    while i<len(data):
        p=pad_record(data,i);p['index']=len(out);out.append(p);i=p['end']
    assert i==len(data)
    return out

def qd_library_updates(source_library):
    """Return {stream:bytes},audit for requested0.5mm pads at radial±3.95mm.

    Only six size int32 fields and the one radial-center int32 are changed per
    pad. Pin numbering, pad order, GUID/UniqueID records, rotation, mask setup,
    net/component fields, tangential positions and the7x7 fill are preserved.
    """
    before=sha(source_library)
    with olefile.OleFileIO(source_library) as ole:
        data=ole.openstream('QD4/Data').read()
        guid=ole.openstream('QD4/PrimitiveGuids/Data').read()
        uid=ole.openstream('QD4/UniqueIDPrimitiveInformation/Data').read()
    n=struct.unpack_from('<I',data,0)[0]&0xffffff
    assert data[4:4+n]==b'\x03QD4'
    pos=4+n;updated=bytearray(data);audit=[];seen=set();allowed=set();other=[]
    size=round(.5/UNIT);radial=round(3.95/UNIT)
    while pos<len(data):
        if data[pos]!=2:
            kind=data[pos];n=struct.unpack_from('<I',data,pos+1)[0]&0xffffff
            other.append({'kind':kind,'start':pos,'end':pos+5+n});pos+=5+n;continue
        p=pad_record(data,pos);pos=p['end'];seen.add(p['number']);b=p['blocks'][4];base=p['block_offsets'][4]
        assert len(b)==202 and p['shape']==2 and p['layer']==1
        x,y,sx,sy,mx,my,bx,by,hole=p['coords']
        assert hole==0 and sx==mx==bx and sy==my==by
        assert abs(sx*UNIT-2)<3e-6 and abs(sy*UNIT-.5)<3e-6
        if abs(p['rotation']%180)<1e-8:
            axis=0;old_radial=x;new_xy=[(1 if x>0 else -1)*radial,y]
        elif abs(p['rotation']%180-90)<1e-8:
            axis=1;old_radial=y;new_xy=[x,(1 if y>0 else -1)*radial]
        else:raise ValueError('Unsupported pad rotation')
        assert abs(abs(old_radial)*UNIT-5)<3e-6
        fields={13+4*axis:new_xy[axis],21:size,25:size,29:size,33:size,37:size,41:size}
        for offset,value in fields.items():
            struct.pack_into('<i',updated,base+offset,value)
            allowed.update(range(base+offset,base+offset+4))
        audit.append({'pin':p['number'],'block4_offset':base,'old_center_mm':[x*UNIT,y*UNIT],'new_center_mm':[v*UNIT for v in new_xy],
                      'old_size_mm':[sx*UNIT,sy*UNIT],'new_size_mm':[size*UNIT,size*UNIT],'rotation_unchanged':p['rotation'],
                      'radial_inner_edge_mm':(radial-size/2)*UNIT,'radial_outer_edge_mm':(radial+size/2)*UNIT,
                      'changed_body_field_offsets':sorted(fields)})
    assert seen=={str(i) for i in range(1,26)} and len(audit)==25
    changed={i for i,(a,b) in enumerate(zip(data,updated)) if a!=b};assert changed<=allowed
    assert len(updated)==len(data)
    for obj in other:assert data[obj['start']:obj['end']]==updated[obj['start']:obj['end']]
    assert len(other)==1 and other[0]['kind']==6,'QD4 contains unexpected non-pad objects'
    assert before==sha(source_library)
    return {'QD4/Data':bytes(updated)}, {'source':str(source_library),'source_sha256':before,'source_unchanged':True,'pads':audit,'other_primitive_records_preserved':other,
        'changed_byte_count':len(changed),'source_guid_sha256':hashlib.sha256(guid).hexdigest(),'source_pad_uid_sha256':hashlib.sha256(uid).hexdigest(),
        'native_grid_mm':UNIT,'actual_pad_size_mm':size*UNIT,'actual_radial_center_mm':radial*UNIT,'nominal_inner_mm':3.7,'nominal_outer_mm':4.2}

def primitive_guid_records(data):
    assert len(data)%24==0
    return [{'type_tag':struct.unpack_from('<I',data,i)[0],'index':struct.unpack_from('<I',data,i+4)[0],
             'guid':str(uuid.UUID(bytes_le=data[i+8:i+24])),'raw':data[i:i+24]} for i in range(0,len(data),24)]
def remap_primitive_guids(data,index_maps):
    """index_maps maps FULL tag -> {oldlocalindex:newlocalindex}; {} deletes tag.

    Untouched tag groups and every retained GUID's16 bytes are byte-identical.
    Record ordering is preserved, except deleted entries are omitted.
    """
    entries=primitive_guid_records(data);out=[];removed=[];changes=[]
    for row in entries:
        tag,old=row['type_tag'],row['index'];raw=row['raw']
        if tag in index_maps:
            mapping=index_maps[tag]
            if old not in mapping:removed.append({'type_tag':tag,'index':old,'guid':row['guid']});continue
            new=mapping[old]
            if new!=old:changes.append({'type_tag':tag,'old_index':old,'new_index':new,'guid':row['guid']})
            raw=struct.pack('<II',tag,new)+raw[8:]
        out.append(raw)
    result=b''.join(out)
    parsed=primitive_guid_records(result)
    assert len({(x['type_tag'],x['index']) for x in parsed})==len(parsed)
    return {'PrimitiveGuids/Data':result,'PrimitiveGuids/Header':struct.pack('<I',len(out))},{'before_count':len(entries),'after_count':len(out),'removed':removed,'remapped':changes}

def detach_cache_links(source_pcb,pad_indices,remove_all_vias=False):
    """Remove modified-pad links to stale stack templates, optionally deleted vias.

    Cache templates are retained unchanged, including their opaque HASH fields.
    Remaining links retain original cache indices; no template renumbering.
    """
    before=sha(source_pcb)
    with olefile.OleFileIO(source_pcb) as ole:
        data=ole.openstream('PadViaCacheLibraryLinksSection/Data').read()
        header=struct.unpack('<I',ole.openstream('PadViaCacheLibraryLinksSection/Header').read())[0]
    assert len(data)==header*10
    kept=[];removed=[];seen=set()
    for i in range(0,len(data),10):
        flag,index,kind,cache=struct.unpack_from('<BIBI',data,i)
        assert flag==0 and kind in (2,3),'Unknown link format; stop instead of guessing'
        remove=(kind==2 and index in pad_indices) or (kind==3 and remove_all_vias)
        if remove:
            removed.append({'flag':flag,'primitive_index':index,'primitive_kind':kind,'cache_index':cache})
            if kind==2:seen.add(index)
        else:kept.append(data[i:i+10])
    assert seen==set(pad_indices),'Not all requested modified pads have the expected cache link'
    assert before==sha(source_pcb)
    return {'PadViaCacheLibraryLinksSection/Data':b''.join(kept),'PadViaCacheLibraryLinksSection/Header':struct.pack('<I',len(kept))},\
        {'before_count':header,'after_count':len(kept),'removed_links':removed,'source_unchanged':True,'cache_template_bytes_not_changed':True,
         'interpretation':'Detaches modified pads from their old cached2x0.5 stack; pad record carries explicit new size. Confirm in Altium after reopening.'}
