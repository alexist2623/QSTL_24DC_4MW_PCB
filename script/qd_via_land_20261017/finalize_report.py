"""Publish the verified QD via reduction and native capacitor model correction."""
from pathlib import Path
import hashlib,json,re,sys,shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PatchPolygon,Circle

H=Path(__file__).resolve().parent;ROOT=H.parents[1]
P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'QD_Via_and_Cap_Models_20261017'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pcb=P/(P.name+'.PcbDoc');digest=sha(pcb)
evidence={}
for name in ('change_audit.json','saved_native_audit.json','support_audit.json','mask_cam_audit.json'):
    r=json.loads((H/name).read_text());assert r['passed'],name
    assert (r['source_sha256'] if 'source_sha256' in r else r['checks']['native_sha256'])==digest,name
    evidence[name]=dict(passed=True,sha256=sha(H/name))
change=json.loads((H/'change_audit.json').read_text())
prep=json.loads((H/'preparation_audit.json').read_text())
drc=(H/'Native_DRC.html').read_text(encoding='utf-8')
count=int(re.search(r'Rule Violations:</td>.*?DRC_summary_header_col3[^>]*>(\d+)',drc,re.S)[1]);assert count==0
assert 'POST_DRC_SAVED_CONNECTION_COUNT=0' in (H/'native_validation.txt').read_text()
assert (H/'Native_DRC.html').stat().st_mtime>=(H/'CorrectCapModels_log.txt').stat().st_mtime
photos=['Altium_All_16_Cap_Models.png','Altium_Corrected_Cap_3D_Closeup.png']
for name in photos:assert (OUT/name).stat().st_size>10000
before=Path('C:/Users/MEASUR~1/AppData/Local/Temp/codex-clipboard-b2abb6da-4800-43cf-829e-f8ed30ed4501.png')
if before.exists():shutil.copy2(before,OUT/'User_Reported_Before.png')

# Show the exact worst remaining protrusion, using the saved native pad and via.
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot
sch=json.loads((P/'schematic_validation.json').read_text())
b=read_snapshot(pcb,sch)
worst=max(change['via_rows'],key=lambda r:r['protrusion_after_mm'])
pad=next(p for p in b[0] if p['ref']=='Q1' and p['pin']==worst['pad'])
row=next(r for r in prep['via_changes'] if r['label']=='Q1-'+worst['pad'])
v=next(v for v in b[3] if v['net']==row['net'] and abs(v['x']-row['x'])<1e-7 and abs(v['y']-row['y'])<1e-7)
fig,axs=plt.subplots(1,2,figsize=(10,6.4))
fig.subplots_adjust(top=.84,bottom=.25,left=.08,right=.98,wspace=.23)
pts=[(x-v['x'],y-v['y']) for x,y in pad['geometry'].exterior.coords]
for ax,d,title in zip(axs,[worst['land_before_mm'],v['diameter']],['Before: land 0.350 mm','Saved: land 0.300 mm']):
    ax.set_facecolor('#132a32')
    ax.add_patch(PatchPolygon(pts,closed=True,facecolor='#e8bd59',edgecolor='#f5d788',lw=1.2,label='Unchanged 0.260 mm bond pad'))
    ax.add_patch(Circle((0,0),d/2,facecolor='#f5d788',edgecolor='#fff1b0',lw=1,label='Via copper land'))
    ax.add_patch(Circle((0,0),v['hole']/2,facecolor='#132a32',edgecolor='#adc0c3',lw=1,label='Unchanged 0.200 mm drill'))
    ax.set(xlim=(-.36,.36),ylim=(-.36,.36),xlabel='X relative to via centre (mm)',ylabel='Y relative to via centre (mm)',title=title,aspect='equal')
    ax.grid(alpha=.15)
fig.suptitle(f"QD pad {worst['pad']}: reduced via land, unchanged pad and hole",fontsize=14,y=.97)
handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.025),ncol=1,frameon=False)
fig.savefig(OUT/'QD_Via_Land_Before_After.png',dpi=190);plt.close(fig)

table='\n'.join(f"| {r['ref']} | {r['model_Z_before_deg']:g} | {r['model_Z_after_deg']:g} |" for r in change['model_rows'] if r['changed'])
max_before=max(r['protrusion_before_mm'] for r in change['via_rows'])
max_after=max(r['protrusion_after_mm'] for r in change['via_rows'])
report=f'''# QD via lands and capacitor 3D registration

Saved native PCB SHA256: `{digest}`.

## Capacitor 3D correction

The eight tilted Bottom capacitors had the wrong sign of model Z rotation. Their actual 3D meshes were mirrored relative to their pad axes. The earlier model check used the cached 2D component-body outline; that outline did not describe the displayed mesh orientation and remained unchanged after the correction. The earlier conclusion that all bodies were aligned was therefore insufficient.

Only `MODEL.3D.ROTZ` changed on these eight component bodies:

| Reference | Previous Z rotation (degrees) | Corrected Z rotation (degrees) |
|---|---:|---:|
{table}

For the saved Bottom models, the projected long-axis direction is the negative of the stored Z rotation, modulo 180 degrees. All 16 capacitor axes now match their pad axes within 0.000051 degrees. Actual Altium 3D inspection confirmed the corrected tilted meshes after save/reopen, with all 16 capacitors visible in the final screenshot. The Yageo CC1206JKNPO9BN104 maximum body geometry (3.50 x 1.80 x 1.80 mm), embedded STEP hashes, origins and heights remain unchanged. No component, pad or route was moved.

- [Actual saved Altium 3D view, all 16 capacitors](Altium_All_16_Cap_Models.png)
- [Actual Altium 3D close-up of all eight tilted capacitors](Altium_Corrected_Cap_3D_Closeup.png)
- [User-supplied image before correction](User_Reported_Before.png)

These are native GUI screenshots, not regenerated illustrations. The orange object is Altium's on-screen navigation indicator.

## QD via copper lands

All 22 QD direct-DC terminal via lands were reduced from nominal 0.350 to **0.300 mm**. Their nominal 0.200 mm drills, XY positions, nets and L1-L6 span are unchanged. The other 1,568 vias are unchanged, including all 1,514 L5-L6 RF shield microvias. The 38 rectangular QD pads remain 0.260 mm wide.

The [JLCPCB via capability table](https://jlcpcb.com/capabilities/pcb-capabilities), checked on 2026-10-17, specifies at least 0.100 mm land-minus-hole diameter difference, corresponding to a 0.050 mm radial annular ring. This edit uses that minimum while preserving the existing drill. Native grid rounding is upward: saved land **0.30000194 mm**, drill **0.19999960 mm**, radial ring **0.05000117 mm**. The common diameter and all 32 native layer-diameter cells were checked.

The dedicated QD via-style rule's preferred/minimum/maximum land width was updated to the new diameter. Its drill fields, scopes, enabled state and priority were retained; the other 43 rules are unchanged. No genuine DRC failure was suppressed.

Maximum land protrusion beyond the rectangular pad decreased from **{max_before:.6f} to {max_after:.6f} mm**. Some protrusion remains because the 0.300 mm land is wider than the 0.260 mm pad and existing centres have offsets. See the [saved before/after detail](QD_Via_Land_Before_After.png) and [all 22 measured changes](QD_Via_Changes.csv).

## Saved validation

- Altium native save/reopen DRC: **0 violations**; stored connections: **0**.
- All **71 named nets** connected and matched to the compiled schematic; 15 unused ZIF contacts retained; enumerated compiler violations: **0**.
- **{len(change['checks'])}** bounded-change and geometry checks passed. Pad, track, arc, region, component and physical stack streams are byte-identical to the baseline. Schematic and canonical pin map hashes are unchanged.
- Minimum clearance from a reduced QD land to a foreign trace: **0.164387 mm**; foreign pad: **0.179268 mm**; foreign via: **0.205810 mm**; GND: **0.225274 mm**.
- Layer roles, one internal layer per DC net, RF routing without signal vias, all 32 L5 C/R openings and QD ground exclusions are retained.
- Restored **0.90 mm C/R solder-control margins**, compact Top via covers, RF/SMP/ZIF protection, normal pad openings and exposed mounting/QD bonding areas remain unchanged.
- Fresh native mask CAM agrees with the saved mask regions/openings within 0.0003 mm; all 22 Top QD vias are fully covered.
- Fresh native paste CAM has exactly 53 Top and 64 Bottom normal SMD apertures; no via/QD/SMP/mounting paste is present.

The native file remains a source document of the existing QD4_2SET_38PAD project. This update does not issue a new production Gerber package or update an order/cart. The minimum via geometry result is not a blanket fabrication approval for the whole board.

Audit evidence: [native DRC](../../script/qd_via_land_20261017/Native_DRC.html), [native connectivity](../../script/qd_via_land_20261017/saved_native_audit.json), [bounded changes](../../script/qd_via_land_20261017/change_audit.json), [support checks](../../script/qd_via_land_20261017/support_audit.json), [mask CAM](../../script/qd_via_land_20261017/mask_cam_audit.json).
'''
(OUT/'IMPLEMENTATION_REPORT.md').write_text(report,encoding='utf-8')
images={p.name:sha(p) for p in OUT.glob('*.png')}
status=dict(passed=True,PCB_sha256=digest,QD_vias_changed=22,nominal_land_mm=.3,nominal_hole_mm=.2,changed_cap_models=8,actual_Altium_3D_checked=True,DRC_violations=count,audits=evidence,images=images,report_sha256=sha(OUT/'IMPLEMENTATION_REPORT.md'))
(OUT/'final_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
req=ROOT/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md';s=req.read_text(encoding='utf-8');heading='## All sixteen R/C placement plan requested 2026-10-16\n\n'
bullet=f'- QD via reduction and capacitor 3D correction verified (2026-10-17): 22 QD direct-DC via lands are now nominal 0.300 mm with 0.200 mm drills (actual radial ring 0.05000117 mm); centres/nets/spans and all other vias are unchanged. Only the dedicated QD via rule land-width fields were updated; all other rule fields and 43 other rules remain. Corrected eight tilted capacitor model Z rotations for actual Bottom rendering, without moving footprints or changing embedded 1206 geometry. All 16 bodies were checked in native Altium 3D. Earlier cached-2D-outline alignment claims are superseded. The 0.90 mm C/R masks, all copper routes/pads/regions, schematic and mapping are preserved. Native save/reopen DRC 0, stored connections 0, 71 connected nets and fresh mask/paste CAM pass. Remaining via protrusion is at most {max_after:.6f} mm. Current PCB `{digest}`; [report](../../QSTL_QD4_2SET_38PAD/QD_Via_and_Cap_Models_20261017/IMPLEMENTATION_REPORT.md), [native 3D view](../../QSTL_QD4_2SET_38PAD/QD_Via_and_Cap_Models_20261017/Altium_All_16_Cap_Models.png). This supersedes earlier current-state hashes, 0.350 mm QD via lands and claims of correct capacitor model registration.\n'
s=re.sub(r'^- QD via reduction and capacitor 3D correction verified .*\n','',s,flags=re.M);assert heading in s;s=s.replace(heading,heading+bullet,1);req.write_text(s,encoding='utf-8')
readme=P/'README.md';s=readme.read_text(encoding='utf-8');start=s.index('The authoritative current PCB SHA256');end=s.index('\n\n',start)
s=s[:start]+f'The authoritative current PCB SHA256 is `{digest}`. The 22 QD direct-DC via lands are nominal 0.300 mm with unchanged 0.200 mm drills; only their dedicated via-style land-width rule fields changed. Eight tilted capacitor model Z rotations are corrected and all 16 bodies were checked in native Altium 3D. Copper footprints/routes, 0.260 mm QD pad widths, 0.90 mm C/R mask margins, 32 L5 openings, schematic and pin mapping remain unchanged. Native save/reopen DRC is zero; all 71 named nets and fresh mask/paste CAM pass. See the [current report](QD_Via_and_Cap_Models_20261017/IMPLEMENTATION_REPORT.md), [actual Altium 3D view](QD_Via_and_Cap_Models_20261017/Altium_All_16_Cap_Models.png) and [audit manifest](QD_Via_and_Cap_Models_20261017/final_status.json). Via lands still protrude by at most 0.049100 mm. No new production Gerber is issued.'+s[end:];readme.write_text(s,encoding='utf-8')
assert sha(pcb)==digest
print(json.dumps(dict(passed=True,PCB_sha256=digest,DRC_violations=count,report=str(OUT/'IMPLEMENTATION_REPORT.md')),indent=2))
