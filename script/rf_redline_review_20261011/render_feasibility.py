"""Read-only illustration of saved geometry and the redline routing constraints."""
import hashlib
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'script/qd38_pad_alignment_20261011'
PCB = ROOT / 'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
native = json.loads((BASE / 'saved_revision_snapshot.json').read_text())
plan = json.loads((BASE / 'alignment_full_candidate.json').read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(PCB) == native['source_sha256']
spec = importlib.util.spec_from_file_location('saved_renderer', ROOT / 'script/qd38_rotation_20261011/render_saved_revision_review.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

fig = plt.figure(figsize=(12, 12), dpi=180)
gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 1], wspace=.18)
ax = fig.add_subplot(gs[0])
renderer.draw(ax, native, plan, 32, (22, 64), 'Current saved Bottom geometry', '#87979a')
for x in (7.30, 10.25):
    for y, height in ((49, 9), (27, 9)):
        ax.add_patch(Rectangle((x, y), 1.95, height, facecolor='#2bceaa', alpha=.20,
                               edgecolor='#47efd1', linewidth=1.1))
for ref in ('R09', 'R31', 'R12', 'R28'):
    shapes = [renderer.pad_shape(p) for p in native['pads'] if p['component'] == ref]
    renderer.polygon(ax, unary_union(shapes).convex_hull, '#f57555', .45, '#ffb09a')
ax.annotate('1.95 mm projected lane', xy=(8.275, 53.2), xytext=(.4, 56), color='white',
            fontsize=8, arrowprops={'arrowstyle': '->', 'color': 'white'})
ax.annotate('Resistor body envelopes', xy=(7, 47.4), xytext=(.4, 50.6), color='#ffccbb',
            fontsize=8, arrowprops={'arrowstyle': '->', 'color': '#ffccbb'})
ax.annotate('Resistor body envelopes', xy=(12.4, 37.4), xytext=(9.8, 34.7), color='#ffccbb',
            fontsize=8, arrowprops={'arrowstyle': '->', 'color': '#ffccbb'})
text_ax = fig.add_subplot(gs[1]); text_ax.axis('off')
notes = [
    (.98, 'REDLINE FEASIBILITY REVIEW', 15, 'bold'),
    (.92, 'Inboard routing is a reasonable redesign direction.\nNo forced crossing in the proposed channel order.\nAll 16 physical routes are not yet solved or verified.', 11, 'normal'),
    (.78, '1  Reassign RF channels', 12, 'bold'),
    (.74, 'Current examples: SMP02 -> QD12; SMP05 -> QD11.\nThose upper connectors target lower-side pads.\nReorder channels by position around the QD.\nKeep PCB, schematic and bias-tee DC nets synchronized.', 10, 'normal'),
    (.60, '2  Clear the local R/C bottlenecks', 12, 'bold'),
    (.56, 'Orange areas are complete resistor envelopes.\nDo not route through the two-pad/body gap.\nRotate, relocate or route around the affected R/C pairs.\nThe upper/lower R-to-QD pad gaps are about 0.81 mm.', 10, 'normal'),
    (.42, '3  Reserve room for ground shielding', 12, 'bold'),
    (.38, 'Green bands illustrate 1.95 mm projected X corridors.\nThey are not certified obstacle-free routing channels.\nA complete nominal two-sided via fence spans 1.12 mm\nfor ONE RF trace, before clearance to nearby signals.\nRebuild shields and mask after the RF paths are chosen.', 10, 'normal'),
    (.21, 'Retained requirements', 12, 'bold'),
    (.17, 'Bottom RF only; 0.11 mm width; tangent curves.\nNo RF signal vias. Retain the 0.20 mm GND gap.\nPreserve the blind cavity and all 38 independent DC nets.', 10, 'normal'),
    (.06, 'Read-only review. No native PCB changes.\nEmpty red circles in the supplied sketch remain ambiguous.', 10, 'normal'),
]
for y, label, size, weight in notes:
    text_ax.text(0, y, label, fontsize=size, fontweight=weight, va='top', linespacing=1.5,
                 color='#16232c', transform=text_ax.transAxes)
fig.suptitle('RF routing review: shorter paths toward the QD', fontsize=16, y=.985)
fig.subplots_adjust(top=.94, bottom=.065, left=.06, right=.98)
out = HERE / 'RF_inboard_feasibility_review.png'
fig.savefig(out, facecolor='white'); plt.close(fig)
assert digest(PCB) == native['source_sha256']
report = {
    'status': 'READ_ONLY_CONDITIONAL_FEASIBILITY_REVIEW',
    'native_sha256': native['source_sha256'],
    'candidate_sha256': digest(BASE / 'alignment_full_candidate.json'),
    'native_changed': False,
    'full_routing_or_DRC_verified': False,
    'proposed_group_to_QD_mapping_for_topological_review_only': {str(k): k for k in (2,5,9,11,12,13,15,16,21,24,28,30,31,32,34,35)},
    'interpretation': 'Inboard RF paths; empty red circles do not establish connector relocation without clarification.',
    'required_followup_for_implementation': ['Solve all 16 RF routes jointly with R/C placement', 'Synchronize schematic and DC bias assignment', 'Regenerate local ground shields and solder mask', 'Check saved copper and native DRC after reopen'],
    'figure': str(out), 'figure_sha256': digest(out),
}
(HERE / 'feasibility_review.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
