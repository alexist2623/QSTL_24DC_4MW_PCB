"""Shared structural checks for the authorized 38-contact carrier revision."""
from __future__ import annotations

from collections import Counter


def contact_pool(contacts):
    """Keep the 24 legacy physical contacts; chip terminal assignment is free."""
    values = [int(p) for p in contacts]
    used = set(values)
    required = set(range(2, 49, 2))
    odds = {p for p in used if p % 2}
    errors = []
    if len(values) != len(used) or len(used) != 38:
        errors.append("Expected 38 distinct DC contact numbers")
    if used - set(range(1, 52)):
        errors.append("Contact number outside 1..51")
    if used - odds != required:
        errors.append("All legacy even contacts 2..48 must be used, with pin 50 unused")
    if odds != set(range(1,28,2)):
        errors.append("The odd extension contacts must be exactly 1,3,...,27")
    return dict(passed=not errors, used_contacts=sorted(used),
                legacy_even_contacts=sorted(required), extension_odd_contacts=sorted(odds),
                pin_50_unused=50 not in used, errors=errors)


def assert_plan_contacts(plan):
    report = contact_pool(row["zif_pin"] for row in plan["pinmap"])
    assert report["passed"], report["errors"]
    assigned = {int(p["pin"]): p["net"] for p in plan["physical_pads"]
                if p["ref"] == "J1" and p["net"] is not None}
    assert set(assigned) == set(report["used_contacts"]), "J1 pad nets differ from the authorized contact pool"
    assert len(set(assigned.values())) == 38 and all(n.startswith("DC") for n in assigned.values())
    for net, members in plan["nets"].items():
        actual = [int(m[3:]) for m in members if m.startswith("J1-")]
        expected = [pin for pin, name in assigned.items() if name == net]
        assert actual == expected, f"J1 net membership differs for {net}"
    return report


def via_groups(plan):
    groups = {"zif": [], "direct_qd": [], "resistor": [], "shield": list(plan["shield_vias"])}
    for via in plan["vias"]:
        label = via["label"]
        key = "zif" if label.startswith("J1-") else "direct_qd" if label.startswith("Q1-") else "resistor" if label.startswith("R") and label.endswith("-2") else None
        assert key is not None, f"Unexpected signal via endpoint {label}"
        groups[key].append(via)
    expected = {"zif": (38, .4, .2, 1, 32), "direct_qd": (22, .4, .2, 1, 32),
                "resistor": (16, .5, .25, 1, 32), "shield": (len(groups["shield"]), .25, .1, 5, 32)}
    for key, (count, land, hole, low, high) in expected.items():
        rows = groups[key]
        assert len(rows) == count and count > 0, f"Incorrect {key} via count"
        assert all(abs(v["diameter"]-land)<1e-8 and abs(v["hole"]-hole)<1e-8 and
                   (v["low"],v["high"])==(low,high) for v in rows), f"Incorrect {key} via geometry"
    assert len({v["net"] for v in groups["direct_qd"]}) == 22
    assert len({v["net"] for v in groups["resistor"]}) == 16
    assert not ({v["net"] for v in groups["direct_qd"]} & {v["net"] for v in groups["resistor"]})
    assert all(v["net"]=="GND" for v in groups["shield"])
    assert not any(v["net"].startswith(("S","MW")) for v in plan["vias"]), "RF signal vias are forbidden"
    assert all(t["layer"]==32 for field in ("tracks","arcs") for t in plan.get(field,[]) if t["net"].startswith(("S","MW"))), "RF must remain on Bottom"
    assert Counter(v["net"] for v in plan["vias"]) == Counter({n:2 for n in plan["nets"] if n.startswith("DC")})
    pads = {(p["ref"],p["pin"]):p for p in plan["physical_pads"]}
    for key in ("direct_qd", "resistor"):
        for via in groups[key]:
            ref,pin=via["label"].split("-")
            assert pads[ref,pin]["net"] == via["net"], "Via endpoint net mismatch"
    return groups
