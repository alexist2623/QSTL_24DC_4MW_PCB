"""Adapt the physical connectivity audit to layer-limited RF shield vias."""
from pathlib import Path
H=Path(__file__).resolve().parent;PREV=H.parent/'rf_six_inward_20260920'
s=(PREV/'audit_connectivity.py').read_text()
s=s.replace("PREV=H;P=", "PREV=H.parent/'rf_six_inward_20260920';P=")
start=s.index("if not (H/(B+'.PcbDoc')).exists():")
end=s.index(';s=snapshot(source)',start)
s=s[:start]+"source=P/(B+'.PcbDoc')"+s[end:]
s=s.replace(" assert (v['body'][29],v['body'][30])==(1,32),'Unexpected via layer span'\n insert(v['net'],'via:'+str(v['index']),layers,", " span=tuple(sorted((v['body'][29],v['body'][30])))\n assert span==((5,32) if v['net']=='GND' else (1,32)),('Unexpected via layer span',v['net'],span)\n insert(v['net'],'via:'+str(v['index']),({5,32} if v['net']=='GND' else layers),")
s=s.replace('via_spans_top_to_bottom=len(vs)',"via_spans_top_to_bottom=sum(v['net']!='GND' for v in vs),via_spans_L5_L6=sum(v['net']=='GND' for v in vs)")
s=s.replace("including through-via spans", "including explicit through and L5-L6 blind-via spans")
s=s.replace("name='after.json' if '--after' in sys.argv else 'before.json'", "name='connectivity.json'")
s=s[:s.index("if '--after' in sys.argv:")]+"assert report['passed']\n(P/'docs/connection_validation.json').write_text(json.dumps(report,indent=2)+'\\n')\n"
(H/'audit_connectivity.py').write_text(s,encoding='utf-8')
s=(H.parent/'mask_ground_20260920/ReopenAudit.pas').read_text().replace('mask_ground_reopen_check.txt','rf50_reopen_check.txt').replace('Mask_Ground_DRC.html','RF50_HDI_DRC.html')
(H/'ReopenAudit.pas').write_text(s,encoding='ascii')
s=(H.parent/'mask_ground_20260920/AuditPaste.pas').read_text().replace('mask_ground_20260920','rf50_hdi_milling_20260920')
(H/'AuditPaste.pas').write_text(s,encoding='ascii')
print('Prepared saved-board audit scripts')
