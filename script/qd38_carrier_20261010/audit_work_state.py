"""Report hash-bound QD38 native progress without treating prepared plans as completion."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import html
import json
import re
import struct
import collections
import olefile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEST = ROOT / 'QSTL_QD4_2SET_38PAD'
PCB = DEST / 'QSTL_QD4_2SET_38PAD.PcbDoc'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def read_text(path):
    return path.read_text(errors='replace') if path.exists() else ''


def scalar_log(text):
    return {line.split('=', 1)[0]: line.split('=', 1)[1]
            for line in text.splitlines() if '=' in line and not line.startswith(('PAD=', 'VIA=', 'PIN=', 'NET='))}


def drc_report():
    path = HERE / 'Native_DRC.html'
    if not path.exists():
        return {'available': False, 'verified_zero': False}
    source = read_text(path)
    fields = {}
    for key in ('Warnings:', 'Rule Violations:', 'Filename:'):
        match = re.search(r'<td[^>]*>' + re.escape(key) + r'</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>', source, re.S)
        if match:
            fields[key] = html.unescape(re.sub('<[^>]+>', '', match.group(1))).strip()
    violations = int(fields['Rule Violations:']) if fields.get('Rule Violations:', '').isdigit() else None
    warnings = int(fields['Warnings:']) if fields.get('Warnings:', '').isdigit() else None
    target_matches = fields.get('Filename:', '').replace('/', '\\').casefold() == str(PCB).replace('/', '\\').casefold()
    stopped = bool(re.search(r'DRC was stopped|violations detected.*stopp', source, re.I))
    fresh = path.stat().st_mtime_ns >= PCB.stat().st_mtime_ns
    rows = re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>', source, re.S)
    rows = [{'rule': html.unescape(re.sub('<[^>]+>', '', name)).strip(), 'violations': int(count)} for name, count in rows]
    expected = {'Clearance Constraint': 3, 'Short-Circuit Constraint': 1,
                'Un-Routed Net Constraint': 1, 'Modified Polygon': 1,
                'Width Constraint': 3, 'Routing Topology Rule': 1,
                'Routing Via': 3, 'Hole Size Constraint': 1,
                'Hole To Hole Clearance': 1, 'Minimum Solder Mask Sliver': 1,
                'Silk To Solder Mask': 1, 'Silk to Silk': 1,
                'Net Antennae': 1, 'Component Clearance Constraint': 1,
                'Height Constraint': 1}
    observed = {family: sum(row['rule'].startswith(family) for row in rows) for family in expected}
    covered = len(rows) == 21 and observed == expected
    return {'available': True, 'path': str(path), 'sha256': digest(path),
            'target_file': fields.get('Filename:'), 'target_matches': target_matches,
            'report_not_older_than_saved_pcb': fresh, 'violations': violations,
            'warnings': warnings, 'stopped_at_violation_limit': stopped,
            'rule_count': len(rows), 'rule_family_counts': observed,
            'expected_rule_family_counts': expected, 'all_21_required_rules_reported': covered,
            'all_rule_rows_zero': bool(rows) and all(row['violations'] == 0 for row in rows),
            'rules': rows,
            'verified_zero': target_matches and fresh and violations == 0 and not stopped
                             and covered and all(row['violations'] == 0 for row in rows)}


def paste_cam_report(native_hash):
    """Use effective exported apertures, never API flags, to verify via paste removal."""
    path = HERE / 'native_paste_cam_validation.json'
    proof = load(path, {})
    current = proof.get('native_sha256') == native_hash
    checks = proof.get('cam_checks', [])
    files_current = bool(checks) and all(Path(check['file']).is_file()
        and digest(Path(check['file'])) == check.get('sha256') for check in checks)
    apertures_match = (len(checks) == 2 and {c.get('layer') for c in checks} == {35, 36}
        and all(c.get('missing_outside_tolerance_mm2') == 0
                and c.get('extra_outside_tolerance_mm2') == 0
                and 0 < c.get('tolerance_mm', float('inf')) <= 0.00005
                and c.get('expected_pad_count') == c.get('objects')
                for c in checks))
    verified = (current and files_current and apertures_match and proof.get('passed') is True
                and proof.get('via_specific_paste_absent') is True
                and proof.get('explicit_paste_object_count') == 0
                and not proof.get('errors', ['missing errors field']))
    return {'verified': verified, 'path': str(path), 'sha256': digest(path) if path.exists() else None,
            'matches_current_native_hash': current, 'CAM_files_match_recorded_hashes': files_current,
            'both_layers_match_intended_pad_apertures': apertures_match,
            'via_specific_paste_absent': proof.get('via_specific_paste_absent') if current else None,
            'normal_pad_apertures': proof.get('normal_pad_apertures'),
            'explicit_paste_object_count': proof.get('explicit_paste_object_count') if current else None,
            'cam_checks': checks, 'errors': proof.get('errors'),
            'interpretation': 'Native API enabled flags do not represent effective CAM aperture geometry. Required R/C pad paste is retained even where its pad contains a via.'}


def connection_inventory():
    """Decode stored airwire net membership without changing or deleting records."""
    with olefile.OleFileIO(PCB) as ole:
        raw = ole.openstream('Connections6/Data').read()
        header_count = struct.unpack('<I', ole.openstream('Connections6/Header').read())[0]
        net_data = ole.openstream('Nets6/Data').read()
    names = []
    pos = 0
    while pos < len(net_data):
        size = struct.unpack_from('<I', net_data, pos)[0] & 0xffffff
        pos += 4
        fields = dict(x.split('=', 1) for x in net_data[pos:pos+size].rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
        names.append(fields['NAME'])
        pos += size
    rows = []
    pos = 0
    while pos < len(raw):
        size = struct.unpack_from('<I', raw, pos)[0]
        pos += 4
        body = raw[pos:pos+size]
        pos += size
        net_index = struct.unpack_from('<H', body, 3)[0]
        coords = struct.unpack_from('<4i', body, 13)
        rows.append({'net': names[net_index] if net_index != 65535 else None,
                     'endpoints_mm': [[v*2.54e-6 for v in coords[:2]], [v*2.54e-6 for v in coords[2:]]],
                     'record_length': size, 'flags_prefix': list(body[:3])})
    assert pos == len(raw) and len(rows) == header_count
    snapshot = load(HERE / 'through_dc_saved_native_snapshot.json', {})
    snapshot_current = snapshot.get('source_sha256') == digest(PCB)
    if snapshot_current:
        for row in rows:
            row['endpoint_pads'] = [[str(p['component']) + '-' + p['number'] for p in snapshot['pads'] if abs(p['x']-xy[0]) < 1e-5 and abs(p['y']-xy[1]) < 1e-5] for xy in row['endpoints_mm']]
    return {'all_endpoints_on_saved_pads': snapshot_current and all(all(row['endpoint_pads']) for row in rows),
            'saved_GND_pad_count': sum(p['net']=='GND' for p in snapshot.get('pads', [])) if snapshot_current else None,
            'stored_count': header_count, 'by_net': dict(collections.Counter(row['net'] for row in rows)),
            'record_lengths': dict(collections.Counter(row['record_length'] for row in rows)),
            'sample': rows[:12], 'all_records': rows,
            'interpretation': 'Stored airwire inventory only. These records are preserved, not deleted to force a zero count.'}

def main():
    provenance = load(DEST / 'copy_provenance.json')
    preserved = {name: digest(Path(provenance['source']) / name) == expected
                 for name, expected in provenance['source_sha256'].items()}
    plan = load(DEST / 'circuit_plan.json')
    schematic = load(DEST / 'schematic_validation.json')
    routed = load(DEST / 'routed_candidate_audit.json', {})
    full = load(DEST / 'full_copper_candidate.json', {})
    saved = load(HERE / 'through_dc_saved_native_audit.json', {})
    snapshot = load(HERE / 'through_dc_saved_native_snapshot.json', {})
    native_hash = digest(PCB)
    saved_current = saved.get('native_sha256') == native_hash
    snapshot_current = snapshot.get('source_sha256') == native_hash
    candidate_current = saved.get('candidate_sha256') == digest(DEST / 'full_copper_candidate.json')
    geometry_verified = saved_current and candidate_current and saved.get('passed') is True
    unchanged = native_hash == provenance['source_sha256']['QSTL_24DC_4MW_PCB.PcbDoc']
    components = len(snapshot.get('components', [])) if snapshot_current else None
    qd_count = sum(p['component'] == 'Q1' for p in snapshot.get('pads', [])) if snapshot_current else None
    applied = not unchanged and components == 50 and qd_count == 38
    pins = [row['zif_pin'] for row in plan['pinmap']]
    plan_valid = (len(pins) == len(set(pins)) == 38 and 50 not in pins
                  and any(pin % 2 for pin in pins)
                  and sum(row['rf'] for row in plan['pinmap']) == 16
                  and schematic['nets'] == plan['nets'])
    validation_log = read_text(HERE / 'native_validation.txt')
    compile_log = read_text(HERE / 'native_compile.txt')
    validation = scalar_log(validation_log)
    compile_state = scalar_log(compile_log)
    schematic_current = (saved.get('schematic_sha256') == digest(DEST / 'QSTL_QD4_2SET_38PAD.SchDoc')
                         == schematic.get('schematic_sha256'))
    compile_current = (saved.get('live_compile_sha256') == digest(HERE / 'native_compile.txt')
                       if (HERE / 'native_compile.txt').exists() else False)
    compiled_verified = (geometry_verified and schematic_current and compile_current
                         and saved.get('live_compile_membership_verified') is True
                         and compile_state.get('VIOLATION_COUNT') == '0'
                         and 'COMPLETE' in compile_log.splitlines())
    reopened = 'REOPENED' in validation_log.splitlines()
    stored_zero = saved_current and saved.get('native_connection_count') == 0
    drc = drc_report()
    coverage = load(HERE / 'saved_paste_drc_coverage.json', {})
    coverage_current = coverage.get('native_sha256') == native_hash
    paste = paste_cam_report(native_hash)
    routing_requirements = load(HERE / 'saved_routing_requirement_audit.json', {})
    routing_requirements_current = routing_requirements.get('native_sha256') == native_hash
    routing_requirements_verified = routing_requirements_current and routing_requirements.get('passed') is True
    pending = []
    if not applied:
        pending.append('Verify the applied native QD38 PCB component and pad counts')
    if not all(preserved.values()):
        pending.append('Investigate changes to original source design files')
    if not plan_valid:
        pending.append('Synchronize the planned schematic and independent DC assignments')
    if not geometry_verified:
        pending.append('Rerun or resolve the exact saved-native geometry and net-map audit')
    if not reopened:
        pending.append('Verify native save and reopen')
    if not stored_zero:
        pending.append('Verify saved native stored-connection count is zero')
    if not drc['verified_zero']:
        pending.append('Run current native DRC to completion and resolve all reported violations')
    if not compiled_verified:
        pending.append('Verify the current saved schematic and native compiled net membership with zero reported violations')
    paste_enabled = validation.get('VIA_PASTE_ENABLED')
    if not paste['verified']:
        pending.append('Regenerate and validate hash-bound native paste CAM against all intended SMD pad apertures')
    if not routing_requirements_verified:
        if routing_requirements_current:
            pending.append('Correct saved routing requirement failures: ' + str(routing_requirements.get('dc_turns_over_45_count')) + ' DC turns above 45 degrees and ' + str(routing_requirements.get('rf_sharp_turn_count')) + ' sharp RF turns without tangent arcs')
        else:
            pending.append('Verify saved routing against H/V/45 straight directions, DC turns at most 45 degrees, and tangent RF corners')
    if routing_requirements_current and routing_requirements.get('direct_QD_DC_via_outside_pad_count', 0):
        pending.append('Restore retained QD DC via-in-pad requirement: ' + str(routing_requirements['direct_QD_DC_via_outside_pad_count']) + ' direct QD DC vias currently lie outside their bonding pads')
    completion = (applied and geometry_verified and drc['verified_zero']
                  and all(preserved.values()) and plan_valid and reopened and stored_zero
                  and not pending)
    status = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'target_project': str(DEST / 'QSTL_QD4_2SET_38PAD.PrjPcb'),
        'current_project_root': str(ROOT),
        'source_files_unchanged': preserved,
        'plan': {'qd_pads': 38, 'independent_dc': 38, 'rf_bias_tees': 16,
                 'odd_zif_pins_used': any(pin % 2 for pin in pins),
                 'zif_pin_50_unused': 50 not in pins,
                 'schematic_netmap_matches_current_plan': schematic['nets'] == plan['nets'],
                 'all_assignment_checks_passed': plan_valid},
        'native_pcb': {'path': str(PCB), 'sha256': native_hash,
                       'unchanged_source_copy': unchanged,
                       'component_count': components, 'qd_pad_count': qd_count,
                       'qd38_replacement_applied': applied,
                       'snapshot_matches_current_hash': snapshot_current,
                       'saved_geometry_audit_matches_current_hash': saved_current,
                       'saved_geometry_audit_matches_current_candidate': candidate_current,
                       'saved_geometry_audit_passed': geometry_verified,
                       'saved_geometry_audit_errors': saved.get('errors') if saved_current else None,
                       'stored_connection_count': saved.get('native_connection_count') if saved_current else None,
                       'physical_ground_copper_connected': saved.get('ground_copper_connected') if saved_current else None,
                       'physical_ground_connected_components': saved.get('ground_copper_component_count') if saved_current else None},
        'native_validation': 'VERIFIED' if completion else 'APPLIED_VALIDATION_INCOMPLETE' if applied else 'NOT_VERIFIED',
        'native_reopened': reopened,
        'native_drc': drc,
        'saved_routing_requirements': {'path': str(HERE / 'saved_routing_requirement_audit.json'),
                                       'matches_current_native_hash': routing_requirements_current,
                                       'passed': routing_requirements_verified,
                                       'dc_turns_over_45_count': routing_requirements.get('dc_turns_over_45_count') if routing_requirements_current else None,
                                       'rf_sharp_turn_count': routing_requirements.get('rf_sharp_turn_count') if routing_requirements_current else None,
                                       'arc_count': routing_requirements.get('arc_count') if routing_requirements_current else None,
                                       'no_standalone_DC_transition_vias': routing_requirements.get('no_standalone_DC_transition_vias') if routing_requirements_current else None,
                                       'direct_QD_DC_via_outside_pad_count': routing_requirements.get('direct_QD_DC_via_outside_pad_count') if routing_requirements_current else None},
        'native_compile': compile_state,
        'native_compile_verification': {'current_log_matches_audit_hash': compile_current,
                                        'current_saved_schematic_matches_validated_hash': schematic_current,
                                        'compiled_pin_membership_matches_saved_PCB_and_schematic': compiled_verified,
                                        'api_success_claimed': compile_state.get('COMPILE_RESULT') == 'True',
                                        'interpretation': 'The raw DM_Compile return is retained. Independent verification uses the completed native compiled netlist, zero reported violations, exact saved PCB pad membership and the hash-matched validated SchDoc; module-statistics proof is not claimed.'},
        'stored_airwire_inventory': connection_inventory(),
        'native_paste': {'api_enabled_via_count': paste_enabled,
                         'coverage_inventory_matches_current_hash': coverage_current,
                         'explicit_paste_object_count': coverage.get('explicit_paste_object_count') if coverage_current else None,
                         'effective_CAM': paste,
                         'interpretation': 'Negative manual expansion and effective CAM apertures require separate interpretation from API enabled flags.'},
        'offline_signal_validation': {k: routed.get(k) for k in ('passed', 'signal_nets', 'all_signal_nets_connected', 'minimum_clearance_mm', 'schematic_map_matches')},
        'prepared_surface_geometry': full.get('surface_validation'),
        'native_update_script_prepared_not_executed': unchanged,
        'completion': completion,
        'fabrication_release': False,
        'pending': pending,
    }
    (DEST / 'work_state_audit.json').write_text(json.dumps(status, indent=2))
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()




