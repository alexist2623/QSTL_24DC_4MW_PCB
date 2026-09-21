"""Build a NEW ZIF24/RF4/DC20 SchDoc and QD24 SchLib without source writes.

Input mapping: {"zif_to_qd":{"1":"24",...,"26":"..."}}. Exactly24
selected ZIF pins map one-to-one to QD1..24. Fixed RF mapping is checked.
The connector is an explicitly local one-part53-pin symbol derived from the
actual two-part saved Molex symbol. Unused27 signal pins plus2 mounts get NC.
"""
from pathlib import Path
import sys,json,struct,hashlib,copy,argparse,collections,re
P=Path(__file__).resolve().parent;WORK=P.parents[1];ROOT=WORK.parent
sys.path.insert(0,str(WORK/'qd_center_revision'))
from cfb_copy_update import update_copy
from native_metadata_helpers import olefile,sha

SOURCE=ROOT/'outputs'/'QSTL_QD_centered_project'
SCH=SOURCE/'QSTL_24DC_4MW_PCB.SchDoc';LIB=SOURCE/'QSTL_24DC_4MW_PCB.SchLib'
ZIF=WORK/'zif_revision'/'zif_connector'
USED={str(i) for i in list(range(1,13))+list(range(15,27))}
RF={1:('1','24'),2:('2','21'),3:('15','14'),4:('16','11')}
KEPT=['Q1','SMP1','SMP2','SMP3','SMP4','R1','R2','R3','R4','C1','C2','C3','C4']
MODELS={'QD4':'QSTL_ZIF24.PcbLib','RF_Con':'Reference_Connectors.PcbLib','CC1608-0603':'Passives_0603.PcbLib','FP-5025985193-MFG':'ZIF_5025985193.PcbLib'}

def require(ok,msg):
    if not ok:raise ValueError(msg)
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def uid(token):
    number=int(hashlib.sha256(('ZIF24|'+token).encode()).hexdigest(),16);s=''
    for _ in range(8):s+=chr(65+number%26);number//=26
    return s
def blocks(data):
    out=[];pos=0
    while pos<len(data):
        word=struct.unpack_from('<I',data,pos)[0];n=word&0xffffff
        out.append((word>>24,data[pos+4:pos+4+n]));pos+=4+n
    require(pos==len(data),'Invalid record boundaries');return out
def props(b):return dict(s.split('=',1) for s in b.rstrip(b'\0').decode('cp1252').split('|') if '=' in s)
def encode(r):return ('|'+'|'.join(k+'='+str(v) for k,v in r.items())+'\0').encode('cp1252')
def pack(rs):return b''.join(struct.pack('<I',len(b)|(flag<<24))+b for flag,b in rs)
def records(path):
    with olefile.OleFileIO(path) as o:bb=blocks(o.openstream('FileHeader').read())
    require(all(flag==0 for flag,b in bb),'Expected ASCII native SchDoc records')
    return [props(b) for flag,b in bb]
def shift(r,dx,dy):
    for k in list(r):
        if k in ('Location.X','Corner.X') or re.fullmatch(r'X\d+',k):r[k]=str(int(r[k])+dx)
        elif k in ('Location.Y','Corner.Y') or re.fullmatch(r'Y\d+',k):r[k]=str(int(r[k])+dy)
        elif 'Frac' in k:require(int(r[k])==0,'Fractional schematic geometry not expected')

def topology(mapping):
    m={str(k):str(v) for k,v in mapping['zif_to_qd'].items()}
    require(set(m)==USED and set(m.values())=={str(i) for i in range(1,25)},'Require24selected ZIF pins mapped to24distinct QD pins')
    for channel,(z,q) in RF.items():require(m[z]==q,'RF physical mapping mismatch atZIF'+z)
    nets=collections.defaultdict(list)
    for z,q in m.items():
        name='ZIF'+z.zfill(2);nets[name].append('J1-'+z)
        channel=next((ch for ch,pair in RF.items() if pair==(z,q)),None)
        if channel:nets[name].append(f'R{channel}-2')
        else:nets[name].append('Q1-'+q)
    for ch,(z,q) in RF.items():
        nets['MW'+str(ch)]=['Q1-'+q,f'R{ch}-1',f'C{ch}-2']
        nets['S'+str(ch)]=[f'SMP{ch}-1',f'C{ch}-1']
        nets['GND'] += [f'SMP{ch}-{n}' for n in range(2,6)]
    pin_net={pin:n for n,pp in nets.items() for pin in pp}
    nc=['J1-'+str(i) for i in range(1,54) if str(i) not in USED]
    require(len(nets)==33 and len(pin_net)==84 and len(nc)==29,'Unexpected circuit cardinality')
    return dict(nets),pin_net,nc

def component_groups(rs):
    indexed={i-1:r for i,r in enumerate(rs)};groups={}
    def owner_component(i):
        seen=set()
        while i in indexed:
            require(i not in seen,'Ownership cycle');seen.add(i);r=indexed[i]
            if r.get('RECORD')=='1':return i
            if 'OwnerIndex' not in r:return None
            i=int(r['OwnerIndex'])
        return None
    for i,r in indexed.items():
        if r.get('RECORD')!='1':continue
        group=[(j,copy.deepcopy(x)) for j,x in indexed.items() if owner_component(j)==i]
        designator=next(x['Text'] for j,x in group if x.get('RECORD')=='34')
        groups[designator]=group
    return groups

def append_group(out,group,ref,origin,pin_net):
    root_index=group[0][0];root=group[0][1]
    removed=set()
    if ref=='Q1':
        old_pin=next(i for i,r in group if r.get('RECORD')=='2' and r['Designator']=='1')
        removed.add(old_pin)
        while True:
            more={i for i,r in group if int(r.get('OwnerIndex','-999')) in removed}
            if more<=removed:break
            removed|=more
        group=[(i,r) for i,r in group if i not in removed]
    dx=origin[0]-int(root.get('Location.X','0'));dy=origin[1]-int(root.get('Location.Y','0'))
    imap={i:len(out)-1+j for j,(i,r) in enumerate(group)}
    for old,r in group:
        if 'OwnerIndex' in r:r['OwnerIndex']=str(imap[int(r['OwnerIndex'])])
        if 'IndexInSheet' in r:r['IndexInSheet']='-1'
        shift(r,dx,dy)
        if r.get('RECORD')=='1':
            library='QSTL_ZIF24.SchLib' if ref=='Q1' else ('Reference_Connectors.SchLib' if ref.startswith('SMP') else '*')
            r.update(SourceLibraryName=library,LibraryPath=library)
            if ref=='Q1':r.update(AllPinCount='24',ComponentDescription='QD4 modified24pins; oldpad1removed,old2-25renumbered1-24; bottom mounted')
            if ref.startswith(('R','C')):
                value='10k' if ref.startswith('R') else '1nF'
                r.update(LibReference=('R_0603_10k' if ref.startswith('R') else 'C_0603_1nF'),DesignItemId=('R_0603_10k' if ref.startswith('R') else 'C_0603_1nF'),ComponentDescription='Generic 0603 '+('resistor 10k' if ref.startswith('R') else 'capacitor 1nF')+'; value from saved reference schematic')
        if ref=='Q1' and r.get('RECORD')=='2':
            number=str(int(r['Designator'])-1);r['Designator']=number;r['Name']=pin_net.get('Q1-'+number,'PIN'+number.zfill(2))
        if r.get('RECORD')=='45' and r.get('ModelType')=='PCBLIB':
            r.update(ModelDatafile0=MODELS[r['ModelName']],ModelDatafileEntity0=r['ModelName'],DatafileCount='1',IntegratedModel='F',DatabaseModel='F',Description='Local ZIF24 revision footprint; pin numbers map directly')
        if ref.startswith(('R','C')) and r.get('RECORD')=='41':
            if r.get('Name')=='Value':r['Text']='10k' if ref.startswith('R') else '1nF'
            if r.get('Name')=='Comment':r['Text']=('10k' if ref.startswith('R') else '1nF')+' / 0603'
            if r.get('Name')=='Layout status':r['Text']='RF4/DC20 reference circuit; ZIF24 revision'
        out.append(r)

def zif_group(out):
    native=[]
    for part in (1,2):
        rows=load(ZIF/'sch_raw'/f'J1_part{part}_records.json')
        native += [x['fields'] for x in rows if x['fields'].get('RECORD')=='2' and x['fields'].get('OwnerPartId')==str(part)]
    bynumber={r['Designator']:r for r in native}
    require(set(bynumber)=={str(i) for i in range(1,54)},'Actual ZIF symbol must have53 active pins')
    root_index=len(out)-1
    out.append({'RECORD':'1','LibReference':'ZIF_5025985193_53','ComponentDescription':'Molex5025985193;51signals+2mountpads; single-part local symbol derived from actual native two-part source',
                'PartCount':'2','DisplayModeCount':'1','IndexInSheet':'-1','OwnerPartId':'-1','Location.X':'300','Location.Y':'700','CurrentPartId':'1','LibraryPath':'*','SourceLibraryName':'*','TargetFileName':'*','UniqueID':'GPQWNHID','AreaColor':'11599871','Color':'128','PartIDLocked':'T','DesignItemId':'ZIF_5025985193_53','AllPinCount':'53'})
    out.append({'RECORD':'14','OwnerIndex':str(root_index),'OwnerPartId':'1','Location.X':'250','Location.Y':'540','Corner.X':'350','Corner.Y':'840','Color':'128','AreaColor':'11599871','IsSolid':'T','UniqueID':uid('J1body')})
    for number in range(1,54):
        r=copy.deepcopy(bynumber[str(number)]);left=number%2==1;row=(number-1)//2
        if number==52:left=True;row=27
        if number==53:left=False;row=27
        r.update(OwnerIndex=str(root_index),OwnerPartId='1',Designator=str(number),UniqueID=uid('J1pin'+str(number)),PinLength='30',
                 **{'Location.X':'250' if left else '350','Location.Y':str(825-row*10),'PinConglomerate':str((int(r.get('PinConglomerate','48'))&~3)|(2 if left else 0))})
        r.pop('OwnerPartDisplayMode',None);r.pop('IndexInSheet',None)
        pin_index=len(out)-1;out.append(r)
        out.append({'RECORD':'41','OwnerIndex':str(pin_index),'OwnerPartId':'1','IsHidden':'T','Name':'PinUniqueId','Text':r['UniqueID'],'UniqueID':uid('J1pinuidparam'+str(number))})
    for name,value,x,y,record in [('Designator','J1',270,855,'34'),('Comment','5025985193 / ZIF51',245,520,'41'),('Manufacturer','Molex',300,700,'41'),('Manufacturer Part Number','5025985193',300,700,'41')]:
        r={'RECORD':record,'OwnerIndex':str(root_index),'OwnerPartId':'-1','Location.X':str(x),'Location.Y':str(y),'Color':'8388608','FontID':'4','Text':value,'Name':name,'UniqueID':uid('J1param'+name)}
        if name in ('Manufacturer','Manufacturer Part Number'):r['IsHidden']='T'
        out.append(r)
    impllist=len(out)-1;out.append({'RECORD':'44','OwnerIndex':str(root_index)})
    impl=len(out)-1;out.append({'RECORD':'45','OwnerIndex':str(impllist),'IndexInSheet':'-1','ModelName':'FP-5025985193-MFG','ModelType':'PCBLIB','DatafileCount':'1','ModelDatafile0':MODELS['FP-5025985193-MFG'],'ModelDatafileEntity0':'FP-5025985193-MFG','ModelDatafileKind0':'PCBLIB','IsCurrent':'T','UniqueID':uid('J1model')})
    out.append({'RECORD':'46','OwnerIndex':str(impl)});out.append({'RECORD':'48','OwnerIndex':str(impl)})

def append_connections(out,pin_net,nc):
    index={i-1:r for i,r in enumerate(out)};ref={int(r['OwnerIndex']):r['Text'] for r in out if r.get('RECORD')=='34'};pins=[]
    for r in list(out):
        if r.get('RECORD')!='2':continue
        key=ref[int(r['OwnerIndex'])]+'-'+r['Designator'];direction=int(r.get('PinConglomerate','0'))&3;dx,dy=((1,0),(0,1),(-1,0),(0,-1))[direction]
        x=int(r.get('Location.X','0'))+dx*int(r['PinLength']);y=int(r.get('Location.Y','0'))+dy*int(r['PinLength'])
        pins.append({'key':key,'tip':[x,y],'direction':direction,'name':r['Name'],'uid':r['UniqueID']})
        if key in nc:
            out.append({'RECORD':'22','OwnerPartId':'-1','Location.X':str(x),'Location.Y':str(y),'Color':'255','IsActive':'T','SuppressAll':'T','UniqueID':uid('NC'+key)})
            continue
        require(key in pin_net,'No explicit connectivity for '+key);name=pin_net[key];ex=x+30*dx;ey=y+30*dy
        out.append({'RECORD':'27','OwnerPartId':'-1','LineWidth':'1','Color':'32768','LocationCount':'2','X1':str(x),'Y1':str(y),'X2':str(ex),'Y2':str(ey),'UniqueID':uid('wire'+key)})
        out.append({'RECORD':'25','OwnerPartId':'-1','Location.X':str(ex),'Location.Y':str(ey),'Color':'128','FontID':'5' if direction in (1,3) else '4','Text':name,
                    'Orientation':'1' if direction in (1,3) else '0','Justification':'0' if direction in (0,1) else '2','UniqueID':uid('netlabel'+key)})
    return pins

def geometry_check(out,pins,pin_net,nc):
    labels=[r for r in out if r.get('RECORD')=='25'];wires=[r for r in out if r.get('RECORD')=='27']
    points={tuple(p['tip']) for p in pins}|{(int(r['Location.X']),int(r['Location.Y'])) for r in labels};segments=[]
    for w in wires:
        a=(int(w['X1']),int(w['Y1']));b=(int(w['X2']),int(w['Y2']));segments.append((a,b));points.update((a,b))
    parent={p:p for p in points}
    def find(p):
        while parent[p]!=p:parent[p]=parent[parent[p]];p=parent[p]
        return p
    for a,b in segments:
        for p in points:
            if (p[0]-a[0])*(b[1]-a[1])==(p[1]-a[1])*(b[0]-a[0]) and min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1]):parent[find(p)]=find(a)
    groups=collections.defaultdict(set)
    for pin in pins:groups[find(tuple(pin['tip']))].add(pin_net.get(pin['key'],'NC:'+pin['key']))
    errors=[sorted(n) for n in groups.values() if len(n)>1]
    require(not errors,'Physical stub/pin collision: '+str(errors))
    return {'passed':True,'pin_count':len(pins),'wires':len(wires),'net_labels':len(labels),'NC':len(nc),'unintended_geometric_joins':errors}

def library_update(pin_names):
    with olefile.OleFileIO(LIB) as o:qd=blocks(o.openstream('QD4/Data').read());header=blocks(o.openstream('FileHeader').read())
    out=[];changed=[]
    for flag,b in qd:
        if flag==1:
            require(b[0]==2,'Unknown binary QD library record')
            namelen=b[26];namepos=27;dpos=namepos+namelen;dlen=b[dpos];old=b[dpos+1:dpos+1+dlen].decode('ascii')
            if old=='1':continue
            number=str(int(old)-1);newname=pin_names.get(number,'PIN'+number.zfill(2)).encode('ascii');newnum=number.encode('ascii')
            fresh=b[:26]+bytes([len(newname)])+newname+bytes([len(newnum)])+newnum+b[dpos+1+dlen:]
            out.append((flag,fresh));changed.append({'old':old,'new':number,'name':newname.decode(),'unchanged_geometry_header':b[:26]==fresh[:26]})
        else:
            r=props(b)
            if r.get('RECORD')=='1':r.update(AllPinCount='24',ComponentDescription='QD4 modified24pin variant; oldpin1removed;old2-25renumbered1-24')
            out.append((flag,encode(r)))
    require(len(changed)==24,'Expected24 renamed QD library pins')
    h=props(header[0][1]);h['Weight']=str(int(h['Weight'])-1)
    return {'QD4/Data':pack(out),'FileHeader':pack([(0,encode(h))])},changed

def build(mapping_path,destination,dry_run=False):
    require(not destination.exists(),'Destination SchDoc already exists')
    require(not destination.with_suffix('.SchLib').exists(),'Destination SchLib already exists')
    require(destination.is_relative_to(WORK/'zif_revision') or destination.is_relative_to(ROOT/'outputs'/'QSTL_ZIF24_project'),'Output must be a new ZIF revision file')
    mapping=load(mapping_path);nets,pin_net,nc=topology(mapping)
    require(dry_run or mapping.get('status')!='STRUCTURAL_TEST_ONLY_NOT_FINAL','Structural test mapping cannot create a SchDoc')
    # Explicitly snapshot every authoritative ZIF input as well.
    protected=[SCH,LIB]+[Path(p) for p in load(ZIF/'zif_connector_manifest.json')['source_hashes']]
    hashes={str(p):sha(p) for p in protected}
    rs=records(SCH);groups=component_groups(rs)
    out=[copy.deepcopy(rs[0])]+[copy.deepcopy(r) for r in rs[1:] if r.get('RECORD')=='31' or (r.get('RECORD')=='41' and r.get('OwnerIndex') in (None,'0'))]
    require(len(out)==29,'Unexpected source sheet/parameter records')
    out[1].update(CustomX='1500',CustomY='1000',UseCustomSheet='T')
    for r in out:
        if r.get('Name')=='Title':r['Text']='QSTL ZIF24 - 4 RF + 20 DC'
    zif_group(out)
    append_group(out,copy.deepcopy(groups['Q1']),'Q1',(1000,700),pin_net)
    for ch,y in enumerate([450,340,230,120],1):
        for prefix,x in [('SMP',500),('C',800),('R',1100)]:
            ref=prefix+str(ch);append_group(out,copy.deepcopy(groups[ref]),ref,(x,y),pin_net)
    pins=append_connections(out,pin_net,nc)
    for i,(text,x,y) in enumerate([('QSTL ZIF24: RF4 + DC20; J1/SMP Top, QD4 Bottom.',100,960),('QD4: old pad1 removed; old2..25 become1..24. RF pad positions follow reference clockwise orientation.',100,930),('J1 uses pins1..12 and15..26 only; other27 signal pins and mounts52/53 intentionally NC.',100,900)]):
        out.append({'RECORD':'4','OwnerPartId':'-1','Location.X':str(x),'Location.Y':str(y),'FontID':'4','Color':'128','Text':text,'UniqueID':uid('note'+str(i))})
    require(len(pins)==113,'Expected113 physical symbol pins')
    uids=[r['UniqueID'] for r in out if 'UniqueID' in r];require(len(set(uids))==len(uids),'Duplicate schematic UniqueID')
    for index,r in enumerate(out[1:]):
        if 'OwnerIndex' in r:require(-1<=int(r['OwnerIndex'])<index,'OwnerIndex must reference an earlier record')
    validation=geometry_check(out,pins,pin_net,nc)
    out[0]['Weight']=str(len(out)-1)
    data=pack([(0,encode(r)) for r in out])
    write=update_copy(SCH,destination,{'FileHeader':data}) if not dry_run else None
    qnames={p['key'].split('-')[1]:p['name'] for p in pins if p['key'].startswith('Q1-')}
    updates,librarypins=library_update(qnames);libdest=destination.with_suffix('.SchLib');libwrite=update_copy(LIB,libdest,updates) if not dry_run else None
    modelmap={'J1':'FP-5025985193-MFG','Q1':'QD4'}|{f'SMP{i}':'RF_Con' for i in range(1,5)}|{p+str(i):'CC1608-0603' for p in ['R','C'] for i in range(1,5)}
    expected={'source_schematic':str(SCH),'destination':str(destination),'mapping_file':str(mapping_path),'mapping_sha256':sha(mapping_path),'component_uids':{'J1':'GPQWNHID'}|{ref:groups[ref][0][1]['UniqueID'] for ref in KEPT},
        'component_models':modelmap,'nets':nets,'pin_net_map':pin_net,'nc_pins':nc,'q1_old_to_new':{str(i):str(i-1) for i in range(2,26)},'removed_QD_pin':'1','RF_fixed_map':RF,
        'counts':{'components':14,'pins':113,'connected_pins':84,'NC_pins':29,'named_nets':33},'pins':pins,'schematic_geometry_validation':validation,
        'passive_values':{p+str(i):('10k' if p=='R' else '1nF') for p in ['R','C'] for i in range(1,5)},'library_pin_changes':librarypins,'models_resolve_relative_to_project':MODELS,
        'source_hashes':hashes,'SchDoc_write':write,'SchLib_write':libwrite,'native_reopen_and_compile_required':True}
    require(hashes=={str(p):sha(p) for p in protected},'A protected source changed during generation')
    expected['dry_run']=dry_run
    (P/('structural_preflight.json' if dry_run else 'zif_expected_netlist.json')).write_text(json.dumps(expected,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'destination':str(destination),'library':str(libdest),'counts':expected['counts'],'validation':validation,'sources_unchanged':True,'dry_run':dry_run},indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--mapping',type=Path,required=True);a.add_argument('--destination',type=Path,required=True);a.add_argument('--dry-run',action='store_true');args=a.parse_args()
    try:build(args.mapping.resolve(),args.destination.resolve(),args.dry_run)
    except ValueError as e:print('GUARD STOP: '+str(e));raise SystemExit(2)
