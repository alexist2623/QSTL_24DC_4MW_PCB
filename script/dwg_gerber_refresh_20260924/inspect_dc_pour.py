"""Read saved polygon definitions and DC-layer copper coverage."""
from pathlib import Path
import sys,json,collections
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision')]
from native_metadata_helpers import properties,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions
s=snapshot(P/'QSTL_24DC_4MW_PCB.PcbDoc');nets=properties(s['Nets6/Data']);polys=properties(s['Polygons6/Data']);regions=read_regions(s['Regions6/Data'])
for i,p in enumerate(polys):
    print(json.dumps(dict(index=i,properties={k:v for k,v in p.items() if not k.startswith(('VX','VY','CX','CY','SA','EA','RADIUS','KIND'))}),indent=2))
summary=collections.defaultdict(lambda:dict(count=0,area_mm2=0))
for r in regions:
    ni=r['net_index']
    if ni==65535 and r['polygon_index']!=65535:ni=int(polys[r['polygon_index']]['NET'])
    if ni!=65535 and nets[ni]['NAME']=='GND':
        q=summary[r['layer']];q['count']+=1;q['area_mm2']+=r['geometry'].area
print(json.dumps(dict(pcb_sha256=sha(P/'QSTL_24DC_4MW_PCB.PcbDoc'),ground_poured_regions_by_layer=summary),indent=2))
