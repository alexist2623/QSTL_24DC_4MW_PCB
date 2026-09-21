"""Catch native binding failures and log each polygon operation without a modal."""
from pathlib import Path
H=Path(__file__).resolve().parent
for name,procedure in [('ApplyRF50.pas','ApplyRF50'),('FinishRF50.pas','FinishRF50')]:
    f=H/name;s=f.read_text()
    if 'Procedure RunSafely;' in s:continue
    start=s.index('  Poly:=PCBServer.PCBObjectFactory(ePolyObject')
    end=s.index("  Mark('CAVITY_ANNOTATED');",start)
    chunk=s[start:end]
    if name=='ApplyRF50.pas':
        chunk=chunk.replace(';Poly.',";Mark('POLY_CHECK');Poly.")
        for i in range(chunk.count("'POLY_CHECK'")):chunk=chunk.replace("'POLY_CHECK'",f"'POLY_CHECK_{i+1}'",1)
        s=s[:start]+chunk+s[end:]
    s+='\nProcedure RunSafely;\nBegin\n Try '+procedure+"; Except Mark('CAUGHT_NATIVE_FAILURE');End;\nEnd;\n"
    f.write_text(s,encoding='ascii')
print('Native scripts wrapped')
