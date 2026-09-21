# Passive 3D model

`R_0603_1608Metric.step` is the generic 1.6 × 0.8 × 0.45 mm resistor from the [official KiCad 3D model library](https://gitlab.com/kicad/libraries/kicad-packages3D/-/blob/master/Resistor_SMD.3dshapes/R_0603_1608Metric.step), retrieved 2026-09-20. It represents the package, not a manufacturer-specific part.

The STEP header credits the 2018 kicadStepUp team and supplies CC BY-SA 4.0 with the KiCad libraries exception for electronic designs. The original header and model are retained without modification. SHA-256: `1875571c326d0d9e96f36b4efeb8094068ef7619f0a449c781caf0b49c2e5861`.

The model is embedded in R1–R6 and `Passives_0603.PcbLib`. Existing capacitor STEP geometry is retained and aligned with the pad axis in the board and `Capacitors_0402.PcbLib`. See `../docs/model_validation.json` for saved-file checks.
