"""Generate Altium API builds from the design plans; never overwrite an open draft."""
from pathlib import Path
import json,shutil,re
H=Path(__file__).resolve().parent;R=H.parents[1]
W=H/'native_work';W.mkdir(exist_ok=True)
plans=[json.loads((R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002'/n/'design_plan.json').read_text()) for n in ('ZIF_to_2xZIF','ZIF_to_DSUB25')]
code=[r'''Var B:IPCB_Board;Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('__H__\native_build_log.txt');End;
Procedure Reg(P:IPCB_Primitive);Begin B.AddPCBObject(P);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,P.I_ObjectAddress);End;
Procedure Line(N:IPCB_Net;L:TLayer;X1,Y1,X2,Y2,W:Double);
Var T:IPCB_Track;
Begin T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);T.X1:=MMsToCoord(X1);T.Y1:=MMsToCoord(Y1);T.X2:=MMsToCoord(X2);T.Y2:=MMsToCoord(Y2);T.Width:=MMsToCoord(W);T.Layer:=L;If N<>Nil Then Begin T.Net:=N;T.SetState_InNet(True);End;Reg(T);End;
''']
e=code.append
def layer(l):return {1:'eTopLayer',32:'eBottomLayer',37:'eTopSolder',38:'eBottomSolder',58:'eMechanical2',74:'eMultiLayer'}[l]
for ix,p in enumerate(plans):
 name=p['name'];target=W/(name+'.PcbDoc')
 if not target.exists():shutil.copy2(H/'dsub_blank.PcbDoc',target)
 cmap={c['ref']:'C'+str(i) for i,c in enumerate(p['components'])}
 e(f'Procedure Build{ix};')
 e('Var D:IServerDocument;I:IPCB_BoardIterator;O:IPCB_BoardOutline;S:TPolySegment;P:IPCB_Primitive;N:IPCB_Net;'+','.join(cmap.values())+':IPCB_Component;PD:IPCB_Pad;V:IPCB_Via;RG:IPCB_Region;G:IPCB_GeometricPolygon;CT:IPCB_Contour;PC:TPadCache;Rule:IPCB_Rule;CL:IPCB_ClearanceConstraint;WC:IPCB_MaxMinWidthConstraint;Count:Integer;Good:Boolean;')
 e('Begin')
 e(f"Mark('OPEN {name}');D:=Client.OpenDocument('PCB','{target}');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{target}') Then Exit;")
 e("I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject,eComponentObject));P:=I.FirstPCBObject;Count:=0;While P<>Nil Do Begin Inc(Count);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If Count<>0 Then Begin Mark('STOP_NOT_BLANK');Exit;End;PCBServer.PreProcess;Try")
 e(f'O:=B.BoardOutline;O.PointCount:={len(p["outline"])};S:=O.Segments[0];')
 for i,(x,y) in enumerate(p['outline']):e(f'S.Kind:=ePolySegmentLine;S.vx:=MMsToCoord({x});S.vy:=MMsToCoord({y});O.Segments[{i}]:=S;')
 e(f"O.Segments[{len(p['outline'])}]:=O.Segments[0];O.Invalidate;O.Rebuild;O.Validate;B.UpdateBoardOutline;B.RebuildSplitBoardRegions(True);Mark('OUTLINE {name}');")
 for c in p['components']:
  v=cmap[c['ref']]
  e(f"{v}:=PCBServer.PCBObjectFactory(eComponentObject,eNoDimension,eCreate_Default);{v}.Name.Text:='{c['ref']}';{v}.Pattern:='{c['pattern']}';{v}.Layer:={layer(c['layer'])};{v}.X:=MMsToCoord({c['x']});{v}.Y:=MMsToCoord({c['y']});{v}.NameOn:=False;{v}.CommentOn:=False;Reg({v});")
 for net in p['nets']+[None]:
  e('N:=Nil;' if net is None else f"N:=PCBServer.PCBObjectFactory(eNetObject,eNoDimension,eCreate_Default);N.Name:='{net}';Reg(N);")
  for pad in [a for a in p['pads'] if a['net']==net]:
   shape='eRectangular' if pad['shape']=='rect' else 'eRounded';v=cmap[pad['ref']]
   e(f"PD:=PCBServer.PCBObjectFactory(ePadObject,eNoDimension,eCreate_Default);PD.Name:='{pad['pin']}';PD.X:=MMsToCoord({pad['x']});PD.Y:=MMsToCoord({pad['y']});PD.Layer:={layer(pad['layer'])};PD.Mode:=ePadMode_Simple;PD.TopShape:={shape};PD.MidShape:={shape};PD.BotShape:={shape};PD.TopXSize:=MMsToCoord({pad['sx']});PD.TopYSize:=MMsToCoord({pad['sy']});PD.MidXSize:=PD.TopXSize;PD.MidYSize:=PD.TopYSize;PD.BotXSize:=PD.TopXSize;PD.BotYSize:=PD.TopYSize;PD.HoleSize:=MMsToCoord({pad['hole']});PD.Plated:=True;If N<>Nil Then Begin PD.Net:=N;PD.SetState_InNet(True);End;PD.SetState_PasteMaskEnabled(False);")
   expansion=.05 if pad['hole'] else 0
   e(f'PC:=PD.GetState_Cache;PC.PasteMaskExpansionValid:=eCacheManual;PC.PasteMaskExpansion:=MMsToCoord(-2);PC.SolderMaskExpansionValid:=eCacheManual;PC.SolderMaskExpansion:=MMsToCoord({expansion});PC.SolderMaskBottomExpansion:=MMsToCoord({expansion});PD.SetState_Cache(PC);{v}.AddPCBObject(PD);Reg(PD);')
  for r in [r for r in p['regions'] if r['net']==net]:
   e('G:=PCBServer.PCBGeometricPolygonFactory;CT:=PCBServer.PCBContourFactory;')
   for x,y in r['points']:e(f'CT.AddPoint(MMsToCoord({x}),MMsToCoord({y}));')
   e(f"G.AddContourIsHole(CT,False);RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={layer(r['layer'])};RG.Name:='{r['name']}';RG.SetGeometricPolygon(G);If N<>Nil Then Begin RG.Net:=N;RG.SetState_InNet(True);End;")
   owner=r['name'].split('_CONTACT_')[0] if '_CONTACT_' in r['name'] else None
   if owner in cmap:e(f'{cmap[owner]}.AddPCBObject(RG);')
   e('Reg(RG);')
  for t in [t for t in p['tracks'] if t['net']==net]:e(f"Line(N,{layer(t['layer'])},{t['a'][0]},{t['a'][1]},{t['b'][0]},{t['b'][1]},{t['width']});")
  for v in [v for v in p['vias'] if v['net']==net]:
   e(f"V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);V.X:=MMsToCoord({v['x']});V.Y:=MMsToCoord({v['y']});V.Size:=MMsToCoord({v['diameter']});V.HoleSize:=MMsToCoord({v['hole']});V.LowLayer:=eTopLayer;V.HighLayer:=eBottomLayer;V.Net:=N;V.SetState_InNet(True);V.SetState_PasteMaskEnabled(False);V.SetState_IsTenting(True);V.SetState_IsTenting_Top(True);V.SetState_IsTenting_Bottom(True);PC:=V.GetState_Cache;PC.SolderMaskExpansionValid:=eCacheManual;PC.SolderMaskExpansion:=MMsToCoord(-1);PC.SolderMaskBottomExpansion:=MMsToCoord(-1);PC.PasteMaskExpansionValid:=eCacheManual;PC.PasteMaskExpansion:=MMsToCoord(-2);V.SetState_Cache(PC);Reg(V);")
 e(f"Mark('COPPER {name}');")
 e("I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));Rule:=I.FirstPCBObject;While Rule<>Nil Do Begin If Rule.RuleKind=eRule_Clearance Then Begin CL:=Rule;CL.Gap:=MMsToCoord(0.0707);End;If Rule.RuleKind=eRule_MaxMinWidth Then Begin WC:=Rule;WC.MinWidth[eTopLayer]:=MMsToCoord(0.09999);WC.MinWidth[eBottomLayer]:=MMsToCoord(0.09999);WC.MaxWidth[eTopLayer]:=MMsToCoord(0.3);WC.MaxWidth[eBottomLayer]:=MMsToCoord(0.3);End;Rule:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.RebuildPadCaches;Finally PCBServer.PostProcess;End;")
 e("I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;")
 e(f"Mark('SAVE {name}');B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');Mark('SAVED {name}');")
 e(f"Good:=B.RunBatchDesignRuleCheck('{W / (name+'_DRC.html')}',eDRC_HTML,False,False);If Good Then Mark('DRC_RETURNED_TRUE {name}') Else Mark('DRC_RETURNED_FALSE {name}');")
 e('End;')
e("Procedure BuildNativeBoth;Begin Log:=TStringList.Create;Mark('START');Build0;Build1;Mark('COMPLETE');Log.Free;End;")
text='\n'.join(code).replace('__H__',str(H));text=re.sub(r'(?<![\w])\.(\d)',r'0.\1',text)
(H/'BuildNativeBoth.pas').write_text(text,encoding='ascii')
(H/'BuildNativeBoth.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=BuildNativeBoth.pas\n[Generic_ScriptingSystem]\nStartProcName=BuildNativeBoth.pas>BuildNativeBoth\n')
print('Native builder prepared:',len(text),'characters')
