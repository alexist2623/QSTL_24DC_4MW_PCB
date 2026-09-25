# Native CAM package and JLCPCB HDI quotation

Revision status (2026-09-23): historical package. The current PCB uses ZIF contacts 2..48 even and leaves contact 50 unused. This package and the previous supplier upload predate that DC remap; regenerate CAM before production.

Generated on 2026-09-22 from the original saved Altium design. No PCB geometry or stackup was edited during export. This is a quotation package, not an approved manufacturing release.

## Package and verification

- [Complete fabrication ZIP](QSTL_24DC_6RF_HDI_Gerber_20260922.zip): six copper layers, two solder masks, two silkscreens, board outline, separate through and blind drill files, Bottom blind-slot Gerber, milling drawing, stackup CSV and impedance requirements JPG.
- [CAM validation](CAM_validation.json): 480 unique 0.10 mm laser holes, native L5-L6 drill pair, coordinate match within 0.000067 mm; 94 separate plated through holes. All 12 Gerber files parsed successfully with the common board origin.
- [Fresh Altium DRC](Native_DRC.html) after reopening the saved original PCB: 0 violations across 15 enabled rules. Stored unrouted connections: 0 before and after DRC. PCB SHA-256 remained `84feed018fbaf5cbfa3203201c8771711b00ffec18aa0aadaf20fdeadb99ca63`.
- The blind drill file appears separately in JLCPCB's uploaded-file list. Layer sequence was explicitly set GTL/G1/G2/G3/G4/GBL. Manufacturer CAM acceptance of the L5-L6-only span remains pending.

## Visible quote

Five boards were used as the quantity assumption. Currency: USD. Destination estimate: Canada. The quote and option screenshots were captured before login.

| Item | Displayed result |
| --- | --- |
| Bare PCB, 5 pcs | $291.99 |
| Build time | 12-13 days |
| DHL Express shipping | $28.08 |
| Shipping time | 2-4 business days |
| PCB + shipping arithmetic subtotal | $320.07 |

This is a preliminary web calculation. The page still lists **Buried Via Fee** and **Lamination Fee** as **Manual Quote**. There are no designed buried vias. Taxes, manual adjustments and combined HDI/pocket process approval are not established by this calculation. The factory holiday banner lists Sep. 25, Sep. 27 and Oct. 1-4 closures; the displayed time is not a committed arrival date.

## Selected options

- Advanced PCB, HDI, 6 layers, 1-step, 19.5 x 67.9 mm, 1.6 mm, 5 single boards, industrial/consumer type.
- Green solder mask, white silkscreen, NP-175F TG170, ENIG 1 microinch; deburring enabled. Finish is a quote assumption, not wire-bond process qualification.
- Outer copper 1 oz. **The HDI page forces inner copper 1 oz; 0.5 oz is disabled.** The original design remains 0.5 oz inner with the requested JLCH06161HN1-1078 stack. The uploaded files and PCB remark retain the original requested stack and require manufacturer review before substitution.
- Layer stackup: Subject to Review. Controlled impedance enabled: +/-10% (+/-5 ohms for targets <=50 ohms). Target requirements: 50 ohm single-ended coplanar L6 with L5 reference, 0.110 mm width, 0.200 mm copper gap, 0.0784 mm outer dielectric. Separate impedance test report: No.
- Epoxy Filled & Capped; minimum mechanical via option 0.25 mm/(0.35/0.4 mm). The separate HDI laser drill is 0.10 mm with 0.25 mm lands, L6-L5 only. The generic minimum-via selector does not constitute approval of the laser span.
- Fully tested flying probe, automatic 4-Wire Kelvin Test, production-file confirmation Yes, outline tolerance +/-0.2 mm, remove PCB mark.
- Blind Slots Yes: one non-plated Bottom pocket, 4.3 x 4.3 mm, R0.5, 1.20 mm deep. Milling drawing attached. This is not a through cutout.
- PCBA and stencil disabled. Gold fingers, castellations, press-fit holes, edge plating, UL marking, backdrill and humidity indicator: No.

## Evidence

- [Price and lead time](06_Price_lead_time_HDI.png)
- [Impedance and forced copper options](07_Impedance_copper_options.png)
- [Milling, no PCBA/stencil and shipping](08_Milling_no_PCBA.png)
- [Bottom blind-slot detail](01_Blind_slot_options.png)
- [Six-layer mapping](02_Layer_sequence.png)
- [Canada shipping choices](03_Canada_shipping.png)
- [Uploaded blind drill file](04_Uploaded_blind_drill_file.png)
- [Full option page](05_All_quote_options.png)
- [Machine-readable selected options](JLC_selected_options.json)
- [Account restriction notice](09_Account_restriction_notice.png)

No order or payment was placed. The original design has not been changed to match the web page's forced 1 oz inner copper.

## Account access limitation

Login to the requested QSTL DOTS account succeeded. JLCPCB then displayed an account restriction notice announcing closure and permanent disablement on November 21, 2026, citing global trade compliance regulations. Opening the quote page while authenticated redirected to the restriction notice. The specific underlying reason was not established.

Consequently, the pre-login quote was not saved to that account and the manufacturer-side detailed viewer could not be used to confirm the blind-via span. Native PCB and exported drill validation passed as recorded above; manufacturer acceptance of the span, stackup and pocket process remains pending. See the [official account-access notice](https://jlcpcb.com/help/article/notice-of-limited-account-access-restrictions) and the saved screenshot.

## JLCPCB references

- [Blind-slot file preparation and ordering](https://jlcpcb.com/help/article/how-to-place-an-order-with-blind-slots)
- [HDI capabilities](https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq)
- [Quote page](https://cart.jlcpcb.com/quote)

Helpers are kept in `script/jlcpcb_hdi_quote_20260922/`. Native Gerbers and drills were generated by Altium Designer 26.10.1; `package_cam.py` copies and validates these outputs and creates the ZIP. `record_quote.py` records the independent native reopen check and the visible quotation.
