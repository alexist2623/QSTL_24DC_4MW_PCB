"""Read-only verification of the saved rule partition and inherited constraints."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from prepare_native_revision_rules import BASELINE, DC_RULE, FROZEN, HERE, QD_RULE, TARGET, ZIF_RULE, read_rules, rule_plan, sha
from revision_invariants import assert_plan_contacts


def numeric_mm(value):
    match=re.fullmatch(r"([-+0-9.eE]+)(mil|mm)",value)
    assert match, f"Unrecognized rule distance {value!r}"
    return float(match[1])*(.0254 if match[2]=="mil" else 1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--audit",type=Path,required=True)
    args=parser.parse_args()
    candidate=args.candidate.resolve(); audit_path=args.audit.resolve()
    plan=json.loads(candidate.read_text());audit=json.loads(audit_path.read_text())
    assert audit.get("passed") is True and audit.get("candidate_sha256")==sha(candidate)
    assert plan.get("routing_complete") is True
    assert_plan_contacts(plan)
    assert sha(BASELINE)==FROZEN
    native_hash=sha(TARGET);before=read_rules(BASELINE);saved=read_rules(TARGET)
    desired=rule_plan(plan);errors=[]
    def check(condition,issue,detail=None):
        if not condition:errors.append(dict(issue=issue,detail=detail))
    check(set(saved)==set(before)|{QD_RULE,DC_RULE},"saved_rule_names_changed",dict(before=sorted(before),saved=sorted(saved)))
    for name,old in before.items():
        new=saved.get(name,{})
        # Adding a routing-via rule can renumber that category's priorities.
        # Its scopes remain disjoint. No constraint limit or enable flag is
        # omitted from this comparison.
        allowed={"PRIORITY"} if old["RULEKIND"] in ("RoutingVias","Clearance") else set()
        if name in ("RoutingVias",ZIF_RULE,"DC_GND_GAP_0P2"):allowed.add("SCOPE1EXPRESSION")
        if name=="DC_GND_GAP_0P2":allowed.add("SCOPE2EXPRESSION")
        differences={k:[old.get(k),new.get(k)] for k in set(old)|set(new) if k not in allowed and old.get(k)!=new.get(k)}
        check(not differences,"inherited_rule_changed",dict(name=name,differences=differences))
    for name,scope in (("RoutingVias",desired["general_scope"]),(ZIF_RULE,desired["zif_scope"]),(QD_RULE,desired["direct_qd_scope"]),("DC_GND_GAP_0P2",desired["dc_ground_scope"])):
        check(saved.get(name,{}).get("SCOPE1EXPRESSION")==scope,"via_scope_mismatch",dict(name=name,expected=scope,actual=saved.get(name,{}).get("SCOPE1EXPRESSION")))
    via_rules=[r for r in saved.values() if r.get("RULEKIND")=="RoutingVias"]
    check(saved.get("DC_GND_GAP_0P2",{}).get("SCOPE2EXPRESSION")==desired["dc_ground_second_scope"],"DC_GND_second_scope_mismatch",saved.get("DC_GND_GAP_0P2",{}).get("SCOPE2EXPRESSION"))
    check(len(via_rules)==4,"via_rule_count",len(via_rules))
    dc_rule=saved.get(DC_RULE,{})
    for field,expected in (("RULEKIND","Clearance"),("NETSCOPE","DifferentNets"),("LAYERKIND","SameLayer"),
                           ("ENABLED","TRUE"),("SCOPE1EXPRESSION",desired["dc_pair_scope"]),("SCOPE2EXPRESSION",desired["dc_pair_scope"])):
        check(dc_rule.get(field)==expected,"DC_pair_rule_definition",dict(field=field,actual=dc_rule.get(field),expected=expected))
    for field in ("GAP","GENERICCLEARANCE"):
        try:actual=numeric_mm(dc_rule[field])
        except (KeyError,AssertionError):actual=None
        check(actual is not None and abs(actual-.10)<1e-5,"DC_pair_rule_gap",dict(field=field,actual_mm=actual))
    check(not dc_rule.get("OBJECTCLEARANCES"),"DC_pair_rule_unexpected_object_matrix",dc_rule.get("OBJECTCLEARANCES"))
    check(int(dc_rule.get("PRIORITY","9999"))<int(saved.get("Clearance",{}).get("PRIORITY","0")),"DC_pair_rule_does_not_override_general_clearance")
    check(int(saved.get("DC_GND_GAP_0P2",{}).get("PRIORITY","9999"))<int(saved.get("Clearance",{}).get("PRIORITY","0")),"DC_GND_rule_does_not_override_general_clearance")
    dimensions={"RoutingVias":(.5,.25,"Through Hole"),ZIF_RULE:(.4,.2,"Through Hole"),
                QD_RULE:(.4,.2,"Through Hole"),"RF_SHIELD_L5_L6":(.25,.1,"Blind Buried (Adjacent Layers)")}
    for name,(land,hole,style) in dimensions.items():
        row=saved.get(name,{})
        check(row.get("ENABLED")=="TRUE","disabled_via_rule",name)
        check(row.get("SCOPE2EXPRESSION")=="All","via_second_scope",name)
        check(row.get("VIASTYLE")==style,"via_style_mismatch",name)
        for field,expected in (("WIDTH",land),("MINWIDTH",land),("MAXWIDTH",land),("HOLEWIDTH",hole),("MINHOLEWIDTH",hole),("MAXHOLEWIDTH",hole)):
            try:actual=numeric_mm(row[field])
            except (KeyError,AssertionError):actual=None
            check(actual is not None and abs(actual-expected)<1e-5,"via_dimension_rule_mismatch",dict(name=name,field=field,actual_mm=actual,expected_mm=expected))
    check(sha(TARGET)==native_hash,"native_file_changed_during_rule_audit")
    report=dict(passed=not errors,native_file=str(TARGET),native_sha256=native_hash,
                candidate_sha256=sha(candidate),candidate_audit_sha256=sha(audit_path),
                baseline_sha256=sha(BASELINE),saved_rule_count=len(saved),via_rule_count=len(via_rules),
                expected_native_DRC_instances=23,inherited_rule_limits_preserved=not any(e["issue"]=="inherited_rule_changed" for e in errors),
                desired_partition=desired,errors=errors,completion=False,
                limitation="This checks saved rule definitions. Actual copper clearance and native full DRC results remain separate required checks.")
    (HERE/"saved_revision_rules.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if errors:raise SystemExit(1)


if __name__=="__main__":main()
