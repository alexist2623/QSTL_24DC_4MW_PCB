"""Prepare a guarded native repair/audit of the generated adapter boards."""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parents[1]
OUT=R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002'
def uid(s):
 n=int(hashlib.sha256(s.encode()).hexdigest(),16)
 return ''.join(chr(65+(n//26**i)%26) for i in range(8))
code=[r'''Var B:IPCB_Board;Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('__H__\native_finish_log.txt');End;
Procedure Rect(L:TLayer;X1,Y1,X2,Y2:Double);
Var RG:IPCB_Region;G:IPCB_GeometricPolygon;CT:IPCB_Contour;
Begin G:=PCBServer.PCBGeometricPolygonFactory;CT:=PCBServer.PCBContourFactory;
CT.AddPoint(MMsToCoord(X1),MMsToCoord(Y1));CT.AddPoint(MMsToCoord(X2),MMsToCoord(Y1));
CT.AddPoint(MMsToCoord(X2),MMsToCoord(Y2));CT.AddPoint(MMsToCoord(X1),MMsToCoord(Y2));
G.AddContourIsHole(CT,False);RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);
RG.Kind:=eRegionKind_Copper;RG.Layer:=L;RG.Name:='DSUB_ROW_COVERLAY';RG.SetGeometricPolygon(G);
B.AddPCBObject(RG);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,RG.I_ObjectAddress);End;
''']
for k,name in enumerate(('ZIF_to_2xZIF','ZIF_to_DSUB25')):
 p=json.loads((OUT/name/'design_plan.json').read_text());f=H/'native_work'/(name+'.PcbDoc')
 code += [f'''Procedure Finish{k};
Var D:IServerDocument;I:IPCB_BoardIterator;C:IPCB_Component;Rule:IPCB_Rule;HR:IPCB_MaxMinHoleSizeConstraint;Good:Boolean;
Begin Mark('OPEN {name}');D:=Client.OpenDocument('PCB','{f}');If D=Nil Then Exit;
Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
If LowerCase(B.FileName)<>LowerCase('{f}') Then Exit;
PCBServer.PreProcess;Try
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
While C<>Nil Do Begin''']
 for c in p['components']:
  code+=[f"If C.Name.Text='{c['ref']}' Then C.SourceUniqueId:='{uid('adapter.sch.'+c['ref'])}';"]
 code+=['C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);']
 if k==1:
  for nums in (range(1,14),range(14,26)):
   pads=[d for d in p['pads'] if d['ref']=='J1' and d['pin'].isdigit() and int(d['pin']) in nums]
   x1=min(d['x']-d['sx']/2 for d in pads)-.10;x2=max(d['x']+d['sx']/2 for d in pads)+.10
   y1=min(d['y']-d['sy']/2 for d in pads)-.10;y2=max(d['y']+d['sy']/2 for d in pads)+.10
   for l in ('eTopSolder','eBottomSolder'):code+=[f'Rect({l},{x1},{y1},{x2},{y2});']
  code+=["I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));Rule:=I.FirstPCBObject;While Rule<>Nil Do Begin If Rule.RuleKind=eRule_MaxMinHoleSize Then Begin HR:=Rule;HR.MaxLimit:=MMsToCoord(2.7);End;Rule:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);"]
 code += [f'''B.RebuildPadCaches;Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');Mark('SAVED {name}');
Good:=B.RunBatchDesignRuleCheck('{H / 'native_work' / (name+'_DRC.html')}',eDRC_HTML,False,False);
If Good Then Mark('DRC_TRUE {name}') Else Mark('DRC_FALSE {name}');
Client.CloseDocument(D);Mark('CLOSED {name}');End;''']
code += ["Procedure NativeFinish;Begin Log:=TStringList.Create;Mark('START');Finish0;Finish1;Mark('COMPLETE');Log.Free;End;"]
(H/'NativeFinish.pas').write_text('\n'.join(code).replace('__H__',str(H)),encoding='ascii')
(H/'NativeFinish.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=NativeFinish.pas\n[Generic_ScriptingSystem]\nStartProcName=NativeFinish.pas>NativeFinish\n')
print('Prepared native metadata, coverlay and hole-rule repair.')
