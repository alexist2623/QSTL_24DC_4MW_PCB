# R/C placement, mask rectangles and corrected shield offsets

Final saved original PCB SHA-256: `6dd4737a82af333bc0672e1e72a8cd007b643c2699f0f8daae56ab9bb5d2c6a4`.

- R3/C3 and R4/C4: +2.0 mm Y; minimum QD pad gap 2.05 mm.
- R1/C1 and R5/C5: +1.0 mm Y. R1/C1 additionally -0.35 mm X. A proposed -0.70 mm X move failed offline clearance checks and was not applied.
- Retained R/C mask margin: 0.30 to 0.90 mm, exact group rectangles. Bottom ZIF array: rectangular mask, 0.40 mm land margin.
- Shield clearance: RF copper edge to laser-hole edge 0.33 mm. Land clearance 0.255 mm; centre offset 0.435 mm. 470 L5-L6 shields, 0.15 mm nominal land-edge spacing.
- SMP rings: 13 equal-angle positions with two symmetric RF-exit omissions, 11 vias per active SMP. No shield land crosses an R/C two-pad/body hull.
- All six mounts have bare surrounding rings on both faces and solid GND joins on L1/L3/L5/L6; SMP mask and normal SMD paste remain.
- Saved copper: 37 connected nets; zero connection lines; 15 native DRC checks, zero violations.

`before.PcbDoc` is the original pre-turn recovery copy. `prepare_move.py`, `ApplyMove.pas`, `ApplyShields.pas` and `FixLabels.pas` are one-time mutation records, not general rerunnable tools. The first native attempt stopped on an uninitialized interface comparison before route replacement; the corrected continuation used explicit Boolean presence flags and absolute destinations, then saved successfully. All final geometry was independently checked.

`verify_final.py`, `verify_refinements.py`, `audit_connectivity.py`, `ReopenAudit.pas` and `AuditPaste.pas` validate the saved source. `publish_outputs.py` and `finalize_docs.py` update previews and hash-bound fabrication companions. Earlier reports are historical. The original schematic and QD library were unchanged in this revision. No Git push or supplier submission was performed.
