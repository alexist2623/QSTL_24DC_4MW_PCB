# Guarded QD pad-alignment delta

Read-only implementation review, 2026-10-11. No native PCB, library, schematic,
candidate or existing completion evidence was changed by this review.

## Verified baseline to preserve

- Native copied PCB: `1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c`.
- Complete companion candidate: `835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495`.
- Canonical QD library: `21948bf605c8762cbc141ac7bd40f55f10d5df138c5afeb757d2092a5f776e0b`.
- Baseline completion report: `f75a4cf17b7ac6ed78704cc2a66c8ef7a91ec56707e511f3d551c60898596ab5`.
- `before_alignment/manifest.json` binds preserved copies of PCB, schematic,
  project, both libraries, both candidate copies, pin table and README.
- The saved native snapshot is
  `../qd38_rotation_20261011/saved_revision_snapshot.json`. Its source hash is
  the above native hash. It contains 50 components, 243 pads, 582 tracks,
  66 arcs, 744 vias and 49 model bodies. There are 76 full-through signal vias
  and 668 L5-to-Bottom GND shield vias.

The saved PCB has normalized/split RF records which differ from the candidate's
primitive decomposition. Preserve that actual geometry as the delta baseline;
do not recreate all signal routes from the older candidate records.

## Smallest safe design change

1. Freeze the newly agreed pad geometry and independently validate it before
   preparing a native script. Compare every Q1 terminal's position, dimensions,
   angle and shape. Record exactly which attributes are allowed to change.
2. Test each existing direct-DC QD via against its new pad before moving it.
   Retain its coordinates if its centre and complete 0.20 mm drill remain in
   the pad and every clearance still passes. There is no requirement that the
   via translate rigidly with the pad. Keep the existing 0.40/0.20 mm size,
   one endpoint via per direct channel, span and net. The sixteen RF QD pads
   must continue to have no signal via.
3. If a pad and retained endpoint still connect, retain the existing route.
   Otherwise reconnect only the affected endpoint approach, cutting at an
   explicit unchanged anchor outside the local edit region. For DC preserve
   its single internal layer, 0.125 mm width and real 45-degree turns. For RF
   preserve Bottom-only routing and genuine tangent arcs. Validate the union
   of edited and retained copper, including old split/overlap records.
4. Apply in-place Q1 pad changes by component designator and pin number. Move
   only the existing direct-QD vias that fail the new pad containment test.
   Identify a via uniquely by net, old quantized XY, span, diameter and drill,
   not iterator order. Identify a track/arc to remove or edit by its exact
   saved geometry, net, layer and width; require exactly one intended match,
   or an explicitly audited set when equivalent duplicate records exist.
5. The GND maps are explicit static copper regions, not automatic polygon
   pours. Any moved signal via/pad/trace requires recomputed GND clearances on
   every occupied layer. Prefer a local old/new obstacle-union replacement;
   otherwise regenerate the GND-region family and prove that its symmetric
   difference is confined to the authorized local edit region. Recheck the
   complete Bottom mask, QD opening and shield lands against the new geometry.
   Preserve unrelated GND regions/masks/shields when no geometric change is
   necessary. Preserve the cavity and its non-Top GND exclusion unchanged.
6. Patch a staged copy of the current canonical library, preserving existing
   pad records, primitive GUIDs and unrelated streams. For a native Bottom Q1
   at `(qx,qy)` and rotation +90 degrees, canonical Top coordinates are
   `library.x = qy - placed.y`, `library.y = qx - placed.x`, and
   `library.rotation = (90 - placed.rotation) mod 360`. The existing native
   library audit independently verifies this transform. Do not regenerate
   the schematic or SchLib for a physical-only pad geometry change: assert
   that nets, terminal numbers, pin table and schematic hashes are unchanged.
7. Update all companion representations coherently: Q1 physical pads,
   descriptive pad polygons/centres/inner ends/bond projections, the changed
   endpoint vias and endpoint/job references, local copper, and any changed
   surfaces. Do not leave old `pads` geometry beside new `physical_pads`.

## Native transaction safeguards

Use a new generator under this directory. Require the baseline native and
candidate hashes, a hash-bound passing geometry audit and the preserved
manifest before script generation and again before dispatch. A logged expected
hash is not itself a runtime hash check. Reopen the verified saved document
before applying to avoid an unverified in-memory revision.

The proven small-patch pattern in `prepare_mask_sliver_repair.py` is reusable:
find all targets first, abort if any guard fails, wrap edits in
`PCBServer.PreProcess`/`PostProcess`, and send `PCBM_BeginModify`/`EndModify`
for each edited object. Preserve each pad/via's solder/paste cache and net
metadata. Do not recreate Q1 or alter its component rotation, origin,
SourceUniqueID, project membership or net objects. Mark the document changed,
rebuild pad caches and update the view. Save/reopen/DRC is a separate explicit
step. Log exact before/after native coordinates and target counts.

## Existing helper hazards and reuse boundaries

| Helper in `qd38_rotation_20261011` | Limitation for this delta |
| --- | --- |
| `prepare_native_revision.py` | Hardcoded original `f8356d...` native and previous-snapshot/model guards. Deletes/recreates almost all non-J1 primitives and nets. Do not bypass the hash and run it on this revision. Reuse only reviewed primitive constructors or region serialization. |
| `prepare_native_revision_rules.py` | Requires target and baseline `f8356d...`. No rule change should be needed for a geometry-only correction. Preserve saved rule bytes/semantics and re-audit instead of reapplying. |
| `promote_verified_sources.py` | Requires `f8356d...` and replaces schematic, SchLib and library. Replace with a new delta-specific promotion manifest; unchanged sources must remain byte-identical. |
| `prepare_mask_sliver_repair.py` | Useful guarded in-place edit pattern, but fixed older native `c179d3...`, candidate `a8e960...`, eighteen R/C pads and old-folder paths. Do not execute unchanged. |
| `promote_mask_repair.py` | Limited to its exact eighteen-mask-cache repair and old promotion manifest. Not a QD geometry promoter. |
| `build_schematic_revision.py` | Stages a complete schematic/library using the original writer, generating new GUIDs. It is not a minimal library coordinate patch; output is fixed to the old `schematic_staging` folder. |
| `audit_canonical_library.py` | Geometric checks are reusable. Output is fixed to old `canonical_library_audit.json`; adapt an output-directory parameter or copy the CLI into this namespace before running. |
| `prepare_surfaces_rotated.py` | Reuses the full surface/shield generator; fixed old merged candidate/audit names and destination. Do not silently replace the accepted 668-shield layout; compare local deltas and preserve ring construction. |
| `prepare_native_revision_validation.py` | Proven save/reopen, connectivity, compile and DRC sequence; writes fixed old logs and runs CleanNet on every net. Stage a new version with new log paths and provenance. Keep geometric-union equivalence because CleanNet may split RF records again. |
| `audit_saved_revision.py` | Strong actual-copper, via, correspondence and RF/DC checks. Uses old-folder logs/outputs and old pre-rotation backup. Parameterize the evidence namespace while retaining old-source preservation checks. |
| `audit_saved_revision_rules.py` | Imports old helper constants, retains old rule-delta logic and fixed report location. For this revision also prove no rule change from `1ac42a...`. |
| `audit_saved_revision_models.py` / `audit_saved_revision_surface.py` | Read-only checks remain useful; outputs and several input paths are fixed to the old namespace. Preserve old completion reports. |
| `prepare_revision_paste_cam.py` / `verify_revision_paste_cam.py` | Require old-folder native/library audits and generate old-folder manifest/log paths. Stage a new evidence namespace and bind to the final new PCB/library hashes. |
| `audit_revision_completion.py` | Fixed old evidence paths, `f8356d...` baseline and previous mask-repair log/hash bindings. A new completion wrapper must bind this delta's reports and native hash while retaining the previous verified completion as baseline evidence. |
| `launch_native_script.py` | Constrains scripts to its own directory. A new launcher or explicit supported dispatch must target this new folder. No execution is part of this review. |

## Required proof before completion

- Actual saved pads and library reproduce the common end boundary while
  preserving numbering, specified pad dimensions and bond directions.
- Moved-via containment and foreign-pad/via/trace clearance pass; zero extra
  DC transitions or RF signal vias; exact ZIF contact pool and netmap remain.
- Saved DC and complete RF line/arc unions pass shape, topology, body-envelope
  and manufacturing clearances. Retained signal copper outside the declared
  local edit region is geometrically identical to the verified native baseline.
- Original board/stack, cavity documentation, unrelated components/models,
  rule settings, net membership and project membership are preserved.
- GND/mask geometry, QD exclusions, shielding and effective paste apertures are
  independently checked on the saved revision. No old hash-bound report is
  reused as evidence for a changed board or library.
- Save/reopen yields zero stored connections and the full native DRC is run
  without suppressing violations. Bind every completion report to the final
  native, candidate, schematic and library hashes.

The pad-alignment feasibility result and exact moved-terminal list are pending
from the placement agent. This review does not claim that every new endpoint
can be repaired without a local routing change.
