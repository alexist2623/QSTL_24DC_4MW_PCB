"""Verify the deliberately retained mask family against its saved baseline."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys

import olefile
from shapely.geometry import box, shape
from shapely.ops import unary_union

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
sys.path.insert(0, str(ROOT / 'script/_support/qd_center_revision'))
from native_metadata_helpers import binary_records

BASE_NATIVE = '1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
BASE_PLAN = '835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def retained_mask_field(plan, pads, regions, native_path):
    """Return the approved field, never a newly generated smaller opening.

    Pad openings are additionally covered by the native cache/paste audits.
    Here every explicit mask-region record must remain byte-identical, and
    the retained field must contain the new pad bounding field plus cavity.
    """
    baseline = H / 'before_alignment/QSTL_QD4_2SET_38PAD.PcbDoc'
    bp = H / 'before_alignment/full_copper_candidate.json'
    assert sha(baseline) == BASE_NATIVE and sha(bp) == BASE_PLAN
    old = json.loads(bp.read_text())
    errors = []
    frozen_fields = ('solder_openings', 'qd_mask_field', 'rc_mask_rectangles',
                     'zif_bottom_mask_rectangle', 'pad_solder_mask_overrides')
    for key in frozen_fields:
        if plan[key] != old[key]:
            errors.append({'issue': 'frozen_mask_family_changed', 'field': key})
    raw_masks = []
    for path in (baseline, native_path):
        with olefile.OleFileIO(path) as doc:
            records = binary_records(doc.openstream('Regions6/Data').read(), 11)
        raw_masks.append(Counter(r['body'] for r in records if r['body'][0] in (37, 38)))
    if raw_masks[0] != raw_masks[1]:
        errors.append({'issue': 'saved_mask_region_bytes_changed',
                       'removed': sum((raw_masks[0] - raw_masks[1]).values()),
                       'added': sum((raw_masks[1] - raw_masks[0]).values())})
    field = shape(old['qd_mask_field'])
    qd = unary_union([p['geometry'] for p in pads if p['ref'] == 'Q1'])
    x0, y0, x1, y1 = qd.bounds
    minimum_field = box(x0 - .15, y0 - .15, x1 + .15, y1 + .15)
    cx, cy = plan['sample_center']
    dx, dy = plan['cavity_mm']
    cavity = box(cx - dx / 2, cy - dy / 2, cx + dx / 2, cy + dy / 2)
    for name, wanted in (('new_pad_field', minimum_field), ('cavity', cavity)):
        missing = wanted.difference(field.buffer(1e-5)).area
        if missing > 1e-8:
            errors.append({'issue': 'retained_QD_field_does_not_cover_' + name,
                           'missing_mm2': missing})
    bottom = unary_union([r['geometry'] for r in regions if r['layer'] == 38])
    missing = field.difference(bottom.buffer(.003)).area
    if missing > 1e-8:
        errors.append({'issue': 'retained_QD_field_not_open_on_Bottom', 'missing_mm2': missing})
    return field, dict(passed=not errors, errors=errors, baseline_native_sha256=BASE_NATIVE,
                      baseline_candidate_sha256=BASE_PLAN,
                      native_mask_region_count=sum(raw_masks[1].values()),
                      mask_region_bytes_unchanged=raw_masks[0] == raw_masks[1],
                      retained_bounds_mm=list(field.bounds), new_minimum_bounds_mm=list(minimum_field.bounds),
                      covers_new_field_and_cavity=not any('cover_' in e['issue'] for e in errors),
                      new_mask_opening_area_mm2=0 if raw_masks[0] == raw_masks[1] else None,
                      policy='Retain the verified larger mask field; no mask aperture enlargement or regeneration.')
