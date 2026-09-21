"""Read saved native SchDoc/SchLib and independently recover label connectivity.

Never writes an Altium document. Optional native compile report comparison keeps
the compiler return boolean and every violation, including an unsuccessful compile.
"""
from pathlib import Path
import argparse, collections, hashlib, json, struct, sys
P=Path(__file__).resolve().parent; ROOT=P.parents[2]
sys.path.insert(0,str(ROOT/'work'/'pcb_python'))
import olefile

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def props(payload):return dict(x.split('=',1) for x in payload.rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
def blocks(data):
    pos=0;out=[]
    while pos<len(data):
        word=struct.unpack_from('<I',data,pos)[0];n=word&0xffffff
        assert pos+4+n<=len(data),'Truncated record'
        out.append((word>>24,data[pos+4:pos+4+n]));pos+=4+n
    assert pos==len(data)
    return out
def getxy(row,prefix='Location.'):
    return tuple(int(row.get(prefix+c,'0'))+int(row.get(prefix+c+'_Frac','0'))/100000 for c in ('X','Y'))
def validate(doc,expected,report=None,pcb=None):
    before=sha(doc)
    with olefile.OleFileIO(doc) as stream:raw=blocks(stream.openstream('FileHeader').read())
    assert all(f==0 for f,b in raw),'Unexpected non-ASCII SchDoc record'
    rs=[props(b) for f,b in raw];index={i-1:r for i,r in enumerate(rs)}
    errors=[]
    def check(ok,reason):
        if not ok:errors.append(reason)
    check(int(rs[0]['Weight'])==len(rs)-1,'FileHeader Weight mismatch')
    for i,r in index.items():
        if 'OwnerIndex' in r:check(-1<=int(r['OwnerIndex'])<i,f'Invalid owner for record {i}')
    designators={int(r['OwnerIndex']):r['Text'] for r in rs if r.get('RECORD')=='34'}
    components={designators[i]:r for i,r in index.items() if r.get('RECORD')=='1'}
    check(set(components)==set(expected['component_uids']),'Component designators differ')
    check(all(components.get(k,{}).get('UniqueID')==v for k,v in expected['component_uids'].items()),'Component UID mismatch')
    pins={}
    for r in rs:
        if r.get('RECORD')!='2':continue
        key=designators[int(r['OwnerIndex'])]+'-'+r['Designator']
        check(key not in pins,'Duplicate physical pin '+key)
        direction=int(r.get('PinConglomerate','0'))&3
        dx,dy=((1,0),(0,1),(-1,0),(0,-1))[direction]
        x,y=getxy(r);length=int(r['PinLength'])
        pins[key]={'tip':(x+dx*length,y+dy*length),'name':r['Name'],'uid':r['UniqueID']}
    expected_pins=set(expected['pin_net_map'])|set(expected['nc_pins'])
    check(set(pins)==expected_pins,'Physical pin inventory mismatch')
    check({p.split('-')[1] for p in pins if p.startswith('Q1-')}=={str(i) for i in range(1,25)},'Q1 must have pins1..24')
    labels=[(getxy(r),r['Text']) for r in rs if r.get('RECORD')=='25']
    segments=[]
    for r in rs:
        if r.get('RECORD')!='27':continue
        xy=[(int(r['X'+str(i)]),int(r['Y'+str(i)])) for i in range(1,int(r['LocationCount'])+1)]
        segments.extend(zip(xy,xy[1:]))
    nc_points=[getxy(r) for r in rs if r.get('RECORD')=='22']
    points={p['tip'] for p in pins.values()}|{p for p,n in labels}|{p for s in segments for p in s}
    parents={p:p for p in points}
    def find(p):
        while parents[p]!=p:parents[p]=parents[parents[p]];p=parents[p]
        return p
    def union(a,b):parents[find(a)]=find(b)
    def onsegment(p,a,b):
        return abs((p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0]))<1e-6 and min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])
    for a,b in segments:
        for point in points:
            if onsegment(point,a,b):union(a,point)
    by_name=collections.defaultdict(list)
    for point,name in labels:by_name[name].append(point)
    for name,locations in by_name.items():
        for location in locations:union(locations[0],location)
    node_names=collections.defaultdict(set);node_pins=collections.defaultdict(set)
    for point,name in labels:node_names[find(point)].add(name)
    for key,pin in pins.items():node_pins[find(pin['tip'])].add(key)
    actual_nets={};actual_nc=[]
    for node,members in node_pins.items():
        names=node_names[node]
        check(len(names)<=1,'Short between labels '+str(sorted(names)))
        if names:actual_nets[next(iter(names))]=sorted(members)
        else:
            check(len(members)==1,'Unlabelled multi-pin connection '+str(sorted(members)))
            actual_nc.extend(members)
    normalized={k:sorted(v) for k,v in expected['nets'].items()}
    check(actual_nets==normalized,'Recovered label connectivity differs from expected')
    check(sorted(actual_nc)==sorted(expected['nc_pins']),'NC pin inventory differs')
    check(collections.Counter(nc_points)==collections.Counter(pins[p]['tip'] for p in expected['nc_pins']),'NC markers do not exactly match unused connector pins')
    check(all(pins[p]['name']==net for p,net in expected['pin_net_map'].items() if p.startswith('Q1-')),'QD pin names do not match assigned functions')
    check(len(labels)==92 and len(segments)==92,'Expected92 label stubs')
    check(len(nc_points)==31,'Expected31 intentional NC markers')
    # Native model ownership may have intermediate implementation-list objects.
    def owner_comp(i):
        while i in index:
            r=index[i]
            if r.get('RECORD')=='1':return designators[i]
            if 'OwnerIndex' not in r:return None
            i=int(r['OwnerIndex'])
        return None
    models={};values={}
    for i,r in index.items():
        if r.get('RECORD')=='45' and r.get('ModelType')=='PCBLIB':models[owner_comp(i)]={'name':r['ModelName'],'file':r.get('ModelDatafile0')}
        if r.get('RECORD')=='41' and r.get('Name')=='Value':values[owner_comp(i)]=r.get('Text')
    check({k:v['name'] for k,v in models.items()}==expected['component_models'],'PCB model names differ')
    check(all(values.get(k)==v for k,v in expected['passive_values'].items()),'Passive values differ from reference10k/1nF')
    check(all(m['file']==expected['models_resolve_relative_to_project'][m['name']] for m in models.values()),'Relative model file paths differ')
    library=doc.with_suffix('.SchLib');librarypins={}
    with olefile.OleFileIO(library) as o:librecords=blocks(o.openstream('QD4/Data').read())
    for flag,b in librecords:
        if flag!=1:continue
        assert b[0]==2
        name=b[27:27+b[26]].decode('ascii');n=27+b[26];number=b[n+1:n+1+b[n]].decode('ascii')
        check(number not in librarypins,'Duplicate QD library pin '+number);librarypins[number]=name
    check(librarypins=={p.split('-')[1]:v for p,v in expected['pin_net_map'].items() if p.startswith('Q1-')},'QD library names/numbers differ from SchDoc')
    source_checks={p:sha(p)==digest for p,digest in expected['source_hashes'].items()}
    check(all(source_checks.values()),'A protected source hash changed')
    native=None
    if report and report.exists():
        try:text=report.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:text=report.read_text(encoding='cp949')
        lines=text.splitlines();net=None;nets=collections.defaultdict(list);summary={}
        for line in lines:
            if line.startswith('NET='):net=line[4:].split('|PINS=')[0]
            elif line.startswith('PIN='):nets[net].append(line[4:])
            elif line.startswith(('COMPILE_RESULT=','VIOLATION_COUNT=','NET_COUNT=')):
                k,v=line.split('=',1);summary[k]=v
        wrong={n:{'expected':ps,'actual':sorted(nets.get(n,[]))} for n,ps in normalized.items() if sorted(nets.get(n,[]))!=ps}
        extra={n:ps for n,ps in nets.items() if n not in normalized}
        extra_bad={n:ps for n,ps in extra.items() if len(ps)!=1 or ps[0] not in expected['nc_pins']}
        check(not wrong,'Native compiled named net mismatch')
        check(not extra_bad,'Native compiler produced unexpected connected nets')
        check(summary.get('NET_COUNT')=='64','Expected33 named nets plus31 singleton NC nets')
        check(sorted(p for ps in extra.values() for p in ps)==sorted(expected['nc_pins']),'Native compiler NC inventory differs')
        check('COMPLETE' in lines,'Native compile export is incomplete')
        native={'report':str(report),'sha256':sha(report),'summary':summary,'named_net_mismatches':wrong,'extra_nets':extra,'unexpected_extra_nets':extra_bad,'violations':[x for x in lines if x.startswith(('VIOLATION=','DETAIL='))],'complete':'COMPLETE' in lines}
    pcb_check=None
    if pcb:
        sys.path.insert(0,str(ROOT/'work'/'qd_center_revision'))
        from native_metadata_helpers import properties,pads_stream
        with olefile.OleFileIO(pcb) as o:
            pcs=properties(o.openstream('Components6/Data').read());pns=properties(o.openstream('Nets6/Data').read());pps=pads_stream(o.openstream('Pads6/Data').read())
        pcb_refs={i:c['SOURCEDESIGNATOR'] for i,c in enumerate(pcs)}
        pcb_pin_nets={pcb_refs[p['component']]+'-'+p['number']:(pns[p['net']]['NAME'] if p['net']!=65535 else None) for p in pps if p['component']!=65535}
        standalone=[p for p in pps if p['component']==65535]
        mount_spec=expected['PCB_only_GND_mounting_pads']
        mount_ok=len(standalone)==mount_spec['count'] and all(p['number']==mount_spec['number'] and p['net']!=65535 and pns[p['net']]['NAME']=='GND' for p in standalone)
        check(mount_ok,'PCB-only mounting pads must be exactly6 standalone GND pads')
        desired=dict(expected['pin_net_map'])|{p:None for p in expected['nc_pins']}
        check(pcb_pin_nets==desired,'Saved PCB pad/net assignments do not match schematic')
        uid_mismatch={pcb_refs[i]:c.get('SOURCEUNIQUEID') for i,c in enumerate(pcs) if c.get('SOURCEUNIQUEID','').lstrip('\\')!=expected['component_uids'].get(pcb_refs[i])}
        check(not uid_mismatch,'Saved PCB SourceUniqueID links do not match schematic')
        model_mismatch={pcb_refs[i]:c.get('PATTERN') for i,c in enumerate(pcs) if c.get('PATTERN')!=expected['component_models'].get(pcb_refs[i])}
        check(not model_mismatch,'Saved PCB footprint models do not match schematic')
        pcb_check={'path':str(pcb),'sha256':sha(pcb),'pad_net_assignments_match':pcb_pin_nets==desired,'component_UID_mismatches':uid_mismatch,'footprint_mismatches':model_mismatch,'standalone_GND_mounts_valid':mount_ok,'standalone_GND_mounts':[{'index':p['index'],'number':p['number'],'net_index':p['net'],'x_dxp':p['coords'][0],'y_dxp':p['coords'][1]} for p in standalone],'counts':{'components':len(pcs),'pads':len(pps),'nets':len(pns)}}
    check(before==sha(doc),'SchDoc changed while validating')
    return {'passed':not errors,'errors':errors,'schematic':str(doc),'sha256':before,'counts':{'components':len(components),'pins':len(pins),'named_nets':len(actual_nets),'connected_pins':sum(map(len,actual_nets.values())),'NC_pins':len(actual_nc),'labels':len(labels),'wire_segments':len(segments),'NC_markers':len(nc_points)},'recovered_nets':actual_nets,'NC_pins':sorted(actual_nc),'models':models,'values':values,'qd_library_pins':librarypins,'source_hash_checks':source_checks,'native_compile':native,'native_reopen_compile_pending':native is None,'PCB_comparison':pcb_check}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--doc',type=Path,required=True);a.add_argument('--expected',type=Path,default=P/'v2_expected_netlist.json');a.add_argument('--report',type=Path);a.add_argument('--pcb',type=Path);a.add_argument('--output',type=Path,default=P/'v2_schematic_validation.json');args=a.parse_args()
    result=validate(args.doc.resolve(),json.loads(args.expected.read_text(encoding='utf-8-sig')),(args.report or args.doc.parent/'native_schematic_compile_v2.txt').resolve(),args.pcb.resolve() if args.pcb else None)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':result['passed'],'counts':result['counts'],'errors':result['errors'],'native_compile_pending':result['native_reopen_compile_pending']},indent=2))
    raise SystemExit(0 if result['passed'] else 1)
