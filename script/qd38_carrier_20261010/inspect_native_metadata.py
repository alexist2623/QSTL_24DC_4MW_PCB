"""Read original board layer metadata without changing the design."""
import re
import olefile
from design_geometry import ROOT,H


with olefile.OleFileIO(ROOT/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc') as doc:
    matches=[]
    for key in doc.listdir():
        if key[-1]!='Data':continue
        data=doc.openstream(key).read().decode('latin1')
        for hit in re.finditer(r'Blind|BLIND|[Ll][Aa][Yy][Ee][Rr].{0,15}[Nn][Aa][Mm][Ee]',data):
            matches.append(('/'.join(key),data[max(0,hit.start()-140):hit.end()+160]))
    board=doc.openstream('Board6/Data').read().decode('latin1')
    values=[v for v in board.split('|') if 'NAME=' in v and ('MECH' in v.upper() or 'MILL' in v.upper() or 'SLOT' in v.upper())]
    print(values)
