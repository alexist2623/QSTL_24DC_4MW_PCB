# QD endpoint-via implementation basis

The aligned pad proposal keeps all 38 rectangular bond pads at 0.8 x 0.25 mm,
their chip-facing directions and the common cavity-facing support lines.
The prior 0.40 mm land / 0.20 mm drill cannot satisfy the retained 0.15 mm foreign
copper gap for every endpoint pair under that geometry. The continuous
optimistic-domain analysis records those impossible pairs rather than
loosening the clearance or independently staggering pad ends again.

The concrete alternative uses 0.35 mm lands and unchanged 0.20 mm full-through
drills at the 22 direct-QD DC endpoints only. Its nominal diameter difference
is 0.15 mm and nominal radial annular ring is 0.075 mm. The 38 ZIF 0.40/0.20 mm,
16 resistor 0.50/0.25 mm, and GND shield 0.25/0.10 mm groups remain unchanged.
RF still has no signal via. The QD vias remain full-through endpoints, not
blind/buried or standalone DC layer transitions.

JLCPCB's [general PCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/)
state a 0.10 mm minimum via-diameter excess over drill, with 0.15 mm preferred.
The 0.35/0.20 mm proposal meets that preferred diameter difference. Separately,
the [HDI capabilities FAQ](https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq)
states at least 0.075 mm radial ring for blind/buried vias. That HDI statement
has a different via-span scope; it is not being used to relabel these QD
through vias as microvias. Sources checked 2026-10-11. These geometric
capability statements are not a completed fabrication-order acceptance.

The independent native-grid placement audit of proposal `89829a12...` finds
minimum foreign-pad clearance 0.150326694 mm, via-land clearance 0.150416765 mm,
drill-to-drill clearance 0.300416465 mm and all 22 complete drills contained in
their intended bond-pad rectangles. These are static placement results;
local routing, plane clearances, masks, canonical-library promotion, actual
saved connectivity and native DRC still require their own fresh evidence.

If this proposal is promoted, declare the chosen via land and the exact QD
via-rule WIDTH/MINWIDTH/MAXWIDTH changes in `alignment_delta_manifest.json`.
Do not change unrelated constraints or suppress violations. The staged
canonical PcbLib changes pad XY coordinates only; it contains no routing
via and therefore does not encode the QD endpoint land-size choice itself.
