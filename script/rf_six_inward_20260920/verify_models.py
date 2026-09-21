"""Read-only audit of embedded passive bodies and footprint pad preservation."""
from pathlib import Path
import sys, struct, json, zlib, math, hashlib
H=Path(__file__).resolve().parent; W=H.parent/'_support'
P=H.parents[1]/'QSTL_24DC_4MW_PCB'; B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/'qd_center_revision'),str(W/'final_routing/schematic')]
from native_metadata_helpers import properties,pads_stream,pad_record,sha,UNIT
from build_routed_copy import snapshot

def body_props(raw):
    start=raw.index(b'V7_LAYER='); size=struct.unpack_from('<I',raw,start-4)[0]&0xffffff
    return dict(x.split('=',1) for x in raw[start:start+size].rstrip(b'\0').decode('cp1252').split('|') if '=' in x)

def records(raw,offset=0):
    pads=[]; bodies=[]
    while offset<len(raw):
        if raw[offset]==2:
            p=pad_record(raw,offset); pads.append(p); offset=p['end']
        else:
            kind=raw[offset]; size=struct.unpack_from('<I',raw,offset+1)[0]&0xffffff
            b=raw[offset+5:offset+5+size]; offset+=5+size
            if kind==12:bodies.append((struct.unpack_from('<H',b,7)[0],body_props(b)))
            if kind==5:offset+=4+(struct.unpack_from('<I',raw,offset)[0]&0xffffff)
    return pads,bodies

def embedded(s,prefix):
    return {(m['ID'],m['ROTZ']):hashlib.sha256(zlib.decompress(s[prefix+str(i)])).hexdigest()
            for i,m in enumerate(properties(s[prefix+'Data'])) if m.get('EMBED')=='TRUE'}

def mm(value):return float(value.removesuffix('mil'))*.0254
expected={'R':'1875571c326d0d9e96f36b4efeb8094068ef7619f0a449c781caf0b49c2e5861',
          'C':'87aba8f59dd0a776648c0d6f799f01e81284ece312cefab9136b263b7d9b99d5'}
errors=[]; results=[]
def check(ok,description):
    if not ok:errors.append(description)

def audit(name,body,pads,models,bottom):
    assert len(pads)==2
    cx,cy=[sum(p['coords'][i]*UNIT for p in pads)/2 for i in (0,1)]
    dx=(pads[1]['coords'][0]-pads[0]['coords'][0])*UNIT; dy=(pads[1]['coords'][1]-pads[0]['coords'][1])*UNIT
    axis=math.degrees(math.atan2(dy,dx))%180
    angle=float(body['MODEL.3D.ROTZ'])%180
    offset=math.dist([cx,cy],[mm(body['MODEL.2D.X']),mm(body['MODEL.2D.Y'])])
    delta=abs((axis-angle+90)%180-90)
    check(offset<8*UNIT,name+' model origin differs from pad midpoint')
    check(delta<.001,name+' model long axis differs from pad axis')
    check(body['MODEL.MODELTYPE']=='1' and body['MODEL.EMBED']=='TRUE',name+' not embedded STEP')
    check(body['BODYPROJECTION']==('1' if bottom else '0'),name+' model side incorrect')
    check(float(body['MODEL.3D.ROTX'])==float(body['MODEL.3D.ROTY'])==0,name+' model tilted')
    checksum=models.get((body['MODELID'],body['MODEL.3D.ROTZ']))
    check(checksum==expected[name[0]],name+' embedded STEP checksum')
    results.append(dict(component=name,origin_offset_mm=offset,pad_axis_deg=axis,model_axis_deg=angle,
                        angle_error_deg=delta,embedded_step_sha256=checksum,side='Bottom' if bottom else 'Top'))

s=snapshot(P/(B+'.PcbDoc')); cs=properties(s['Components6/Data']); ps=pads_stream(s['Pads6/Data'])
_,bs=records(s['ComponentBodies6/Data']); models=embedded(s,'Models/')
for ci,body in bs:
    if ci==65535:continue
    name=cs[ci]['SOURCEDESIGNATOR']
    if name.startswith(('R','C')):audit(name,body,[p for p in ps if p['component']==ci],models,True)
check(len(results)==12,'Board passive body count')
libraries=[]
for name,pattern,label in [('Passives_0603.PcbLib','CC1608-0603','R_library'),('Capacitors_0402.PcbLib','FP-GCM155-0_05-IPC_A','C_library')]:
    lib=snapshot(P/name); old=snapshot(H/name); raw=lib[pattern+'/Data']; before=old[pattern+'/Data']
    pp,bb=records(raw,4+(struct.unpack_from('<I',raw,0)[0]&0xffffff))
    oldpp,_=records(before,4+(struct.unpack_from('<I',before,0)[0]&0xffffff))
    shape=lambda pads:sorted((p['number'],p['coords'],p['rotation'],p['shape'],p['layer']) for p in pads)
    rawpads=lambda pads:sorted((p['number'],p['blocks']) for p in pads)
    check(shape(pp)==shape(oldpp),name+' pad geometry changed')
    check(len(bb)==1,name+' passive body count')
    audit(label,bb[0][1],pp,embedded(lib,'Library/Models/'),False)
    libraries.append(dict(file=name,sha256=sha(P/name),pad_geometry_identical=shape(pp)==shape(oldpp),
                          pad_records_byte_identical=rawpads(pp)==rawpads(oldpp),
                          note='Altium library save updates native serialization; number, coordinates, all layer sizes, hole, rotation, shape and layer compared explicitly.'))
dimensions=json.loads((H/'STEP_dimensions.json').read_text())
check(all(x['valid'] for x in dimensions.values()),'Invalid STEP geometry')
report=dict(passed=not errors,errors=errors,pcb_sha256=sha(P/(B+'.PcbDoc')),bodies=results,libraries=libraries,
            STEP_geometry=dimensions,resistor_model='Generic KiCad 0603 (1.6 x 0.8 x 0.45 mm)',
            capacitor_model='Existing 0402 package shape preserved; orientation corrected')
(H/'model_validation.json').write_text(json.dumps(report,indent=2)+'\n')
if report['passed']:(P/'docs/model_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=report['passed'],errors=errors,checked_bodies=len(results)),indent=2))
raise SystemExit(0 if report['passed'] else 1)
