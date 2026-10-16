"""Measure the repaired critical pad aperture gaps from saved native copper."""
from pathlib import Path
import hashlib, html, json, re
from shapely.geometry import LineString
from shapely.ops import nearest_points, unary_union
from audit_saved_revision_surface import read_snapshot
from audit_saved_mask_repair import dump, UNIT
from prepare_native_revision_rules import read_rules

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
PCB=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
CANDIDATE=H/'full_copper_candidate.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    native_hash=sha(PCB);candidate_hash=sha(CANDIDATE)
    assert native_hash=='1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
    assert candidate_hash=='835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495'
    sch=json.loads((ROOT/'QSTL_QD4_2SET_38PAD/schematic_validation.json').read_text())
    pads,regions,tracks,vias,board=read_snapshot(PCB,sch)
    by_pad={(p['ref'],p['pin']):p for p in pads if p['ref']}
    cache=dump(H/'native_mask_after_reopen.txt','AFTER_REOPEN',candidate_hash)
    cache_by_pad={(k[0],k[1]):v for k,v in cache.items() if k[0]!='MOUNT'}
    bottom_general_open=unary_union([r['geometry'] for r in regions if r['layer']==38])
    pairs=json.loads((H/'mask_sliver_repair_plan_audit.json').read_text())['pairs']
    rows=[]
    for pair in pairs:
        keys=[tuple(s.split('-')) for s in pair['pads']]
        pa,pb=[by_pad[k] for k in keys]
        expansion=[cache_by_pad[k][1]*UNIT for k in keys]
        a,b=[p['geometry'].buffer(e,quad_segs=128) for p,e in zip((pa,pb),expansion)]
        segment=LineString([p.coords[0] for p in nearest_points(a,b)])
        row=dict(pads=pair['pads'],copper_gap_mm=pa['geometry'].distance(pb['geometry']),
                 saved_bottom_expansion_mm=expansion,aperture_edge_gap_mm=a.distance(b),
                 analytic_gap_mm=pa['geometry'].distance(pb['geometry'])-sum(expansion),
                 nearest_gap_segment_mm=list(segment.coords),
                 explicit_general_opening_crosses_gap=segment.intersects(bottom_general_open),
                 gap_segment_clearance_to_general_opening_mm=segment.distance(bottom_general_open))
        assert row['analytic_gap_mm']>.1049 and not row['explicit_general_opening_crosses_gap']
        rows.append(row)
    rule=read_rules(PCB)['MinimumSolderMaskSliver']
    assert rule['ENABLED']=='TRUE' and rule['SCOPE1EXPRESSION']==rule['SCOPE2EXPRESSION']=='All'
    rule_min=float(rule['MINSOLDERMASKWIDTH'].removesuffix('mil'))*.0254
    assert abs(rule_min-.1)<1e-6
    text=(H/'Native_DRC.html').read_text()
    summary=re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>',text,re.S)
    mask=[dict(rule=html.unescape(re.sub('<[^>]+>','',name)),violations=int(n)) for name,n in summary if 'Minimum Solder Mask Sliver' in name]
    assert len(mask)==1 and mask[0]['violations']==0
    report=dict(passed=True,native_sha256=native_hash,candidate_sha256=candidate_hash,
                native_sliver_rule=rule,native_sliver_rule_minimum_mm=rule_min,native_DRC=mask[0],
                minimum_saved_critical_aperture_gap_mm=min(r['analytic_gap_mm'] for r in rows),
                minimum_saved_RC_pair_gap_mm=min(r['analytic_gap_mm'] for r in rows if all(not x.startswith('SMP') for x in r['pads'])),
                critical_pairs=sorted(rows,key=lambda r:r['analytic_gap_mm']),
                interpretation='Gap is between mask aperture edges, i.e. the nominal retained mask web where no explicit opening interrupts it. It is not mask expansion, copper clearance, or a guaranteed as-fabricated width. Intentional common openings in the QD/general unmasked field are not mask dams.',
                scope='All 16 previously critical native pad pairs measured independently; native enabled All/All DRC checks the saved full board.')
    assert sha(PCB)==native_hash and sha(CANDIDATE)==candidate_hash
    (H/'saved_mask_minimum_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('passed','minimum_saved_critical_aperture_gap_mm','minimum_saved_RC_pair_gap_mm','native_DRC')},indent=2))

if __name__=='__main__':main()
