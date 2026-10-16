"""Draw the 12-RF reference width without rearranging the 16-RF proposal."""
import json
from pathlib import Path

from width23_outline_plan import (
    ROOT, SOURCES, PLAN, RC, ROD, sha, board, rod_width, plt,
)

OUT = ROOT / 'QSTL_QD4_2SET_38PAD/Width32p6_Outline_Plan_20261015'
WIDTH = 32.6
LENGTH = 77.5
CENTRE = 9.75


def state(data, groups, snapshot):
    return json.dumps(dict(rows=data['rows'], pads=data['pads'],
                           mounts=data['mounts'], paths=data['paths'],
                           groups=groups, snapshot=snapshot), sort_keys=True)


def preview(ax, data, groups, snapshot, width, zoom=False):
    board(ax, data, groups, snapshot, width, zoom=zoom)
    resistor_pads = [(p['x'], p['y']) for g in groups
                     for p in g['resistor_component']['pads']]
    for label in list(ax.texts):
        if label.get_text() in ('1', '2') and label.get_position() in resistor_pads:
            label.remove()
    if zoom:
        ax.set_ylim(36.5, 59.0)
    # All comparison panels use the same X range; component coordinates are
    # copied directly from the existing proposal, without translation.
    ax.set_xlim(-9.05, 28.55)
    if width == WIDTH:
        for x in (CENTRE - 11.5, CENTRE + 11.5):
            ax.plot([x, x], [0, LENGTH], color='#a35ca3', ls=':', lw=1, zorder=3)
    if not zoom:
        ax.set_title('Previous 23.00 mm plan' if width == 23 else
                     '32.60 mm reference-width plan', fontsize=12, pad=12)


def main():
    OUT.mkdir(exist_ok=True)
    sizes = json.loads(ROD.read_text())
    reference = Path(sizes['reference']['source'])
    rod = sizes['henning_rod']
    assert sha(reference) == sizes['reference']['sha256']
    assert sha(Path(rod['source'])) == rod['sha256']
    assert abs(sizes['reference']['width_mm'] - WIDTH) < 1e-5
    assert sizes['reference_gerber']['width_mm'] == WIDTH
    native = ROOT / 'QSTL_QD4_2SET_38PAD'
    protect = [PLAN, RC, ROD, reference, Path(rod['source']), SOURCES['snapshot']]
    protect += [native / n for n in (
        'QSTL_QD4_2SET_38PAD.PcbDoc', 'QSTL_QD4_2SET_38PAD.SchDoc',
        'QD4_2SET_38.PcbLib', 'pin_mapping.csv')]
    hashes = {str(p): sha(p) for p in protect}
    data = json.loads(PLAN.read_text())
    groups = json.loads(RC.read_text())['groups']
    snapshot = json.loads(SOURCES['snapshot'].read_text())
    before = state(data, groups, snapshot)

    fig = plt.figure(figsize=(14, 13), dpi=210)
    gs = fig.add_gridspec(2, 3, width_ratios=(1, 1, 1.25),
                         height_ratios=(1, .8), left=.045, right=.97,
                         top=.88, bottom=.13, wspace=.23, hspace=.25)
    old = fig.add_subplot(gs[:, 0])
    new = fig.add_subplot(gs[:, 1])
    detail = fig.add_subplot(gs[0, 2])
    rail = fig.add_subplot(gs[1, 2])
    preview(old, data, groups, snapshot, 23.)
    preview(new, data, groups, snapshot, WIDTH)
    preview(detail, data, groups, snapshot, WIDTH, zoom=True)
    rod_width(rail, rod, WIDTH)
    fig.suptitle('Match the 12-RF PCB width: 32.60 mm', fontsize=19, y=.975)
    fig.text(.5, .936,
             '23.00 -> 32.60 mm | Add 4.80 mm on each side | Keep proposed length 77.50 mm',
             ha='center', fontsize=11)
    fig.text(.5, .908,
             'All 16 SMPs, QD, ZIF, mounting holes and four trial R/C pairs stay in place.',
             ha='center', fontsize=11)
    fig.text(.5, .091,
             'Green: area beyond the original 19.50 mm width. Grey dashed: 19.50 mm. Purple dotted: 23.00 mm.',
             ha='center', fontsize=10)
    fig.text(.5, .063,
             'Reference Sample_Holder: 32.60 x 107.10 mm. Only its width is adopted here; routing is not changed.',
             ha='center', fontsize=10)
    fig.text(.5, .034,
             'PLAN ONLY: native PCB/CAD unchanged. Rail-width clearance does not resolve the known carrier/mounting conflicts.',
             ha='center', fontsize=9.5, color='#9b5038')
    fig.savefig(OUT / 'PCB_32p6mm_No_Rearrangement_Plan.png')
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 13), dpi=220)
    preview(ax, data, groups, snapshot, WIDTH)
    ax.set_title('32.60 x 77.50 mm proposal\nExisting placements retained', fontsize=15, pad=15)
    fig.text(.5, .050, 'Width matches Carrier_12MW_72DC / Sample_Holder',
             ha='center', fontsize=10)
    fig.text(.5, .028, '+4.80 mm per side from the 23 mm plan | Native PCB unchanged',
             ha='center', fontsize=10)
    fig.tight_layout(rect=(0, .075, 1, .985))
    fig.savefig(OUT / 'PCB_32p6mm_Enlarged.png')
    plt.close(fig)

    assert before == state(data, groups, snapshot)
    assert hashes == {str(p): sha(p) for p in protect}
    audit = dict(
        status='WIDTH32P6_OUTLINE_ONLY_NOT_APPLIED',
        reference_source=str(reference), reference_width_mm=WIDTH,
        reference_length_mm=107.1, previous_proposed_width_mm=23.,
        new_proposed_width_mm=WIDTH, retained_proposed_length_mm=LENGTH,
        fixed_x_centreline_mm=CENTRE,
        new_x_limits_mm=[round(CENTRE-WIDTH/2, 2), round(CENTRE+WIDTH/2, 2)],
        added_each_side_from_23mm=4.8, added_each_side_from_19p5mm=6.55,
        all_positions_and_path_samples_unchanged=True,
        retained_counts=dict(SMP=16, QD_pads=38, mounts=len(data['mounts']), trial_RC_pairs=4),
        rod_inside_width_mm=39., centred_PCB_to_rail_clearance_each_side_mm=3.2,
        native_and_reference_files_unchanged=True, source_hashes=hashes,
        limitations=[
            'Unapplied outline proposal; native remains 19.5 x 67.9 mm.',
            'Only the four previously proposed central R/C pairs are shown.',
            'No new full RF/DC routing, DRC or mechanical assembly-fit claim.',
            'Known copper-carrier and mounting conflicts remain unresolved.'])
    (OUT / 'width32p6_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    (OUT / 'README.md').write_text(
        '# 32.60 mm width-only proposal\n\n'
        'Match the measured 12-RF Sample_Holder reference width. Keep the existing '
        '77.50 mm planning length and all proposed component/pad/hole coordinates. '
        'The reference itself is 32.60 x 107.10 mm; its length is not adopted.\n\n'
        'The new X limits are -6.55..26.05 mm, centred at X=9.75 mm. '
        'This adds 4.80 mm per side relative to the preceding 23.00 mm picture. '
        'Centred in the Henning rod\'s 39.00 mm inner width, side clearance is 3.20 mm.\n\n'
        '[Comparison](PCB_32p6mm_No_Rearrangement_Plan.png) | '
        '[Enlarged view](PCB_32p6mm_Enlarged.png) | [Audit](width32p6_audit.json)\n\n'
        'Native PCB/CAD and references remain unchanged. This picture does not '
        'resolve the previously recorded copper-carrier mounting conflicts or '
        'validate full routing or the remaining twelve R/C pairs.\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k!='source_hashes'}, indent=2))


if __name__ == '__main__':
    main()
