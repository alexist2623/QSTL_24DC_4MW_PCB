"""Emit independent lower triple-SMP corridor proposals from corridor A."""
import apply_corridor_placement as placement

H=placement.HERE
placement.SOURCE=H/"placement_corridor_candidate.json"
variants={
    "outer_vertical": {"R15":(1.1,27.3,270.),"R21":(18.4,27.3,270.)},
    "outer_mixed": {"R15":(1.1,27.3,90.),"R21":(18.4,27.3,270.)},
    "over_smp": {"R15":(3.75,28.05,0.),"R21":(15.75,28.05,180.),"C15":(3.75,26.55,90.),"C21":(15.75,26.55,90.)},
}
for name,targets in variants.items():
    placement.TARGETS=targets
    placement.DEST=H/f"placement_lower_{name}_candidate.json"
    placement.main()
