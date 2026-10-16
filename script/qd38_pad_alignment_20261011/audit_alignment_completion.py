"""Require fresh, mutually bound saved evidence for the local QD alignment.

No native commands or design writes. A completion report is written only
after every required report and current-file hash passes. This is not a
manufacturing release or a physical prototype/impedance certification.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

from alignment_invariants import assert_plan_contacts, via_groups

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
DEST = ROOT / 'QSTL_QD4_2SET_38PAD'
NAME = DEST.name
BASE = '1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    files = {
        'candidate': H / 'alignment_full_candidate.json', 'candidate_audit': H / 'alignment_full_audit.json',
        'native': DEST / (NAME + '.PcbDoc'), 'schematic': DEST / (NAME + '.SchDoc'),
        'project': DEST / (NAME + '.PrjPcb'), 'library': DEST / 'QD4_2SET_38.PcbLib',
        'schematic_library': DEST / (NAME + '.SchLib'), 'pin_table': DEST / 'pin_mapping.csv',
        'schematic_validation': DEST / 'schematic_validation.json',
        'native_audit': H / 'saved_revision_audit.json', 'snapshot': H / 'saved_revision_snapshot.json',
        'surface_audit': H / 'saved_revision_surface.json', 'model_audit': H / 'saved_revision_models.json',
        'canonical_audit': H / 'canonical_library_audit.json', 'rule_audit': H / 'saved_alignment_rules.json',
        'delta_audit': H / 'saved_alignment_delta.json', 'delta_manifest': H / 'alignment_delta_manifest.json',
        'paste_audit': H / 'revision_native_paste_cam_validation.json',
        'paste_manifest': H / 'revision_paste_audit_source_manifest.json',
        'promotion': H / 'alignment_source_promotion.json', 'images': H / 'alignment_review_images.json',
        'library_patch_audit': H / 'library_staging/library_xy_patch_audit.json',
        'backup_manifest': H / 'before_alignment/manifest.json',
        'baseline': H / 'before_alignment' / (NAME + '.PcbDoc'),
        'DRC': H / 'Native_DRC.html', 'compile_log': H / 'native_compile.txt',
        'validation_log': H / 'native_validation.txt', 'delta_log': H / 'native_alignment_delta.txt',
        'paste_log': H / 'revision_paste_export_native_log.txt',
        'provenance': DEST / 'copy_provenance.json',
        'first_save_manifest': H / 'first_save_connection_cache/manifest.json',
        'connectivity_rebuild_log': H / 'native_connectivity_rebuild.txt'}
    missing = [{'item': k, 'path': str(p)} for k, p in files.items() if not p.is_file()]
    if missing:
        print(json.dumps(dict(passed=False, status='MISSING_ALIGNMENT_COMPLETION_EVIDENCE', missing=missing,
                              completion_report_written=False), indent=2))
        raise SystemExit(2)
    hashes = {k: sha(p) for k, p in files.items()}
    data = {k: read(p) for k, p in files.items() if p.suffix == '.json'}
    errors = []
    def check(ok, issue, detail=None):
        if not ok: errors.append(dict(issue=issue, detail=detail))
    def bind(row, field, item):
        check(row.get(field) == hashes[item], 'stale_hash_binding',
              dict(field=field, item=item, recorded=row.get(field), actual=hashes[item]))
    plan = data['candidate']; native = data['native_audit']; snapshot = data['snapshot']
    for key in ('candidate_audit', 'native_audit', 'surface_audit', 'model_audit', 'canonical_audit',
                'rule_audit', 'delta_audit', 'paste_audit', 'library_patch_audit'):
        row = data[key]
        check(row.get('passed') is True and not row.get('errors') and not row.get('failures'), 'audit_not_passed', key)
    for key in ('candidate_audit', 'native_audit', 'surface_audit', 'canonical_audit', 'rule_audit', 'delta_audit', 'paste_audit'):
        bind(data[key], 'candidate_sha256', 'candidate')
    for key in ('native_audit', 'surface_audit', 'model_audit', 'rule_audit', 'delta_audit', 'paste_audit'):
        bind(data[key], 'native_sha256', 'native')
    bind(snapshot, 'source_sha256', 'native')
    bind(native, 'schematic_sha256', 'schematic'); bind(native, 'candidate_audit_sha256', 'candidate_audit')
    bind(native, 'live_compile_sha256', 'compile_log')
    bind(data['canonical_audit'], 'library_sha256', 'library')
    bind(data['library_patch_audit'], 'staged_library_sha256', 'library')
    bind(data['schematic_validation'], 'schematic_sha256', 'schematic')
    check(data['schematic_validation'].get('nets') == plan['nets'], 'schematic_membership_differs')
    check(hashes['baseline'] == BASE and hashes['native'] != BASE, 'alignment_not_applied_or_backup_changed')
    check(plan.get('routing_complete') is True, 'routing_not_complete')
    check(native.get('native_connection_count') == 0, 'stored_connections_nonzero')
    check(native.get('layer_stack_preserved') is True and native.get('component_SourceUniqueIDs_match') is True,
          'stack_or_component_identity_not_preserved')
    check(native.get('ground_copper_connected') is True and native.get('ground_copper_component_count') == 1,
          'ground_connectivity_failed')
    check(native.get('live_compile_membership_verified') is True and native.get('live_compile', {}).get('VIOLATION_COUNT') == '0',
          'compiled_membership_failed')
    dc_names = {f'DC{i:02}' for i in range(1, 39)}
    layers = native.get('DC_internal_layers', {})
    check(set(layers) == dc_names and all(v in ([2], [4]) for v in layers.values()), '38_DC_single_layer_failed')
    dc = native.get('saved_DC_geometry', {}); rf = native.get('saved_RF_geometry', {})
    check(dc.get('passed') is True and not dc.get('failures'), 'saved_DC_geometry_failed')
    check(len(dc.get('SMP_envelopes', [])) == 32 and len(dc.get('resistor_envelopes', [])) == 32, 'DC_envelope_coverage_missing')
    check(rf.get('passed') is True and rf.get('RF_signal_vias') == 0 and rf.get('net_count') == 32, '16_RF_geometry_or_no_via_failed')
    check(not [v for v in snapshot['vias'] if (v.get('net') or '').startswith(('S', 'MW'))], 'snapshot_RF_vias_found')
    pool = assert_plan_contacts(plan); groups = via_groups(plan)
    check(native.get('ZIF_contact_pool', {}).get('used_contacts') == pool['used_contacts'], 'saved_ZIF_pool_changed')
    direct = native.get('direct_QD_via_in_pad', [])
    check(len(direct) == 22 and all(r.get('drill_within_pad') and r.get('center_in_pad') and r.get('endpoint_via_count') == 1 for r in direct),
          'saved_QD_endpoint_containment_failed')
    delta = data['delta_audit']; rules = data['rule_audit']; manifest = data['delta_manifest']
    bind(delta, 'declaration_sha256', 'delta_manifest')
    check(delta.get('baseline_sha256') == BASE and delta.get('maximum_inner_boundary_error_mm', 1) < 1e-5,
          'common_inner_boundary_failed')
    check(delta.get('minimum_cavity_clearance_mm', 0) >= .2 - 1e-5 and len(delta.get('alignment', [])) == 38, 'cavity_or_pad_alignment_count_failed')
    check(delta.get('signal_edits_confined') is True and delta.get('surface_edits_confined') is True
          and delta.get('all_pad_mask_paste_caches_unchanged') is True
          and delta.get('all_other_pad_bytes_unchanged') is True, 'local_delta_or_pad_cache_preservation_failed')
    check(rules.get('all_unrelated_rules_unchanged') is True, 'unrelated_rules_changed')
    expected_rule_delta = {('QD38_QD_VIA_0P4_0P2', v) for v in ('WIDTH', 'MINWIDTH', 'MAXWIDTH')}
    check({(v['name'], v['field']) for v in rules.get('declared_changes', [])} == expected_rule_delta,
          'unexpected_rule_delta')
    check(manifest['qd_endpoint_via'] == dict(count=22, baseline_land_mm=.4, land_mm=.35, drill_mm=.2, low=1, high=32),
          'QD_via_declaration_changed')
    surface = data['surface_audit']['checks']; drc = surface.get('native_DRC', {}); rings = surface.get('SMP_rings', {})
    bind(drc, 'report_sha256', 'DRC')
    check(drc.get('categories') == 23 and drc.get('violation_sum') == 0 and drc.get('via_style_rule_count') == 4
          and drc.get('early_stop') is False, 'native_DRC_coverage_or_zero_failed')
    check(len(drc.get('summary', [])) == 23 and all(v['violations'] == 0 for v in drc.get('summary', [])), 'DRC_summary_invalid')
    check(rings.get('passed') is True and len(rings.get('rings', [])) == 16
          and all(v.get('nonempty') and v.get('symmetric') for v in rings.get('rings', [])), 'SMP_rings_failed')
    masks = surface.get('retained_mask_family', {})
    check(masks.get('passed') is True and masks.get('mask_region_bytes_unchanged') is True
          and masks.get('new_mask_opening_area_mm2') == 0 and masks.get('covers_new_field_and_cavity') is True,
          'frozen_mask_family_failed')
    check(surface.get('shield_geometry', {}).get('passed') is True, 'saved_shield_clearance_failed')
    validation = files['validation_log'].read_text()
    check(all(s in validation for s in ('REOPENED', 'COMPLETE', 'POST_DRC_SAVED_CONNECTION_COUNT=0')) and 'STOP_' not in validation,
          'save_reopen_validation_log_failed')
    delta_log = files['delta_log'].read_text()
    check('COMPLETE_NOT_SAVED' in delta_log and 'STOP_' not in delta_log
          and 'CANDIDATE_SHA256=' + hashes['candidate'] in delta_log, 'native_delta_log_failed')
    rebuild = files['connectivity_rebuild_log'].read_text()
    check('CONNECTION_COUNT_AFTER_REBUILD=0' in rebuild and 'COMPLETE_NOT_SAVED' in rebuild and 'STOP_' not in rebuild,
          'native_connectivity_rebuild_not_verified')
    for entry in data['first_save_manifest']:
        p = Path(entry['path'])
        check(p.is_file() and sha(p) == entry['sha256'], 'first_save_failure_evidence_changed', str(p))
    paste = data['paste_audit']; pm = data['paste_manifest']
    for field, item in (('pcb_sha256', 'native'), ('project_sha256', 'project'), ('candidate_sha256', 'candidate'),
                        ('candidate_audit_sha256', 'candidate_audit'), ('saved_revision_audit_sha256', 'native_audit'),
                        ('canonical_library_audit_sha256', 'canonical_audit'), ('QD_library_sha256', 'library'), ('schematic_sha256', 'schematic')):
        bind(pm, field, item)
    for field, item in (('source_manifest_sha256', 'paste_manifest'), ('QD_library_sha256', 'library'), ('native_export_log_sha256', 'paste_log')):
        bind(paste, field, item)
    check(paste.get('via_specific_paste_absent') is True and paste.get('explicit_paste_object_count') == 0
          and paste.get('normal_pad_apertures') == {'35': 53, '36': 64}, 'effective_paste_failed')
    check(len(paste.get('cam_checks', [])) == 2 and paste.get('export_token') == pm.get('export_token'), 'paste_export_run_mismatch')
    for cam in paste.get('cam_checks', []):
        p = Path(cam['file']); check(p.is_file() and sha(p) == cam['sha256'], 'paste_CAM_changed', str(p))
    promotion = data['promotion']
    for field, item in (('candidate_sha256', 'candidate'), ('library_sha256', 'library'), ('project_unchanged_sha256', 'project')):
        bind(promotion, field, item)
    changed = promotion.get('changed', promotion.get('changed_outputs', []))
    check(bool(changed), 'source_promotion_output_list_missing')
    for entry in changed:
        p = Path(entry['path']) if 'path' in entry else DEST / entry['name']
        check(p.is_file() and sha(p) == entry['sha256'], 'promoted_source_changed', str(p))
    frozen = data['backup_manifest']; unchanged_names = {NAME + '.SchDoc', NAME + '.SchLib', NAME + '.PrjPcb', 'pin_mapping.csv'}
    unchanged = {}
    for entry in frozen['files']:
        check(sha(Path(entry['backup'])) == entry['sha256'], 'baseline_backup_changed', entry['backup'])
        source = Path(entry['source'])
        if source.name in unchanged_names:
            unchanged[source.name] = source.is_file() and sha(source) == entry['sha256']
    check(set(unchanged) == unchanged_names and all(unchanged.values()), 'unchanged_sources_failed', unchanged)
    declared_unchanged = promotion.get('unchanged_sources', {})
    check(bool(declared_unchanged), 'promotion_unchanged_source_hashes_missing')
    for name, digest in declared_unchanged.items():
        p = Path(name) if Path(name).is_absolute() else DEST / name
        check(p.is_file() and sha(p) == digest, 'promotion_unchanged_source_hash_mismatch', str(p))
    original = {}
    for name, digest in data['provenance']['source_sha256'].items():
        p = ROOT / 'QSTL_24DC_4MW_PCB' / name; original[name] = p.is_file() and sha(p) == digest
    check(original and all(original.values()) and native.get('source_files_unchanged') == original, 'original_sources_changed')
    old_completion = Path(frozen['completion_evidence'])
    check(sha(old_completion) == frozen['completion_sha256'], 'old_completion_report_changed')
    for value in read(old_completion)['evidence'].values():
        p = Path(value['path'])
        if p.parent == H.parent / 'qd38_rotation_20261011':
            check(p.is_file() and sha(p) == value['sha256'], 'old_revision_evidence_changed', str(p))
    images = data['images']; bind(images, 'candidate_sha256', 'candidate'); bind(images, 'native_sha256', 'native')
    rows = images.get('images', [])
    check(len(rows) >= 2 and len({r.get('view') for r in rows}) >= 2, 'review_views_missing')
    for image in rows:
        p = Path(image['path']); check(p.is_file() and sha(p) == image['sha256'], 'review_image_changed', str(p))
    for key, path in files.items(): check(sha(path) == hashes[key], 'evidence_changed_during_audit', key)
    if errors:
        print(json.dumps(dict(passed=False, status='ALIGNMENT_COMPLETION_EVIDENCE_FAILED', errors=errors,
                              completion_report_written=False), indent=2))
        raise SystemExit(1)
    result = dict(passed=True, completion=True, status='SAVED_QD_INNER_END_ALIGNMENT_VERIFIED',
                  verified_utc=datetime.now(timezone.utc).isoformat(), candidate_sha256=hashes['candidate'],
                  native_sha256=hashes['native'], library_sha256=hashes['library'], schematic_sha256=hashes['schematic'],
                  project_sha256=hashes['project'], baseline_native_sha256=BASE,
                  maximum_inner_boundary_error_mm=delta['maximum_inner_boundary_error_mm'],
                  minimum_cavity_clearance_mm=delta['minimum_cavity_clearance_mm'],
                  DC_channels=38, RF_channels=16, RF_signal_vias=0, stored_connections=0,
                  native_DRC_categories=23, native_DRC_violations=0, QD_endpoint_vias=manifest['qd_endpoint_via'],
                  source_preservation=original, unchanged_sources=unchanged,
                  evidence={k: dict(path=str(files[k]), sha256=v) for k, v in hashes.items()},
                  warnings=native.get('warnings', []), fabrication_release=False,
                  scope='Saved local alignment verified; no order, manufacturing certification, physical prototype or impedance measurement.')
    (H / 'alignment_completion_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
