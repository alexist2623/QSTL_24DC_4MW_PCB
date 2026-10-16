"""Read-only check that canonical Top library pads place correctly on Bottom.

The library stores the unrotated Bottom footprint mirrored onto Top. Native Q1
is Bottom, rotation +90 degrees. Applying the Bottom mirror and this rotation
must reproduce every actual planned absolute bonding-pad centre and angle.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--library",type=Path,default=HERE/"schematic_staging/QD4_2SET_38.PcbLib")
    args=parser.parse_args();candidate=args.candidate.resolve();library=args.library.resolve()
    plan=json.loads(candidate.read_text());initial=sha(library);errors=[];checks=[]
    spec=importlib.util.spec_from_file_location("canonical_native_helpers",ROOT/"script/_support/qd_center_revision/native_metadata_helpers.py")
    nh=importlib.util.module_from_spec(spec);spec.loader.exec_module(nh)
    with nh.olefile.OleFileIO(library) as source:data=source.openstream("QD4_2SET_38/Data").read()
    offset=4+struct.unpack_from("<I",data)[0];rows=[]
    while offset<len(data):
        record=nh.pad_record(data,offset);blocks=record["blocks"];body=blocks[4]
        pin=blocks[0][1:1+blocks[0][0]].decode("ascii")
        x,y,sx,sy=struct.unpack_from("<4i",body,13)
        rows.append(dict(pin=pin,x=x*nh.UNIT,y=y*nh.UNIT,sx=sx*nh.UNIT,sy=sy*nh.UNIT,rotation=struct.unpack_from("<d",body,52)[0],layer=body[0]))
        # Record readers expose the byte following their final block.
        offset=record["end"]
    q1=next(c for c in plan["components"] if c["ref"]=="Q1")
    assert q1["layer"]==32 and abs(q1["rotation"]-90)<1e-8
    actual={p["pin"]:p for p in plan["physical_pads"] if p["ref"]=="Q1"}
    if {p["pin"] for p in rows}!=set(actual) or len(rows)!=38:errors.append("Library Q1 pin set/count differs")
    for p in rows:
        if p["pin"] not in actual:continue
        target=actual[p["pin"]]
        # Mirror Top-X for Bottom placement, then rotate CCW by +90 degrees.
        placed=[q1["x"]-p["y"],q1["y"]-p["x"]]
        angle=(q1["rotation"]-p["rotation"])%360
        da=abs((angle-target["rotation"]+180)%360-180)
        # A rectangular pad's long axis is invariant under 180-degree rotation.
        da=min(da,abs(da-180))
        item=dict(pin=p["pin"],placed_center_mm=placed,centre_error_mm=math.dist(placed,[target["x"],target["y"]]),axis_error_deg=da,
                  size_error_mm=max(abs(p["sx"]-target["sx"]),abs(p["sy"]-target["sy"])),top_library_layer=p["layer"]==1)
        item["passed"]=item["centre_error_mm"]<1e-5 and da<1e-7 and item["size_error_mm"]<1e-5 and item["top_library_layer"]
        checks.append(item)
        if not item["passed"]:errors.append(item)
    if sha(library)!=initial:errors.append("Library changed during audit")
    report=dict(passed=not errors,candidate_sha256=sha(candidate),library_file=str(library),library_sha256=initial,
                pad_count=len(rows),Q1_rotation_deg=q1["rotation"],errors=errors,checks=checks,
                scope="Library pad geometry and canonical Bottom/+90 placement only; native footprint update and copper connectivity are separate checks.")
    (HERE/"canonical_library_audit.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if errors:raise SystemExit(1)


if __name__=="__main__":main()
