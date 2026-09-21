"""Regenerate local shielding after verifying the saved movement geometry."""
from pathlib import Path
H=Path(__file__).resolve().parent
template=(H.parent/'rc_mask_clearance_20260921/prepare_shields.py').read_text()
template=template.split("for name in ('audit_connectivity.py'")[0]
template=template.replace("len(n['vias'])==60","len(n['vias'])==48")
template=template.replace("source=P/(B+'.PcbDoc');", "original_arckey=arckey\ndef arckey(a):\n    k=original_arckey(a);return k[:-2]+(k[-2]%360,k[-1]%360)\nsource=P/(B+'.PcbDoc');")
template=template.replace("prefix=prefix.replace('OFFSET=.51'","prefix=prefix.replace('len(signals_v)==60','len(signals_v)==48')\nprefix=prefix.replace('OFFSET=.51'")
exec(compile(template,'validated_shield_generator','exec'))
print('Prepared',len(vias),'L5-L6 GND shields.')
