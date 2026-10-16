"""Refresh DC/RF review views from the verified saved alignment revision.

Reuse the existing rendering functions without executing their old-folder
main routine or changing the old audit evidence. All displayed pads, routes,
arcs and via coordinates are read from the new saved native snapshot.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
PROJECT=ROOT/'QSTL_QD4_2SET_38PAD'
BASE_SHA='1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--after-snapshot',required=True,type=Path)
    ap.add_argument('--saved-audit',required=True,type=Path)
    ap.add_argument('--candidate',required=True,type=Path)
    ap.add_argument('--native',type=Path,default=PROJECT/'QSTL_QD4_2SET_38PAD.PcbDoc')
    args=ap.parse_args();native_hash=sha(args.native)
    audit=json.loads(args.saved_audit.read_text());native=json.loads(args.after_snapshot.read_text());plan=json.loads(args.candidate.read_text())
    assert native_hash!=BASE_SHA and audit['passed'] is True and not audit.get('errors',[])
    assert audit['native_sha256']==native_hash==native['source_sha256']
    assert audit['candidate_sha256']==sha(args.candidate)
    renderer_path=H.parent/'qd38_rotation_20261011/render_saved_revision_review.py'
    spec=importlib.util.spec_from_file_location('previous_saved_copper_renderer',renderer_path)
    render=importlib.util.module_from_spec(spec);spec.loader.exec_module(render)
    # The old renderer accepts plan-shaped via/component dictionaries.
    # Supply actual native coordinates so this image never silently falls
    # back to theoretical candidate via XY after save/reopen normalization.
    display=copy.deepcopy(plan)
    display['vias']=[copy.deepcopy(v) for v in native['vias'] if v['net']!='GND']
    display['shield_vias']=[copy.deepcopy(v) for v in native['vias'] if v['net']=='GND']
    assert len(display['vias'])==76 and len(display['shield_vias'])==len(plan['shield_vias'])
    display['components']=[dict(ref=c['designator'],x=c['x'],y=c['y']) for c in native['components']]
    out=PROJECT/'review';out.mkdir(exist_ok=True)
    dc_path=out/'DC_saved_two_layers.png';rf_path=out/'RF_saved_bottom.png'
    fig,axes=plt.subplots(1,2,figsize=(9,14),dpi=180)
    for ax,layer,color in zip(axes,(2,4),('#f7b36c','#66d3ea')):
        count=len({t['net'] for t in native['tracks'] if (t['net'] or '').startswith('DC') and t['layer']==layer})
        render.draw(ax,native,display,layer,(-.5,68.4),f'L{layer} DC — {count} channels',color)
    fig.suptitle('Saved 38-channel DC routing\nAligned QD pads · 0.125 mm width · 0.10 mm DC pair rule',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(dc_path);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,14),dpi=180)
    render.draw(ax,native,display,32,(22,64),'Saved Bottom RF — tangent arcs, no RF signal vias','#edb95c')
    fig.tight_layout();fig.savefig(rf_path);plt.close(fig)
    assert sha(args.native)==native_hash,'Native document changed during rendering'
    files=[dict(path=str(dc_path),sha256=sha(dc_path),view='dc_routing'),dict(path=str(rf_path),sha256=sha(rf_path),view='rf_routing')]
    manifest=dict(native_sha256=native_hash,candidate_sha256=sha(args.candidate),
                  snapshot_sha256=sha(args.after_snapshot),saved_audit_sha256=sha(args.saved_audit),
                  source='Saved native copper snapshot, including actual native pad/track/arc/via geometry',files=files)
    (out/'image_sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (H/'saved_alignment_routes_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    review_path=H/'alignment_review_images.json'
    review=dict(native_sha256=native_hash,candidate_sha256=sha(args.candidate),images=files)
    if review_path.exists():
        old=json.loads(review_path.read_text())
        if old.get('native_sha256')==native_hash and old.get('candidate_sha256')==review['candidate_sha256']:
            review['images']=[x for x in old.get('images',[]) if x.get('view') not in ('dc_routing','rf_routing')]+files
    review_path.write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
