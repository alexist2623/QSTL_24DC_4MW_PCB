from pathlib import Path
import json
h=Path(__file__).resolve().parent
p=json.loads((h.parents[1]/'QSTL_QD4_2SET_38PAD/circuit_plan.json').read_text())
for v in p['vias']:
    v['assigned_dc_layer']=v['high'] if v['label'].startswith('J1-') else v['low']
    v['low']=1;v['high']=32
(h/'through_dc_input.json').write_text(json.dumps(p,indent=2))
s=(h/'route_dc_flow.py').read_text()
s=s.replace("v['low'] == layer]", "v['assigned_dc_layer'] == layer]")
s=s.replace("v['high'] == layer]", "v['assigned_dc_layer'] == layer]")
s=s.replace("(DEST/'circuit_plan.json')", "(H/'through_dc_input.json')")
s=s.replace("(H/f'flow_L", "(H/f'through_dc_flow_L")
s=s.replace("(DEST/'dc_flow_candidate.json')", "(H/f'through_dc_candidate_{STEP}_{OFFSET_X}_{OFFSET_Y}.json')")
(h/'through_dc_flow.py').write_text(s)
