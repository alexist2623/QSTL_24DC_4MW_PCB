"""Exercise new read-only geometry audits on the frozen, superseded real PCB.

This intentionally does not certify that PCB or the new candidate. The old
saved snapshot contains known routing defects; both audits must expose them.
"""
import collections
import html
import json
from pathlib import Path
import re
import struct
import sys

from audit_saved_dc_geometry import inspect_saved_dc
from audit_saved_rf_geometry import inspect_saved_rf
from prepare_native_revision_rules import BASELINE, FROZEN, sha

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"script/_support/qd_center_revision"))
from native_metadata_helpers import UNIT, binary_records, olefile, properties


def main():
    assert sha(BASELINE)==FROZEN
    snapshot=json.loads((HERE.parent/"qd38_carrier_20261010/through_dc_saved_native_snapshot.json").read_text())
    assert snapshot["source_sha256"]==FROZEN
    with olefile.OleFileIO(BASELINE) as source:
        nets=properties(source.openstream("Nets6/Data").read())
        records=binary_records(source.openstream("Vias6/Data").read(),3)
    vias=[]
    for record in records:
        body=record["body"];net=struct.unpack_from("<H",body,3)[0];x,y,diameter,hole=struct.unpack_from("<4i",body,13)
        vias.append(dict(net=None if net==65535 else nets[net]["NAME"],x=x*UNIT,y=y*UNIT,diameter=diameter*UNIT,hole=hole*UNIT,low=body[29],high=body[30]))
    dc=inspect_saved_dc(snapshot,vias,[])
    rf=inspect_saved_rf(snapshot,vias)
    assert not dc["passed"] and not rf["passed"], "Known old-board defects were unexpectedly accepted"
    assert any(e["kind"]=="DC_inside_SMP_five_pad_envelope_clearance" for e in dc["failures"])
    drc_path=HERE.parent/"qd38_carrier_20261010/Native_DRC.html"
    text=drc_path.read_text(errors="replace")
    summary=re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>',text,re.S)
    summary=[dict(rule=html.unescape(re.sub("<[^>]+>","",name)),violations=int(count)) for name,count in summary]
    report=dict(status="HISTORICAL_DEFECT_DETECTION_CHECK_ONLY",source_sha256=FROZEN,
                DC_failures_by_kind=dict(collections.Counter(e["kind"] for e in dc["failures"])),
                RF_failures_by_kind=dict(collections.Counter(e["kind"] for e in rf["failures"])),
                historical_DRC_clearance_rows=[r for r in summary if "Clearance" in r["rule"]],
                limitation="Ground regions deliberately not loaded for this helper smoke check; full saved revision audit supplies them. No new candidate/native pass is asserted.")
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
