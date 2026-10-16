"""Render the static .35/.20 via alternative without modifying CAD sources."""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/"qd38_rotation_20261011"
sys.path.insert(0,str(OLD))
from route_rf_corridor_bounded import pgeom

old=json.loads((OLD/"full_copper_candidate.json").read_text())
proposal=json.loads((HERE/"aligned_qd_vias_land_0p35_candidate.json").read_text())
assert proposal["all_static_checks_passed"]
oldpads=[p for p in old["physical_pads"] if p["ref"]=="Q1"]
oldvias=[v for v in old["vias"] if v["label"].startswith("Q1-")]
fig,axes=plt.subplots(1,2,figsize=(12,7.7))
fig.subplots_adjust(bottom=.2,top=.9,left=.07,right=.99,wspace=.18)
for ax,pads,vias,title in zip(axes,(oldpads,proposal["qd_pads"]),(oldvias,proposal["qd_vias"]),
                             ("Saved pad field / 0.40 mm via lands","Aligned inner corners / 0.35 mm via lands")):
    ax.add_patch(Rectangle((7.6,39.85),4.3,5.3,facecolor="#e2e8ef",edgecolor="#647183",lw=1.2))
    ax.add_patch(Rectangle((7.4,39.65),4.7,5.7,fill=False,edgecolor="#14836b",ls="--",lw=1.3))
    for p in pads:
        color="#377da5" if p["net"].startswith("MW") else "#b8802f"
        ax.add_patch(Polygon(np.array(pgeom(p).exterior.coords),facecolor=color,edgecolor="#33485a",lw=.6))
        ax.text(p["x"],p["y"],p["pin"],color="white",ha="center",va="center",fontsize=7)
    for v in vias:
        ax.add_patch(Circle((v["x"],v["y"]),v["diameter"]/2,fill=False,edgecolor="#692b74",lw=1))
        ax.add_patch(Circle((v["x"],v["y"]),v["hole"]/2,fill=False,edgecolor="#692b74",lw=.6))
    ax.set(xlim=(6,13.5),ylim=(38,47),aspect="equal",title=title,xlabel="X (mm)",ylabel="Y (mm)")
    ax.grid(alpha=.16)
fig.suptitle("QD pad-end alignment: offline static feasibility review",fontsize=15)
fig.text(.5,.102,"Same 0.80 × 0.25 mm rectangular pads, bond angles and 4.3 × 5.3 mm cavity.\nDashed inner boundary: X=7.40 / 12.10; Y=39.65 / 45.35 mm (0.20 mm from cavity).",ha="center",fontsize=10)
fig.text(.5,.040,"Right: all 22 direct-DC vias keep 0.20 mm drills; land diameter changes to 0.35 mm.\nStatic minimums: pad–via 0.150326 mm; via–via 0.150416 mm. Local routing/surfaces/native DRC are pending.\nOnly nearest corners align; complete tilted short edges are not collinear.",ha="center",fontsize=9)
fig.savefig(HERE/"aligned_qd_0p35_feasibility_preview.png",dpi=190,bbox_inches="tight")
print(HERE/"aligned_qd_0p35_feasibility_preview.png")
