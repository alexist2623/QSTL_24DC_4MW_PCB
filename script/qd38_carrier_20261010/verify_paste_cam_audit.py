"""Compare native paste CAM with saved native J1/R/C pad apertures only.

All input design/CAM is read-only. Outputs stay in this script directory.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import math
import re
import struct
import sys

import olefile
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely.affinity import rotate

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'script/fpc_gerber_20261005/work/deps'),str(ROOT/'script/_support/qd_center_revision')]
from native_metadata_helpers import properties,pads_stream,binary_records,UNIT
from gerbonara import GerberFile
from gerbonara.utils import MM

TOL=.00005


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def gerber_geometry(path):
    gerber=GerberFile.open(path)
    shapes=[]
    for obj in gerber.objects:
        for primitive in obj.to_primitives(unit=MM):
            assert primitive.polarity_dark, 'Unexpected clear-polarity paste primitive; review explicitly'
            kind=type(primitive).__name__
            if kind=='Circle':
                geom=Point(primitive.x,primitive.y).buffer(primitive.r,quad_segs=128)
            elif kind=='Line':
                geom=LineString([(primitive.x1,primitive.y1),(primitive.x2,primitive.y2)]).buffer(primitive.width/2,quad_segs=128)
            elif kind=='Rectangle':
                geom=Polygon(primitive.to_arc_poly().outline)
            elif kind=='ArcPoly':
                geom=Polygon(primitive.approximate_arcs(max_error=1e-7).outline)
            else:
                raise ValueError('Unsupported emitted paste shape '+kind)
            assert geom.is_valid
            shapes.append(geom)
    return unary_union(shapes),dict(objects=len(gerber.objects),object_types=dict(Counter(type(o).__name__ for o in gerber.objects)),primitive_count=len(shapes))


def pad_geometry(pad):
    x,y,sx,sy,*_=pad['coords']
    x,y,sx,sy=[v*UNIT for v in (x,y,sx,sy)]
    if pad['shape']==1:
        assert abs(sx-sy)<TOL,'Elliptical pads need a separate exact shape implementation'
        return Point(x,y).buffer(sx/2,quad_segs=128)
    assert pad['shape']==2, f"Unimplemented saved pad shape {pad['shape']}"
    geom=Polygon([(x-sx/2,y-sy/2),(x+sx/2,y-sy/2),(x+sx/2,y+sy/2),(x-sx/2,y+sy/2)])
    return rotate(geom,pad['rotation'],origin=(x,y))


def main():
    manifest=json.loads((HERE/'paste_audit_source_manifest.json').read_text())
    path=Path(manifest['pcb']);before=sha(path)
    errors=[]
    def check(ok,issue,detail=None):
        if not ok:errors.append(dict(issue=issue,detail=detail))
    check(before==manifest['pcb_sha256'],'PCB changed since paste preparation',[before,manifest['pcb_sha256']])
    project=path.with_suffix('.PrjPcb')
    check(sha(project)==manifest['project_sha256'],'Project file changed since paste preparation')
    log=(HERE/'paste_export_native_log.txt').read_text()
    check('COMPLETE' in log and 'EXPORT_RETURNED' in log,'Native export did not complete')
    check(not any(line.startswith('STOP_') for line in log.splitlines()),'Native export guard stopped')
    flags={}
    for line in log.splitlines():
        if line.startswith('PAD|'):
            _,ref,pin,x,y,layer,expansion,mode,enabled,top,bottom=line.split('|')
            flags[ref,pin,int(x),int(y)]=dict(layer=int(layer),expansion=int(expansion),mode=int(mode),enabled=enabled=='1',top=top=='1',bottom=bottom=='1')
    with olefile.OleFileIO(path) as doc:
        blobs={'/'.join(key):doc.openstream(key).read() for key in doc.listdir()}
    comps=properties(blobs['Components6/Data'])
    names={i:c.get('SOURCEDESIGNATOR') for i,c in enumerate(comps)}
    offset=0;data=blobs['Texts6/Data']
    while offset<len(data):
        assert data[offset]==5
        n=struct.unpack_from('<I',data,offset+1)[0]&0xffffff;body=data[offset+5:offset+5+n];offset+=5+n
        n=struct.unpack_from('<I',data,offset)[0]&0xffffff;value=data[offset+4:offset+4+n];offset+=4+n
        name=value[1:].decode('cp1252')
        if re.fullmatch(r'J1|Q1|(?:SMP|R|C)\d{2}',name):
            names[struct.unpack_from('<H',body,7)[0]]=name
    pads=pads_stream(blobs['Pads6/Data'])
    selected={35:[],36:[]};counts=Counter();excluded=Counter()
    for pad in pads:
        ref='MOUNT' if pad['component']==65535 else names[pad['component']]
        key=(ref,pad['number'],pad['coords'][0],pad['coords'][1])
        flag=flags.get(key)
        check(flag is not None,'Pad missing native flag audit',key)
        intended=ref=='J1' or bool(re.fullmatch(r'[RC]\d{2}',ref))
        if not intended:
            excluded[ref[:3] if ref.startswith('SMP') else ref]+=1
            check(flag is not None and not flag['enabled'],'Excluded pad paste enabled',key)
            continue
        check(pad['layer'] in (1,32),'Normal paste pad on unsupported layer',key)
        check(flag is not None and flag['enabled'],'Required SMD paste disabled',key)
        check(flag is not None and flag['expansion']==0,'Nonzero native SMD paste expansion needs explicit geometry handling',dict(pad=key,flag=flag))
        if flag is None:continue
        face=35 if pad['layer']==1 else 36
        check(flag['top'] if face==35 else flag['bottom'],'Required face paste disabled',key)
        selected[face].append(pad_geometry(pad));counts[face]+=1
    check(dict(counts)=={35:53,36:64},'Expected normal pad aperture count differs',dict(counts))
    checks=[]
    actual={}
    for face,extension in [(35,'GTP'),(36,'GBP')]:
        file=Path(manifest['cam_directory'])/(path.stem+'.'+extension)
        check(file.exists(),'Missing native paste Gerber',str(file))
        if not file.exists():continue
        expected=unary_union(selected[face]);emitted,meta=gerber_geometry(file);actual[face]=emitted
        missing=expected.difference(emitted.buffer(TOL)).area
        added=emitted.difference(expected.buffer(TOL)).area
        check(missing<1e-8 and added<1e-8,'Paste CAM differs from saved intended pad shapes',dict(face=face,missing=missing,added=added))
        checks.append(dict(layer=face,file=str(file),sha256=sha(file),expected_pad_count=counts[face],
                           expected_area_mm2=expected.area,actual_area_mm2=emitted.area,
                           missing_outside_tolerance_mm2=missing,extra_outside_tolerance_mm2=added,
                           tolerance_mm=TOL,**meta))
    explicit=[]
    for stream,kind in [('Tracks6/Data',4),('Arcs6/Data',1),('Fills6/Data',6),('Regions6/Data',11),('ShapeBasedRegions6/Data',11)]:
        for i,record in enumerate(binary_records(blobs.get(stream,b''),kind)):
            if record['body'][0] in (35,36):explicit.append((stream,i))
    check(not explicit,'Explicit paste primitives remain',explicit)
    check(sha(path)==before,'PCB changed during audit')
    report=dict(passed=not errors,status='NATIVE_PASTE_CAM_COMPARED_WITH_SAVED_PAD_GEOMETRY',native_sha256=before,
                normal_pad_apertures=dict(counts),excluded_pads=dict(excluded),cam_checks=checks,errors=errors,
                explicit_paste_object_count=len(explicit),
                via_specific_paste_absent=not errors,
                note='No extra CAM paste beyond intended J1 and R/C SMD pads. Paste coincident with R/C via-in-pad belongs to the required SMD pad and is intentionally retained.',
                fabrication_release=False)
    (HERE/'native_paste_cam_validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    assert report['passed'],errors


if __name__=='__main__':main()
