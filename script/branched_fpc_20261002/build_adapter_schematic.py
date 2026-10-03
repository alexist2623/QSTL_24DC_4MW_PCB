"""Build a native embedded-symbol schematic matching the adapter's saved pin map."""
from pathlib import Path
import sys,json,struct,hashlib,csv
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import olefile,properties,pads_stream
from cfb_copy_update import update_copy
NAME=sys.argv[1] if len(sys.argv)>1 else 'ZIF_to_DSUB25'
assert NAME in ('ZIF_to_DSUB25','ZIF_to_2xZIF')
branch=NAME=='ZIF_to_2xZIF'
OUT=R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002'/NAME
plan=json.loads((OUT/'design_plan.json').read_text());source=R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.SchDoc'
with olefile.OleFileIO(source) as o:raw=o.openstream('FileHeader').read()
records=properties(raw)
def uid(s):
 n=int(hashlib.sha256(s.encode()).hexdigest(),16);return ''.join(chr(65+(n//26**i)%26) for i in range(8))
def enc(p):
 b=('|'+'|'.join(k+'='+str(v) for k,v in p.items())+'\0').encode('cp1252');return struct.pack('<I',len(b))+b
out=[dict(records[0])]
sheet=next(dict(r) for r in records if r.get('RECORD')=='31');sheet.update(CustomX='1450',CustomY='850',UseCustomSheet='T');out.append(sheet)
mapping=plan.get('source_mapping',{});inverse={v:int(k) for k,v in mapping.items()};pinmap={};allpins=[]
symbols=[('C',230,51,'FPC51_P030_STAGGERED'),('A',680,51,'FPC51_P030_STAGGERED'),('B',1130,51,'FPC51_P030_STAGGERED')] if branch else [('A',300,51,'FPC51_P030_STAGGERED'),('J1',1030,27,'NORCOMP_381_025_112L565')]
for ref,x,n,pattern in symbols:
 owner=len(out)-1;ytop=710;ybot=ytop-n*10-10
 out.append(dict(RECORD='1',LibReference=pattern,ComponentDescription='Integral FPC contact array' if branch or ref=='A' else 'NorComp 381-025-112L565, 25 signal pins and two boardlocks',PartCount='2',DisplayModeCount='1',IndexInSheet='-1',OwnerPartId='-1',CurrentPartId='1',LibraryPath='*',SourceLibraryName='*',TargetFileName='*',UniqueID=uid('adapter.sch.'+ref),AreaColor='11599871',Color='128',PartIDLocked='T',DesignItemId=pattern,AllPinCount=str(n),**{'Location.X':str(x),'Location.Y':str(ytop)}))
 out.append(dict(RECORD='14',OwnerIndex=str(owner),OwnerPartId='1',Color='128',AreaColor='11599871',IsSolid='T',UniqueID=uid(ref+'body'),**{'Location.X':str(x-40),'Location.Y':str(ybot),'Corner.X':str(x+40),'Corner.Y':str(ytop)}))
 pins=[str(i) for i in range(1,52)] if branch or ref=='A' else [str(i) for i in range(1,26)]+['BL1','BL2']
 for i,pin in enumerate(pins):
  y=ytop-10-10*i;direction=0 if ref=='A' else 2;px=x+(40 if ref=='A' else -40);dx=1 if ref=='A' else -1
  net=f'FPC_{int(pin):02d}' if branch else ((f'DSUB_{inverse[int(pin)]:02d}' if int(pin) in inverse else None) if ref=='A' else (f'DSUB_{int(pin):02d}' if pin.isdigit() else None))
  out.append(dict(RECORD='2',OwnerIndex=str(owner),OwnerPartId='1',FormalType='1',Electrical='4',PinConglomerate=str(48+direction),PinLength='20',Name=pin,Designator=pin,UniqueID=uid(ref+'.'+pin),**{'Location.X':str(px),'Location.Y':str(y)}))
  tx=px+dx*20;allpins.append((ref,pin,net));pinmap[ref+'.'+pin]=net
  if net:
   ex=tx+dx*30
   out.append(dict(RECORD='27',OwnerPartId='-1',LineWidth='1',Color='32768',LocationCount='2',X1=str(tx),Y1=str(y),X2=str(ex),Y2=str(y),UniqueID=uid(ref+'.'+pin+'.wire')))
   out.append(dict(RECORD='25',OwnerPartId='-1',Color='128',FontID='1',Text=net,Orientation='0',Justification='0' if dx>0 else '2',UniqueID=uid(ref+'.'+pin+'.net'),**{'Location.X':str(ex),'Location.Y':str(y)}))
  else:out.append(dict(RECORD='22',OwnerPartId='-1',Color='255',IsActive='T',SuppressAll='T',UniqueID=uid(ref+'.'+pin+'.nc'),**{'Location.X':str(tx),'Location.Y':str(y)}))
 out.append(dict(RECORD='34',OwnerIndex=str(owner),OwnerPartId='-1',Color='8388608',FontID='1',Text=ref,Name='Designator',UniqueID=uid(ref+'.ref'),**{'Location.X':str(x-20),'Location.Y':str(ytop+15)}))
 out.append(dict(RECORD='41',OwnerIndex=str(owner),OwnerPartId='-1',Color='8388608',FontID='1',Text=pattern,Name='Comment',UniqueID=uid(ref+'.comment'),**{'Location.X':str(x-90),'Location.Y':str(ybot-25)}))
notes=['ZIF to two ZIF ends - 51 identical-number parallel branches','C is the common end; A and B are the two output ends.','C.n = A.n = B.n for every n = 1..51; no pin-number partition.','C contacts on Bottom; A/B contacts on Top. Pitch 0.30 mm.','Draft: native Altium project reopen, compile and DRC are pending.'] if branch else ['ZIF contact tail to 25-pin Micro-D - Anton reference mapping','A: 51 integral FPC fingers, 0.30 mm pitch; odd contacts intentionally unconnected.','J1: NorComp 381-025-112L565; BL1/BL2 are isolated mechanical boardlocks.','DSUB 1..13 -> A2,A6,...A50; DSUB 14..25 -> A4,A8,...A48.','Draft: native Altium project reopen, compile and DRC are pending.']
for i,t in enumerate(notes):
 out.append(dict(RECORD='4',OwnerPartId='-1',FontID='1',Color='128',Text=t,UniqueID=uid('note'+str(i)),**{'Location.X':'100','Location.Y':str(820-i*18)}))
out[0]['Weight']=str(len(out)-1)
target=OUT/(NAME+'.SchDoc');tmp=H/(NAME+'_schematic.SchDoc')
if tmp.exists():tmp.unlink()
update_copy(source,tmp,{'FileHeader':b''.join(enc(r) for r in out)})
import shutil
shutil.copy2(tmp,target)
(OUT/(NAME+'.PrjPcb')).write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath='+NAME+'.SchDoc\n[Document2]\nDocumentPath='+NAME+'.PcbDoc\n')
with olefile.OleFileIO(OUT/(NAME+'.PcbDoc')) as o:
 pads=pads_stream(o.openstream('Pads6/Data').read());comps=properties(o.openstream('Components6/Data').read());nets=properties(o.openstream('Nets6/Data').read())
actual={comps[p['component']]['SOURCEDESIGNATOR']+'.'+p['number']:None if p['net']==65535 or nets[p['net']]['NAME'].startswith('NC_') else nets[p['net']]['NAME'] for p in pads}
assert actual==pinmap
assert len(set(r['UniqueID'] for r in out if 'UniqueID' in r))==sum('UniqueID' in r for r in out)
(OUT/'schematic_correspondence.json').write_text(json.dumps({'saved_pcb_pin_map_matches_schematic':True,'pin_count':len(pinmap),'signal_nets':51 if branch else 25,'no_connect_pins':0 if branch else 28,'native_compile_verified':False,'pin_net_map':pinmap},indent=2)+'\n')
with (OUT/'contact_mapping.csv').open('w',newline='') as f:
 w=csv.writer(f)
 if branch:
  w.writerow(['Common_C','Output_A','Output_B','Net'])
  for n in range(1,52):w.writerow([n,n,n,f'FPC_{n:02d}'])
 else:
  w.writerow(['DSUB_pin','FPC_A_contact','Net'])
  for k,v in sorted(mapping.items(),key=lambda kv:int(kv[0])):w.writerow([k,v,f'DSUB_{int(k):02d}'])
print(f'Native schematic written; saved PCB pin assignments match all {len(pinmap)} schematic pins. Native compilation pending.')
