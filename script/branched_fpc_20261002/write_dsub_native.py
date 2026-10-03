"""Write a separate native PCB draft from verified Altium primitive templates.

This never overwrites a source/reference PCB. Native reopen and DRC are required
before this draft can be described as a completed Altium design.
"""
from pathlib import Path
import sys,json,struct,uuid,hashlib,re,shutil
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,pads_stream,binary_records,olefile,GUID_TAGS,UNIT
from cfb_copy_update import update_copy
NAME=sys.argv[1] if len(sys.argv)>1 else 'ZIF_to_DSUB25'
assert NAME in ('ZIF_to_DSUB25','ZIF_to_2xZIF')
OUT=R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002'/NAME;P=OUT/(NAME+'.PcbDoc')
plan=json.loads((OUT/'design_plan.json').read_text())
def snap(p):
 with olefile.OleFileIO(p) as o:return {'/'.join(k):o.openstream(k).read() for k in o.listdir()}
fpc=snap(R/'QSTL_24DC_4MW_PCB/FPC_15015_0451/FPC_15015_0451.PcbDoc')
carrier=snap(R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc')
seed=H/'dsub_blank.PcbDoc'
if not seed.exists():shutil.copy2(P,seed)
d=snap(seed)
def u(v):return round(v/UNIT)
def mil(v):return f'{v/.0254:.9f}mil'
def pp(p,leading=True):
 raw=(('|' if leading else '')+'|'.join(k+'='+str(v) for k,v in p.items())+'\0').encode('cp1252');return struct.pack('<I',len(raw))+raw
def bo(rows,k):return b''.join(bytes([k])+struct.pack('<I',len(r))+r for r in rows)
def uid(s):
 n=int(hashlib.sha256(s.encode()).hexdigest(),16);return ''.join(chr(65+(n//26**i)%26) for i in range(8))
ids={name:i for i,name in enumerate(plan['nets'])};comps={c['ref']:i for i,c in enumerate(plan['components'])}
counts={};updates={}
def stream(name,body,count):
 updates[name+'/Data']=body;updates[name+'/Header']=struct.pack('<I',count);counts[name]=count
bb=properties(d['Board6/Data'])[0]
for k in list(bb):
 if re.fullmatch(r'(KIND|VX|VY|CX|CY|SA|EA|R)\d+',k):del bb[k]
for i,(x,y) in enumerate(plan['outline']+[plan['outline'][0]]):bb.update({f'KIND{i}':'0',f'VX{i}':mil(x),f'VY{i}':mil(y)})
bb.update(ORIGINX='0mil',ORIGINY='0mil')
stream('Board6',pp(bb),1)
n0=properties(fpc['Nets6/Data'])[0];nets=[]
for name in plan['nets']:nets.append(n0|{'NAME':name,'UNIQUEID':uid('adapter.net.'+name)})
stream('Nets6',b''.join(pp(n) for n in nets),len(nets))
c0=properties(fpc['Components6/Data'])[0];cs=[]
for c in plan['components']:
 cs.append(c0|dict(X=mil(c['x']),Y=mil(c['y']),LAYER='BOTTOM' if c['layer']==32 else 'TOP',PATTERN=c['pattern'],SOURCEDESIGNATOR=c['ref'],SOURCELIBREFERENCE=c['pattern'],SOURCEUNIQUEID=uid('adapter.sch.'+c['ref']),UNIQUEID=uid('adapter.comp.'+c['ref'])))
stream('Components6',b''.join(pp(c) for c in cs),len(cs))
smd=pads_stream(fpc['Pads6/Data'])[0]
pth=next(p for p in pads_stream(carrier['Pads6/Data']) if p['coords'][8]>0)
out=[]
for p in plan['pads']:
 blocks=list((pth if p['hole'] else smd)['blocks']);b=bytearray(blocks[4]);name=p['pin'].encode('ascii');blocks[0]=bytes([len(name)])+name
 b[0]=p['layer'];struct.pack_into('<3H',b,3,ids.get(p['net'],65535),65535,comps[p['ref']]);b[9:13]=b'\xff'*4
 struct.pack_into('<9i',b,13,*map(u,[p['x'],p['y'],p['sx'],p['sy'],p['sx'],p['sy'],p['sx'],p['sy'],p['hole']]))
 b[49:52]=bytes([2 if p['shape']=='rect' else 1])*3;struct.pack_into('<d',b,52,0)
 # Cache links are removed separately below; preserve unknown pad fields.
 blocks[4]=bytes(b);out.append(bytes([2])+b''.join(struct.pack('<I',len(v))+v for v in blocks))
stream('Pads6',b''.join(out),len(out))
t0=binary_records(fpc['Tracks6/Data'],4)[0]['body'];ts=[]
for t in plan['tracks']:
 b=bytearray(t0);b[0]=t['layer'];struct.pack_into('<H',b,3,ids.get(t['net'],65535));b[5:13]=b'\xff'*8
 struct.pack_into('<5i',b,13,*map(u,t['a']+t['b']+[t['width']]));struct.pack_into('<I',b,36,0)
 struct.pack_into('<I',b,41,0x01000000+t['layer'] if t['layer'] in (1,32) else 0x01030002);ts.append(bytes(b))
stream('Tracks6',bo(ts,4),len(ts))
r0=binary_records(fpc['Regions6/Data'],11)[0]['body']
ln={1:'TOP',32:'BOTTOM',37:'TOPSOLDER',38:'BOTTOMSOLDER'}
def region(layer,net,points,name,board_region=False):
 h=bytearray(r0[:18]);h[0]=layer;struct.pack_into('<3H',h,3,ids.get(net,65535),65535,65535);h[9:13]=b'\xff'*4
 props=dict(V7_LAYER=ln.get(layer,'MULTILAYER'),NAME=name,KIND='0',SUBPOLYINDEX='-1',UNIONINDEX='0',ARCRESOLUTION='0.5mil',ISSHAPEBASED='FALSE',CAVITYHEIGHT='0mil')
 if board_region:props.update(V7_LAYER='MULTILAYER',LAYER='KEEPOUT',KEEPOUT='TRUE',ISBOARDCUTOUT='TRUE',OBJECTKIND='BoardRegion',BENDINGLINECOUNT='0',LOCKED3D='FALSE',LAYERSTACKID=bb['V9_SUBSTACK0_ID'])
 return bytes(h)+pp(props,False)+struct.pack('<I',len(points))+b''.join(struct.pack('<2d',u(x),u(y)) for x,y in points)
rs=[region(r['layer'],r['net'],r['points'],r['name']) for r in plan['regions']]
stream('Regions6',bo(rs,11),len(rs));stream('ShapeBasedRegions6',b'',0)
stream('BoardRegions',bo([region(56,None,plan['outline'],'Flex body',True)],11),1)
v0=next(v['body'] for v in binary_records(carrier['Vias6/Data'],3) if v['body'][29:31]==bytes([1,32]));vs=[]
for v in plan['vias']:
 b=bytearray(v0);struct.pack_into('<H',b,3,ids[v['net']]);b[5:13]=b'\xff'*8
 struct.pack_into('<4i',b,13,*map(u,[v['x'],v['y'],v['diameter'],v['hole']]))
 b[29:31]=bytes([1,32]);b[74]=0
 for i in range(32):struct.pack_into('<i',b,75+4*i,u(v['diameter']))
 b[259:291]=b'\0'*32;vs.append(bytes(b))
stream('Vias6',bo(vs,3),len(vs))
# Copy only native component-designator text headers, replacing their strings.
data=fpc['Texts6/Data'];pos=0;templates=[]
while pos<len(data):
 assert data[pos]==5;n=struct.unpack_from('<I',data,pos+1)[0]&0xffffff;body=data[pos+5:pos+5+n];pos+=5+n
 z=struct.unpack_from('<I',data,pos)[0]&0xffffff;txt=data[pos+4:pos+4+z];pos+=4+z
 if txt[1:] in (b'A',b'B'):templates.append((body,txt))
assert templates
textrows=[]
for i,c in enumerate(plan['components']):
 b=bytearray(templates[0][0]);struct.pack_into('<H',b,7,i);struct.pack_into('<2i',b,13,u(c['x']),u(c['y']));name=c['ref'].encode()
 textrows.append(bytes([5])+struct.pack('<I',len(b))+b+struct.pack('<I',len(name)+1)+bytes([len(name)])+name)
stream('Texts6',b''.join(textrows),len(textrows));stream('Texts',b'',0);stream('WideStrings6',b'',0)
classes=properties(fpc['Classes6/Data'])
for c in classes:
 for k in list(c):
  if re.fullmatch(r'M\d+',k):del c[k]
stream('Classes6',b''.join(pp(c) for c in classes),len(classes))
rr=[];raw=d['Rules6/Data'];pos=0
while pos<len(raw):
 kind=raw[pos:pos+2];n=struct.unpack_from('<I',raw,pos+2)[0]&0xffffff;p=properties(raw[pos+2:pos+6+n])[0];pos+=6+n
 if p.get('RULEKIND')=='Clearance':p.update(GAP=mil(.0707),GENERICCLEARANCE=mil(.0707))
 if p.get('RULEKIND')=='Width':
  for k in list(p):
   if 'MINWIDTH' in k:p[k]=mil(.09999)
   if 'MAXWIDTH' in k:p[k]=mil(.30)
 rr.append(kind+pp(p))
stream('Rules6',b''.join(rr),len(rr))
for name in ['Connections6','PadViaCacheLibraryLinksSection','ExtendedPrimitiveInformation']:
 stream(name,b'',0)
uu=[dict(PRIMITIVEINDEX=i,PRIMITIVEOBJECTID='Pad',UNIQUEID=uid(f'adapter.pad.{i}')) for i in range(len(plan['pads']))]
stream('UniqueIDPrimitiveInformation',b''.join(pp(p) for p in uu),len(uu))
guid=[]
for name,count in counts.items():
 if name in GUID_TAGS:
  for i in range(count):guid.append(struct.pack('<II',GUID_TAGS[name],i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/adapter/{name}/{i}').bytes_le)
stream('PrimitiveGuids',b''.join(guid),len(guid))
temp=H/(NAME+'_populated.PcbDoc')
if temp.exists():temp.unlink()
update_copy(seed,temp,updates);shutil.copy2(temp,P)
(OUT/'native_status.json').write_text(json.dumps({'native_generation':'offline template writer','native_reopen_verified':False,'native_drc_verified':False,'requires_native_rebuild':True,'pcb_sha256':hashlib.sha256(P.read_bytes()).hexdigest()},indent=2)+'\n')
print(json.dumps({'native_pcb':str(P),'counts':counts},indent=2))
