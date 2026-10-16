"""Move contour and via data out of script code to avoid huge compiler units."""
from pathlib import Path
import re,json
H=Path(__file__).resolve().parent
s=(H/'ApplyNative16RF.pas').read_text();header=s.split('Procedure BuildRevision000;')[0]
probe=header+"""Procedure Probe16Native;
Begin Log:=TStringList.Create;Mark('PROBE_START');B:=PCBServer.GetCurrentPCBBoard;Mark('GOT_BOARD');If B=Nil Then Exit;Mark(B.FileName);
Mark('COMP='+IntToStr(ObjectCount('components',False)));Mark('PAD='+IntToStr(ObjectCount('pads',False)));Mark('TRK='+IntToStr(ObjectCount('tracks',True)));Mark('ARC='+IntToStr(ObjectCount('arcs',True)));Mark('VIA='+IntToStr(ObjectCount('vias',False)));Mark('BODY='+IntToStr(ObjectCount('bodies',False)));Mark('PROBE_DONE');Log.Free;End;
"""
probe=probe.replace('ApplyNative16RF_native_log.txt','probe_native.txt')
(H/'Probe16Native.pas').write_text(probe,encoding='ascii')
def prj(stem):(H/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n')
prj('Probe16Native')
# Contours are pure coordinates. Read them as data instead of 70,000 scripted
# function calls. Construction uses the same exact native contour API.
coords=[]
def contour(m):
    start=len(coords)
    for x,y in re.findall(r'CT.AddPoint\(MMsToCoord\(([^)]+)\),MMsToCoord\(([^)]+)\)\);',m.group()):coords.append(x+'|'+y)
    return f'LoadContour({start},{len(coords)-start});'
s=re.sub(r'(?:CT.AddPoint\(MMsToCoord\([^)]+\),MMsToCoord\([^)]+\)\);\n)+',contour,s)
(H/'contours.txt').write_text('\n'.join(coords),encoding='ascii')
helper=f"""
Procedure LoadContour(Start,Count:Integer);
Var J:Integer;Fields:TStringList;
Begin Fields:=TStringList.Create;Fields.Delimiter:='|';For J:=Start To Start+Count-1 Do Begin Fields.DelimitedText:=ContourData[J];CT.AddPoint(MMsToCoord(StrToFloat(Fields[0])),MMsToCoord(StrToFloat(Fields[1])));End;Fields.Free;End;
"""
s=s.replace('Good:Boolean;FabText:', 'ContourData:TStringList;Good:Boolean;FabText:')
s=s.replace('Procedure BuildRevision000;',helper+'\nProcedure BuildRevision000;')
s=s.replace('Procedure ApplyNative16RF;','Procedure ApplyNative16RFCompact;')
s=s.replace('ApplyNative16RF_native_log.txt','compact_native.txt')
# Skip workspace reopen; target project is already attached and shown. Avoid
# querying the workspace during the in-progress project-open event.
s=re.sub(r' WS:=GetWorkspace;WS.DM_OpenProject[^\n]+\n','',s)
s=s.replace(' Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;'," Client.ShowDocument(D);Mark('DOCUMENT_SHOWN');B:=PCBServer.GetCurrentPCBBoard;Mark('BOARD_ACQUIRED');")
s=s.replace(" If ObjectCount('components',False)"," Mark('START_COUNTS');If ObjectCount('components',False)")
s=s.replace(" J1:=Nil;For K:=0 To 2", " Mark('COUNTS_AND_POSITIONS_OK');J1:=Nil;For K:=0 To 2")
s=s.replace(" Mark('PREFLIGHT_OK');PCBServer.PreProcess;",f" Mark('PREFLIGHT_OK');ContourData:=TStringList.Create;ContourData.LoadFromFile('{H/'contours.txt'}');PCBServer.PreProcess;")
s=s.replace("Mark('BUILT_NOT_SAVED_REQUIRES_NATIVE_REVIEW_SAVE_REOPEN_DRC');Log.Free;","Mark('BUILT_NOT_SAVED_REQUIRES_NATIVE_REVIEW_SAVE_REOPEN_DRC');ContourData.Free;Log.Free;")
(H/'ApplyNative16RFCompact.pas').write_text(s,encoding='ascii');prj('ApplyNative16RFCompact')
print('Compact bytes',len(s),'contour points',len(coords))
