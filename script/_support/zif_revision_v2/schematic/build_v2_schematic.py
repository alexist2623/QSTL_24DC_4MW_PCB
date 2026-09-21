"""Build a NEW v2 SchDoc/SchLib from verified v1; no source or GUI writes.

Mapping contract:
  zif_to_target: selected ZIF pin -> Q1-<DC pin> OR R<channel>-2
  rf_qd_map: channel1..4 -> QD pin24,21,14,11 (fixed physical RF positions)
The four resistor inputs may use any of the24selected ZIF pins.
"""
from pathlib import Path
import argparse,collections,copy,hashlib,json,sys
P=Path(__file__).resolve().parent;ROOT=P.parents[2];WORK=ROOT/'work'
sys.path[:0]=[str(WORK/'zif_revision'/'schematic'),str(WORK/'qd_center_revision')]
import build_zif_schematic as base
from cfb_copy_update import update_copy
from native_metadata_helpers import olefile,sha
SOURCE=ROOT/'outputs'/'QSTL_ZIF24_project'
SCH=SOURCE/'QSTL_ZIF24.SchDoc';LIB=SOURCE/'QSTL_ZIF24.SchLib'
USED={str(i) for i in list(range(1,13))+list(range(15,27))}
FIXED_RF={'1':'24','2':'21','3':'14','4':'11'}
SPARE_UIDS={'SMP7':'VTSMPSEV','SMP8':'VTSMPEIG'}
KEPT=['J1','Q1']+[f'SMP{i}' for i in range(1,5)]+[p+str(i) for p in ('R','C') for i in range(1,5)]
require=base.require;load=base.load

def uid(token):
    n=int(hashlib.sha256(('ZIF24V2|'+token).encode()).hexdigest(),16);text=''
    for _ in range(8):text+=chr(65+n%26);n//=26
    return text

def topology(mapping):
    require('zif_to_target' in mapping,'Missing complete zif_to_target mapping')
    zt={str(k):str(v) for k,v in mapping['zif_to_target'].items()}
    rf={str(k):str(v) for k,v in mapping.get('rf_qd_map',{}).items()}
    require(rf==FIXED_RF,'rf_qd_map must retain fixed RF positions24,21,14,11')
    wanted={f'Q1-{q}' for q in range(1,25) if str(q) not in rf.values()}|{f'R{c}-2' for c in range(1,5)}
    require(set(zt)==USED,'Use exactly ZIF1..12,15..26')
    require(len(set(zt.values()))==24 and set(zt.values())==wanted,'Targets must be20distinct non-RF QD pins plus R1..4 pin2')
    nets={f'ZIF{int(z):02d}':[f'J1-{z}',target] for z,target in sorted(zt.items(),key=lambda kv:int(kv[0]))}
    for ch,q in rf.items():
        nets['MW'+ch]=['Q1-'+q,'R'+ch+'-1','C'+ch+'-2']
        nets['S'+ch]=['SMP'+ch+'-1','C'+ch+'-1']
    nets['GND']=[f'SMP{c}-{p}' for c in (1,2,3,4,7,8) for p in range(2,6)]
    pin_net={p:n for n,pp in nets.items() for p in pp}
    nc=[f'J1-{p}' for p in range(1,54) if str(p) not in USED]+['SMP7-1','SMP8-1']
    require(len(nets)==33 and len(pin_net)==92 and len(nc)==31,'V2 circuit cardinality mismatch')
    bias={ch:next(z for z,target in zt.items() if target=='R'+ch+'-2') for ch in rf}
    return nets,pin_net,nc,bias

def append_group(out,group,ref,pin_net,libname,qd_pcblib,origin=None,clone=False):
    group=copy.deepcopy(group);oldref=next(r['Text'] for i,r in group if r.get('RECORD')=='34')
    root=group[0][1];oldx=int(root.get('Location.X','0'));oldy=int(root.get('Location.Y','0'))
    dx,dy=(origin[0]-oldx,origin[1]-oldy) if origin else (0,0)
    imap={i:len(out)-1+j for j,(i,r) in enumerate(group)}
    uids={r['UniqueID']:uid(ref+'|'+r['UniqueID']) for i,r in group if 'UniqueID' in r} if clone else {}
    for old,r in group:
        if 'OwnerIndex' in r:r['OwnerIndex']=str(imap[int(r['OwnerIndex'])])
        if 'IndexInSheet' in r:r['IndexInSheet']='-1'
        if clone and 'UniqueID' in r:r['UniqueID']=uids[r['UniqueID']]
        if clone and r.get('Name')=='PinUniqueId' and r.get('Text') in uids:r['Text']=uids[r['Text']]
        base.shift(r,dx,dy)
        if r.get('RECORD')=='1':
            if ref=='Q1':r.update(SourceLibraryName=libname,LibraryPath=libname,ComponentDescription='QD4 modified24pins; Bottom; RF4 fixed physical pins and freely assigned DC20')
            if clone:r.update(UniqueID=SPARE_UIDS[ref],ComponentDescription='Restored reference SMP; signal pin1 intentionally NC; shield pins2-5 GND')
        if r.get('RECORD')=='34':r['Text']=ref
        if ref=='Q1' and r.get('RECORD')=='2':
            require(r['Designator'] in {str(i) for i in range(1,25)},'V1 QD must already have pins1..24')
            r['Name']=pin_net['Q1-'+r['Designator']]
        if r.get('RECORD')=='45' and r.get('ModelType')=='PCBLIB' and r.get('ModelName')=='QD4':r['ModelDatafile0']=qd_pcblib
        if r.get('RECORD')=='41' and r.get('Name')=='Layout status':r['Text']='RF4/DC20 v2; R/C and QD Bottom; resistor bias tee via in pad'
        out.append(r)

def library_update(pin_net):
    with olefile.OleFileIO(LIB) as o:rows=base.blocks(o.openstream('QD4/Data').read())
    out=[];audit=[]
    for flag,b in rows:
        if flag==1:
            require(b[0]==2,'Unexpected binary SchLib record')
            namelen=b[26];dpos=27+namelen;dlen=b[dpos];number=b[dpos+1:dpos+1+dlen].decode('ascii')
            require('Q1-'+number in pin_net,'Unexpected QD pin in source library')
            name=pin_net['Q1-'+number].encode('ascii')
            fresh=b[:26]+bytes([len(name)])+name+b[dpos:]
            audit.append({'pin':number,'old_name':b[27:27+namelen].decode('ascii'),'new_name':name.decode(),'number_and_geometry_preserved':True})
            out.append((flag,fresh))
        else:
            r=base.props(b)
            if r.get('RECORD')=='1':r.update(AllPinCount='24',ComponentDescription='QD4 modified24pin variant; v2 RF4/DC20 assignments; original numbering preserved')
            out.append((flag,base.encode(r)))
    require(len(audit)==24 and {r['pin'] for r in audit}=={str(i) for i in range(1,25)},'Expected24librarypins')
    return {'QD4/Data':base.pack(out)},audit

def compile_script(destination):
    text=(WORK/'zif_revision'/'schematic'/'ValidateZIF24CircuitV1.pas').read_text(encoding='ascii')
    text=text.replace('ValidateZIF24CircuitV1','ValidateZIF24V2CircuitV1')
    text=text.replace('GuardZIF24','GuardZIF24V2').replace('Count=14','Count=16')
    text=text.replace("'QSTL_ZIF24.SCHDOC'",repr(destination.name.upper()))
    text=text.replace("'\\OUTPUTS\\QSTL_ZIF24_PROJECT\\'",repr('\\OUTPUTS\\'+destination.parent.name.upper()+'\\').replace('\\\\','\\'))
    text=text.replace("ExtractFilePath(DraftSchPath)+'QSTL_ZIF24.PrjPcb'","ChangeFileExt(DraftSchPath,'.PrjPcb')")
    text=text.replace("ExtractFilePath(DraftSchPath)+'..\\..\\work\\zif_revision\\schematic\\zif_sch_compile_report.txt'","ExtractFilePath(DraftSchPath)+'native_schematic_compile_v2.txt'")
    anchor="    If Not GuardZIF24V2Part('C4','ZCAPCHAD') Then Exit;"
    text=text.replace(anchor,anchor+"\n    If Not GuardZIF24V2Part('SMP7','VTSMPSEV') Then Exit;\n    If Not GuardZIF24V2Part('SMP8','VTSMPEIG') Then Exit;")
    require('Count=16' in text and "SMP7','VTSMPSEV" in text,'Compile script substitution failed')
    require(text.isascii(),'Compile script paths must be ASCII-local names')
    name='ValidateZIF24V2CircuitV1';(P/(name+'.pas')).write_text(text,encoding='ascii')
    (P/(name+'.PrjScr')).write_text('[Design]\nVersion=1.0\n\n[Document1]\nDocumentPath='+name+'.pas\n',encoding='ascii')

def build(mapping_file,destination,dry_run=False,qd_pcblib=None):
    require(destination.suffix.lower()=='.schdoc','Destination must be SchDoc')
    require(destination.resolve()!=SCH.resolve(),'V1 source cannot be a destination')
    require(destination.is_relative_to(WORK/'zif_revision_v2') or destination.is_relative_to(ROOT/'outputs'),'Destination must be a new work/output file')
    require(not destination.exists() and not destination.with_suffix('.SchLib').exists(),'Destination SchDoc/SchLib already exists')
    mapping=load(mapping_file);nets,pin_net,nc,bias=topology(mapping)
    require(dry_run or mapping.get('status')!='STRUCTURAL_TEST_ONLY_NOT_FINAL','Structural test may not produce Altium files')
    old_expected=load(WORK/'zif_revision'/'schematic'/'zif_expected_netlist.json')
    protected=list(dict.fromkeys([SCH,LIB,SOURCE/'QSTL_ZIF24.PcbDoc']+[Path(s) for s in old_expected['source_hashes']]))
    hashes={str(p):sha(p) for p in protected}
    rs=base.records(SCH);groups=base.component_groups(rs)
    require(set(groups)==set(KEPT),'Unexpected v1 schematic component set')
    for ref,expected_uid in old_expected['component_uids'].items():require(groups[ref][0][1]['UniqueID']==expected_uid,'Unexpected v1 UID '+ref)
    out=[copy.deepcopy(rs[0])]+[copy.deepcopy(r) for r in rs[1:] if r.get('RECORD')=='31' or (r.get('RECORD')=='41' and r.get('OwnerIndex') in (None,'0'))]
    require(len(out)==29,'Unexpected sheet parameters')
    for r in out:
        if r.get('Name')=='Title':r['Text']='QSTL ZIF24 v2 - RF4 + DC20; 6 SMP; Bottom R/C/QD'
    qd_pcblib=qd_pcblib or destination.with_suffix('.PcbLib').name
    require(Path(qd_pcblib).name==qd_pcblib,'QD PcbLib path must be project-relative filename')
    for ref in KEPT:append_group(out,groups[ref],ref,pin_net,destination.with_suffix('.SchLib').name,qd_pcblib)
    append_group(out,groups['SMP4'],'SMP7',pin_net,destination.with_suffix('.SchLib').name,qd_pcblib,(270,340),True)
    append_group(out,groups['SMP3'],'SMP8',pin_net,destination.with_suffix('.SchLib').name,qd_pcblib,(270,120),True)
    pins=base.append_connections(out,pin_net,nc)
    notes=[('QSTL ZIF24 v2: RF4 + DC20; ZIF/SMP Top; QD4 and R1-4/C1-4 Bottom.',100,960),
           ('QD pins1..24 retained. RF positions fixed; four ZIF bias inputs and DC20 assigned by final routing map.',100,930),
           ('SMP7/8 restored: pin1 NC, pins2-5 GND. Six plated GND mounting holes are PCB-only mechanical features.',100,900),
           ('J1 uses1..12,15..26; remaining27 signal pins and mounts52/53 NC. Bias resistor tees use via in pad.',100,870),
           ('Spare reference SMP connectors (signal NC)',180,430)]
    for i,(txt,x,y) in enumerate(notes):out.append({'RECORD':'4','OwnerPartId':'-1','Location.X':str(x),'Location.Y':str(y),'FontID':'4','Color':'128','Text':txt,'UniqueID':uid('note'+str(i))})
    require(len(pins)==123,'Expected123symbolpins')
    alluids=[r['UniqueID'] for r in out if 'UniqueID' in r];require(len(set(alluids))==len(alluids),'Duplicate UniqueID')
    for i,r in enumerate(out[1:]):
        if 'OwnerIndex' in r:require(-1<=int(r['OwnerIndex'])<i,'Invalid OwnerIndex')
    geometry=base.geometry_check(out,pins,pin_net,nc)
    out[0]['Weight']=str(len(out)-1);native=base.pack([(0,base.encode(r)) for r in out])
    libupdates,libaudit=library_update(pin_net)
    writes={'SchDoc':update_copy(SCH,destination,{'FileHeader':native}),'SchLib':update_copy(LIB,destination.with_suffix('.SchLib'),libupdates)} if not dry_run else {}
    models=old_expected['component_models']|{'SMP7':'RF_Con','SMP8':'RF_Con'}
    modelpaths=old_expected['models_resolve_relative_to_project']|{'QD4':qd_pcblib}
    result={'source_schematic':str(SCH),'destination':str(destination),'mapping_file':str(mapping_file),'mapping_sha256':sha(mapping_file),
      'component_uids':old_expected['component_uids']|SPARE_UIDS,'component_models':models,'models_resolve_relative_to_project':modelpaths,
      'nets':nets,'pin_net_map':pin_net,'nc_pins':nc,'rf_qd_map':FIXED_RF,'rf_bias_zif_pins':bias,'zif_to_target':mapping['zif_to_target'],
      'counts':{'components':16,'pins':123,'connected_pins':92,'NC_pins':31,'named_nets':33},'pins':pins,
      'PCB_only_GND_mounting_pads':{'count':6,'component_index':65535,'net':'GND','number':'1','not_schematic_components':True},
      'PCB_expected_counts':{'components':16,'pads':129,'named_nets':33},'native_compiled_expected_net_count':64,
      'passive_values':old_expected['passive_values'],'source_hashes':hashes,'library_pin_changes':libaudit,'schematic_geometry_validation':geometry,
      'writes':writes,'dry_run':dry_run,'native_reopen_and_compile_required':True}
    require(hashes=={str(p):sha(p) for p in protected},'Protected source changed')
    (P/('structural_preflight_v2.json' if dry_run else 'v2_expected_netlist.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if not dry_run:compile_script(destination)
    print(json.dumps({'destination':str(destination),'counts':result['counts'],'bias_ZIF_pins':bias,'geometry':geometry,'dry_run':dry_run,'sources_unchanged':True},indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--mapping',required=True,type=Path);a.add_argument('--destination',required=True,type=Path);a.add_argument('--qd-pcblib');a.add_argument('--dry-run',action='store_true');args=a.parse_args()
    try:build(args.mapping.resolve(),args.destination.resolve(),args.dry_run,args.qd_pcblib)
    except ValueError as e:print('GUARD STOP: '+str(e));raise SystemExit(2)
