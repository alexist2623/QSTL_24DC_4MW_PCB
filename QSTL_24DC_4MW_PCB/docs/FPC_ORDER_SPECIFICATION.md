# FPC order specification

Updated: 2026-10-05. Units: mm unless stated otherwise.

**Status: draft ordering specification; unresolved items prevent fabrication release.** This is the order worksheet for the three flex designs. It records saved values separately from proposed supplier options. No order or quote has been submitted for these designs in this documentation task. See [FPC_DRC_AND_MANUFACTURABILITY.md](FPC_DRC_AND_MANUFACTURABILITY.md) for limits, findings and verification requirements.

## Document and decision ownership

- User requirements are maintained in [DESIGN_REQUIREMENTS.md](DESIGN_REQUIREMENTS.md).
- **Current baseline: 18 um copper.** A 12 um alternative is under consideration only; it has not been applied or approved as the selected order stack.
- The 70 mm dimension is the branch's A-to-B output-tip separation. It is not the overall cable length and did not shorten the original 101.6 mm straight cable.
- Use separate manufacturing packages and order line items for each design. Quantity, delivery address, shipping method, price and lead time remain unspecified.

## Board-specific order worksheet

| Setting | Straight cable | Branched cable | Micro-D adapter |
| --- | --- | --- | --- |
| Project | [FPC_15015_0451](../FPC_15015_0451/FPC_15015_0451.PrjPcb) | [ZIF_to_2xZIF](../FPC_Adapters_20261002/ZIF_to_2xZIF/ZIF_to_2xZIF.PrjPcb) | [ZIF_to_DSUB25](../FPC_Adapters_20261002/ZIF_to_DSUB25/ZIF_to_DSUB25.PrjPcb) |
| Fabrication category | Flexible PCB | Flexible PCB | Flexible PCB with bonded connector backing |
| Copper layers | 1 | 2 | 2 |
| Saved copper per layer | 18 um / 0.5 oz | 18 um / 0.5 oz | 18 um / 0.5 oz |
| Finished outline envelope | 101.60 x 15.60 | 420.00 x 41.20 | 40.00 x 31.00 |
| Mechanical status | Molex nominal reconstruction | 420 overall and 10 clear strip gap remain provisional; 70 tip separation confirmed | 40 length and 31 base are provisional |
| Contact ends | A/B on Top | A/B on Top; C on Bottom | A on Top |
| Contacts at each end | 51; 0.30 pitch; 15.60 mating width | Same | Same |
| Contact exposure / backing length | 3.00 / 4.00 | 3.00 / 4.00 | 3.00 / 4.00 |
| Finished mating thickness target | 0.20 +/- 0.03 | 0.20 +/- 0.03 | 0.20 +/- 0.03 |
| Drilling in current artwork | None | 51 plated through vias, 0.10 drill / 0.30 land | 12 plated through vias, 0.20 / 0.40; 25 signal PTHs, 0.7112 / 0.9652; two boardlocks, 2.69 drill |
| Special processing | Contact-gap issue unresolved | Extreme fine drilling plus contact-gap issue | Contact gap and PTH annulus unresolved; via-process confirmation |
| Electrical topology | A.n = B.n, all 51 | C.n = A.n = B.n, all 51 | Anton Micro-D map; odd contacts NC |

The Micro-D connector is NorComp 381-025-112L565, not a full-size DB25. DSUB pins 1..13 map to ZIF 2,6,...50; pins 14..25 map to 4,8,...48. Preserve [contact_mapping.csv](../FPC_Adapters_20261002/ZIF_to_DSUB25/contact_mapping.csv). The adapter uses contact 50; the carrier's separate unused-pin-50 rule does not apply here.

## Common order fields

| Field | Intended setting / status |
| --- | --- |
| Supplier | JLCPCB FPC service, subject to the manufacturing findings being resolved |
| Material | Polyimide flex; actual core, adhesive and coverlay construction to be matched to a supplier stack |
| Coverlay color | Yellow proposed for the quote; not yet an approved or selected order option |
| Surface finish | ENIG 2 microinch proposed for supplier review; see the source-cable finish difference below |
| Impedance option | No controlled-impedance requirement specified for these flex interconnects; do not import the carrier's 50-ohm HDI settings |
| Blind/buried vias | None; the adapter vias are through vias connecting the two flex copper layers |
| Milling / cavity | No QD blind pocket, Z-milling or carrier mechanical fabrication layer belongs in these packages |
| Via coverlay | Covered on both faces; verify exported apertures, not only cached pad flags |
| Paste / stencil | No paste artwork or stencil required for this cable fabrication package |
| PCBA | Bare-board fabrication worksheet; assembly service not included in the proposed scope |
| Silkscreen | None proposed; keep engineering annotations on fabrication documentation layers |
| Electrical test | Request continuity/isolation against the released netlist, including the three-end branch map and intended Micro-D NC contacts |
| Edge finish | Laser outline; no V-score instruction |
| Quantity / price / lead time | TBD; no verified quote exists |

JLCPCB lists ENIG in 1 or 2 microinch and lists 12 um copper for two-/four-layer flex; its single-layer list contains 18 and 35 um. [FPC capability source, checked 2026-10-05](https://jlcpcb.com/capabilities/flex-pcb-capabilities)

The straight cable reconstruction's source calls for hard gold. ENIG is a proposed process substitution, not proof of equivalent contact wear or mating-cycle life. Confirm acceptability before release, particularly if repeated insertion is expected. This issue is independent of copper thickness.

## Stack and stiffener specification

| Region | Saved nominal construction | Ordering disposition |
| --- | --- | --- |
| Straight body | 18 um copper + 45 um PI/adhesive + 50 um coverlay/adhesive = 0.113 | Reconstruction stack; do not enter 0.113 as if it were an available catalog option |
| Straight exposed contact | 45 + 18 + 150 um backing/adhesive = 0.213 before plating | Nominal arithmetic only; verify finished thickness and tolerance with the fabricator |
| Adapter body | 18 + 45 + 18 + 25 + 25 um = 0.131 | Draft two-layer construction; replace with an agreed supplier stack before export |
| ZIF contact backing | 4 mm long, on the face opposite each exposed contact array | Select PI backing and adhesive using the actual local copper/coverlay stack to meet 0.20 +/- 0.03 |
| Micro-D connector base | Bonded backing; provisional finished mounting thickness 1.60 | Backing material, adhesive, hole alignment and thickness still need definition; 1.60 is not an instruction to add a 1.60-thick stiffener |

Use the [JLCPCB PI thickness calculator](https://jlcpcb.com/gold-fingers-pi-thickness-calculator) with the selected supplier stack. Record its inputs, proposed backing and supplier-confirmed finished thickness. Account for the absent coverlay over exposed contacts and for the opposite face's actual local construction; do not use the body thickness indiscriminately. No calculator result is recorded yet.

Mechanical 2 currently describes backing boundaries rather than native stiffener solids. Create a fabrication layer map with separate Top-side and Bottom-side backing files and explicit material/thickness notes. On the branch, A/B require Bottom backing and C requires Top backing. On the straight cable and Micro-D mating tail, backing is on Bottom. The connector-base backing must be distinguished from the thin mating-tail backing.

## Copper selection paths

| Path | Required work before ordering |
| --- | --- |
| Retain 18 um baseline | Revise the contact transitions to satisfy the applicable regular limits while retaining mating dimensions, or obtain specific process acceptance. A zero stored-rule DRC is insufficient. |
| Change two-layer adapters to 12 um | First select this design change; update native stack, fabrication notes, rules and reports. Current 0.0707105 contact gaps fit the published 2/2 mil absolute capability, but are below the regular 3/3 mil spacing. Confirm the actual artwork's acceptance. Resolve the Micro-D annulus independently. |
| Change straight single-layer cable to 12 um | Not a listed single-layer option. Obtain an explicit supplier offer or revise the construction; do not silently order two layers or add copper. |

For the 12 um option, record allowable current and voltage drop before acceptance. With unchanged length/width/material, copper resistance rises by 50%; finished connector thickness must be recalculated. The current 18 um files must not be sent with an unrecorded 12 um order selection.

Do not describe 2/2 mil as a verified separate order option or assume a surcharge for it. Line/space pricing remains unconfirmed; the fine-via extra cost is a separate published condition.

## Panel and fabrication package

Proposed delivery is individual finished circuits with manufacturer panelization reviewed before production. Do not assume the supplier will add handling features without confirming the panel drawing. The branch envelope plus 5 mm handling edges is 51.2 x 430 mm; this is only a size estimate, not a complete panel design.

For panel preparation, use 5 mm handling edges, 2 mm circuit spacing (3 mm for metal stiffeners), and laser tabs rather than V-cuts or mouse bites. Coordinate tooling/fiducials and the long branch's support with the fabricator. [JLCPCB flex panel guide](https://jlcpcb.com/blog/design-guidelines-flex-pcb-panels)

The future release archive for each board must include:

| Output | Content and verification |
| --- | --- |
| Copper Gerbers | Top; Bottom only for the two-layer designs. Inspect actual widths, spacing and contact transitions. |
| Coverlay Gerbers | Explicit Top/Bottom mapping; correct exposed contact face, grouped Micro-D row openings and covered vias. |
| Outline Gerber | One unambiguous finished laser outline; no duplicated backing boundary treated as a cutout. |
| Drill files and map | Exact plated/non-plated classification from the accepted source and connector requirements; separate tooling from product holes. Straight cable has no drills. |
| Backing fabrication layers | Filled Top/Bottom backing outlines, material, thickness, adhesive and finished regional thickness targets. |
| Fabrication drawing | Overall/contact dimensions, contact faces, stack, finish, backing and static no-bend junction area. |
| Electrical data | IPC-D-356 or agreed equivalent test netlist plus contact mapping and intentional NC list. |
| Release manifest | Native source and CAM hashes, revision, export date, DRC/copper checks and the exact quote/order settings. |

Do not include the carrier's HDI drill pairs, QD milling layer, obsolete drafts, history files or an unlabeled collection of engineering mechanical layers. Gerbers cannot by themselves communicate the selected copper weight, finished stack and backing requirements.

## Open decisions and final checks

| Item | Current status |
| --- | --- |
| 18 versus 12 um | 18 saved; 12 considered, not selected |
| Minimum contact gap / exposed-contact acceptance | Unresolved; applies to all three designs |
| Branch and Micro-D via process | Supplier-specific confirmation needed |
| Micro-D signal annulus | Below published absolute limit; redesign or accepted exception required |
| Edge/slot, coverlay and pad-to-trace checks | Full supplier-profile/CAM review outstanding |
| Supplier stack and contact backing | Not selected; finished mating target remains binding |
| Contact finish | ENIG proposed; source hard-gold equivalence not established |
| Branch and Micro-D provisional dimensions | Mechanical confirmation outstanding |
| Native library reload / schematic compilation | Final adapter recompile outstanding |
| DRC and independent checks after any revision | Must be regenerated; archived zero reports are not supplier approval |
| Gerbers, panel, quote and order | Not released by this task; quantity and commercial details TBD |

When these items are resolved, replace proposals with the exact selected options, link the supplier's written exception/process confirmation where applicable, and retain screenshots of the final quote settings with the release manifest. Update this document whenever geometry, copper, backing or supplier options change.
