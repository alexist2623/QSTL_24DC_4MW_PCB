"""Measure the imported reference solids and PCB registration without edits."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script/mechanical_assembly_20260921'))
import inspect_geometry as geo
OUT=ROOT/'QSTL_QD4_2SET_38PAD/Reference12_Fastening_20261015'
PCB=Path('F:/Nextcloud/Lab/Instruments/CustomParts/Carrier_12MW_72DC/PCB/Sample_Holder/Sample_Holder.step')


def main():
    data={}
    for path in list(OUT.glob('*_reference.step'))+[PCB]:
        print('Reading '+path.name,flush=True)
        result=geo.inspect(geo.read(path))
        data[path.name]=result
        print(json.dumps(dict(name=path.name,bounds=result['bounds'],valid=result['valid'],volume=result['volume'],
            cylinders=[v for v in result['cylinders'] if v['radius']>.7],
            largest_planes=sorted(result['planes'],key=lambda p:-p['area'])[:10]),indent=2),flush=True)
    (OUT/'reference_geometry.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
