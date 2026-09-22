"""Independently inspect exported solids, hole counts, locations, and clearances."""
from pathlib import Path
import hashlib
import json
import math
import sys
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read,inspect,bounds,volume

OUT=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'/'Probe_H_Frame'
shape=read(OUT/'Probe_H_Frame.step')
assert all(abs(a-b)<1e-5 for a,b in zip(bounds(shape),[0,0,0,51,360,6]))
explorer=TopExp_Explorer(shape,TopAbs_SOLID)
solids=[]
while explorer.More():
    solids.append(explorer.Current());explorer.Next()
assert len(solids)==4
reports=[]
expected_bounds=[[0,0,0,6,360,6],[45,0,0,51,360,6],[6,246,0,45,254,6],[6,86,0,45,94,6]]
for solid,expected in zip(solids,expected_bounds):
    data=inspect(solid)
    assert data['valid']
    assert max(abs(a-b) for a,b in zip(data['bounds'],expected))<1e-5
    rod=expected[4]-expected[1]>300
    assert len(data['cylinders'])==(33 if rod else 0)
    if rod:
        centres=sorted(round(c['point'][1],5) for c in data['cylinders'])
        assert centres==list(range(10,331,10))
        assert all(abs(c['radius']-1.5)<1e-5 for c in data['cylinders'])
        expected_volume=6*360*6-33*math.pi*1.5**2*6
    else:
        expected_volume=39*8*6
    assert abs(data['volume']-expected_volume)<1e-4
    reports.append(dict(bounds_mm=data['bounds'],valid=True,hole_count=len(data['cylinders']),volume_mm3=data['volume']))
for i,a in enumerate(solids):
    for b in solids[i+1:]:
        assert abs(volume(BRepAlgoAPI_Common(a,b).Shape()))<1e-5
pcb=ROOT/'QSTL_24DC_4MW_PCB'/'QSTL_24DC_4MW_PCB.PcbDoc'
assert hashlib.sha256(pcb.read_bytes()).hexdigest()=='84feed018fbaf5cbfa3203201c8771711b00ffec18aa0aadaf20fdeadb99ca63'
result=dict(overall_dimensions_mm=[51,360,6],solid_count=4,total_simplified_M3_holes=66,positive_volume_interferences=0,source_pcb_unchanged=True,solids=reports)
(OUT/'geometry_verification.json').write_text(json.dumps(result,indent=2))
print('PASS: 4 valid solids; 51 x 360 x 6 mm; 33 holes per rod; 10 mm pitch; no solid overlaps.')
