"""Copy-only Windows native Compound File stream updater with full verification.

Uses ole32 StgOpenStorage/IStorage/IStream; no hand-built FAT/miniFAT sectors.
Source is read only. Existing destinations and source=destination are rejected.
Only existing named streams can be replaced; untouched bytes/hierarchy verified.
"""
from __future__ import annotations
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'pcb_python'))
import olefile

STGM_READWRITE=0x2
STGM_SHARE_EXCLUSIVE=0x10
MODE=STGM_READWRITE|STGM_SHARE_EXCLUSIVE
HRESULT=C.c_int32
DWORD=C.c_uint32
PTR=C.c_void_p

def _hr(value,operation):
    if value<0:raise OSError(f'{operation} failed: HRESULT0x{value & 0xffffffff:08X}')

def _method(ptr,index,restype,argtypes):
    table=C.cast(ptr,C.POINTER(C.POINTER(PTR))).contents
    return C.WINFUNCTYPE(restype,PTR,*argtypes)(table[index])

def _release(ptr):
    if ptr and ptr.value:_method(ptr,2,DWORD,[])(ptr)

def _commit_storage(ptr):
    _hr(_method(ptr,9,HRESULT,[DWORD])(ptr,0),'IStorage.Commit')

def _open_storage(parent,name):
    child=PTR()
    _hr(_method(parent,6,HRESULT,[C.c_wchar_p,PTR,DWORD,PTR,DWORD,C.POINTER(PTR)])(parent,name,None,MODE,None,0,C.byref(child)),f'IStorage.OpenStorage({name})')
    return child

def _replace_stream(root,path,payload):
    handles=[];parent=root;stream=PTR()
    try:
        for name in path[:-1]:
            child=_open_storage(parent,name);handles.append(child);parent=child
        _hr(_method(parent,4,HRESULT,[C.c_wchar_p,PTR,DWORD,DWORD,C.POINTER(PTR)])(parent,path[-1],None,MODE,0,C.byref(stream)),f'IStorage.OpenStream({path[-1]})')
        # IStream Seek uses signed LARGE_INTEGER, SetSize unsigned ULARGE_INTEGER.
        _hr(_method(stream,5,HRESULT,[C.c_int64,DWORD,C.POINTER(C.c_uint64)])(stream,0,0,None),'IStream.Seek')
        _hr(_method(stream,6,HRESULT,[C.c_uint64])(stream,len(payload)),'IStream.SetSize')
        write=_method(stream,4,HRESULT,[PTR,DWORD,C.POINTER(DWORD)])
        for offset in range(0,len(payload),1024*1024):
            chunk=payload[offset:offset+1024*1024]
            buffer=C.create_string_buffer(chunk);written=DWORD()
            _hr(write(stream,C.cast(buffer,PTR),len(chunk),C.byref(written)),'IStream.Write')
            if written.value!=len(chunk):raise OSError('IStream.Write returned a short write')
        _hr(_method(stream,8,HRESULT,[DWORD])(stream,0),'IStream.Commit')
    finally:
        _release(stream)
        for handle in reversed(handles):_release(handle)

def _native_replace_existing_streams(copy_path,replacements):
    if os.name!='nt':raise RuntimeError('Native Structured Storage helper requires Windows')
    ole32=C.WinDLL('ole32')
    ole32.CoInitializeEx.argtypes=[PTR,DWORD];ole32.CoInitializeEx.restype=HRESULT
    ole32.CoUninitialize.argtypes=[];ole32.CoUninitialize.restype=None
    ole32.StgOpenStorage.argtypes=[C.c_wchar_p,PTR,DWORD,PTR,DWORD,C.POINTER(PTR)]
    ole32.StgOpenStorage.restype=HRESULT
    initialized=ole32.CoInitializeEx(None,2)
    # An already initialized MTA can also use this synchronous storage API.
    if initialized<0 and (initialized & 0xffffffff)!=0x80010106:_hr(initialized,'CoInitializeEx')
    root=PTR()
    try:
        _hr(ole32.StgOpenStorage(str(copy_path),None,MODE,None,0,C.byref(root)),'StgOpenStorage(copy)')
        for path,payload in replacements.items():_replace_stream(root,path,payload)
        _commit_storage(root)
    finally:
        _release(root)
        if initialized>=0:ole32.CoUninitialize()

def normalize_stream_path(path):
    if isinstance(path,str):parts=tuple(path.replace('\\','/').split('/'))
    else:parts=tuple(path)
    if not parts or any(not isinstance(p,str) or p in ('','.','..') or '\x00' in p or '/' in p or '\\' in p for p in parts):
        raise ValueError(f'Invalid compound stream path: {path!r}')
    return parts

def file_sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()

def stream_snapshot(path):
    """Public result contains stream hashes/sizes and exact storage hierarchy."""
    with olefile.OleFileIO(path,raise_defects=olefile.DEFECT_INCORRECT) as ole:
        streams={}
        for p in ole.listdir(streams=True,storages=False):
            data=ole.openstream(p).read();streams['/'.join(p)]={'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        storages=sorted('/'.join(p) for p in ole.listdir(streams=False,storages=True))
        return {'streams':streams,'storages':storages,'root_clsid':ole.root.clsid}

def update_copy(source,destination,replacements):
    """Create a NEW validated copy with arbitrary existing streams resized.

    replacements maps 'Storage/Stream' or tuple paths to bytes. A b'' value empties
    a stream without deleting its directory entry. Source and existing output
    files are never overwritten. The finalized output appears only after native
    write, close, and complete independent olefile verification all succeed.
    """
    source=Path(source).resolve(strict=True);destination=Path(destination).resolve()
    if source==destination:raise ValueError('Source and destination must differ')
    if destination.exists():raise FileExistsError(f'Destination already exists: {destination}')
    normalized={}
    for path,payload in replacements.items():
        key=normalize_stream_path(path)
        if key in normalized:raise ValueError(f'Duplicate stream update: {key}')
        if not isinstance(payload,(bytes,bytearray,memoryview)):raise TypeError(f'Payload must be bytes: {key}')
        normalized[key]=bytes(payload)
    source_hash=file_sha256(source);before=stream_snapshot(source)
    missing=['/'.join(p) for p in normalized if '/'.join(p) not in before['streams']]
    if missing:raise KeyError(f'Only existing streams are supported; missing: {missing}')
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.parent/(destination.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        shutil.copyfile(source,temporary)
        if file_sha256(temporary)!=source_hash or file_sha256(source)!=source_hash:
            raise RuntimeError('Source changed during snapshot/copy; output not finalized')
        _native_replace_existing_streams(temporary,normalized)
        after=stream_snapshot(temporary)
        if set(before['streams'])!=set(after['streams']):raise AssertionError('Native write changed stream names/hierarchy')
        if before['storages']!=after['storages']:raise AssertionError('Native write changed storage hierarchy')
        if before['root_clsid']!=after['root_clsid']:raise AssertionError('Native write changed root CLSID')
        expected_changes={'/'.join(p):payload for p,payload in normalized.items()}
        for name,info in after['streams'].items():
            if name in expected_changes:
                payload=expected_changes[name];expected={'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
            else:expected=before['streams'][name]
            if info!=expected:raise AssertionError(f'Stream content mismatch: {name}')
        if file_sha256(source)!=source_hash:raise RuntimeError('Source changed during operation; output not finalized')
        # Windows rename fails if destination exists, unlike replace/overwrite.
        os.rename(temporary,destination)
        changed=[{'path':name,'old_size':before['streams'][name]['size'],'new_size':len(payload),'new_sha256':hashlib.sha256(payload).hexdigest()} for name,payload in expected_changes.items()]
        return {'source':str(source),'destination':str(destination),'source_sha256':source_hash,'destination_sha256':file_sha256(destination),'source_unchanged':True,'stream_count':len(before['streams']),'storage_count':len(before['storages']),'all_untouched_stream_bytes_preserved':True,'storage_hierarchy_preserved':True,'root_clsid_preserved':True,'updated_streams':changed,'writer':'Windows ole32 StgOpenStorage/IStorage.OpenStream/IStream.SetSize+Write+Commit','validated_by':'olefile full stream hashes and hierarchy'}
    finally:
        # Exact task-specific temporary file only; no recursive filesystem action.
        if temporary.exists():temporary.unlink()

def _main():
    import argparse
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--source',required=True);a.add_argument('--destination',required=True)
    a.add_argument('--manifest',required=True);a.add_argument('--report')
    args=a.parse_args();manifest_path=Path(args.manifest).resolve()
    report_path=Path(args.report).resolve() if args.report else None
    if report_path and (report_path in [Path(args.source).resolve(),Path(args.destination).resolve()] or report_path.exists()):
        raise FileExistsError('Report must be a separate new file, not source/destination or an existing file')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'));changes={}
    for name,spec in manifest.items():
        if spec=={'empty':True}:changes[name]=b''
        elif isinstance(spec,dict) and set(spec)=={'hex'}:changes[name]=bytes.fromhex(spec['hex'])
        elif isinstance(spec,dict) and set(spec)=={'file'}:changes[name]=(manifest_path.parent/spec['file']).read_bytes()
        else:raise ValueError(f'Invalid payload specification for {name}')
    report=update_copy(args.source,args.destination,changes)
    if report_path:
        with report_path.open('x',encoding='utf-8') as handle:handle.write(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':_main()
