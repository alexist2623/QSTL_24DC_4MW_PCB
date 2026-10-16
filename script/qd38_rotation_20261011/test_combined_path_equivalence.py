"""Focused adversarial checks for the saved RF normalization comparison."""
from copy import deepcopy
from pathlib import Path
import json

from combined_path_equivalence import inspect_combined_path_equivalence


def fixture():
    plan = dict(tracks=[dict(net="MW01", layer=32, width=.11, a=[.5, .75], b=[1, .75]),
                        dict(net="MW01", layer=32, width=.11, a=[1.25, 1], b=[1.25, 1.5])],
                arcs=[dict(net="MW01", layer=32, width=.11, cx=1, cy=1, radius=.25, start_angle=270, end_angle=360)],
                physical_pads=[dict(ref="C01", pin="2", net="MW01", layer=32, shape="rect", x=.5, y=.75, sx=.2, sy=.2, rotation=0),
                               dict(ref="Q1", pin="1", net="MW01", layer=32, shape="rect", x=1.25, y=1.5, sx=.2, sy=.2, rotation=0)])
    native = dict(tracks=[dict(net=t["net"], layer=t["layer"], width=t["width"], x1=t["a"][0], y1=t["a"][1], x2=t["b"][0], y2=t["b"][1]) for t in plan["tracks"]],
                  arcs=deepcopy(plan["arcs"]),
                  pads=[dict(component=p["ref"], number=p["pin"], net=p["net"], layer=p["layer"], shape=2,
                             x=p["x"], y=p["y"], size_x=p["sx"], size_y=p["sy"], rotation=0) for p in plan["physical_pads"]])
    return native, plan


def main():
    rows = []
    for name in ("exact", "arc_split_and_reversed_tracks", "pad_covered_trim", "changed_radius", "shifted_arc", "shifted_external_track"):
        native, plan = fixture()
        should_pass = name in ("exact", "arc_split_and_reversed_tracks", "pad_covered_trim")
        if name == "arc_split_and_reversed_tracks":
            first = native["arcs"][0]
            second = deepcopy(first)
            first["end_angle"], second["start_angle"] = 315, 315
            native["arcs"].append(second)
            for t in native["tracks"]:
                t["x1"], t["x2"], t["y1"], t["y2"] = t["x2"], t["x1"], t["y2"], t["y1"]
        elif name == "pad_covered_trim":
            native["tracks"][0]["x1"] += .04
        elif name == "changed_radius":
            native["arcs"][0]["radius"] += .001
        elif name == "shifted_arc":
            native["arcs"][0]["cx"] += .001
        elif name == "shifted_external_track":
            native["tracks"][0]["y1"] += .001
            native["tracks"][0]["y2"] += .001
        result = inspect_combined_path_equivalence(native, plan)
        rows.append(dict(name=name, expected_pass=should_pass, actual_pass=result["passed"],
                         passed=result["passed"] == should_pass, failures=result["failures"]))
    output = dict(passed=all(r["passed"] for r in rows), tests=rows)
    path = Path(__file__).with_name("combined_path_equivalence_tests.json")
    path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if output["passed"] else 2)


if __name__ == "__main__":
    main()
