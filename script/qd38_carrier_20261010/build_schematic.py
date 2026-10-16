"""Create a native QD38 schematic and local libraries in the isolated copy."""
from pathlib import Path
import sys,json,copy,struct,uuid,shutil,ctypes as C,ast,configparser,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[1];DEST=ROOT/'QSTL_QD4_2SET_38PAD';NAME='QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/_support/zif_revision/schematic'))
sys.path.insert(0,str(ROOT/'script/_support/qd_center_revision'))
import build_zif_schematic as s
import native_metadata_helpers as nh
import cfb_copy_update as cfb
from cfb_copy_update import _method,_hr,_release,PTR,DWORD,HRESULT
olefile=nh.olefile

def snapshot(p):
 with olefile.OleFileIO(p) as o:return {'/'.join(k):o.openstream(k).read() for k in o.listdir()}

# Reuse the repository's verified Windows structured-storage writer only.
tree=ast.parse((ROOT/'script/branched_fpc_20261002/recover_footprint_libraries.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='create_storage'],type_ignores=[]),'storage_writer','exec'),globals())

def block(b):return struct.pack('<I',len(b))+b
def short(name):return block(bytes([len(name)])+name.encode('ascii'))
def prop(r):return block(s.encode(r))
def fresh(path,streams):
 tmp=H/('new_'+path.name)
 if tmp.exists():tmp.unlink()
 create_storage(tmp,streams)
 backup=H/'before_native_changes';backup.mkdir(exist_ok=True)
 if path.exists() and not (backup/path.name).exists():shutil.copy2(path,backup/path.name)
 shutil.copy2(tmp,path)

def component(out,group,ref,origin):
 group=copy.deepcopy(group);root=group[0][1];dx=origin[0]-int(root['Location.X']);dy=origin[1]-int(root['Location.Y'])
 imap={old:len(out)-1+i for i,(old,r) in enumerate(group)};umap={r['UniqueID']:s.uid('QD38|'+ref+'|'+str(old)) for old,r in group if 'UniqueID' in r}
 for old,r in group:
  if 'OwnerIndex' in r:r['OwnerIndex']=str(imap[int(r['OwnerIndex'])])
  s.shift(r,dx,dy)
  if 'UniqueID' in r:r['UniqueID']=umap[r['UniqueID']]
  if r.get('Name')=='PinUniqueId':r['Text']=umap.get(r['Text'],r['Text'])
  if r.get('RECORD')=='34':r['Text']=ref
  if r.get('RECORD')=='45':r['Description']='Copied QD38 carrier; physical pin numbers preserved'
  if ref.startswith('R') and r.get('RECORD')=='1':r.update(SourceLibraryName='Reference_Resistors.SchLib',LibraryPath='Reference_Resistors.SchLib')
  for key in list(r):
   # Native text templates occasionally contain unsupported replacement glyphs.
   r[key]=r[key].encode('cp1252',errors='replace').decode('cp1252')
  out.append(r)

def qd(out,plan):
 root=len(out)-1;x,y=1450,1220
 out.append(dict(RECORD='1',LibReference='QD4_2SET_38',PartCount='2',DisplayModeCount='1',IndexInSheet='-1',OwnerPartId='-1',CurrentPartId='1',LibraryPath=NAME+'.SchLib',SourceLibraryName=NAME+'.SchLib',TargetFileName='*',UniqueID=s.uid('QD38-Q1'),AreaColor='11599871',Color='128',PartIDLocked='T',DesignItemId='QD4_2SET_38',AllPinCount='38',ComponentDescription='QD4_2SET: 38 independent DC terminals; 16 RF terminals through bias tees',**{'Location.X':str(x),'Location.Y':str(y)}))
 out.append(dict(RECORD='14',OwnerIndex=str(root),OwnerPartId='1',IsSolid='T',Color='128',AreaColor='11599871',UniqueID=s.uid('QD38body'),**{'Location.X':str(x-200),'Location.Y':str(y-200),'Corner.X':str(x+200),'Corner.Y':str(y+200)}))
 for n,p in enumerate(plan['pads'],1):
  left=n<=19;row=n-1 if left else n-20;uid=s.uid('QD38pin'+str(n));at=len(out)-1
  out.append(dict(RECORD='2',OwnerIndex=str(root),OwnerPartId='1',FormalType='1',Electrical='4',PinConglomerate='58' if left else '56',PinLength='30',Name=p['net'],Designator=str(n),UniqueID=uid,**{'Location.X':str(x-200 if left else x+200),'Location.Y':str(y+180-row*20)}))
  out.append(dict(RECORD='41',OwnerIndex=str(at),OwnerPartId='1',IsHidden='T',Name='PinUniqueId',Text=uid,UniqueID=s.uid('QD38param'+str(n))))
 for rec,name,text,xx,yy in [('34','Designator','Q1',x-190,y+220),('41','Comment','QD4_2SET / 38 DC + 16 RF',x-100,y-220)]:
  out.append(dict(RECORD=rec,OwnerIndex=str(root),OwnerPartId='-1',Color='8388608',FontID='4',Name=name,Text=text,UniqueID=s.uid('QD38'+name),**{'Location.X':str(xx),'Location.Y':str(yy)}))
 impl=len(out)-1;out.append(dict(RECORD='44',OwnerIndex=str(root)));model=len(out)-1
 out.append(dict(RECORD='45',OwnerIndex=str(impl),IndexInSheet='-1',ModelName='QD4_2SET_38',ModelType='PCBLIB',DatafileCount='1',ModelDatafile0='QD4_2SET_38.PcbLib',ModelDatafileEntity0='QD4_2SET_38',ModelDatafileKind0='PCBLIB',IsCurrent='T',IntegratedModel='F',DatabaseModel='F',UniqueID=s.uid('QD38model')))
 out.extend([dict(RECORD='46',OwnerIndex=str(model)),dict(RECORD='48',OwnerIndex=str(model))])

def libraries(plan):
 source=ROOT/'QSTL_24DC_4MW_PCB'
 lib=snapshot(source/'QSTL_24DC_4MW_PCB.SchLib');bb=s.blocks(lib['QD4/Data']);template=next(b for f,b in bb if f==1)
 root=next(s.props(b) for f,b in bb if f==0 and s.props(b).get('RECORD')=='1')
 root.update(LibReference='QD4_2SET_38',AllPinCount='38',UniqueID=s.uid('QD38lib'),ComponentDescription='38-terminal QD4_2SET wire-bond component')
 records=[(0,s.encode(root)),(0,s.encode(dict(RECORD='14',OwnerPartId='1',IsSolid='T',Color='128',AreaColor='11599871',UniqueID=s.uid('QD38libbody'),**{'Location.X':'-200','Location.Y':'-200','Corner.X':'200','Corner.Y':'200'})))]
 for n,p in enumerate(plan['pads'],1):
  head=bytearray(template[:26]);head[15]=58 if n<=19 else 56;struct.pack_into('<hhh',head,16,30,-200 if n<=19 else 200,180-20*((n-1)%19))
  name=p['net'].encode();number=str(n).encode();records.append((1,bytes(head)+bytes([len(name)])+name+bytes([len(number)])+number+b'\0\x03|&|\0'))
 for f,b in bb:
  if f:continue
  r=s.props(b)
  if r.get('RECORD') in ('1','14'):continue
  if r.get('Name')=='Comment':r['Text']='QD4_2SET / 38 terminals'
  if r.get('RECORD')=='45':r.update(ModelName='QD4_2SET_38',ModelDatafile0='QD4_2SET_38.PcbLib',ModelDatafileEntity0='QD4_2SET_38')
  records.append((0,s.encode(r)))
 header=s.props(s.blocks(lib['FileHeader'])[0][1]);header.update(CompCount='1',LibRef0='QD4_2SET_38',PartCount0='2',Weight=str(len(records)),UniqueID=s.uid('QD38SchLib'))
 for key in ('LibRef1','PartCount1'):header.pop(key,None)
 fresh(DEST/(NAME+'.SchLib'),{'FileHeader':prop(header),'QD4_2SET_38/Data':s.pack(records),'Storage':lib['Storage']})

 template_lib=snapshot(source/'QSTL_24DC_4MW_PCB.PcbLib');data=template_lib['QD4/Data'];offset=4+struct.unpack_from('<I',data)[0];template_pad=nh.pad_record(data,offset)
 primitives=[]
 for p in plan['pads']:
  blocks=[bytes(b) for b in template_pad['blocks']];n=str(p['number']).encode();blocks[0]=bytes([len(n)])+n;b=bytearray(blocks[4]);b[0]=1
  for at in (3,5,7,9,11):struct.pack_into('<H',b,at,65535)
  x,y=p['center'];vals=[-x,y,.8,.25,.8,.25,.8,.25,0];struct.pack_into('<9i',b,13,*[round(v/nh.UNIT) for v in vals]);b[49]=b[50]=b[51]=2;struct.pack_into('<d',b,52,(-p['rotation'])%360)
  blocks[4]=bytes(b);primitives.append(b'\x02'+b''.join(block(bb) for bb in blocks))
 lname='QD4_2SET_38';ld=template_lib['Library/Data'];length=struct.unpack_from('<I',ld)[0];head=nh.properties(ld[:4+length])[0];head.update(FILENAME=str(DEST/(lname+'.PcbLib')),DATE='2026-10-10')
 streams={k:v for k,v in template_lib.items() if k=='FileHeader' or k.startswith('FileVersionInfo/')}
 streams.update({'Library/Header':struct.pack('<I',1),'Library/Data':prop(head)+struct.pack('<I',1)+short(lname),'Library/ComponentParamsTOC/Header':struct.pack('<I',1),'Library/ComponentParamsTOC/Data':block(f'Name={lname}|Pad Count=38|Height=0|Description=38 rotated bond pads\r\n\0'.encode()),lname+'/Header':struct.pack('<I',38),lname+'/Data':short(lname)+b''.join(primitives),lname+'/Parameters':prop(dict(PATTERN=lname,HEIGHT='0mil',DESCRIPTION='QD4_2SET; 0.80 x 0.25 mm wire-parallel lands',ITEMGUID=str(uuid.uuid4()).upper(),REVISIONGUID=str(uuid.uuid4()).upper())),lname+'/PrimitiveGuids/Header':struct.pack('<I',39),lname+'/PrimitiveGuids/Data':b''.join(struct.pack('<II',kind,i)+uuid.uuid4().bytes_le for kind,i in [(85,0)]+[(2,i) for i in range(38)])})
 fresh(DEST/(lname+'.PcbLib'),streams)

def main():
 plan=json.loads((DEST/'circuit_plan.json').read_text());rs=json.loads((H/'baseline_schematic_records.json').read_text());groups=s.component_groups(rs)
 out=[copy.deepcopy(rs[0])]+[copy.deepcopy(r) for r in rs[1:] if r.get('RECORD')=='31' or r.get('RECORD')=='41' and r.get('OwnerIndex') in (None,'0')]
 for r in out:
  if r.get('RECORD')=='31':r.update(CustomX='2400',CustomY='1600',UseCustomSheet='T')
  if r.get('Name')=='Title':r['Text']='QD4_2SET carrier: 38 DC / 16 RF bias tees'
 component(out,groups['J1'],'J1',(500,1250));qd(out,plan)
 for k,n in enumerate([d['q'] for d in plan['smp']]):
  x=200+(k%4)*580;y=840-(k//4)*180
  for src,ref,dx in [('SMP1',f'SMP{n:02}',0),('C1',f'C{n:02}',160),('R1',f'R{n:02}',360)]:component(out,groups[src],ref,(x+dx,y))
  out.append(dict(RECORD='4',OwnerPartId='-1',FontID='4',Color='128',Text=f"RF + DC: Q1-{n} / {plan['pads'][n-1]['net']}",UniqueID=s.uid('caption'+str(n)),**{'Location.X':str(x-40),'Location.Y':str(y+80)}))
 pin_net={pin:net for net,pp in plan['nets'].items() for pin in pp};nc=[f'J1-{n}' for n in range(1,54) if f'J1-{n}' not in pin_net]
 pins=s.append_connections(out,pin_net,nc);validation=s.geometry_check(out,pins,pin_net,nc)
 assert len(pins)==235,len(pins)
 ids=[r['UniqueID'] for r in out if 'UniqueID' in r];assert len(ids)==len(set(ids))
 for i,r in enumerate(out[1:]):
  if 'OwnerIndex' in r:assert -1<=int(r['OwnerIndex'])<i,(i,r)
 out[0]['Weight']=str(len(out)-1);streams=snapshot(ROOT/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.SchDoc');streams['FileHeader']=s.pack([(0,s.encode(r)) for r in out])
 fresh(DEST/(NAME+'.SchDoc'),streams);libraries(plan)
 proj=DEST/(NAME+'.PrjPcb');cfg=configparser.ConfigParser(interpolation=None,strict=False);cfg.optionxform=str;cfg.read(proj)
 for sec in list(cfg.sections()):
  if sec.startswith('GeneratedDocument'):cfg.remove_section(sec)
 if not any(cfg.get(sec,'DocumentPath',fallback='')=='QD4_2SET_38.PcbLib' for sec in cfg.sections()):
  number=max(int(sec[8:]) for sec in cfg.sections() if sec.startswith('Document') and sec[8:].isdigit())+1
  cfg['Document'+str(number)]={'DocumentPath':'QD4_2SET_38.PcbLib'}
 with proj.open('w') as f:cfg.write(f,space_around_delimiters=False)
 report=dict(status='Native files generated; Altium reopening/compile pending',nets=plan['nets'],pins=pins,pin_net=pin_net,nc=nc,schematic_geometry_validation=validation,components={r['Text']:out[int(r['OwnerIndex'])+1]['UniqueID'] for r in out if r.get('RECORD')=='34'},schematic_sha256=hashlib.sha256((DEST/(NAME+'.SchDoc')).read_bytes()).hexdigest())
 (DEST/'schematic_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(components=50,pins=len(pins),named_nets=len(plan['nets']),validation=validation),indent=2))

if __name__=='__main__':main()
