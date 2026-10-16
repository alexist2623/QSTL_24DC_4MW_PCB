"""Require a mutually hash-bound set of final saved/native revision audits.

Read-only except for revision_completion_audit.json, which is written only
after every required report, hash binding and completion condition passes.
Missing/stale/failed evidence is printed to stdout and exits nonzero.
"""
import argparse,csv,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path

from revision_invariants import assert_plan_contacts,via_groups

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PROJECT=ROOT/"QSTL_QD4_2SET_38PAD"
NAME=PROJECT.name
FROZEN="f8356dd694810d2318a51e99544ab2345f8b9996de80e9ddc4456bbc6a14c632"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate",type=Path,default=HERE/"full_copper_candidate.json")
    parser.add_argument("--audit",type=Path,default=HERE/"full_copper_audit.json")
    args=parser.parse_args()
    files={"candidate":args.candidate.resolve(),"candidate_audit":args.audit.resolve(),
        "native":PROJECT/(NAME+".PcbDoc"),"schematic":PROJECT/(NAME+".SchDoc"),
        "project":PROJECT/(NAME+".PrjPcb"),"library":PROJECT/"QD4_2SET_38.PcbLib",
        "schematic_library":PROJECT/(NAME+".SchLib"),"pin_table":PROJECT/"pin_mapping.csv",
        "schematic_validation":PROJECT/"schematic_validation.json",
        "native_audit":HERE/"saved_revision_audit.json","snapshot":HERE/"saved_revision_snapshot.json",
        "model_audit":HERE/"saved_revision_models.json","rule_audit":HERE/"saved_revision_rules.json",
        "surface_audit":HERE/"saved_revision_surface.json","paste_audit":HERE/"revision_native_paste_cam_validation.json",
        "shield_audit":HERE/"shield_surface_audit.json",
        "paste_manifest":HERE/"revision_paste_audit_source_manifest.json","canonical_audit":HERE/"canonical_library_audit.json",
        "promotion":HERE/"source_promotion.json","provenance":PROJECT/"copy_provenance.json",
        "backup_manifest":HERE/"before_rotation/manifest.json","baseline":HERE/"before_rotation"/(NAME+".PcbDoc"),
        "DRC":HERE/"Native_DRC.html","compile_log":HERE/"native_compile.txt","validation_log":HERE/"native_validation.txt",
        "paste_log":HERE/"revision_paste_export_native_log.txt"}
    preliminary_plan=json.loads(args.candidate.read_text()) if args.candidate.is_file() else {}
    if preliminary_plan.get('pad_solder_mask_overrides'):
        files['pad_mask_audit']=HERE/'saved_mask_repair_audit.json'
        files['pad_mask_reopen_log']=HERE/'native_mask_after_reopen.txt'
    missing=[dict(item=k,path=str(p)) for k,p in files.items() if not p.is_file()]
    if missing:
        print(json.dumps(dict(passed=False,status="MISSING_REQUIRED_COMPLETION_EVIDENCE",missing=missing,completion_report_written=False),indent=2))
        raise SystemExit(2)
    hashes={k:sha(p) for k,p in files.items()}
    report={k:json.loads(p.read_text()) for k,p in files.items() if p.suffix==".json"}
    errors=[]
    def check(ok,issue,detail=None):
        if not ok:errors.append(dict(issue=issue,detail=detail))
    def binding(data,field,key):check(data.get(field)==hashes[key],"stale_hash_binding",dict(field=field,item=key,recorded=data.get(field),current=hashes[key]))
    p=report["candidate"];native=report["native_audit"];snapshot=report["snapshot"]
    if 'pad_mask_audit' in report:
        mask=report['pad_mask_audit']
        check(mask.get('passed') is True and not mask.get('errors'),'pad_mask_repair_not_verified')
        binding(mask,'candidate_sha256','candidate');binding(mask,'native_sha256','native')
        binding(mask,'after_log_sha256','pad_mask_reopen_log')
        check(mask.get('changed_pad_count')==len(p['pad_solder_mask_overrides']) and mask.get('pad_count')==243,'pad_mask_repair_count_wrong')
        check(mask.get('untouched_pad_mask_and_all_pad_paste_preserved') is True,'pad_mask_or_paste_unexpected_delta')
    check(p.get("routing_complete") is True,"candidate_not_completely_routed")
    for key in ("candidate_audit","native_audit","rule_audit","surface_audit","paste_audit","canonical_audit","shield_audit"):
        check(report[key].get("passed") is True,"audit_not_passed",key)
        check(not report[key].get("errors") and not report[key].get("failures"),"audit_contains_failures",key)
        binding(report[key],"candidate_sha256","candidate")
    shield=report['shield_audit']
    check(shield.get('grounded_on_both_layers') is True,'candidate_shields_not_grounded')
    check(all(g>=.20 for g in shield.get('minimum_signal_clearance_mm',{}).values()) and set(shield.get('minimum_signal_clearance_mm',{}))=={'5','32'},'candidate_shield_signal_clearance_not_verified')
    for key in ("native_audit","rule_audit","surface_audit","paste_audit","model_audit"):
        binding(report[key],"native_sha256","native")
    check(report["model_audit"].get("passed") is True and not report["model_audit"].get("errors"),"model_audit_not_passed")
    binding(native,"schematic_sha256","schematic");binding(native,"candidate_audit_sha256","candidate_audit")
    binding(native,"live_compile_sha256","compile_log")
    binding(report["rule_audit"],"candidate_audit_sha256","candidate_audit")
    binding(report["canonical_audit"],"library_sha256","library")
    binding(report["schematic_validation"],"schematic_sha256","schematic")
    binding(snapshot,"source_sha256","native")
    check(report["schematic_validation"].get("nets")==p["nets"],"schematic_net_map_differs")
    check(hashes["native"]!=FROZEN and hashes["baseline"]==FROZEN,"native_revision_not_applied_or_backup_changed")
    check(native.get("native_connection_count")==0,"stored_connections_nonzero")
    check(native.get("layer_stack_preserved") is True,"native_stack_not_preserved")
    check(native.get("ground_copper_connected") is True and native.get("ground_copper_component_count")==1,"ground_not_connected")
    check(native.get("component_SourceUniqueIDs_match") is True,"component_schematic_identity_mismatch")
    check(native.get("live_compile_membership_verified") is True and native.get("live_compile",{}).get("VIOLATION_COUNT")=="0","native_compile_or_membership_failed")
    dc_layers=native.get("DC_internal_layers",{})
    expected_dc={f"DC{i:02}" for i in range(1,39)}
    check(set(dc_layers)==expected_dc and all(v in ([2],[4]) for v in dc_layers.values()),"38_DC_single_internal_layer_failed",dc_layers)
    direct=native.get("direct_QD_via_in_pad",[])
    check(len(direct)==22 and all(v.get("drill_within_pad") and v.get("center_in_pad") and v.get("endpoint_via_count")==1 for v in direct),"direct_QD_endpoint_vias_failed")
    rf=native.get("saved_RF_geometry",{});dc=native.get("saved_DC_geometry",{})
    check(rf.get("passed") is True and rf.get("RF_signal_vias")==0 and rf.get("net_count")==32,"saved_RF_no_via_topology_failed")
    check(dc.get("passed") is True and not dc.get("failures"),"saved_DC_spacing_envelopes_failed")
    check(len(dc.get("SMP_envelopes",[]))==32 and len(dc.get("resistor_envelopes",[]))==32,"saved_DC_envelope_coverage_incomplete")
    rf_vias=[v for v in snapshot.get("vias",[]) if (v.get("net") or "").startswith(("S","MW"))]
    check(not rf_vias,"snapshot_RF_vias_present",rf_vias)
    for net in expected_dc:
        layers={v["layer"] for v in snapshot.get("tracks",[]) if v.get("net")==net and v["layer"] in (2,4)}
        check(len(layers)==1,"snapshot_DC_single_layer_failed",dict(net=net,layers=sorted(layers)))
    try:contact_pool=assert_plan_contacts(p);via_groups(p)
    except AssertionError as exc:contact_pool={"passed":False};check(False,"candidate_structural_invariant",str(exc))
    check(native.get("ZIF_contact_pool",{}).get("passed") is True and native["ZIF_contact_pool"].get("used_contacts")==contact_pool.get("used_contacts"),"saved_ZIF_contact_pool_differs")
    surface=report["surface_audit"].get("checks",{});drc=surface.get("native_DRC",{});rings=surface.get("SMP_rings",{})
    binding(drc,"report_sha256","DRC")
    check(drc.get("categories")==23 and drc.get("violation_sum")==0 and drc.get("via_style_rule_count")==4 and drc.get("early_stop") is False,"native_DRC_not_complete_zero",drc)
    check(len(drc.get("summary",[]))==23 and all(v.get("violations")==0 for v in drc.get("summary",[])),"native_DRC_summary_invalid")
    check(rings.get("passed") is True and len(rings.get("rings",[]))==16 and all(v.get("nonempty") and v.get("symmetric") for v in rings.get("rings",[])),"SMP_ring_semantics_failed")
    check(report["rule_audit"].get("via_rule_count")==4 and report["rule_audit"].get("inherited_rule_limits_preserved") is True,"native_rule_coverage_or_preservation_failed")
    log=files["validation_log"].read_text()
    check(all(s in log for s in ("REOPENED","COMPLETE","POST_DRC_SAVED_CONNECTION_COUNT=0")) and "STOP_" not in log,"native_save_reopen_log_incomplete")
    manifest=report["paste_manifest"];paste=report["paste_audit"]
    for field,key in (("pcb_sha256","native"),("project_sha256","project"),("candidate_sha256","candidate"),("candidate_audit_sha256","candidate_audit"),
        ("saved_revision_audit_sha256","native_audit"),("canonical_library_audit_sha256","canonical_audit"),("QD_library_sha256","library"),("schematic_sha256","schematic")):
        binding(manifest,field,key)
    for field,key in (("source_manifest_sha256","paste_manifest"),("QD_library_sha256","library"),("native_export_log_sha256","paste_log")):
        binding(paste,field,key)
    check(paste.get("via_specific_paste_absent") is True and paste.get("explicit_paste_object_count")==0,"extra_paste_present")
    check(paste.get("normal_pad_apertures")=={"35":53,"36":64},"normal_SMD_paste_count_differs")
    check(len(paste.get("cam_checks",[]))==2 and paste.get("export_token")==manifest.get("export_token"),"paste_CAM_run_mismatch")
    for cam in paste.get("cam_checks",[]):
        file=Path(cam["file"]);check(file.is_file() and sha(file)==cam["sha256"],"paste_CAM_changed",str(file))
    promotion=report["promotion"];binding(promotion,"candidate_sha256","candidate");binding(promotion,"project_unchanged_sha256","project")
    for item in promotion.get("changed",[]):
        file=PROJECT/item["name"];check(file.is_file() and sha(file)==item["sha256"],"promoted_source_changed",item["name"])
    with files["pin_table"].open(newline="",encoding="utf-8") as stream:
        reader=csv.DictReader(stream);rows=list(reader);columns=reader.fieldnames
    expected_rows=[{k:"" if row.get(k) is None else str(row[k]) for k in columns} for row in p["pinmap"]]
    check(rows==expected_rows,"saved_pin_table_differs")
    source_checks={}
    for name,value in report["provenance"]["source_sha256"].items():
        file=ROOT/"QSTL_24DC_4MW_PCB"/name;source_checks[name]=file.is_file() and sha(file)==value
    check(source_checks and all(source_checks.values()),"original_sources_changed",source_checks)
    check(native.get("source_files_unchanged")==source_checks and report["model_audit"].get("original_unchanged") is True,"source_preservation_reports_disagree")
    for name,value in report["backup_manifest"].items():
        file=HERE/"before_rotation"/name;check(file.is_file() and sha(file)==value,"pre_revision_backup_changed",name)
    check(report["backup_manifest"].get(NAME+".PrjPcb")==hashes["project"],"project_membership_changed")
    for name,path in files.items():check(sha(path)==hashes[name],"evidence_changed_during_completion_audit",name)
    if errors:
        print(json.dumps(dict(passed=False,status="COMPLETION_EVIDENCE_FAILED",errors=errors,completion_report_written=False),indent=2))
        raise SystemExit(1)
    output=dict(passed=True,completion=True,status="SAVED_NATIVE_REVISION_VERIFIED",verified_utc=datetime.now(timezone.utc).isoformat(),
        candidate_sha256=hashes["candidate"],native_sha256=hashes["native"],schematic_sha256=hashes["schematic"],library_sha256=hashes["library"],
        project_sha256=hashes["project"],evidence={k:dict(path=str(files[k]),sha256=v) for k,v in hashes.items()},
        DC_channels=38,DC_single_internal_layer=True,RF_channels=16,RF_signal_vias=0,stored_connections=0,
        native_DRC_categories=23,native_DRC_violations=0,source_preservation=source_checks,
        warnings=native.get("warnings",[]),fabrication_release=False,
        scope="Complete saved revision audit chain. Does not order fabrication, publish supplier files or certify unperformed physical prototype tests.")
    (HERE/"revision_completion_audit.json").write_text(json.dumps(output,indent=2))
    print(json.dumps(output,indent=2))


if __name__=="__main__":main()
