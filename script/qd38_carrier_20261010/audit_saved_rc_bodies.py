"""Read-only comparison of saved passive body envelopes and embedded STEP bounds."""
from pathlib import Path
import json,re,zlib,hashlib
import olefile
from shapely.geometry import Polygon
from audit_source_model_transforms import inspect

H=Path(__file__).resolve().parent;ROOT=H.parents[1];DEST=ROOT/'QSTL_QD4_2SET_38PAD'


def main():
    original=inspect(ROOT/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc')
    path=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc';current=inspect(path)
    sch=json.loads((DEST/'schematic_validation.json').read_text());names={v:k for k,v in sch['components'].items()}
    selected=[]
    for body in current['bodies']:
        ref=names.get(body['component_fields'].get('SOURCEUNIQUEID','').strip('\\'),body['component'])
        if ref and re.fullmatch(r'[RC]\d+',ref):
            body['component']=ref;selected.append(body)
    def brief(body):
        geom=Polygon(body['outline_mm'])
        return dict(component=body['component'],component_origin=body['component_origin_mm'],model_origin=body['model_origin_mm'],
                    rotation=body['rotation_xyz_deg'],body_outline_bounds=geom.bounds,body_outline=body['outline_mm'],
                    body_projection=body['body_projection'],standoff=body['standoff_mm'],height=body['overall_height_mm'],
                    model_id=body['body_fields']['MODELID'])
    collisions=[];pair_gaps=[]
    for i,a in enumerate(selected):
        pa=Polygon(a['outline_mm'])
        for b in selected[i+1:]:
            pb=Polygon(b['outline_mm']);dist=pa.distance(pb)
            if a['component'][1:]==b['component'][1:]:
                pair_gaps.append(dict(a=a['component'],b=b['component'],distance_mm=dist,overlap_mm2=pa.intersection(pb).area))
            if dist<.254:
                intersection=pa.intersection(pb)
                collisions.append(dict(a=a['component'],b=b['component'],distance_mm=dist,overlap_mm2=intersection.area,
                                       overlap_bounds=None if intersection.is_empty else list(intersection.bounds)))
    source=[brief(b) for b in original['bodies'] if b['component'] in ('R1','C1')]
    # STEP Cartesian point envelopes are recorded only as a diagnostic; these
    # include construction/control points and are not certified solid bounds.
    stepbounds=[]
    with olefile.OleFileIO(path) as doc:
        from audit_source_model_transforms import properties
        rows=properties(doc.openstream('Models/Data').read())
        for index,row in enumerate(rows):
            if row.get('ID') not in {b['body_fields']['MODELID'] for b in selected}:continue
            text=zlib.decompress(doc.openstream(f'Models/{index}').read()).decode('ascii',errors='replace')
            matches=re.findall(r'CARTESIAN_POINT\s*\([^,]*,\s*\(([^)]+)\)\)',text)
            pts=[tuple(float(v) for v in s.split(',')) for s in matches]
            pts=[p for p in pts if len(p)==3]
            stepbounds.append(dict(index=index,metadata=row,cartesian_bounds=[min(p[k] for p in pts) for k in range(3)]+[max(p[k] for p in pts) for k in range(3)],
                                   coordinate_count=len(pts),sha256=hashlib.sha256(text.encode()).hexdigest()))
    report=dict(native_sha256=current['source_sha256'],source_passives=source,passives=[brief(b) for b in selected],
                body_projection_clearance_below_0254=collisions,paired_rc_body_gaps=pair_gaps,
                paired_rc_body_minimum_gap_mm=min(pair['distance_mm'] for pair in pair_gaps),step_coordinate_envelopes=stepbounds,
                note='Body contour distances are saved Altium projection contours; STEP coordinate bounds are diagnostic only.')
    (H/'saved_rc_body_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('passives','source_passives','step_coordinate_envelopes')},indent=2))


if __name__=='__main__':main()
