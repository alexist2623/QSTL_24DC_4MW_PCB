"""Emit separate statically checked lower-only and both-neck route candidates."""
import apply_corridor_placement as placement

H=placement.HERE
placement.SOURCE=H/"placement_corridor_candidate.json"
lower={"C12":(6.45,36.,0.),"R12":(7.17856224,37.,0.),
       "C28":(13.05,36.,180.),"R28":(12.32143776,37.,180.)}
upper={"C09":(6.45,49.,0.),"R09":(7.17856224,48.,0.),
       "C31":(13.05,49.,180.),"R31":(12.32143776,48.,180.)}
placement.TARGETS=lower
placement.DEST=H/"placement_corridor_lower_candidate.json"
placement.main()
placement.TARGETS={**lower,**upper}
placement.DEST=H/"placement_corridor_b_candidate.json"
placement.main()
