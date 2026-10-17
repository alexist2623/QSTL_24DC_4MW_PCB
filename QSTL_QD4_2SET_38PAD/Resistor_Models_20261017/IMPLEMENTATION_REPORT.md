# Resistor 3D registration correction

Current saved PCB SHA256: `edd42f24edac77e77edbf044c594f1bbccf6f832195d7200ffb0dcccd57e6060`.

Eight tilted Bottom resistor meshes retained the same incorrect rotation sign previously found in the capacitors. The capacitor-only correction did not change these resistors. This follow-up corrects their model Z rotations without moving their copper footprints or component origins.

| Reference | Previous model Z (degrees) | Corrected model Z (degrees) |
|---|---:|---:|
| R35 | 30 | 330 |
| R31 | 150 | 210 |
| R09 | 60 | 300 |
| R30 | 120 | 240 |
| R11 | 300 | 60 |
| R28 | 240 | 120 |
| R12 | 330 | 30 |
| R16 | 210 | 150 |

All 16 resistor and 16 capacitor projected long axes now agree with their two-pad axes within 0.000051 degrees, and each model remains centred between its pads. This includes the previously corrected capacitors. Actual Altium 3D inspection after save/reopen confirmed their terminals line up with the pads. The 0603 resistor geometry, 0.45 mm height and embedded STEP content are unchanged.

- [Saved and reopened Altium 3D view](Altium_RC_Models_Corrected.png)
- [Native view before resistor correction](Altium_Resistors_Before.png)

## Validation

- Native save/reopen DRC: **0 violations**; stored unconnected objects: **0**.
- 596 preservation/model checks passed. Only eight resistor model Z fields changed in both native body representations; all other 41 model instances, including all 16 capacitors, retain their transforms and embedded geometry.
- Pad, track, arc, via, region, component, net, rule and physical layer-stack streams are byte-identical to the validated baseline. All 44 design rules are unchanged.
- The 22 QD via lands remain nominal 0.300 mm with 0.200 mm drills; all 1,590 vias and 1,514 L5-L6 shield vias are unchanged.
- The schematic and pin mapping are byte-identical. All 71-net connectivity, one-layer-per-DC-net routing and RF signal-via exclusions from the validated baseline remain applicable because every electrical geometry and net stream is unchanged.
- All mask/paste-driving pad, via, region and rule data are unchanged. The baseline's verified normal paste apertures (53 Top / 64 Bottom), absence of via/QD/SMP/mounting paste, 0.90 mm C/R masks, QD mask openings and all 32 L5 C/R copper cutouts therefore remain. This mesh-only update does not generate new manufacturing CAM.
- Native save serialization also updates model indexing, save-time metadata and unused text buffer bytes; text strings and geometric fields remain unchanged. Embedded STEP identity was checked by decompressed content hashes rather than model stream indices.

[Native DRC](../../script/resistor_models_20261017/Native_DRC.html), [saved audit](../../script/resistor_models_20261017/audit.json), [serialization audit](../../script/resistor_models_20261017/serialization.json).
