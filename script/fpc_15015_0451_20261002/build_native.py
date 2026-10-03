"""Generate the guarded native Altium cable builder; all dimensions are mm."""
from pathlib import Path
import json, hashlib, re

H = Path(__file__).resolve().parent
R = H.parents[1]
OUT = R / 'QSTL_24DC_4MW_PCB/FPC_15015_0451'
OUT.mkdir(exist_ok=True)
target = OUT / 'FPC_15015_0451.PcbDoc'
carrier = R / 'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc'
(H/'carrier_before.sha256').write_text(hashlib.sha256(carrier.read_bytes()).hexdigest())

def terminal(i, right=False):
    y = .3*i
    # Sales-drawing staggered contact: 0.10 neck, 0.30 finger, 0.20 body.
    if i % 2:
        edge = [(0,.05),(.15,.05),(.25,.15),(1.10,.15),(1.20,.05),(2.00,.05),(2.10,.10),(3.05,.10)]
    else:
        edge = [(0,.05),(1.10,.05),(1.20,.15),(2.00,.15),(2.10,.10),(3.05,.10)]
    points = [(x,y+w) for x,w in edge] + [(x,y-w) for x,w in reversed(edge)]
    return [(101.6-x if right else x, yy) for x,yy in points]

spec = dict(length_mm=101.6,width_mm=15.6,pitch_mm=.3,circuits=51,corner_radius_mm=.2,
    copper_mm=.018,base_pi_adhesive_mm=.045,coverlay_pi_adhesive_mm=.050,
    contact_exposure_mm=3,stiffener_length_mm=4,stiffener_adhesive_mm=.150,
    specified_contact_thickness_mm=.20,contact_thickness_tolerance_mm=.03,
    body_trace_width_mm=.2,contact_neck_width_mm=.1,contact_finger_width_mm=.3)
(OUT/'nominal_geometry.json').write_text(json.dumps(spec,indent=2)+'\n')
p=[]
def emit(s):p.append(s)
emit(r'''Var B:IPCB_Board; Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('__H__\build_log.txt');End;
Procedure Reg(O:IPCB_Primitive);Begin B.AddPCBObject(O);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,O.I_ObjectAddress);End;
Procedure Line(X1,Y1,X2,Y2,W:Double;LayerId:TLayer;N:IPCB_Net);
Var T:IPCB_Track;
Begin T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);T.X1:=MMsToCoord(X1);T.Y1:=MMsToCoord(Y1);T.X2:=MMsToCoord(X2);T.Y2:=MMsToCoord(Y2);T.Width:=MMsToCoord(W);T.Layer:=LayerId;If N<>Nil Then T.Net:=N;Reg(T);End;
Procedure LabelText(X,Y:Double;S:String);
Var T:IPCB_Text;
Begin T:=PCBServer.PCBObjectFactory(eTextObject,eNoDimension,eCreate_Default);T.XLocation:=MMsToCoord(X);T.YLocation:=MMsToCoord(Y);T.Size:=MMsToCoord(0.8);T.Width:=MMsToCoord(0.1);T.Text:=S;T.Layer:=eMechanical1;Reg(T);End;
Procedure Pad(Cmp:IPCB_Component;N:IPCB_Net;Pin:String;X,Y:Double);
Var P:IPCB_Pad;PC:TPadCache;
Begin
 P:=PCBServer.PCBObjectFactory(ePadObject,eNoDimension,eCreate_Default);P.Name:=Pin;P.X:=MMsToCoord(X);P.Y:=MMsToCoord(Y);P.Layer:=eTopLayer;
 P.Mode:=ePadMode_Simple;P.TopShape:=eRectangular;P.MidShape:=eRectangular;P.BotShape:=eRectangular;
 P.TopXSize:=MMsToCoord(.30);P.TopYSize:=MMsToCoord(.10);P.MidXSize:=P.TopXSize;P.MidYSize:=P.TopYSize;P.BotXSize:=P.TopXSize;P.BotYSize:=P.TopYSize;P.HoleSize:=0;
 P.Net:=N;P.SetState_InNet(True);P.SetState_PasteMaskEnabled(False);
 PC:=P.GetState_Cache;PC.PasteMaskExpansionValid:=eCacheManual;PC.PasteMaskExpansion:=MMsToCoord(-1);PC.SolderMaskExpansionValid:=eCacheManual;PC.SolderMaskExpansion:=0;PC.SolderMaskBottomExpansion:=0;P.SetState_Cache(PC);
 Cmp.AddPCBObject(P);Reg(P);
End;
Procedure BuildFPC;
Var D:IServerDocument;I:IPCB_BoardIterator;N:IPCB_Net;P:IPCB_Primitive;A,Z:IPCB_Component;J,K:Integer;
 G:IPCB_GeometricPolygon;C:IPCB_Contour;RG:IPCB_Region;S:TPolySegment;O:IPCB_BoardOutline;
 Rule:IPCB_Rule;Clr:IPCB_ClearanceConstraint;W:IPCB_MaxMinWidthConstraint;
Begin
 D:=Client.OpenDocument('PCB','__TARGET__');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('__TARGET__') Then Exit;
 Log:=TStringList.Create;Mark('START');K:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject,eComponentObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin Inc(K);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If K<>0 Then Begin Mark('STOP_NOT_BLANK');Log.Free;Exit;End;
 PCBServer.PreProcess;
 Try
  O:=B.BoardOutline;O.PointCount:=8;S:=O.Segments[0];
''')
# Counter-clockwise board boundary: true native circular corners.
vertices=[(.2,0,None),(101.4,0,(101.4,.2,270,360)),(101.6,.2,None),(101.6,15.4,(101.4,15.4,0,90)),(101.4,15.6,None),(.2,15.6,(.2,15.4,90,180)),(0,15.4,None),(0,.2,(.2,.2,180,270))]
for i,(x,y,arc) in enumerate(vertices):
    emit(f'S.vx:=MMsToCoord({x});S.vy:=MMsToCoord({y});')
    if arc:
        cx,cy,a1,a2=arc
        emit(f'S.Kind:=ePolySegmentArc;S.cx:=MMsToCoord({cx});S.cy:=MMsToCoord({cy});S.Radius:=MMsToCoord(.2);S.Angle1:={a1};S.Angle2:={a2};')
    else:emit('S.Kind:=ePolySegmentLine;')
    emit(f'O.Segments[{i}]:=S;')
emit("O.Segments[8]:=O.Segments[0];O.Invalidate;O.Rebuild;O.Validate;B.UpdateBoardOutline;B.RebuildSplitBoardRegions(True);Mark('OUTLINE');")
for ref,x,var in [('A',0,'A'),('B',101.6,'Z')]:
    emit(f"{var}:=PCBServer.PCBObjectFactory(eComponentObject,eNoDimension,eCreate_Default);{var}.Name.Text:='{ref}';{var}.Pattern:='FPC51_P030_STAGGERED';{var}.Comment.Text:='Integral same-face cable contacts';{var}.Layer:=eTopLayer;{var}.X:={round(x/2.54e-6)};{var}.Y:=MMsToCoord(7.8);{var}.NameOn:=False;{var}.CommentOn:=False;Reg({var});")

def region(points,layer,name,net=False,comp=None):
    emit('G:=PCBServer.PCBGeometricPolygonFactory;C:=PCBServer.PCBContourFactory;')
    for x,y in points:emit(f'C.AddPoint({round(x/2.54e-6)},{round(y/2.54e-6)});')
    emit(f"G.AddContourIsHole(C,False);RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={layer};RG.Name:='{name}';RG.SetGeometricPolygon(G);")
    if net:emit('RG.Net:=N;RG.SetState_InNet(True);')
    if comp:emit(f'{comp}.AddPCBObject(RG);')
    emit('Reg(RG);')

for i in range(1,52):
    emit(f"N:=PCBServer.PCBObjectFactory(eNetObject,eNoDimension,eCreate_Default);N.Name:='CH{i:02d}';Reg(N);")
    for right,cmp,x in [(False,'A',.65),(True,'Z',100.95)]:
        emit(f"Pad({cmp},N,'{i}',{x},{.3*i:.3f});")
        region(terminal(i,right),'eTopLayer',f'{cmp}_CONTACT_{i:02d}',True,cmp)
    emit(f'Line(3,{.3*i:.3f},98.6,{.3*i:.3f},.20,eTopLayer,N);')
emit("Mark('51_NETS_102_CONTACTS');")
for x0,x1,name in [(0,3,'A'),(98.6,101.6,'B')]:
    region([(x0,-.01),(x1,-.01),(x1,15.61),(x0,15.61)],'eTopSolder',name+'_COVERLAY_OPENING')
for x0,x1 in [(0,4),(97.6,101.6)]:
    for a,b in [((x0,0),(x1,0)),((x1,0),(x1,15.6)),((x1,15.6),(x0,15.6)),((x0,15.6),(x0,0))]:
        emit(f'Line({a[0]},{a[1]},{b[0]},{b[1]},.02,eMechanical2,Nil);')
emit("LabelText(0,19,'FPC 15015-0451 | 51 x 0.30 | TYPE A - SAME CONTACT FACE');")
emit("LabelText(0,17.5,'101.60 x 15.60 mm | R0.20 corners | 3.00 exposed contacts | 4.00 back stiffeners');")
emit("LabelText(0,-2,'Top Solder = coverlay apertures; Mechanical 2 = back stiffener boundaries. NO PASTE.');")
emit("LabelText(0,-3.5,'18 um Cu / 45 um PI+adhesive base / 50 um PI+adhesive coverlay. Contact 0.20 +/-0.03 mm.');")
emit(r'''
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));Rule:=I.FirstPCBObject;
 While Rule<>Nil Do Begin
  If Rule.RuleKind=eRule_Clearance Then Begin Clr:=Rule;Clr.Gap:=MMsToCoord(.09999);End;
  If Rule.RuleKind=eRule_MaxMinWidth Then Begin W:=Rule;W.MinWidth[eTopLayer]:=MMsToCoord(.09999);W.MaxWidth[eTopLayer]:=MMsToCoord(.30);W.FavoredWidth[eTopLayer]:=MMsToCoord(.20);End;
  Rule:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);B.RebuildPadCaches;
 Finally PCBServer.PostProcess;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 B.GraphicalView_ZoomOnRect(MMsToCoord(-2),MMsToCoord(-5),MMsToCoord(104),MMsToCoord(21));Mark('COMPLETE');Log.Free;
End;
''')
code = '\n'.join(p).replace('__H__',str(H)).replace('__TARGET__',str(target))
code = re.sub(r'(?<![\w])\.(\d)', r'0.\1', code)
(H/'BuildFPC.pas').write_text(code,encoding='ascii')
(H/'BuildFPC.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=BuildFPC.pas\n[Generic_ScriptingSystem]\nStartProcName=BuildFPC.pas>BuildFPC\n')
(OUT/'FPC_15015_0451.PrjPcb').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=FPC_15015_0451.PcbDoc\n')
print('Generated',H/'BuildFPC.pas')
