from pathlib import Path
h=Path(__file__).resolve().parent
s=(h/'apply_dc_flow.py').read_text()
s=s.replace('from design_geometry import DEST','from design_geometry import H')
s=s.replace("(DEST / 'circuit_plan.json')", "(H/'through_dc_input.json')")
s=s.replace("(DEST / 'dc_flow_candidate.json')", "(H/'through_dc_candidate_0.28_0.1_0.02.json')")
s=s.replace("(DEST/'circuit_plan.json')", "(H/'through_dc_plan_passed.json')")
s=s.replace("(DEST/'pin_mapping.csv')", "(H/'through_dc_pin_mapping.csv')")
(h/'through_dc_apply.py').write_text(s)
