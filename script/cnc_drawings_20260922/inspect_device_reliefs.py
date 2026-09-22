"""Measure the device lips in the current central plate coordinate system."""
from pathlib import Path
import sys, json
import numpy as np
from OCP.gp import gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'script/mechanical_assembly_20260921'))
from inspect_geometry import read, inspect
MODEL = ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
records = json.loads((MODEL/'inward_placements.json').read_text(encoding='utf-8-sig'))
def matrix(record):
    m=np.array(record['matrix_cm']);m[:3,3]*=10;return m
carrier=next(r for r in records if r['name']=='Existing_Carrier_Hung_From_Side_Slots')
plate=next(r for r in records if r['name']=='Centre_Plate_With_Device_Boss')
m=np.linalg.inv(matrix(plate))@matrix(carrier)
t=gp_Trsf();t.SetValues(*m[:3,:].ravel().tolist())
shape=BRepBuilderAPI_Transform(read(Path(carrier['path']).with_suffix('.step')),t,True).Shape()
data=inspect(shape)
planes=[p for p in data['planes'] if abs(p['normal'][2])>.99 and abs(p['point'][2]-4)<.02]
adjacent=[p for p in data['planes'] if abs(p['normal'][0])>.99 and p['bounds'][2]<4.02 and p['bounds'][5]>4.1]
result={'device_in_plate_bounds':data['bounds'],'deck_contact_faces':planes,'adjacent_vertical_faces':adjacent}
result['right_side_faces']=[p for p in data['planes'] if p['bounds'][0]>31 and p['bounds'][2]<10.5]
(Path(__file__).parent/'tmp/device_lip_measurement.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
