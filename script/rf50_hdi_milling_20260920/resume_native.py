"""Resume the observed live state: polygon and cavity outline already exist."""
from pathlib import Path
H=Path(__file__).resolve().parent
s=(H/'FinishRF50.pas').read_text()
start=s.index('  Poly:=PCBServer.PCBObjectFactory(ePolyObject')
end=s.index('  FabText:=',start)
s=s[:start]+s[end:]
s=s.replace('FabText.X:=MMsToCoord(21);FabText.Y:=MMsToCoord(43);','FabText.MoveToXY(MMsToCoord(21),MMsToCoord(43));')
s=s.replace('Procedure FinishRF50;','Procedure CompleteRF50;').replace('Try FinishRF50;', 'Try CompleteRF50;')
# Text location uses the native primitive movement method, not unsupported X/Y fields.
(H/'CompleteRF50.pas').write_text(s,encoding='ascii')
# Correct the reproducible original generator as well.
f=H/'build_native_change.py';g=f.read_text();g=g.replace('FabText.X:=MMsToCoord(21);FabText.Y:=MMsToCoord(43);','FabText.MoveToXY(MMsToCoord(21),MMsToCoord(43));');f.write_text(g)
print('Prepared completion without duplicate polygon or cavity')
