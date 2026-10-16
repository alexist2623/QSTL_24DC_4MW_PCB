"""Publish the staged revision documentation only after final completion."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    a=json.loads((H/'alignment_completion_audit.json').read_text())
    assert a['passed'] and a['completion']
    assert sha(DEST/(DEST.name+'.PcbDoc'))==a['native_sha256']
    text=(H/'README_alignment_draft.md').read_text()
    paragraphs=text.split('\n\n')
    assert paragraphs[1].startswith('Revision status:')
    paragraphs[1]=f"Revision status: 2026-10-11, QD pad-end alignment correction. **Applied to the native PCB and canonical library, saved, reopened and verified. All 38 DC channels and 16 RF bias tees remain connected; stored connections are zero. Full Altium DRC reports zero violations across 23 rule instances.** Native PCB SHA256: `{a['native_sha256']}`. The [final completion audit](../script/qd38_pad_alignment_20261011/alignment_completion_audit.json) binds the saved copper, schematic, library, stack, rules, surfaces, models, paste CAM and comparison images."
    text='\n\n'.join(paragraphs)
    text=text.replace('The current offline [alignment_full_candidate.json]', 'The verified [alignment_full_candidate.json]')
    text=text.replace('## Current verification and pending native checks','## Completed verification')
    text=text.replace('The following offline reports bind to this correction:', 'The following geometric reports bind to this correction:')
    pending=re.search(r'\*\*Pending for final native SHA256.*?\n\n',text,re.S)
    assert pending
    verified="""Saved-native results also pass:

- [Saved copper and schematic correspondence](../script/qd38_pad_alignment_20261011/saved_revision_audit.json): 50 components, 243 pads, 585 signal tracks, 66 Bottom RF arcs and 744 vias; zero stored connections; all DC nets remain on one internal layer and RF has no signal vias.
- [Canonical library](../script/qd38_pad_alignment_20261011/canonical_library_audit.json) and [local alignment delta](../script/qd38_pad_alignment_20261011/saved_alignment_delta.json): pad sizes, bond angles, terminal identities and net mapping retained, with common inward supporting lines. Only library XY fields changed; other library bytes and GUIDs are unchanged.
- [Saved rules](../script/qd38_pad_alignment_20261011/saved_alignment_rules.json), [surfaces](../script/qd38_pad_alignment_20261011/saved_revision_surface.json) and [models](../script/qd38_pad_alignment_20261011/saved_revision_models.json): only the three QD-via diameter fields changed in the rules; masks, shields, model transforms and stack are preserved.
- [Complete native DRC](../script/qd38_pad_alignment_20261011/Native_DRC.html): 23 rule instances, zero violations. Live compiled membership matches; the UI reported "Compile successful, no errors found" while the compiler API still returned False with zero reported violations.
- [Effective paste CAM](../script/qd38_pad_alignment_20261011/revision_native_paste_cam_validation.json): 53 Top and 64 Bottom ordinary SMD apertures, with no extra via/SMP/mount/QD paste.
- [Actual saved pad comparison](review/QD_pad_end_alignment_before_after.png), [aligned QD close-up](review/QD_pad_end_alignment.png), [current DC](review/DC_saved_two_layers.png) and [current RF](review/RF_saved_bottom.png).

The first save retained 751 connection-display records despite independently connected physical copper and zero unrouted DRC violations. This evidence is preserved under [first_save_connection_cache](../script/qd38_pad_alignment_20261011/first_save_connection_cache/). Rebuilding every existing net with Altium's native Rebuild operation, followed by fresh save/reopen and DRC, produced zero stored records. No connection objects were manually deleted and no rule was disabled.

"""
    text=text[:pending.start()]+verified+text[pending.end():]
    assert 'PENDING_FINAL_NATIVE_SHA256' not in text
    text=text.replace('Effective Top/Bottom paste CAM must be regenerated and checked for the final saved hash.', 'Fresh effective Top/Bottom paste CAM has been checked against the final saved hash.')
    (DEST/'README.md').write_text(text,encoding='utf-8')
    req=ROOT/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md'
    r=req.read_text(encoding='utf-8-sig')
    r=r.replace('Alignment implementation under verification (2026-10-11):', 'Verified alignment implementation (2026-10-11):')
    r=r.replace('These are implementation choices pending saved-native validation, not a manufacturing release or a change to the specified bond-pad dimensions.', 'Saved-native validation passes for this correction: common inward supporting lines, zero stored connections, 23 native DRC rule instances with zero violations, and fresh effective paste CAM. These implementation choices do not change the specified bond-pad dimensions and do not constitute a manufacturing release.')
    req.write_text(r,encoding='utf-8')
    (H/'documentation_publication.json').write_text(json.dumps(dict(completion_audit_sha256=sha(H/'alignment_completion_audit.json'),native_sha256=a['native_sha256'],readme_sha256=sha(DEST/'README.md'),requirements_sha256=sha(req)),indent=2)+'\n')
    print('Published verified alignment README and requirements record.')
if __name__=='__main__':main()
