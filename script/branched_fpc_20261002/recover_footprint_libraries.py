"""Recover exact local footprint libraries from saved PCB component primitives.

This changes only the adapter schematics/project membership and creates local
libraries. PCB geometry is read-only. Native library loading and project compile
must subsequently verify the generated libraries in Altium.
"""
from pathlib import Path
import ctypes as C
import hashlib
import json
import shutil
import struct
import sys
import uuid

H=Path(__file__).resolve().parent; R=H.parents[1]
P=R/'QSTL_24DC_4MW_PCB'; OUT=P/'FPC_Adapters_20261002'
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import olefile, properties, pads_stream, binary_records
from cfb_copy_update import update_copy, _method, _hr, _release, PTR, DWORD, HRESULT


def block(b): return struct.pack('<I',len(b))+b
def text_block(s): return block(s.encode('cp1252')+b'\0')
def props(p): return text_block('|'+'|'.join(k+'='+str(v) for k,v in p.items()))
def short_string(s):
    b=s.encode('cp1252')
    return block(bytes([len(b)])+b)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(p):
    with olefile.OleFileIO(p) as o:
        return {'/'.join(k):o.openstream(k).read() for k in o.listdir()}


def create_storage(path, streams):
    """Use Windows structured storage; never invent a compound-file FAT."""
    assert not path.exists()
    ole=C.WinDLL('ole32'); ole.CoInitializeEx.argtypes=[PTR,DWORD]
    ole.CoInitializeEx.restype=HRESULT
    init=ole.CoInitializeEx(None,2)
    ole.StgCreateDocfile.argtypes=[C.c_wchar_p,DWORD,DWORD,C.POINTER(PTR)]
    ole.StgCreateDocfile.restype=HRESULT
    root=PTR(); handles={'':root}; mode=0x1012
    try:
        _hr(ole.StgCreateDocfile(str(path),mode,0,C.byref(root)),'Create library storage')
        for name,data in sorted(streams.items()):
            parts=name.split('/'); parent=root; prefix=''
            for part in parts[:-1]:
                prefix=(prefix+'/' if prefix else '')+part
                if prefix not in handles:
                    child=PTR()
                    _hr(_method(parent,5,HRESULT,[C.c_wchar_p,DWORD,DWORD,DWORD,C.POINTER(PTR)])(parent,part,mode,0,0,C.byref(child)),'Create footprint storage')
                    handles[prefix]=child
                parent=handles[prefix]
            stream=PTR()
            try:
                _hr(_method(parent,3,HRESULT,[C.c_wchar_p,DWORD,DWORD,DWORD,C.POINTER(PTR)])(parent,parts[-1],mode,0,0,C.byref(stream)),'Create library stream')
                buffer=C.create_string_buffer(data); written=DWORD()
                _hr(_method(stream,4,HRESULT,[PTR,DWORD,C.POINTER(DWORD)])(stream,C.cast(buffer,PTR),len(data),C.byref(written)),'Write library stream')
                assert written.value==len(data)
                _hr(_method(stream,8,HRESULT,[DWORD])(stream,0),'Commit stream')
            finally: _release(stream)
        for key in sorted(handles,key=lambda x:x.count('/'),reverse=True):
            _hr(_method(handles[key],9,HRESULT,[DWORD])(handles[key],0),'Commit storage')
    finally:
        for key in sorted(handles,key=lambda x:(x.count('/'),len(x)),reverse=True):_release(handles[key])
        if init>=0:ole.CoUninitialize()
    assert snapshot(path)==streams


template=snapshot(P/'Capacitors_0402.PcbLib')
lib_n=struct.unpack_from('<I',template['Library/Data'])[0]
lib_head=properties(template['Library/Data'][:4+lib_n])[0]
unit=2.54e-6
checks=[]
for name in ('ZIF_to_2xZIF','ZIF_to_DSUB25'):
    folder=OUT/name; pcb=folder/(name+'.PcbDoc'); before=digest(pcb)
    d=snapshot(pcb); sch=folder/(name+'.SchDoc'); sr=properties(snapshot(sch)['FileHeader'])
    refs={int(r['OwnerIndex']):r['Text'] for r in sr if r.get('RECORD')=='34'}
    roots={r['UniqueID']:(i-1,refs[i-1]) for i,r in enumerate(sr) if r.get('RECORD')=='1'}
    components=properties(d['Components6/Data']); pads=pads_stream(d['Pads6/Data'])
    regions=binary_records(d['Regions6/Data'],11)
    backup=H/'before_library_recovery'/name; backup.mkdir(parents=True,exist_ok=True)
    for f in (sch,folder/(name+'.PrjPcb')):
        if not (backup/f.name).exists():shutil.copy2(f,backup/f.name)
    libraries=[]
    for ci,comp in enumerate(components):
        owner,ref=roots[comp['SOURCEUNIQUEID']]; pattern=comp['PATTERN']
        libfile=f'{ref}_{pattern}.PcbLib'; libraries.append(libfile)
        cx=round(float(comp['X'].removesuffix('mil'))*10000)
        cy=round(float(comp['Y'].removesuffix('mil'))*10000)
        bottom=comp['LAYER']=='BOTTOM'
        primitives=[]; kind_list=[]; pin_numbers=[]
        for pad in (p for p in pads if p['component']==ci):
            record=bytearray(d['Pads6/Data'][pad['start']:pad['end']])
            offset=pad['block_offsets'][4]-pad['start']
            for pos in (3,5,7,9,11):struct.pack_into('<H',record,offset+pos,65535)
            x,y=pad['coords'][:2]; lx=x-cx; ly=y-cy
            if bottom:lx=-lx
            struct.pack_into('<ii',record,offset+13,lx,ly)
            if bottom:
                record[offset]={32:1,38:37}.get(record[offset],record[offset])
                angle=struct.unpack_from('<d',record,offset+52)[0]
                struct.pack_into('<d',record,offset+52,(-angle)%360)
            primitives.append(bytes(record));kind_list.append(2);pin_numbers.append(pad['number'])
            assert (cx+(-lx if bottom else lx),cy+ly)==(x,y)
        for r in regions:
            body=bytearray(r['body'])
            if struct.unpack_from('<H',body,7)[0]!=ci:continue
            for pos in (3,5,7,9,11):struct.pack_into('<H',body,pos,65535)
            if bottom:body[0]={32:1,38:37}.get(body[0],body[0])
            n=struct.unpack_from('<I',body,18)[0]; at=22+n
            count=struct.unpack_from('<I',body,at)[0]; at+=4
            assert len(body)>=at+count*16
            for i in range(count):
                x,y=struct.unpack_from('<dd',body,at+i*16);lx=x-cx;ly=y-cy
                if bottom:lx=-lx
                struct.pack_into('<dd',body,at+i*16,lx,ly)
                assert (cx+(-lx if bottom else lx),cy+ly)==(x,y)
            primitives.append(bytes([11])+block(body));kind_list.append(11)
        assert len(pin_numbers)==(27 if ref=='J1' else 51)
        head=dict(lib_head); head.update(FILENAME=str(folder/libfile),DATE='2026-10-02')
        streams={k:v for k,v in template.items() if k.startswith('FileVersionInfo/') or k=='FileHeader'}
        streams.update({
            'Library/Header':struct.pack('<I',1),
            'Library/Data':props(head)+struct.pack('<I',1)+short_string(pattern),
            'Library/ComponentParamsTOC/Header':struct.pack('<I',1),
            'Library/ComponentParamsTOC/Data':text_block(f'Name={pattern}|Pad Count={len(pin_numbers)}|Height=0|Description=Recovered from saved adapter PCB\r\n'),
            pattern+'/Header':struct.pack('<I',len(primitives)),
            pattern+'/Data':short_string(pattern)+b''.join(primitives),
            pattern+'/Parameters':props({'PATTERN':pattern,'HEIGHT':'0mil','DESCRIPTION':'Saved adapter geometry; component-specific orientation','ITEMGUID':str(uuid.uuid4()).upper(),'REVISIONGUID':str(uuid.uuid4()).upper()}),
            pattern+'/PrimitiveGuids/Header':struct.pack('<I',len(primitives)+1),
            pattern+'/PrimitiveGuids/Data':b''.join(struct.pack('<II',kind,index)+uuid.uuid4().bytes_le for kind,index in [(85,0)]+[(k,i) for i,k in enumerate(kind_list)]),
        })
        tmp=H/('recovered_'+name+'_'+ref+'.PcbLib')
        if tmp.exists():tmp.unlink()
        create_storage(tmp,streams);shutil.copy2(tmp,folder/libfile)
        existing=[r for r in sr if r.get('RECORD')=='45' and r.get('ModelDatafile0')==libfile]
        if not existing:
            impl_list=len(sr)-1;sr.append({'RECORD':'44','OwnerIndex':str(owner)})
            impl=len(sr)-1
            sr.append({'RECORD':'45','OwnerIndex':str(impl_list),'IndexInSheet':'-1','ModelName':pattern,'ModelType':'PCBLIB','DatafileCount':'1','ModelDatafile0':libfile,'ModelDatafileEntity0':pattern,'ModelDatafileKind0':'PCBLIB','IsCurrent':'T','IntegratedModel':'F','DatabaseModel':'F','UniqueID':hashlib.sha256((name+ref+'model').encode()).hexdigest()[:8].upper()})
            sr.extend([{'RECORD':'46','OwnerIndex':str(impl)},{'RECORD':'48','OwnerIndex':str(impl)}])
        checks.append({'design':name,'component':ref,'library':libfile,'footprint':pattern,'pad_count':len(pin_numbers),'primitive_count':len(primitives),'native_load_verified':False,'round_trip_coordinates_match':True,'source_pcb_sha256':before,'library_sha256':digest(folder/libfile)})
    for record in sr:
        if record.get('RECORD')=='4' and record.get('Text','').startswith('Draft: native Altium'):
            record['Text']='Editable flex design; supplier approval is required before fabrication.'
    sr[0]['Weight']=str(len(sr)-1)
    tmp=H/(name+'_linked.SchDoc')
    if tmp.exists():tmp.unlink()
    update_copy(sch,tmp,{'FileHeader':b''.join(props(r) for r in sr)})
    shutil.copy2(tmp,sch)
    prj=folder/(name+'.PrjPcb');text=prj.read_text()
    next_index=3
    for libfile in libraries:
        if 'DocumentPath='+libfile not in text:
            text+=f'[Document{next_index}]\nDocumentPath={libfile}\n'
        next_index+=1
    prj.write_text(text)
    assert digest(pcb)==before
(OUT/'footprint_recovery.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
