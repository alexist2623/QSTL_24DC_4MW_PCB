"""Render the frozen static placement from actual candidate pad/body geometry."""
import hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch,Circle
from build_rotated_placement import pg

H=Path(__file__).resolve().parent
source=H/"placement_lower_over_smp_candidate.json";raw=source.read_bytes();p=json.loads(raw)
assert hashlib.sha256(raw).hexdigest()=="99a7cc8fef9c21e235f47fbdc24733121a37e6ddc4a939d6d92f4fbdb1d70c0e"
fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout="constrained")
for ax,(lo,hi,title) in zip(axes,[(20.5,33.5,"Lower triple-SMP corridor"),(35.,49.5,"Sample and middle corridor")]):
 ax.set_facecolor("#eef3f6")
 for b in p["passive_bodies"]:
  ax.add_patch(Patch(b["outline"],facecolor="#ca935f",edgecolor="#77552f",alpha=.65,zorder=3))
 for pad in p["physical_pads"]:
  color="#9da7b2" if pad["net"]=="GND" else "#de9a18" if (pad["net"] or "").startswith("DC") else "#49a9bb"
  g=pg(pad)
  ax.add_patch(Patch(list(g.exterior.coords),facecolor=color,edgecolor="#405365",linewidth=.4,zorder=2))
  if pad["hole"]:ax.add_patch(Circle((pad["x"],pad["y"]),pad["hole"]/2,facecolor="white",edgecolor="#405365",linewidth=.4,zorder=4))
 for v in p["vias"]:
  ax.add_patch(Circle((v["x"],v["y"]),v["diameter"]/2,facecolor="#e3b354",edgecolor="#88601d",linewidth=.4,zorder=4))
  ax.add_patch(Circle((v["x"],v["y"]),v["hole"]/2,facecolor="white",edgecolor="#88601d",linewidth=.3,zorder=5))
 for s in p["smp"]:
  if lo<s["y"]<hi:ax.text(s["x"],s["y"]+.56,s["ref"],ha="center",va="bottom",fontsize=7,color="#24374d")
 for c in p["components"]:
  if c["ref"].startswith(("R","C")) and lo+.7<c["y"]<hi-.7:
   ax.text(c["x"],c["y"]+.6,c["ref"],ha="center",fontsize=7,color="#392b1f",bbox=dict(facecolor="white",alpha=.8,edgecolor="none",pad=.2))
 cx,cy=p["sample_center"];w,h=p["cavity_mm"]
 ax.add_patch(Patch([(cx-w/2,cy-h/2),(cx+w/2,cy-h/2),(cx+w/2,cy+h/2),(cx-w/2,cy+h/2)],fill=False,edgecolor="#d7505a",linestyle="--",linewidth=1.2))
 ax.axvline(0,color="#28443a");ax.axvline(19.5,color="#28443a")
 ax.set(xlim=(-.2,19.7),ylim=(lo,hi),aspect="equal",xlabel="X (mm)",ylabel="Y (mm)",title=title)
 ax.grid(alpha=.18)
fig.suptitle("Frozen placement review | source 99a7cc8f | no routed copper shown",fontsize=13)
fig.savefig(H/"frozen_placement_review.png",dpi=180)
assert source.read_bytes()==raw
