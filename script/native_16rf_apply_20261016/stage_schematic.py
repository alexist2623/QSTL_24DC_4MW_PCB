"""Synchronize explicit ZIF labels and C1206 metadata without changing symbols."""
from pathlib import Path
import sys,json,copy,csv,struct,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path[:0]=[str(ROOT/'script/_support/zif_revision/schematic'),str(ROOT/'script/_support/qd_center_revision')]
import build_zif_schematic as s
import native_metadata_helpers as nh
plan=json.loads((HERE/'candidate.json').read_text())
source=HERE/'backup/QSTL_QD4_2SET_38PAD.SchDoc';dest=HERE/source.name
rs=s.records(source);out=copy.deepcopy(rs);groups=s.component_groups(rs)
pin_net={pin:net for net,pins in plan['nets'].items() for pin in pins}
old=json.loads((HERE/'backup/schematic_validation.json').read_text());pins=old['pins'];nc=old['nc'];changed=[]
for pin in pins:
    if not pin['key'].startswith('J1-') or pin['key'] in nc:continue
    dx,dy=((1,0),(0,1),(-1,0),(0,-1))[pin['direction']];x,y=pin['tip'];end=(x+30*dx,y+30*dy)
    ids=[i for i,r in enumerate(out) if r.get('RECORD')=='25' and (int(r['Location.X']),int(r['Location.Y']))==end]
    assert len(ids)==1
    i=ids[0];assert out[i]['Text']==old['pin_net'][pin['key']]
    if out[i]['Text']!=pin_net[pin['key']]:changed.append(dict(pin=pin['key'],old=out[i]['Text'],new=pin_net[pin['key']]))
    out[i]['Text']=pin_net[pin['key']]
cfg=json.loads((ROOT/'script/cap_1206_apply_20261014/native_prep/part_parameters.json').read_text())
params={'Value':cfg['value'],'Case/Package':cfg['package'],'Comment':cfg['value']+' / 1206','Manufacturer':'Yageo','Manufacturer Part Number':cfg['mpn'],'Voltage':cfg['voltage'],'Tolerance':cfg['tolerance'],'Dielectric':cfg['dielectric'],'Height (max)':'1.8mm'}
for ref,g in groups.items():
    if not ref.startswith('C'):continue
    ri,root=next((i,r) for i,r in g if r.get('RECORD')=='1');out[ri+1].update(ComponentDescription=cfg['description'],DesignItemId=cfg['mpn'])
    found=set()
    for i,r in g:
        if r.get('RECORD')=='41' and r.get('OwnerIndex')==str(ri) and r.get('Name') in params:
            out[i+1]['Text']=params[r['Name']];found.add(r['Name'])
        if r.get('RECORD')=='45' and r.get('ModelType')=='PCBLIB':out[i+1].update(ModelName=cfg['footprint'],ModelDatafile0=cfg['footprint_library'],ModelDatafileEntity0=cfg['footprint'],ModelDatafileKind0='PCBLIB',DatafileCount='1',IsCurrent='T',IntegratedModel='F',DatabaseModel='F',Description=cfg['description'])
    for name,value in params.items():
        if name not in found:out.append(dict(RECORD='41',OwnerIndex=str(ri),IndexInSheet='-1',OwnerPartId='-1',Color='8388608',FontID='1',IsHidden='T',Text=value,Name=name,UniqueID=s.uid('CAP1206_16RF|'+ref+'|'+name)))
out[0]['Weight']=str(len(out)-1)
validation=s.geometry_check(out,pins,pin_net,nc)
s.update_copy(source,dest,{'FileHeader':s.pack([(0,s.encode(r)) for r in out])})
assert s.records(dest)==out
report=dict(old,nets=plan['nets'],pin_net=pin_net,schematic_sha256=s.sha(dest),schematic_geometry_validation=validation,status='Staged synchronized schematic; native compile pending',changed_ZIF_labels=changed)
(HERE/'schematic_validation.json').write_text(json.dumps(report,indent=2))
# Preserve the existing footprint structure/UIDs; inverse board rotation and
# Bottom mirroring place each accepted pad into canonical library coordinates.
lib=HERE/'backup/QD4_2SET_38.PcbLib'
with nh.olefile.OleFileIO(lib) as ole:data=ole.openstream('QD4_2SET_38/Data').read()
b=bytearray(data);pos=4+struct.unpack_from('<I',data)[0];by={d['pin']:d for d in plan['physical_pads'] if d['ref']=='Q1'};n=0;cx,cy=plan['sample_center']
while pos<len(data):
    q=nh.pad_record(data,pos);pos=q['end'];d=by[q['number']];at=q['block_offsets'][4]
    # inverse 90 degree gives (dy,-dx); library top-side mirror gives (-dy,-dx)
    xy=[-(d['y']-cy),-(d['x']-cx)];values=[*xy,d['sx'],d['sy'],d['sx'],d['sy'],d['sx'],d['sy'],0]
    struct.pack_into('<9i',b,at+13,*[round(v/nh.UNIT) for v in values]);struct.pack_into('<d',b,at+52,(-(d['rotation']-90))%360);n+=1
assert n==38
s.update_copy(lib,HERE/lib.name,{'QD4_2SET_38/Data':bytes(b)})
shutil.copy2(ROOT/'QSTL_24DC_4MW_PCB/Capacitors_1206.PcbLib',HERE/'Capacitors_1206.PcbLib')
print(json.dumps(dict(changed_ZIF_labels=len(changed),capacitors=16,QD_library_pads=n,geometry=validation),indent=2))
