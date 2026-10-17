# QD via lands and capacitor 3D registration

Saved native PCB SHA256: `97581f7c13d63e503f25b2d211d5f3593e22ee7ad6817f86f47d3dbe955f0d7f`.

## Capacitor 3D correction

The eight tilted Bottom capacitors had the wrong sign of model Z rotation. Their actual 3D meshes were mirrored relative to their pad axes. The earlier model check used the cached 2D component-body outline; that outline did not describe the displayed mesh orientation and remained unchanged after the correction. The earlier conclusion that all bodies were aligned was therefore insufficient.

Only `MODEL.3D.ROTZ` changed on these eight component bodies:

| Reference | Previous Z rotation (degrees) | Corrected Z rotation (degrees) |
|---|---:|---:|
| C35 | 120 | 240 |
| C31 | 60 | 300 |
| C09 | 150 | 210 |
| C30 | 30 | 330 |
| C28 | 330 | 30 |
| C12 | 240 | 120 |
| C16 | 300 | 60 |
| C11 | 210 | 150 |

For the saved Bottom models, the projected long-axis direction is the negative of the stored Z rotation, modulo 180 degrees. All 16 capacitor axes now match their pad axes within 0.000051 degrees. Actual Altium 3D inspection confirmed the corrected tilted meshes after save/reopen, with all 16 capacitors visible in the final screenshot. The Yageo CC1206JKNPO9BN104 maximum body geometry (3.50 x 1.80 x 1.80 mm), embedded STEP hashes, origins and heights remain unchanged. No component, pad or route was moved.

- [Actual saved Altium 3D view, all 16 capacitors](Altium_All_16_Cap_Models.png)
- [Actual Altium 3D close-up of all eight tilted capacitors](Altium_Corrected_Cap_3D_Closeup.png)
- [User-supplied image before correction](User_Reported_Before.png)

These are native GUI screenshots, not regenerated illustrations. The orange object is Altium's on-screen navigation indicator.

## QD via copper lands

All 22 QD direct-DC terminal via lands were reduced from nominal 0.350 to **0.300 mm**. Their nominal 0.200 mm drills, XY positions, nets and L1-L6 span are unchanged. The other 1,568 vias are unchanged, including all 1,514 L5-L6 RF shield microvias. The 38 rectangular QD pads remain 0.260 mm wide.

The [JLCPCB via capability table](https://jlcpcb.com/capabilities/pcb-capabilities), checked on 2026-10-17, specifies at least 0.100 mm land-minus-hole diameter difference, corresponding to a 0.050 mm radial annular ring. This edit uses that minimum while preserving the existing drill. Native grid rounding is upward: saved land **0.30000194 mm**, drill **0.19999960 mm**, radial ring **0.05000117 mm**. The common diameter and all 32 native layer-diameter cells were checked.

The dedicated QD via-style rule's preferred/minimum/maximum land width was updated to the new diameter. Its drill fields, scopes, enabled state and priority were retained; the other 43 rules are unchanged. No genuine DRC failure was suppressed.

Maximum land protrusion beyond the rectangular pad decreased from **0.074098 to 0.049100 mm**. Some protrusion remains because the 0.300 mm land is wider than the 0.260 mm pad and existing centres have offsets. See the [saved before/after detail](QD_Via_Land_Before_After.png) and [all 22 measured changes](QD_Via_Changes.csv).

## Saved validation

- Altium native save/reopen DRC: **0 violations**; stored connections: **0**.
- All **71 named nets** connected and matched to the compiled schematic; 15 unused ZIF contacts retained; enumerated compiler violations: **0**.
- **2126** bounded-change and geometry checks passed. Pad, track, arc, region, component and physical stack streams are byte-identical to the baseline. Schematic and canonical pin map hashes are unchanged.
- Minimum clearance from a reduced QD land to a foreign trace: **0.164387 mm**; foreign pad: **0.179268 mm**; foreign via: **0.205810 mm**; GND: **0.225274 mm**.
- Layer roles, one internal layer per DC net, RF routing without signal vias, all 32 L5 C/R openings and QD ground exclusions are retained.
- Restored **0.90 mm C/R solder-control margins**, compact Top via covers, RF/SMP/ZIF protection, normal pad openings and exposed mounting/QD bonding areas remain unchanged.
- Fresh native mask CAM agrees with the saved mask regions/openings within 0.0003 mm; all 22 Top QD vias are fully covered.
- Fresh native paste CAM has exactly 53 Top and 64 Bottom normal SMD apertures; no via/QD/SMP/mounting paste is present.

The native file remains a source document of the existing QD4_2SET_38PAD project. This update does not issue a new production Gerber package or update an order/cart. The minimum via geometry result is not a blanket fabrication approval for the whole board.

Audit evidence: [native DRC](../../script/qd_via_land_20261017/Native_DRC.html), [native connectivity](../../script/qd_via_land_20261017/saved_native_audit.json), [bounded changes](../../script/qd_via_land_20261017/change_audit.json), [support checks](../../script/qd_via_land_20261017/support_audit.json), [mask CAM](../../script/qd_via_land_20261017/mask_cam_audit.json).
