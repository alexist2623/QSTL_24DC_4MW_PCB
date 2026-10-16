"""Read native carrier pin membership and Anton's immutable KiCad reference.

This audit writes only its report beside this script. It does not modify any
design, schematic, mapping CSV, reference PCB or user documentation. Old QD pad
numbers are not assumed to identify the new QD4/2SET chip's terminal functions.
"""
from pathlib import Path
import csv
import hashlib
import json
import re
import struct
import sys

import olefile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "script/_support/qd_center_revision"))
from native_metadata_helpers import properties, pads_stream

ORIGINAL = ROOT / "QSTL_24DC_4MW_PCB"
COPIED = ROOT / "QSTL_QD4_2SET_38PAD"
REFERENCE = ROOT / "script/anton_zif_20260923/reference/DSUBtoZIF_20250306"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_pads(path):
    before = sha(path)
    with olefile.OleFileIO(path) as doc:
        component_data = doc.openstream("Components6/Data").read()
        components = properties(component_data)
        nets = properties(doc.openstream("Nets6/Data").read())
        pads = pads_stream(doc.openstream("Pads6/Data").read())
        text_data = doc.openstream("Texts6/Data").read()
    texts = []
    pos = 0
    while pos < len(text_data):
        assert text_data[pos] == 5
        size = struct.unpack_from("<I", text_data, pos+1)[0] & 0xffffff
        body = text_data[pos+5:pos+5+size]
        pos += 5+size
        size = struct.unpack_from("<I", text_data, pos)[0] & 0xffffff
        raw = text_data[pos+4:pos+4+size]
        pos += 4+size
        texts.append((struct.unpack_from("<H", body, 7)[0], raw[1:].decode("cp1252")))
    names = {}
    for i, component in enumerate(components):
        designator = [text for owner, text in texts if owner == i and re.fullmatch(r"(?:J|Q|R|C|SMP)\d+", text)]
        assert len(designator) == 1, (path, i, designator)
        names[i] = designator[0]
    result = {}
    for pad in pads:
        if pad["component"] == 65535:
            continue
        key = (names[pad["component"]], pad["number"])
        assert key not in result
        result[key] = None if pad["net"] == 65535 else nets[pad["net"]]["NAME"]
    assert sha(path) == before
    return result, {names[i]: c for i, c in enumerate(components)}


def parse_sexp(path):
    stack = [[]]
    for match in re.finditer(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', path.read_text(encoding="utf-8")):
        token = match.group()
        if token == "(":
            node = []
            stack[-1].append(node)
            stack.append(node)
        elif token == ")":
            assert len(stack) > 1
            stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    assert len(stack) == 1 and len(stack[0]) == 1
    return stack[0][0]


def rows(node, key):
    return [item for item in node if isinstance(item, list) and item and item[0] == key]


def row(node, key):
    result = rows(node, key)
    return result[0] if result else None


def value(node, key):
    result = row(node, key)
    return result[1] if result and len(result) > 1 else None


def main():
    files = [ORIGINAL / "QSTL_24DC_4MW_PCB.PcbDoc", ORIGINAL / "QSTL_24DC_4MW_PCB.SchDoc", ORIGINAL / "docs/PIN_MAPPING.csv",
             COPIED / "QSTL_QD4_2SET_38PAD.PcbDoc", COPIED / "QSTL_QD4_2SET_38PAD.SchDoc", COPIED / "pin_mapping.csv",
             ORIGINAL / "docs/Anton_ZIF_20260923/pinout_audit.json"] + sorted(p for p in REFERENCE.iterdir() if p.is_file())
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in files}
    original, original_components = native_pads(files[0])
    copied, copied_components = native_pads(files[3])
    with files[2].open(newline="", encoding="utf-8-sig") as stream:
        legacy_csv = list(csv.DictReader(stream))
    with files[5].open(newline="", encoding="utf-8-sig") as stream:
        copied_csv = list(csv.DictReader(stream))
    errors = []

    def check(ok, issue, details=None):
        if not ok:
            errors.append(dict(issue=issue, details=details))

    legacy = []
    for item in legacy_csv:
        q, z = int(item["QD_pad"]), int(item["ZIF_pin"])
        dc_net = original[(item["Bias_resistor"], "2")] if item["Bias_resistor"] else original[("Q1", str(q))]
        qd_net = original[("Q1", str(q))]
        check(qd_net == item["QD_net"], "original_QD_net_differs_from_PIN_MAPPING", item)
        actual_zif = sorted(int(pin) for (ref, pin), net in original.items() if ref == "J1" and pin.isdigit() and net == dc_net)
        check(actual_zif == [z], "original_ZIF_assignment_differs_from_PIN_MAPPING", dict(qd_pad=q, expected=z, actual=actual_zif))
        legacy.append(dict(legacy_QD_pad=q, zif_pin=z, original_DC_net=dc_net, original_QD_net=qd_net,
                           original_bias_resistor=item["Bias_resistor"] or None, original_reference_bond_pad=int(item["Reference_carrier_bond_pad"])))
    current = []
    for item in copied_csv:
        q, z = int(item["qd_pad"]), int(item["zif_pin"])
        dc_net = copied[(f"R{q:02}", "2")] if item["rf"].lower() == "true" else copied[("Q1", str(q))]
        actual_zif = sorted(int(pin) for (ref, pin), net in copied.items() if ref == "J1" and pin.isdigit() and net == dc_net)
        check(actual_zif == [z], "copied_ZIF_assignment_differs_from_pin_mapping", dict(qd_pad=q, expected=z, actual=actual_zif))
        current.append(dict(qd38_pad=q, chip_function=item["chip_net"], zif_pin=actual_zif[0] if len(actual_zif)==1 else None, DC_net=dc_net, expected_csv_pin=z))

    # Parse both independently stored Anton board and exported netlist now.
    board = parse_sexp(REFERENCE / "DSUBtoZIF_20250106.kicad_pcb")
    netlist = parse_sexp(REFERENCE / "DSUBtoZIF_20250106.net")
    anton_pads = {}
    footprint_values = {}
    for fp in rows(board, "footprint"):
        props = {prop[1]: prop[2] for prop in rows(fp, "property")}
        ref = props["Reference"]
        footprint_values[ref] = props.get("Value")
        for pad in rows(fp, "pad"):
            net = row(pad, "net")
            anton_pads[(ref, pad[1])] = net[2] if net else None
    netlist_pads = {}
    for net in rows(row(netlist, "nets"), "net"):
        for node in rows(net, "node"):
            netlist_pads[(value(node, "ref"), value(node, "pin"))] = value(net, "name")
    anton = []
    for pin in range(1, 52):
        net = anton_pads[("J2", str(pin))]
        dsub = sorted(int(p) for (ref, p), name in anton_pads.items() if ref == "J1" and p.isdigit() and name == net)
        check(net == netlist_pads[("J2", str(pin))], "Anton_KiCad_vs_netlist_mismatch", pin)
        anton.append(dict(zif_pin=pin, dsub_pin=dsub[0] if len(dsub)==1 else None, net=net))
    previous_anton = json.loads(files[6].read_text())
    documented = {int(p["pin"]): [int(x["pin"]) for x in p["connected_pads"] if x["reference"] == "J1"] for p in previous_anton["ZIF_pad_mapping"] if p["pin"].isdigit()}
    check(all(documented[item["zif_pin"]] == ([] if item["dsub_pin"] is None else [item["dsub_pin"]]) for item in anton), "Anton_current_parse_differs_from_previous_audit")
    check(all(sha(REFERENCE/name)==expected for name, expected in previous_anton["source_hashes"].items()), "Anton_source_hash_changed")
    dsub_by_zif = {item["zif_pin"]: item["dsub_pin"] for item in anton}
    for item in legacy:
        item["Anton_DSUB_pin"] = dsub_by_zif[item["zif_pin"]]
    for item in current:
        item["Anton_DSUB_pin"] = dsub_by_zif.get(item["zif_pin"])
    original_contacts = sorted(item["zif_pin"] for item in legacy)
    copied_contacts = sorted(item["zif_pin"] for item in current if item["zif_pin"] is not None)
    per_contact = []
    legacy_by_contact = {item["zif_pin"]: item for item in legacy}
    current_by_contact = {item["zif_pin"]: item for item in current}
    for pin in sorted(set(original_contacts) | set(copied_contacts)):
        old, new = legacy_by_contact.get(pin), current_by_contact.get(pin)
        per_contact.append(dict(zif_pin=pin, old_QD24_pad=old["legacy_QD_pad"] if old else None,
                                new_QD38_pad=new["qd38_pad"] if new else None,
                                new_chip_function=new["chip_function"] if new else None,
                                Anton_DSUB_pin=dsub_by_zif[pin]))
    # Numeric equal-pad comparisons are descriptive only: QD24 and QD38 pads
    # are from different components and do not establish functional continuity.
    current_by_q = {item["qd38_pad"]: item for item in current}
    numeric_changes = [dict(qd_number=item["legacy_QD_pad"], old_zif=item["zif_pin"], new_zif=current_by_q[item["legacy_QD_pad"]]["zif_pin"])
                       for item in legacy if item["zif_pin"] != current_by_q[item["legacy_QD_pad"]]["zif_pin"]]
    with olefile.OleFileIO(ORIGINAL / "QSTL_24DC_4MW_PCB.SchDoc") as document:
        original_schematic_text = document.openstream("FileHeader").read().decode("cp1252", errors="replace").upper()
    function_tokens = ("OHMIC", "PLUNGER", "BARRIER", "ACCUMULATION", "SET_NE", "SET_SW", "QD_SCREEN")
    functional_evidence = dict(original_QD_pattern=original_components["Q1"]["PATTERN"],
                               copied_QD_pattern=copied_components["Q1"]["PATTERN"],
                               original_schematic_function_tokens_found=[token for token in function_tokens if token in original_schematic_text],
                               original_PIN_MAPPING_fields=list(legacy_csv[0]),
                               copied_pin_mapping_fields=list(copied_csv[0]))
    check(all(sha(ROOT/name)==digest for name, digest in hashes.items()), "Source_file_changed_during_audit")
    report = dict(passed=not errors, scope="Read-only stored pad/net membership, CSV agreement, and independent Anton KiCad/netlist comparison. This is not an independent full copper-connectivity audit.",
                  source_hashes=hashes, original_matches_PIN_MAPPING=not any(e["issue"].startswith("original_") for e in errors),
                  copied_matches_pin_mapping=not any(e["issue"].startswith("copied_") for e in errors),
                  original_24_mapping=legacy, copied_38_mapping=current, contact_comparison=per_contact,
                  original_used_contacts=original_contacts, copied_used_contacts=copied_contacts,
                  legacy_even_contacts_missing=sorted(set(original_contacts)-set(copied_contacts)),
                  newly_used_contacts=sorted(set(copied_contacts)-set(original_contacts)),
                  common_contact_count=len(set(original_contacts)&set(copied_contacts)),
                  numeric_pad_comparison_only=numeric_changes,
                  semantic_QD24_to_QD38_mapping_established=False,
                  functional_mapping_evidence=functional_evidence,
                  semantic_mapping_limitation="Legacy PIN_MAPPING has QD pad numbers, generic MW/ZIF nets and reference-carrier bond-pad numbers, but no chip gate/ohmic/screen function. QD38 has explicit QD4_2SET chip function labels. Equal numerical pad IDs must not be treated as verified same signals.",
                  anton_mapping=anton, anton_footprint_values=footprint_values,
                  copied_channels_reaching_unmodified_Anton=sum(item["Anton_DSUB_pin"] is not None for item in current),
                  copied_channels_not_reaching_unmodified_Anton=[item for item in current if item["Anton_DSUB_pin"] is None],
                  anton_previous_source_note=previous_anton["source_note"], errors=errors)
    (HERE / "legacy_zif_mapping_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("passed", "original_matches_PIN_MAPPING", "copied_matches_pin_mapping", "original_used_contacts", "copied_used_contacts", "legacy_even_contacts_missing", "newly_used_contacts", "common_contact_count", "copied_channels_reaching_unmodified_Anton", "semantic_QD24_to_QD38_mapping_established", "errors")}, indent=2))
    print("LEGACY_QD24_TO_ZIF", " ".join(f"{item['legacy_QD_pad']}:{item['zif_pin']}" for item in legacy))
    print("ANTON_ZIF_TO_DSUB", " ".join(f"{item['zif_pin']}:{item['dsub_pin']}" for item in anton if item["dsub_pin"] is not None))
    print("NUMERIC_ONLY_CHANGES", json.dumps(numeric_changes))


if __name__ == "__main__":
    main()
