# Alignment saved-evidence workflow

This directory is a new audit namespace. No helper here invokes Altium or
modifies a native design. The prior verified `1ac42a...` PCB, `835347...`
candidate and old completion report remain immutable baseline evidence.

## Inputs required after native save/reopen

- `alignment_full_candidate.json` and its hash-bound passing
  `alignment_full_audit.json` (other names may be passed explicitly).
- `alignment_delta_manifest.json`, with the exact final candidate hash and
  a reviewed local edit region. Do not derive the allowed region from observed
  differences after a native edit.
- Fresh `native_validation.txt`, `native_compile.txt` and `Native_DRC.html`
  generated in this directory by the parent's new validation helper.
- Saved project PCB/library plus unchanged schematic, SchLib, project and pin
  table in `QSTL_QD4_2SET_38PAD`. Native validation is expected to have saved,
  reopened and run all 23 DRC instances without suppressing real failures.

Manifest schema (values below are illustrative, not a generated approval):

```json
{
  "candidate_file": "absolute path to alignment_full_candidate.json",
  "candidate_sha256": "actual final SHA256",
  "inner_alignment": "nearest_corner_per_side",
  "outer_alignment": "not_requested",
  "qd_endpoint_via": {
    "count": 22,
    "baseline_land_mm": 0.4,
    "land_mm": 0.35,
    "drill_mm": 0.2,
    "low": 1,
    "high": 32
  },
  "allowed_rule_changes": [
    {
      "name": "QD38_QD_VIA_0P4_0P2",
      "field": "WIDTH",
      "before": "exact baseline native string",
      "after_mm": 0.35
    }
  ],
  "edit_region": {"type": "Polygon", "coordinates": []}
}
```

The actual via land is not selected by this workflow. A retained 0.40 mm land
uses an empty rule-change list. If the reviewed candidate uses 0.35 mm QD
lands, declare WIDTH, MINWIDTH and MAXWIDTH separately with their exact prior
values. A necessary QD rule spatial-scope adjustment may be declared with an
exact `before` and `after` string. No other rule field is allowed to change.
All unrelated via groups, drill sizes, spans, counts and rule definitions
remain strict. A missing or hash-stale declaration fails.

The current geometric test means the nearest cavity-facing corner/supporting
extent is common on each side, with corner-category pads assigned to their
existing horizontal side. It preserves all 0.8 x 0.25 mm rectangles and bond
rays. This is not a claim that every tilted short edge or outer edge lies on
one line. If the user requests both inner and outer boundaries, revise this
explicit contract before running it; do not mark that request as satisfied by
the existing test.

## Run and outputs

```powershell
& ../.venv/Scripts/python.exe ./run_alignment_saved_audits.py
```

Run from this directory. Stages are `copper,surface,models,canonical,rules,delta`.
The runner reuses reviewed read-only code in isolated Python subprocesses,
sets its evidence directory here, and verifies old evidence was not changed.
It never launches the old full-board native updater.

- `saved_revision_audit.json` / `saved_revision_snapshot.json`: actual saved
  copper, zero stored connections, schematic membership, all 38 one-layer DC
  channels, no extra DC transitions, zero RF signal vias, contained direct-QD
  drills, route geometry and source/stack preservation against `1ac42a...`.
- `saved_revision_surface.json`: saved masks, GND exclusion, shield rings,
  shield clearance, direct mounting GND and complete zero-violation DRC.
- `saved_revision_models.json`: embedded model hashes and transforms.
- `canonical_library_audit.json`: canonical library corresponds to actual
  planned Bottom/+90 Q1 geometry.
- `saved_alignment_rules.json`: exact baseline rules except explicitly
  declared QD-via changes; every moved QD endpoint remains in its actual rule.
- `saved_alignment_delta.json`: common inward boundary, 0.20 mm cavity gap,
  dimensions/rays, unchanged nets/components/schematic/project/pin table and
  model transforms, all pad mask/paste cache bytes unchanged, and signal
  changes confined to the declared local region.
- `alignment_saved_audit_workflow.json`: stage outcomes and hashes. This is
  not a final completion report by itself.

The optional `paste` stage reuses the native CAM verifier with this directory's
fresh `revision_paste_audit_source_manifest.json`, fresh native export log and
new CAM paths. A separate parent preparation/export step is required. Old CAM
or old native logs must not stand in for evidence for the new saved hash.
Final completion must also bind all resulting reports, updated canonical
library, actual CAM files and source-preservation evidence. No successful
post-save result has been claimed while the candidate/native update is pending.

## Retained mask field and local ground contours

The old QD mask opening is intentionally larger than the aligned pad field.
`alignment_surface_contract.py` requires the candidate mask-family fields and
all fourteen actual saved explicit mask-region records to remain unchanged.
The retained field must cover the new pad bounding rectangle plus its 0.15 mm
margin and the cavity. It is also used as the exception boundary for the
unchanged RF and R/C mask protection. No opening is enlarged or regenerated.
The new ground contours are prequantized and are checked without applying
the old global 0.001 mm simplification a second time.

## Final completion evidence

Run `audit_alignment_completion.py` only after source promotion, saved audits,
fresh paste export/verification and review-image rendering. It writes
`alignment_completion_audit.json` only when all checks pass. Missing or stale
evidence exits with an explanation and does not create a passing report.

`alignment_source_promotion.json` binds `candidate_sha256`, `library_sha256`
and `project_unchanged_sha256`. Its `changed` list contains entries with
`path` or project-relative `name` and `sha256`; `unchanged_sources` maps
source paths or project-relative filenames to their unchanged hashes.

`alignment_review_images.json` binds `candidate_sha256` and `native_sha256`;
its `images` list contains `path`, `sha256` and `view`. At least two distinct
views must be present. This binds review images to the revision; it does not
replace physical geometry or saved-native verification.

Completion verifies only this saved local alignment, its source preservation
and audit chain. It does not release fabrication, place an order, or certify
an unperformed prototype test or impedance measurement.
