"""Read-only integration smoke check using the current offline route sources.

This checks the remapping bridge, not final routing or fabrication readiness.
It does not execute source promotion, schematic generation or native scripts.
"""
import argparse
import hashlib
import json
from pathlib import Path

from geodesic_rf_assignment import remap
from revision_invariants import assert_plan_contacts

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dc",type=Path,required=True)
    parser.add_argument("--rf",type=Path,required=True)
    args=parser.parse_args()
    dc=json.loads(args.dc.read_text());rf=json.loads(args.rf.read_text())
    mapping={int(s["ref"][3:]):s["q"] for s in rf["smp"]}
    assert set(mapping)==set(mapping.values()) and len(mapping)==16
    merged=remap(dc,mapping)
    assert_plan_contacts(merged)
    # Net-name reassignment must not bend, offset or reroute any DC primitive.
    original_tracks=[t for t in dc["tracks"] if t["layer"] in (2,4)]
    result_tracks=[t for t in merged["tracks"] if t["layer"] in (2,4)]
    assert len(original_tracks)==len(result_tracks)
    for old,new in zip(original_tracks,result_tracks):
        assert {k:v for k,v in old.items() if k!="net"}=={k:v for k,v in new.items() if k!="net"}
        q=int(old["net"][2:])
        assert new["net"]==f"DC{mapping.get(q,q):02}"
    captions=[]
    # The wrapper's old builder iterates mapped q values as reference IDs;
    # because this is a permutation, it still emits each physical group once.
    for ref_id in [s["q"] for s in merged["smp"]]:
        smp=next(s for s in merged["smp"] if s["ref"]==f"SMP{ref_id:02}")
        q=smp["q"]
        assert set(merged["nets"][f"MW{q:02}"])=={f"Q1-{q}",f"R{ref_id:02}-1",f"C{ref_id:02}-2"}
        assert set(merged["nets"][f"S{ref_id:02}"])=={f"SMP{ref_id:02}-1",f"C{ref_id:02}-1"}
        assert f"R{ref_id:02}-2" in merged["nets"][f"DC{q:02}"]
        captions.append(dict(physical_group=ref_id,QD=q,caption=f"RF + DC: Q1-{q} / {merged['pads'][q-1]['net']}"))
    for old,new in zip(dc["vias"],merged["vias"]):
        assert {k:v for k,v in old.items() if k!="net"}=={k:v for k,v in new.items() if k!="net"}
    for source in rf["smp"]:
        target=next(s for s in merged["smp"] if s["ref"]==source["ref"])
        for key in ("x","y","rotation","escape_angle_deg"):
            assert target.get(key)==source.get(key),(source["ref"],key)
    report=dict(status="READ_ONLY_INTEGRATION_CHECK",passed=True,
        sources=[dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (args.dc,args.rf)],
        internal_DC_primitives_preserved=len(original_tracks),signal_via_geometry_preserved=len(dc["vias"]),
        captions=captions,exact_ZIF_contact_pool=assert_plan_contacts(merged),
        completion=False,limitation="No route clearance, native API execution or final source promotion is certified by this helper.")
    (HERE/"integration_review.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
